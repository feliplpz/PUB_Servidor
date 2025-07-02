import asyncio
import json
import time
from typing import Dict, List, Set
from fastapi import WebSocket
from src.utils.logging import Logger
from src.connection.event_bus import EventBus

class WebSocketManager:
    """Gerencia conexões WebSocket e distribuição de dados de forma mais reativa"""
    
    def __init__(self):
        """Inicializa o gerenciador WebSocket"""
        # Conexões para sensores específicos
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Conexões para lista de dispositivos
        self.device_list_connections: Set[WebSocket] = set()
        
        # Estatísticas de conexão
        self.connection_stats = {
            "total_sensor_connections": 0,
            "total_device_list_connections": 0,
            "messages_sent": 0,
            "last_device_update": None,
            "failed_sends": 0
        }
        
        # Cache para evitar spam de atualizações
        self.last_device_list_update = None
        self.device_update_debounce_time = 0.5  # 500ms debounce
        
        # Inscreve-se nos eventos
        EventBus.subscribe("sensor_update", self.handle_sensor_update)
        EventBus.subscribe("device_connected", self.handle_device_connected)
        EventBus.subscribe("device_disconnected", self.handle_device_disconnected)
        
        Logger.log_message("WebSocketManager inicializado com configuração reativa")
    
    async def connect(self, websocket: WebSocket, device_id: str, sensor_type: str):
        """
        Conecta um novo WebSocket para sensor específico
        
        Args:
            websocket (WebSocket): Conexão WebSocket
            device_id (str): ID do dispositivo
            sensor_type (str): Tipo de sensor
        """
        await websocket.accept()
        # print(f"✅ WEBSOCKET ACEITO: {device_id}_{sensor_type}")
        
        client_key = f"{device_id}_{sensor_type}"
        if client_key not in self.active_connections:
            self.active_connections[client_key] = []
        
        self.active_connections[client_key].append(websocket)
        self.connection_stats["total_sensor_connections"] += 1
        
        Logger.log_message(f"WebSocket conectado: {client_key} (total: {len(self.active_connections[client_key])})")
        
        # Envia dados históricos imediatamente
        await self.send_historical_data(websocket, device_id, sensor_type)
        
        # Envia estatísticas de conexão
        await self.send_connection_stats(websocket)
    
    async def connect_device_list(self, websocket: WebSocket):
        """
        Conecta um WebSocket para receber atualizações da lista de dispositivos
        
        Args:
            websocket (WebSocket): Conexão WebSocket
        """
        await websocket.accept()
        self.device_list_connections.add(websocket)
        self.connection_stats["total_device_list_connections"] += 1
        
        Logger.log_message(f"WebSocket conectado para lista de dispositivos (total: {len(self.device_list_connections)})")
        
        # Envia lista inicial imediatamente
        await self.send_device_list_update(websocket)
    
    def disconnect(self, websocket: WebSocket, device_id: str, sensor_type: str):
        """
        Desconecta um WebSocket de sensor específico
        
        Args:
            websocket (WebSocket): Conexão WebSocket
            device_id (str): ID do dispositivo
            sensor_type (str): Tipo de sensor
        """
        client_key = f"{device_id}_{sensor_type}"
        
        if client_key in self.active_connections:
            if websocket in self.active_connections[client_key]:
                self.active_connections[client_key].remove(websocket)
                self.connection_stats["total_sensor_connections"] -= 1
            
            # Remove a chave se não há mais conexões
            if not self.active_connections[client_key]:
                del self.active_connections[client_key]
        
        Logger.log_message(f"WebSocket desconectado: {client_key}")
    
    def disconnect_device_list(self, websocket: WebSocket):
        """
        Desconecta um WebSocket da lista de dispositivos
        
        Args:
            websocket (WebSocket): Conexão WebSocket
        """
        self.device_list_connections.discard(websocket)
        self.connection_stats["total_device_list_connections"] -= 1
        Logger.log_message(f"WebSocket da lista de dispositivos desconectado (restam: {len(self.device_list_connections)})")
    
    async def send_historical_data(self, websocket: WebSocket, device_id: str, sensor_type: str):
        """
        Envia dados históricos quando conecta
        
        Args:
            websocket (WebSocket): Conexão WebSocket
            device_id (str): ID do dispositivo
            sensor_type (str): Tipo de sensor
        """
        try:
            from src.connection.bluetooth_server import DeviceManager
            
            devices = DeviceManager.get_all_devices()
            if device_id in devices and sensor_type in devices[device_id]["sensors"]:
                sensor = devices[device_id]["sensors"][sensor_type]
                data = sensor.get_data()
                
                # Adiciona metadados aos dados históricos
                current_time = time.time()
                data_points = len(data.get("time", []))
                
                message = {
                    "type": "historical",
                    "device_id": device_id,
                    "sensor_type": sensor_type,
                    "data": data,
                    "metadata": {
                        "data_points": data_points,
                        "timestamp": current_time,
                        "has_data": data_points > 0
                    }
                }
                
                await websocket.send_text(json.dumps(message))
                self.connection_stats["messages_sent"] += 1
            else:
                # Envia mensagem indicando que não há dados
                await websocket.send_text(json.dumps({
                    "type": "no_data",
                    "device_id": device_id,
                    "sensor_type": sensor_type,
                    "message": "Sensor não encontrado ou sem dados"
                }))
                
        except Exception as e:
            Logger.log_message(f"Erro ao enviar dados históricos: {e}")
            self.connection_stats["failed_sends"] += 1
    
    async def send_connection_stats(self, websocket: WebSocket):
        """
        Envia estatísticas de conexão para o cliente
        
        Args:
            websocket (WebSocket): Conexão WebSocket
        """
        try:
            stats_message = {
                "type": "connection_stats",
                "stats": self.connection_stats.copy(),
                "timestamp": time.time()
            }
            await websocket.send_text(json.dumps(stats_message))
        except Exception as e:
            Logger.log_message(f"Erro ao enviar estatísticas: {e}")
    
    async def send_device_list_update(self, websocket: WebSocket = None):
        """
        Envia atualização da lista de dispositivos com debounce
        
        Args:
            websocket (WebSocket, optional): WebSocket específico. Se None, envia para todos.
        """
        current_time = time.time()
        
        # Implementa debounce para evitar spam de atualizações
        if (self.last_device_list_update and 
            current_time - self.last_device_list_update < self.device_update_debounce_time):
            Logger.log_message("Atualização de dispositivos em debounce, pulando...")
            return
        
        self.last_device_list_update = current_time
        
        try:
            from src.connection.bluetooth_server import DeviceManager
            
            # USA VERSÃO SERIALIZÁVEL em vez da versão com objetos
            devices = DeviceManager.get_serializable_devices()
            
            # Adiciona metadados à mensagem
            message = {
                "type": "device_list_update",
                "devices": devices,
                "metadata": {
                    "device_count": len(devices),
                    "timestamp": current_time,
                    "active_connections": len(self.device_list_connections)
                }
            }
            
            message_json = json.dumps(message)
            
            if websocket:
                # Envia para um WebSocket específico
                await websocket.send_text(message_json)
                self.connection_stats["messages_sent"] += 1
                Logger.log_message(f"Lista de dispositivos enviada para cliente específico ({len(devices)} dispositivos)")
            else:
                # Envia para todos os WebSockets da lista de dispositivos
                failed_connections = []
                sent_count = 0
                
                for ws in self.device_list_connections.copy():
                    try:
                        await ws.send_text(message_json)
                        sent_count += 1
                        self.connection_stats["messages_sent"] += 1
                    except Exception as e:
                        Logger.log_message(f"Erro ao enviar lista de dispositivos: {e}")
                        failed_connections.append(ws)
                        self.connection_stats["failed_sends"] += 1
                
                # Remove conexões que falharam
                for ws in failed_connections:
                    self.device_list_connections.discard(ws)
                    self.connection_stats["total_device_list_connections"] -= 1
                
            self.connection_stats["last_device_update"] = current_time
                
        except Exception as e:
            Logger.log_message(f"Erro ao enviar lista de dispositivos: {e}")
            self.connection_stats["failed_sends"] += 1
    
    def handle_sensor_update(self, event_data):
        """
        Manipula eventos de atualização de sensores (callback do Event Bus)
        
        Args:
            event_data (dict): Dados do evento contendo device_id, sensor_type e data
        """
        try:
            device_id = event_data["device_id"]
            sensor_type = event_data["sensor_type"]
            data = event_data["data"]
            
            # Criar task para enviar dados com prioridade alta
            task = asyncio.create_task(
                self.send_sensor_update(device_id, sensor_type, data)
            )
            
            # Adiciona callback para logging de erros
            task.add_done_callback(lambda t: self._handle_task_result(t, f"sensor_update_{device_id}_{sensor_type}"))
            
        except Exception as e:
            Logger.log_message(f"Erro ao processar atualização de sensor: {e}")
    
    def handle_device_connected(self, event_data):
        """
        Manipula eventos de conexão de dispositivos
        
        Args:
            event_data (dict): Dados do evento
        """
        try:
            device_name = event_data.get('device_name', 'Unknown')
            Logger.log_message(f"Dispositivo conectado: {device_name}")
            
            # Envia atualização imediata da lista de dispositivos
            task = asyncio.create_task(self.send_device_list_update())
            task.add_done_callback(lambda t: self._handle_task_result(t, "device_connected"))
            
        except Exception as e:
            Logger.log_message(f"Erro ao processar conexão de dispositivo: {e}")
    
    def handle_device_disconnected(self, event_data):
        """
        Manipula eventos de desconexão de dispositivos
        
        Args:
            event_data (dict): Dados do evento
        """
        try:
            device_name = event_data.get('device_name', 'Unknown')
            Logger.log_message(f" Dispositivo desconectado: {device_name}")
            
            # Envia atualização imediata da lista de dispositivos
            task = asyncio.create_task(self.send_device_list_update())
            task.add_done_callback(lambda t: self._handle_task_result(t, "device_disconnected"))
            
        except Exception as e:
            Logger.log_message(f"Erro ao processar desconexão de dispositivo: {e}")
    
    def _handle_task_result(self, task, context):
        """
        Manipula resultado de tasks assíncronas
        
        Args:
            task: Task concluída
            context: Contexto para logging
        """
        try:
            if task.exception():
                Logger.log_message(f"Erro em task {context}: {task.exception()}")
                self.connection_stats["failed_sends"] += 1
        except Exception:
            pass  # Ignora erros de logging
    
    async def send_sensor_update(self, device_id: str, sensor_type: str, data: dict):
        """
        Envia atualização de dados de sensor para clientes WebSocket
        
        Args:
            device_id (str): ID do dispositivo
            sensor_type (str): Tipo de sensor
            data (dict): Dados do sensor
        """
        client_key = f"{device_id}_{sensor_type}"
        
        if client_key not in self.active_connections:
            # Ninguém conectado neste sensor específico
            return
        
        current_time = time.time()
        data_points = len(data.get("time", []))
        
        # Prepara mensagem com metadados
        message = {
            "type": "update",
            "device_id": device_id,
            "sensor_type": sensor_type,
            "data": data,
            "metadata": {
                "data_points": data_points,
                "timestamp": current_time,
                "latest_value": {
                    "x": data.get("x", [None])[-1] if data.get("x") else None,
                    "y": data.get("y", [None])[-1] if data.get("y") else None,
                    "z": data.get("z", [None])[-1] if data.get("z") else None,
                } if data_points > 0 else None
            }
        }
        
        message_json = json.dumps(message)
        
        # Copia a lista para evitar modificação durante iteração
        connections_copy = self.active_connections[client_key].copy()
        failed_connections = []
        sent_count = 0
        
        for websocket in connections_copy:
            try:
                await websocket.send_text(message_json)
                sent_count += 1
                self.connection_stats["messages_sent"] += 1
            except Exception as e:
                Logger.log_message(f"Erro ao enviar dados WebSocket para {client_key}: {e}")
                failed_connections.append(websocket)
                self.connection_stats["failed_sends"] += 1
        
        # Remove conexões que falharam
        for websocket in failed_connections:
            self.disconnect(websocket, device_id, sensor_type)
        
    
    def get_connection_count(self):
        """
        Retorna o número total de conexões ativas
        
        Returns:
            dict: Estatísticas detalhadas das conexões
        """
        sensor_connections = sum(len(connections) for connections in self.active_connections.values())
        device_list_connections = len(self.device_list_connections)
        
        return {
            "sensor_connections": sensor_connections,
            "device_list_connections": device_list_connections,
            "total_connections": sensor_connections + device_list_connections,
            "active_sensor_types": len(self.active_connections),
            "stats": self.connection_stats.copy()
        }
    
    def get_health_status(self):
        """
        Retorna status de saúde do WebSocket Manager
        
        Returns:
            dict: Status de saúde
        """
        current_time = time.time()
        stats = self.get_connection_count()
        
        # Calcula taxa de falhas
        total_attempts = self.connection_stats["messages_sent"] + self.connection_stats["failed_sends"]
        failure_rate = (self.connection_stats["failed_sends"] / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            "status": "healthy" if failure_rate < 10 else "degraded" if failure_rate < 50 else "unhealthy",
            "timestamp": current_time,
            "connections": stats,
            "failure_rate_percent": round(failure_rate, 2),
            "last_device_update": self.connection_stats["last_device_update"],
            "uptime_seconds": current_time - (self.connection_stats.get("start_time", current_time))
        }