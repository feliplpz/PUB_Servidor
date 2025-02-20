from datetime import datetime
import bluetooth
import json
import os
import logging
import asyncio
import time
import secrets
from collections import deque
from threading import Lock
from flask import Flask, jsonify, render_template, Response
import matplotlib
import matplotlib.pyplot as plt
from io import BytesIO
from app_config import MAX_DATA_POINTS, MAX_MESSAGE_SIZE, SERVER_LOG_FILE_PATH

# Backend para evitar problemas em threads
matplotlib.use("Agg")

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Estruturas de dados thread-safe
data_lock = Lock()
data_t = deque(maxlen=MAX_DATA_POINTS)
data_x = deque(maxlen=MAX_DATA_POINTS)
data_y = deque(maxlen=MAX_DATA_POINTS)
data_z = deque(maxlen=MAX_DATA_POINTS)

# Inicializa o tempo inicial
start_time = time.time()

# Inicializa o Flask
app = Flask(__name__)


# Gera um ID aleatório para o dispositivo
def generate_device_id():
    return secrets.token_hex(4).upper()


# Função para logar mensagens
def log_message(message):
    logging.info(message)

    with open(f"{SERVER_LOG_FILE_PATH}", "a+") as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")


# Função para salvar os dados recebidos no CSV e atualizar os dados do gráfico
def save_data(device_id, device_name, message):
    try:
        accel_x = message.get("x", float("nan"))
        accel_y = message.get("y", float("nan"))
        accel_z = message.get("z", float("nan"))

        if not all(isinstance(v, (int, float)) for v in (accel_x, accel_y, accel_z)):
            return

        timestamp = datetime.now().isoformat()
        is_new_file = not os.path.exists("data.csv")

        with open("data.csv", "a") as f:
            if is_new_file:
                f.write("timestamp,device_id,device_name,accel_x,accel_y,accel_z\n")
            f.write(
                f"{timestamp},{device_id},{device_name},{accel_x},{accel_y},{accel_z}\n"
            )

        # Atualiza os dados para o gráfico
        with data_lock:
            current_time = time.time() - start_time
            data_t.append(current_time)
            data_x.append(accel_x)
            data_y.append(accel_y)
            data_z.append(accel_z)

    except Exception as e:
        log_message(f"Erro ao salvar dados: {e}")


# Rota principal - Renderiza o template HTML com o gráfico dinâmico
@app.route("/")
def index():
    return render_template("index.html")


# Rota para fornecer os dados em formato JSON (para Plotly)
@app.route("/get_data")
def get_data():
    with data_lock:
        return jsonify(
            {
                "time": list(data_t),
                "x": list(data_x),
                "y": list(data_y),
                "z": list(data_z),
            }
        )


# Função para gerar o gráfico
@app.route("/plot.png")
def plot():
    with data_lock:
        try:
            fig, axes = plt.subplots(3, 1, figsize=(10, 8))

            for ax, data, label, color in zip(
                axes,
                [data_x, data_y, data_z],
                ["X", "Y", "Z"],
                ["blue", "orange", "green"],
            ):
                ax.plot(data_t, data, color=color, label=f"Aceleração {label}")
                ax.legend()
                ax.set_xlabel("Tempo (s)")
                ax.set_ylabel("Aceleração (m/s²)")
                ax.grid(True)

            plt.tight_layout()
            img = BytesIO()
            plt.savefig(img, format="png")
            plt.close(fig)
            img.seek(0)
            return Response(img.getvalue(), mimetype="image/png")

        except Exception as e:
            log_message(f"Erro ao gerar gráfico: {e}")
            return Response(status=500)


# Função para receber todos os dados do socket
async def recv_all(socket, length):
    received_data = b""
    while len(received_data) < length:
        chunk = await asyncio.to_thread(socket.recv, length - len(received_data))
        if not chunk:
            break
        received_data += chunk
    return received_data


# Função para lidar com os clientes Bluetooth
async def handle_client(socket, device_id):
    try:
        device_name = bluetooth.lookup_name(socket.getpeername()[0]) or "Unknown"
        log_message(f"Conectado: {device_name}")

        while True:
            try:
                length_bytes = await recv_all(socket, 4)
                if not length_bytes or len(length_bytes) != 4:
                    log_message("Erro: Tamanho da mensagem inválido.")
                    break

                length = int.from_bytes(length_bytes, byteorder="big")
                if length <= 0 or length > MAX_MESSAGE_SIZE:
                    log_message(
                        f"Erro: Tamanho da mensagem fora do limite: {length} bytes"
                    )
                    continue

                message_bytes = await recv_all(socket, length)
                if not message_bytes or len(message_bytes) != length:
                    log_message("Erro: Mensagem incompleta ou corrompida.")
                    break

                try:
                    message = json.loads(message_bytes.decode("utf-8"))
                    if not isinstance(message, dict):
                        raise ValueError("Mensagem não é um JSON válido")
                except (json.JSONDecodeError, ValueError) as e:
                    log_message(f"Erro ao decodificar mensagem: {e}")
                    continue

                log_message(f"Dados recebidos de {device_name}: {message}")
                save_data(device_id, device_name, message)

            except (asyncio.TimeoutError, bluetooth.btcommon.BluetoothError) as e:
                log_message(f"Erro na conexão: {e}")
                break
            except Exception as e:
                log_message(f"Erro inesperado: {e}")
                break

    except Exception as e:
        log_message(f"Erro crítico: {e}")
    finally:
        try:
            socket.close()
            log_message(f"Conexão com {device_name} encerrada.")
        except:
            pass


# Servidor Bluetooth
async def bluetooth_server():
    server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_socket.bind(("", bluetooth.PORT_ANY))
    server_socket.listen(1)
    log_message(f"Servidor Bluetooth ativo na porta {server_socket.getsockname()[1]}")

    try:
        while True:
            client_sock, _ = await asyncio.to_thread(server_socket.accept)
            device_id = generate_device_id()
            asyncio.create_task(handle_client(client_sock, device_id))
    except asyncio.CancelledError:
        pass
    finally:
        server_socket.close()


# Inicia o Flask
def run_flask():
    app.run(host="0.0.0.0", port=5000, use_reloader=False, threaded=True)


# Função principal para rodar Bluetooth e Flask simultaneamente
async def main():
    await asyncio.gather(bluetooth_server(), asyncio.to_thread(run_flask))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_message("Servidor encerrado")
