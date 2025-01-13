import bluetooth
import json
import os
import psutil
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import random
import string

# Configuração básica de log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

MAX_MESSAGE_SIZE = 1024  # 1 KiB
MAX_WORKERS = 20  # Ajuste para maior número de conexões simultâneas
CONNECTION_TIMEOUT = 60  # Timeout de 60 segundos para inatividade no servidor
RECEIVE_TIMEOUT = 10  # Timeout de 10 segundos para operações de leitura de socket

# Caminho para o arquivo de log TXT
TXT_LOG_FILE = 'log_messages.txt'

# Função para gerar um ID aleatório para o dispositivo
def generate_device_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Função para identificar o nome do dispositivo Bluetooth
def get_device_name(socket):
    try:
        return bluetooth.lookup_name(socket.getpeername()[0])  # Obtém o nome do dispositivo pelo IP
    except bluetooth.btcommon.BluetoothError:
        return "Unknown"

# Função de log com escrita em arquivo TXT
def log_message(message):
    logging.info(message)

    # Registra também no arquivo de texto
    try:
        with open(TXT_LOG_FILE, mode='a', encoding='utf-8') as file:
            file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        logging.error(f"Erro ao escrever no arquivo TXT: {e}")

# Função de monitoramento de uso de memória
def monitor_and_cleanup():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    if mem_info.rss / 1024 / 1024 > 100:  # 100 MB
        log_message("Uso excessivo de memória detectado. Limpando recursos.")

# Função para receber dados completos com timeout
async def recv_all(socket, length):
    data = b''
    try:
        while len(data) < length:
            more = await asyncio.wait_for(asyncio.to_thread(socket.recv, length - len(data)), timeout=RECEIVE_TIMEOUT)
            if not more:
                return None
            data += more
        return data
    except asyncio.TimeoutError:
        log_message("Timeout excedido durante a leitura dos dados.")
        return None
    except bluetooth.btcommon.BluetoothError as e:
        log_message(f"Erro ao receber dados: {e}")
        return None

# Função para lidar com a conexão
async def handle_connection(socket, info, device_id):
    try:
        device_name = get_device_name(socket)
        log_message(f"Conexão aceita de {device_name} ({device_id})")

        last_activity_time = time.time()

        while True:
            socket.settimeout(10)  # Timeout de 10 segundos para o socket

            try:
                length_bytes = await recv_all(socket, 4)
                if not length_bytes:
                    log_message("Erro: Não conseguiu receber 4 bytes para o comprimento da mensagem.")
                    break

                length = int.from_bytes(length_bytes, byteorder='big')
                if length <= 0:
                    log_message("Erro: Comprimento inválido recebido.")
                    break

                if length > MAX_MESSAGE_SIZE:
                    log_message(f"Erro: Mensagem muito grande ({length} bytes). Ignorando mensagem.")
                    socket.recv(length)  # Descarta os dados
                    continue

                message_bytes = await recv_all(socket, length)
                if not message_bytes:
                    log_message("Erro: Não conseguiu receber a mensagem completa.")
                    break

                message_json = str(message_bytes, 'utf-8')
                message = json.loads(message_json)
                log_message(f"Mensagem recebida: {message}")

                # Monitora o uso de memória
                monitor_and_cleanup()

                # Atualiza o tempo da última atividade
                last_activity_time = time.time()

            except bluetooth.btcommon.BluetoothError as bt_err:
                log_message(f"Erro Bluetooth: {bt_err}")
                break
            except asyncio.TimeoutError:
                log_message(f"Conexão com {info} ({device_name}) excedeu o tempo limite.")
                break
            except Exception as e:
                log_message(f"Erro inesperado: {e}")
                break

        socket.close()
        log_message(f"Conexão com {info} ({device_name}) encerrada.")

    finally:
        socket.close()

# Função para iniciar o servidor
async def start_server():
    server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_socket.bind(('', bluetooth.PORT_ANY))
    server_socket.listen(1)

    name = server_socket.getsockname()[1]
    log_message(f"Servidor iniciado no canal {name}")
    log_message("Aguardando conexões...")

    last_connection_time = time.time()
    last_activity_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            try:
                socket, info = await asyncio.to_thread(server_socket.accept)
                device_id = generate_device_id()  # Gerando um ID único para o dispositivo
                log_message(f"Nova conexão de {info}")

                # Inicia uma nova tarefa para lidar com a conexão
                asyncio.create_task(handle_connection(socket, info, device_id))

                # Atualiza o tempo da última conexão
                last_connection_time = time.time()
                last_activity_time = time.time()

            except Exception as e:
                log_message(f"Erro ao aceitar conexão: {e}")

            # Verifica se o servidor deve ser fechado devido a inatividade
            if time.time() - last_connection_time > CONNECTION_TIMEOUT:
                log_message(f"Sem novas conexões por {CONNECTION_TIMEOUT} segundos. Fechando o servidor.")
                break

            # Verifica se o servidor deve ser fechado devido a inatividade nas conexões ativas
            if time.time() - last_activity_time > CONNECTION_TIMEOUT:
                log_message(f"Sem atividade nas conexões por {CONNECTION_TIMEOUT} segundos. Fechando o servidor.")
                break

# Função principal
async def main():
    try:
        await start_server()
    except KeyboardInterrupt:
        log_message("Servidor interrompido.")
    finally:
        log_message("Servidor encerrado.")

if __name__ == '__main__':
    asyncio.run(main())
