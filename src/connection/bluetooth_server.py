import secrets
from datetime import datetime
from src.utils.logging import Logger
from src.connection.event_bus import EventBus
import os
import asyncio
import bluetooth
import json
from src.sensors.sensor_factory import SensorFactory


class DeviceManager:
    """Gerencia dispositivos conectados ao servidor"""

    # Dicionário para armazenar informações sobre dispositivos conectados
    devices = {}

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
        if device_id not in cls.devices:
            cls.devices[device_id] = {
                "name": device_name,
                "connected_at": datetime.now().isoformat(),
                "sensors": {},
            }
            Logger.log_message(f"Dispositivo registrado: {device_name} ({device_id})")
            
            # Publica evento de dispositivo conectado
            EventBus.publish("device_connected", {
                "device_id": device_id,
                "device_name": device_name,
                "connected_at": cls.devices[device_id]["connected_at"]
            })

    @classmethod
    def unregister_device(cls, device_id):
        """
        Remove um dispositivo do sistema

        Args:
            device_id (str): ID único do dispositivo
        """
        if device_id in cls.devices:
            device_name = cls.devices[device_id]["name"]
            del cls.devices[device_id]
            Logger.log_message(f"Dispositivo removido: {device_name} ({device_id})")
            
            # Publica evento de dispositivo desconectado
            EventBus.publish("device_disconnected", {
                "device_id": device_id,
                "device_name": device_name
            })

    @classmethod
    def get_all_devices(cls):
        """
        Retorna todos os dispositivos registrados

        Returns:
            dict: Dicionário com informações de todos os dispositivos
        """
        return cls.devices


class BluetoothConnection:
    """Gerencia conexões Bluetooth com dispositivos"""

    def __init__(self):
        """Inicializa o gerenciador de conexões Bluetooth"""

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
        device_name = "Unknown"
        buffer = b""
        
        try:
            device_name = bluetooth.lookup_name(socket.getpeername()[0]) or "Unknown"
            DeviceManager.register_device(device_id, device_name)
            Logger.log_message(f"Conectado: {device_name} (ID: {device_id})")

            # Cria um sensor de acelerômetro para o dispositivo
            accel_sensor = SensorFactory.create_sensor(
                "accelerometer", device_id, int(os.getenv("MAX_DATA_POINTS", 100))
            )

            # Cria um sensor de giroscópio para o dispositivo
            gyro_sensor = SensorFactory.create_sensor(
                "gyroscope", device_id, int(os.getenv("MAX_DATA_POINTS", 100))
            )

            # Registra os sensores no dispositivo
            DeviceManager.devices[device_id]["sensors"]["accelerometer"] = accel_sensor
            DeviceManager.devices[device_id]["sensors"]["gyroscope"] = gyro_sensor

            while True:
                try:
                    # Lê dados em chunks
                    data = await asyncio.to_thread(socket.recv, 1024)
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Processa todos os JSONs completos no buffer
                    while True:
                        # Procura início de JSON
                        start = buffer.find(b'{"type":')
                        if start == -1:
                            # Não achou início, mantém só os últimos 100 bytes
                            buffer = buffer[-100:] if len(buffer) > 100 else b""
                            break
                        
                        # Remove lixo antes do JSON
                        if start > 0:
                            buffer = buffer[start:]
                            start = 0
                        
                        # Procura fim do JSON (fecha chave)
                        brace_count = 0
                        end = -1
                        
                        for i in range(len(buffer)):
                            if buffer[i:i+1] == b'{':
                                brace_count += 1
                            elif buffer[i:i+1] == b'}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end = i + 1
                                    break
                        
                        if end == -1:
                            # JSON incompleto, aguarda mais dados
                            break
                        
                        # Extrai JSON completo
                        json_data = buffer[:end]
                        buffer = buffer[end:]
                        
                        # Tenta processar
                        try:
                            message = json.loads(json_data.decode('utf-8'))
                            if isinstance(message, dict) and "type" in message:
                                
                                sensor_type = message.get("type")
                                Logger.log_message(f"Dados recebidos {device_name}: {sensor_type}")
                                
                                if sensor_type == "accelerometer":
                                    if accel_sensor.process_data(message):
                                        accel_sensor.save_to_file(message, device_name, device_id)
                                elif sensor_type == "gyroscope":
                                    if gyro_sensor.process_data(message):
                                        gyro_sensor.save_to_file(message, device_name, device_id)
                        
                        except json.JSONDecodeError:
                            # JSON inválido, ignora
                            Logger.log_message(f" JSON inválido: {json_data[:50]}...")
                            continue

                except Exception as e:
                    Logger.log_message(f"Erro no loop: {e}")
                    break

        except Exception as e:
            Logger.log_message(f"Erro crítico: {e}")
        finally:
            try:
                
                socket.close()
                # Remove o dispositivo quando desconecta
                DeviceManager.unregister_device(device_id)
                Logger.log_message(f"Conexão com {device_name} encerrada.")
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