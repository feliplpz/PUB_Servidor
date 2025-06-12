import secrets
import re
import os
import asyncio
import bluetooth
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from src.utils.logging import Logger
from src.connection.event_bus import EventBus
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
                    Logger.log_message(f"Erro ao serializar sensor {sensor_type}: {e}")
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


class BluetoothMessageParser:
    """
    Parser especializado para mensagens JSON concorrentes em streams Bluetooth
    
    Esta classe implementa um algoritmo robusto para extrair mensagens JSON válidas
    de um buffer que pode conter múltiplas mensagens intercaladas, fragmentadas
    ou corrompidas vindas de sensores que transmitem concorrentemente.
    """
    
    def __init__(self, json_start_pattern: str, max_buffer_size: int, fallback_size: int):
        """
        Inicializa o parser com configurações específicas
        
        Args:
            json_start_pattern (str): Padrão que identifica o início de um JSON
            max_buffer_size (int): Tamanho máximo do buffer antes da limpeza
            fallback_size (int): Tamanho para manter em fallback durante limpeza
        """
        self.json_start_pattern = json_start_pattern.encode('utf-8')
        self.max_buffer_size = max_buffer_size
        self.fallback_size = fallback_size
        
        # Regex para identificar potenciais JSONs válidos
        # Padrão flexível que aceita variações de formatação
        self.json_regex = re.compile(
            rb'\{\s*"type"\s*:\s*"[^"]+"\s*,.*?\}',
            re.DOTALL
        )
        
    def extract_complete_jsons(self, buffer: bytes) -> Tuple[List[bytes], bytes]:
        """
        Extrai todas as mensagens JSON completas de um buffer
        
        Algoritmo:
        1. Busca por padrões que iniciam JSONs válidos
        2. Para cada padrão encontrado, calcula o fim usando balanceamento de chaves
        3. Valida se o JSON está sintaticamente correto
        4. Retorna JSONs válidos e o buffer restante
        
        Args:
            buffer (bytes): Buffer contendo dados brutos possivelmente intercalados
            
        Returns:
            Tuple[List[bytes], bytes]: Lista de JSONs válidos e buffer restante
        """
        complete_jsons = []
        
        # Primeira tentativa: usar regex para encontrar padrões válidos
        matches = list(self.json_regex.finditer(buffer))
        
        if matches:
            last_end = 0
            for match in matches:
                json_candidate = match.group()
                
                # Valida se é um JSON sintaticamente correto
                if self._is_valid_json(json_candidate):
                    complete_jsons.append(json_candidate)
                    last_end = match.end()
            
            # Remove dados processados do buffer
            remaining_buffer = buffer[last_end:] if last_end > 0 else buffer
        else:
            # Fallback: busca manual por padrões
            complete_jsons, remaining_buffer = self._manual_json_extraction(buffer)
        
        return complete_jsons, remaining_buffer
    
    def _manual_json_extraction(self, buffer: bytes) -> Tuple[List[bytes], bytes]:
        """
        Extração manual de JSONs quando regex falha
        
        Usa algoritmo de balanceamento de chaves respeitando strings
        """
        complete_jsons = []
        start = 0
        
        while True:
            # Procura início de JSON
            json_start = buffer.find(self.json_start_pattern, start)
            if json_start == -1:
                break
            
            # Encontra o fim usando balanceamento de chaves
            json_end = self._find_json_end(buffer, json_start)
            if json_end == -1:
                # JSON incompleto, mantém no buffer
                break
            
            # Extrai candidato
            json_candidate = buffer[json_start:json_end + 1]
            
            # Valida se é JSON válido
            if self._is_valid_json(json_candidate):
                complete_jsons.append(json_candidate)
            
            start = json_end + 1
        
        # Retorna buffer restante a partir do último ponto processado
        remaining_buffer = buffer[start:] if start < len(buffer) else b""
        
        return complete_jsons, remaining_buffer
    
    def _find_json_end(self, buffer: bytes, start: int) -> int:
        """
        Encontra o fim de um JSON usando balanceamento de chaves
        
        Considera strings e caracteres de escape para evitar falsos positivos
        """
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start, len(buffer)):
            byte_char = chr(buffer[i]) if buffer[i] < 128 else None
            
            if escape_next:
                escape_next = False
                continue
            
            if byte_char == '\\':
                escape_next = True
                continue
            
            if byte_char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if byte_char == '{':
                    brace_count += 1
                elif byte_char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return i
        
        return -1  # JSON incompleto
    
    def _is_valid_json(self, json_bytes: bytes) -> bool:
        """
        Valida se os bytes representam um JSON sintaticamente válido
        """
        try:
            data = json.loads(json_bytes.decode('utf-8'))
            # Verifica se tem estrutura esperada
            return isinstance(data, dict) and "type" in data
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return False
    
    def cleanup_buffer(self, buffer: bytes) -> bytes:
        """
        Limpa buffer mantendo dados potencialmente úteis
        
        Estratégia:
        1. Procura pelo último JSON válido completo
        2. Mantém dados após esse ponto
        3. Se não encontrar, mantém apenas os últimos bytes como fallback
        """
        if len(buffer) <= self.max_buffer_size:
            return buffer
        
        # Procura último padrão de fim de JSON
        last_brace = buffer.rfind(b'}')
        
        if last_brace != -1 and last_brace < len(buffer) - 1:
            # Mantém dados após o último JSON completo
            return buffer[last_brace + 1:]
        else:
            # Fallback: mantém apenas os últimos bytes
            return buffer[-self.fallback_size:]


class BluetoothConnection:
    """
    Gerencia conexões Bluetooth com suporte a múltiplos sensores concorrentes
    
    Esta implementação resolve o problema de message interleaving que ocorre
    quando múltiplos sensores enviam dados simultaneamente através do mesmo
    socket Bluetooth, causando fragmentação e sobreposição de mensagens.
    """

    def __init__(self):
        """
        Inicializa o gerenciador de conexões Bluetooth com configurações do ambiente
        """
        # Configurações de buffer e rede carregadas do .env
        self.recv_chunk_size = int(os.getenv("BT_RECV_CHUNK_SIZE", 1024))
        self.max_buffer_size = int(os.getenv("BT_MAX_BUFFER_SIZE", 8192))
        self.buffer_cleanup_threshold = int(os.getenv("BT_BUFFER_CLEANUP_THRESHOLD", 4096))
        self.buffer_fallback_size = int(os.getenv("BT_BUFFER_FALLBACK_SIZE", 256))
        self.max_message_size = int(os.getenv("BT_MAX_MESSAGE_SIZE", 2048))
        self.connection_timeout = int(os.getenv("BT_CONNECTION_TIMEOUT", 30))
        self.json_start_pattern = os.getenv("BT_JSON_START_PATTERN", '{"type"')
        
        # Inicializa parser especializado
        self.message_parser = BluetoothMessageParser(
            json_start_pattern=self.json_start_pattern,
            max_buffer_size=self.max_buffer_size,
            fallback_size=self.buffer_fallback_size
        )
        
        Logger.log_message(f"BluetoothConnection inicializado com buffer_size={self.max_buffer_size}, "
                          f"chunk_size={self.recv_chunk_size}, timeout={self.connection_timeout}s")

    async def handle_client(self, socket, device_id: str):
        """
        Gerencia conexão de cliente Bluetooth com suporte a múltiplos sensores
        
        Esta implementação resolve problemas de:
        - Message interleaving (mensagens intercaladas)
        - Fragmentação de dados
        - Buffer overflow
        - Parsing de JSON concorrente
        
        Args:
            socket (BluetoothSocket): Socket do cliente conectado
            device_id (str): ID único do dispositivo
        """
        device_name = "Unknown"
        buffer = b""
        message_count = 0
        error_count = 0
        
        try:
            # Resolve nome do dispositivo
            device_name = bluetooth.lookup_name(socket.getpeername()[0]) or "Unknown"
            DeviceManager.register_device(device_id, device_name)
            Logger.log_message(f"Conectado: {device_name} (ID: {device_id})")

            # Inicializa sensores
            sensors = await self._initialize_sensors(device_id)
            DeviceManager.devices[device_id]["sensors"].update(sensors)

            # Loop principal de recepção de dados
            while True:
                try:
                    # Recebe chunk de dados
                    data = await asyncio.wait_for(
                        asyncio.to_thread(socket.recv, self.recv_chunk_size),
                        timeout=self.connection_timeout
                    )
                    
                    if not data:
                        Logger.log_message(f"Conexão fechada pelo cliente: {device_name}")
                        break
                    
                    # Adiciona ao buffer
                    buffer += data
                    
                    # Extrai e processa mensagens completas
                    complete_jsons, buffer = self.message_parser.extract_complete_jsons(buffer)
                    
                    # Processa cada mensagem encontrada
                    for json_data in complete_jsons:
                        success = await self._process_sensor_message(
                            json_data, sensors, device_name, device_id
                        )
                        if success:
                            message_count += 1
                        else:
                            error_count += 1
                    
                    # Gerenciamento de buffer
                    if len(buffer) > self.buffer_cleanup_threshold:
                        old_size = len(buffer)
                        buffer = self.message_parser.cleanup_buffer(buffer)
                        Logger.log_message(f"Buffer limpo: {old_size} -> {len(buffer)} bytes")
                    
                except asyncio.TimeoutError:
                    Logger.log_message(f"Timeout na conexão com {device_name}")
                    break
                except bluetooth.btcommon.BluetoothError as e:
                    Logger.log_message(f"Erro Bluetooth com {device_name}: {e}")
                    break
                except Exception as e:
                    error_count += 1
                    Logger.log_message(f"Erro no loop de {device_name}: {e}")
                    
                    # Se muitos erros, interrompe conexão
                    if error_count > 10:
                        Logger.log_message(f"Muitos erros ({error_count}), encerrando {device_name}")
                        break

        except Exception as e:
            Logger.log_message(f"Erro crítico com {device_name}: {e}")
        finally:
            await self._cleanup_connection(socket, device_id, device_name, message_count, error_count)

    async def _initialize_sensors(self, device_id: str) -> Dict:
        """
        Inicializa sensores para o dispositivo
        
        Returns:
            Dict: Dicionário com sensores inicializados
        """
        max_data_points = int(os.getenv("MAX_DATA_POINTS", 100))
        
        sensors = {
            "accelerometer": SensorFactory.create_sensor("accelerometer", device_id, max_data_points),
            "gyroscope": SensorFactory.create_sensor("gyroscope", device_id, max_data_points)
        }
        
        Logger.log_message(f"Sensores inicializados para {device_id}: {list(sensors.keys())}")
        return sensors

    async def _process_sensor_message(self, json_data: bytes, sensors: Dict, 
                                     device_name: str, device_id: str) -> bool:
        """
        Processa uma mensagem individual de sensor
        
        Args:
            json_data (bytes): Dados JSON da mensagem
            sensors (Dict): Dicionário de sensores disponíveis
            device_name (str): Nome do dispositivo
            device_id (str): ID do dispositivo
            
        Returns:
            bool: True se processado com sucesso
        """
        try:
            message = json.loads(json_data.decode('utf-8'))
            
            if not isinstance(message, dict) or "type" not in message:
                Logger.log_message(f"Mensagem inválida de {device_name}: estrutura incorreta")
                return False
            
            sensor_type = message.get("type")
            
            if sensor_type not in sensors:
                Logger.log_message(f"Tipo de sensor desconhecido de {device_name}: {sensor_type}")
                return False
            
            sensor = sensors[sensor_type]
            
            # Processa e salva dados
            if sensor.process_data(message):
                sensor.save_to_file(message, device_name, device_id)
                return True
            else:
                Logger.log_message(f"Falha ao processar dados de {sensor_type} de {device_name}")
                return False
                
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            Logger.log_message(f"Erro de decodificação de {device_name}: {e}")
            return False
        except Exception as e:
            Logger.log_message(f"Erro ao processar mensagem de {device_name}: {e}")
            return False

    async def _cleanup_connection(self, socket, device_id: str, device_name: str, 
                                 message_count: int, error_count: int):
        """
        Limpa recursos da conexão
        """
        try:
            socket.close()
            DeviceManager.unregister_device(device_id)
            Logger.log_message(f"Conexão com {device_name} (ID: {device_id}) encerrada. "
                              f"Stats: {message_count} mensagens, {error_count} erros")
        except Exception as e:
            Logger.log_message(f"Erro na limpeza de {device_name}: {e}")

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
                client_sock, address = await asyncio.to_thread(server_socket.accept)
                device_id = DeviceManager.generate_device_id()
                Logger.log_message(f"Nova conexão de {address} -> ID: {device_id}")
                asyncio.create_task(self.handle_client(client_sock, device_id))
        except asyncio.CancelledError:
            Logger.log_message("Servidor Bluetooth cancelado")
        except Exception as e:
            Logger.log_message(f"Erro no servidor Bluetooth: {e}")
        finally:
            server_socket.close()
            Logger.log_message("Servidor Bluetooth encerrado")