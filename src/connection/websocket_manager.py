import asyncio
from typing import Dict, List
from fastapi import WebSocket
from src.utils.logging import Logger
from src.connection.event_bus import EventBus

class WebSocketManager:
    """Gerencia conexões WebSocket e distribuição de dados"""
    
    def __init__(self):
        """Inicializa o gerenciador WebSocket"""
        self.active_connections: Dict[str, List[WebSocket]] = {}
        EventBus.subscribe("sensor_update", self.handle_sensor_update)
        Logger.log_message("WebSocketManager inicializado")
    
    async def connect(self, websocket: WebSocket, device_id: str, sensor_type: str):
        """
        Conecta um novo WebSocket
        
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
        await self.send_historical_data(websocket, device_id, sensor_type)
    
    def disconnect(self, websocket: WebSocket, device_id: str, sensor_type: str):
        """
        Desconecta um WebSocket
        
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
            
            # Usar asyncio.create_task para executar função async
            asyncio.create_task(
                self.send_sensor_update(device_id, sensor_type, data)
            )
        except Exception as e:
            Logger.log_message(f"Erro ao processar atualização de sensor: {e}")
    
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
                self.disconnect(websocket, device_id, sensor_type)
        
        Logger.log_message(f"Dados enviados via WebSocket para {device_id}:{sensor_type}")
    
    def get_connection_count(self):
        """
        Retorna o número total de conexões ativas
        
        Returns:
            int: Número de conexões ativas
        """
        total = sum(len(connections) for connections in self.active_connections.values())
        return total