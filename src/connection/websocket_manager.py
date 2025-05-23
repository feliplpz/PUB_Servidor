import asyncio
import json
from typing import Dict, List, Set
from fastapi import WebSocket
from src.utils.logging import Logger
from src.connection.event_bus import EventBus

class WebSocketManager:
    """Gerencia conexões WebSocket e distribuição de dados"""
    
    def __init__(self):
        """Inicializa o gerenciador WebSocket"""
        # Conexões para sensores específicos
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Conexões para lista de dispositivos
        self.device_list_connections: Set[WebSocket] = set()
        
        # Inscreve-se nos eventos
        EventBus.subscribe("sensor_update", self.handle_sensor_update)
        EventBus.subscribe("device_connected", self.handle_device_connected)
        EventBus.subscribe("device_disconnected", self.handle_device_disconnected)
        
        Logger.log_message("WebSocketManager inicializado")
    
    async def connect(self, websocket: WebSocket, device_id: str, sensor_type: str):
        """
        Conecta um novo WebSocket para sensor específico
        
        Args:
            websocket (WebSocket): Conexão WebSocket
            device_id (str): ID do dispositivo
            sensor_type (str): Tipo de sensor
        """
        await websocket.accept()
        
        client_key = f"{device_id}_{sensor_type}"
        if client_key not in self.active_connections:
            self.active_connections[client_key] = []
        
        self.active_connections[client_key].append(websocket)
        Logger.log_message(f"WebSocket conectado: {client_key}")
        
        # Envia dados históricos imediatamente
        await self.send_historical_data(websocket, device_id, sensor_type)
    
    async def connect_device_list(self, websocket: WebSocket):
        """
        Conecta um WebSocket para receber atualizações da lista de dispositivos
        
        Args:
            websocket (WebSocket): Conexão WebSocket
        """
        await websocket.accept()
        self.device_list_connections.add(websocket)
        Logger.log_message("WebSocket conectado para lista de dispositivos")
        
        # Envia lista inicial
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
        Logger.log_message("WebSocket da lista de dispositivos desconectado")
    
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
                
                await websocket.send_json({
                    "type": "historical",
                    "device_id": device_id,
                    "sensor_type": sensor_type,
                    "data": data
                })
                
                Logger.log_message(f"Dados históricos enviados para {device_id}:{sensor_type}")
        except Exception as e:
            Logger.log_message(f"Erro ao enviar dados históricos: {e}")
    
    async def send_device_list_update(self, websocket: WebSocket = None):
        """
        Envia atualização da lista de dispositivos
        
        Args:
            websocket (WebSocket, optional): WebSocket específico. Se None, envia para todos.
        """
        try:
            from src.connection.bluetooth_server import DeviceManager
            
            devices = DeviceManager.get_all_devices()
            message = {
                "type": "device_list_update",
                "devices": devices
            }
            
            if websocket:
                # Envia para um WebSocket específico
                await websocket.send_text(json.dumps(message))
            else:
                # Envia para todos os WebSockets da lista de dispositivos
                failed_connections = []
                
                for ws in self.device_list_connections.copy():
                    try:
                        await ws.send_text(json.dumps(message))
                    except Exception as e:
                        Logger.log_message(f"Erro ao enviar lista de dispositivos: {e}")
                        failed_connections.append(ws)
                
                # Remove conexões que falharam
                for ws in failed_connections:
                    self.device_list_connections.discard(ws)
                
                Logger.log_message(f"Lista de dispositivos enviada para {len(self.device_list_connections)} clientes")
                
        except Exception as e:
            Logger.log_message(f"Erro ao enviar lista de dispositivos: {e}")
    
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
            
            # Criar task para enviar dados
            asyncio.create_task(
                self.send_sensor_update(device_id, sensor_type, data)
            )
        except Exception as e:
            Logger.log_message(f"Erro ao processar atualização de sensor: {e}")
    
    def handle_device_connected(self, event_data):
        """
        Manipula eventos de conexão de dispositivos
        
        Args:
            event_data (dict): Dados do evento
        """
        try:
            Logger.log_message(f"Dispositivo conectado: {event_data.get('device_name')}")
            # Enviar atualização da lista de dispositivos
            asyncio.create_task(self.send_device_list_update())
        except Exception as e:
            Logger.log_message(f"Erro ao processar conexão de dispositivo: {e}")
    
    def handle_device_disconnected(self, event_data):
        """
        Manipula eventos de desconexão de dispositivos
        
        Args:
            event_data (dict): Dados do evento
        """
        try:
            Logger.log_message(f"Dispositivo desconectado: {event_data.get('device_name')}")
            # Enviar atualização da lista de dispositivos
            asyncio.create_task(self.send_device_list_update())
        except Exception as e:
            Logger.log_message(f"Erro ao processar desconexão de dispositivo: {e}")
    
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
        
        # Copia a lista para evitar modificação durante iteração
        connections_copy = self.active_connections[client_key].copy()
        failed_connections = []
        
        for websocket in connections_copy:
            try:
                await websocket.send_json({
                    "type": "update",
                    "device_id": device_id,
                    "sensor_type": sensor_type,
                    "data": data
                })
            except Exception as e:
                Logger.log_message(f"Erro ao enviar dados WebSocket: {e}")
                failed_connections.append(websocket)
        
        # Remove conexões que falharam
        for websocket in failed_connections:
            self.disconnect(websocket, device_id, sensor_type)
        
        if len(connections_copy) - len(failed_connections) > 0:
            Logger.log_message(f"Dados enviados via WebSocket para {device_id}:{sensor_type}")
    
    def get_connection_count(self):
        """
        Retorna o número total de conexões ativas
        
        Returns:
            int: Número de conexões ativas
        """
        sensor_connections = sum(len(connections) for connections in self.active_connections.values())
        device_list_connections = len(self.device_list_connections)
        return sensor_connections + device_list_connections