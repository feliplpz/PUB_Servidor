import secrets
from datetime import datetime
from src.utils.logging import Logger
from src.connection.event_bus import EventBus
import os
import asyncio
import bluetooth
import json
import time
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

    @classmethod
    def get_serializable_devices(cls):
        """
        Retorna versão serializável dos dispositivos (sem objetos de sensores)
        
        Returns:
            dict: Dicionário com informações serializáveis dos dispositivos
        """
        serializable_devices = {}
        current_time = time.time()
        
        for device_id, device_info in cls.devices.items():
            # Processa informações dos sensores de forma serializável
            sensor_summary = {}
            
            for sensor_type, sensor_obj in device_info.get("sensors", {}).items():
                try:
                    # Obtém dados do sensor
                    data = sensor_obj.get_data()
                    data_points = len(data.get("time", []))
                    
                    # Calcula se tem dados recentes
                    has_recent_data = False
                    time_since_update = None
                    
                    if data_points > 0 and data.get("time"):
                        last_relative_time = data["time"][-1]
                        sensor_start_time = getattr(sensor_obj, 'start_time', current_time)
                        last_data_time = sensor_start_time + last_relative_time
                        time_since_update = current_time - last_data_time
                        has_recent_data = time_since_update < 5.0  # 5 segundos
                    
                    sensor_summary[sensor_type] = {
                        "type": sensor_type,
                        "data_points": data_points,
                        "has_data": data_points > 0,
                        "has_recent_data": has_recent_data,
                        "time_since_update": time_since_update,
                        "last_values": {
                            "x": data.get("x", [None])[-1] if data.get("x") else None,
                            "y": data.get("y", [None])[-1] if data.get("y") else None,
                            "z": data.get("z", [None])[-1] if data.get("z") else None,
                        } if data_points > 0 else None
                    }
                    
                except Exception as e:
                    Logger.log_message(f" Erro ao serializar sensor {sensor_type}: {e}")
                    sensor_summary[sensor_type] = {
                        "type": sensor_type,
                        "data_points": 0,
                        "has_data": False,
                        "has_recent_data": False,
                        "error": str(e)
                    }
            
            # Conta sensores ativos
            active_sensors = sum(1 for s in sensor_summary.values() if s.get("has_recent_data", False))
            
            serializable_devices[device_id] = {
                "name": device_info["name"],
                "connected_at": device_info["connected_at"],
                "sensors": sensor_summary,
                "sensor_count": len(sensor_summary),
                "active_sensor_count": active_sensors,
                "last_updated": current_time
            }
        
        return serializable_devices


class BluetoothConnection:
    """Gerencia conexões Bluetooth com dispositivos"""

    def __init__(self):
        """Inicializa o gerenciador de conexões Bluetooth"""

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
                            Logger.log_message(f"JSON inválido: {json_data[:50]}...")
                            continue

                except Exception as e:
                    Logger.log_message(f"Erro no loop: {e}")
                    break

        except Exception as e:
            Logger.log_message(f"❌ Erro crítico ❌ : {e}")
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