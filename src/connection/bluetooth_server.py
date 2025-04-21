import secrets
from datetime import datetime
from src.utils.logging import Logger
import os
import asyncio
import bluetooth
import json
from src.sensors.sensor_factory import SensorFactory


class DeviceManager:
    """Gerencia dispositivos conectados ao servidor"""

    # Dicionário para armazenar informações sobre dispositivos conectados
    _devices = {}

    @staticmethod
    def generate_device_id():
        """
        Gera um ID único para um novo dispositivo

        Returns:
            str: ID do dispositivo no formato hexadecimal
        """
        return secrets.token_hex(4).upper()

    @classmethod
    def register_device(cls, device_id, device_name):
        """
        Registra um novo dispositivo no sistema

        Args:
            device_id (str): ID único do dispositivo
            device_name (str): Nome do dispositivo Bluetooth
        """
        if device_id not in cls._devices:
            cls._devices[device_id] = {
                "name": device_name,
                "connected_at": datetime.now().isoformat(),
                "sensors": {},
            }
            Logger.log_message(f"Dispositivo registrado: {device_name} ({device_id})")

    @classmethod
    def get_all_devices(cls):
        """
        Retorna todos os dispositivos registrados

        Returns:
            dict: Dicionário com informações de todos os dispositivos
        """
        return cls._devices


class BluetoothConnection:
    """Gerencia conexões Bluetooth com dispositivos"""

    def __init__(self):
        """Inicializa o gerenciador de conexões Bluetooth"""
        self.max_message_size = int(os.getenv("MAX_MESSAGE_SIZE", 4096))

    async def recv_all(self, socket, length):
        """
        Recebe todos os dados do socket até o comprimento especificado

        Args:
            socket (BluetoothSocket): Socket Bluetooth
            length (int): Comprimento dos dados a serem recebidos

        Returns:
            bytes: Dados recebidos
        """
        received_data = b""
        while len(received_data) < length:
            chunk = await asyncio.to_thread(socket.recv, length - len(received_data))
            if not chunk:
                break
            received_data += chunk
        return received_data

    async def handle_client(self, socket, device_id):
        """
        Lida com conexões de clientes Bluetooth

        Args:
            socket (BluetoothSocket): Socket do cliente conectado
            device_id (str): ID do dispositivo
        """
        try:
            device_name = bluetooth.lookup_name(socket.getpeername()[0]) or "Unknown"
            DeviceManager.register_device(device_id, device_name)
            Logger.log_message(f"Conectado: {device_name} (ID: {device_id})")

            # Cria um sensor de acelerômetro para o dispositivo
            accel_sensor = SensorFactory.create_sensor(
                "accelerometer", device_id, int(os.getenv("MAX_DATA_POINTS", 100))
            )

            # Registra o sensor no dispositivo
            DeviceManager._devices[device_id]["sensors"]["accelerometer"] = accel_sensor

            while True:
                try:
                    # Recebe o tamanho da mensagem (4 bytes)
                    length_bytes = await self.recv_all(socket, 4)
                    if not length_bytes or len(length_bytes) != 4:
                        Logger.log_message("Erro: Tamanho da mensagem inválido.")
                        break

                    # Converte para inteiro
                    length = int.from_bytes(length_bytes, byteorder="big")
                    if length <= 0 or length > self.max_message_size:
                        Logger.log_message(
                            f"Erro: Tamanho da mensagem fora do limite: {length} bytes"
                        )
                        continue

                    # Recebe a mensagem completa
                    message_bytes = await self.recv_all(socket, length)
                    if not message_bytes or len(message_bytes) != length:
                        Logger.log_message("Erro: Mensagem incompleta ou corrompida.")
                        break

                    # Decodifica a mensagem JSON
                    try:
                        message = json.loads(message_bytes.decode("utf-8"))
                        if not isinstance(message, dict):
                            raise ValueError("Mensagem não é um JSON válido")
                    except (json.JSONDecodeError, ValueError) as e:
                        Logger.log_message(f"Erro ao decodificar mensagem: {e}")
                        continue

                    Logger.log_message(f"Dados recebidos de {device_name}: {message}")

                    # Processa e salva os dados do acelerômetro
                    if accel_sensor.process_data(message):
                        accel_sensor.save_to_file(message, device_name, device_id)

                except (asyncio.TimeoutError, bluetooth.btcommon.BluetoothError) as e:
                    Logger.log_message(f"Erro na conexão: {e}")
                    break
                except Exception as e:
                    Logger.log_message(f"Erro inesperado: {e}")
                    break

        except Exception as e:
            Logger.log_message(f"Erro crítico: {e}")
        finally:
            try:
                socket.close()
                Logger.log_message(
                    f"Conexão com {device_name} (ID: {device_id}) encerrada."
                )
            except:
                pass

    async def start_server(self):
        """
        Inicia o servidor Bluetooth

        Returns:
            None
        """
        server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_socket.bind(("", bluetooth.PORT_ANY))
        server_socket.listen(1)
        port = server_socket.getsockname()[1]
        Logger.log_message(f"Servidor Bluetooth ativo na porta {port}")

        try:
            while True:
                client_sock, _ = await asyncio.to_thread(server_socket.accept)
                device_id = DeviceManager.generate_device_id()
                asyncio.create_task(self.handle_client(client_sock, device_id))
        except asyncio.CancelledError:
            pass
        finally:
            server_socket.close()
