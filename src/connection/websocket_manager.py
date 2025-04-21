from src.utils.logging import Logger


class WebSocketManager:
    """Gerencia conexões WebSocket e distribuição de dados"""

    def __init__(self, socketio):
        """
        Inicializa o gerenciador WebSocket

        Args:
            socketio (SocketIO): Instância do Flask-SocketIO
        """
        self.socketio = socketio
        from src.connection.event_bus import EventBus

        # Inscreve-se para receber atualizações de sensores
        EventBus.subscribe("sensor_update", self.handle_sensor_update)

    def handle_sensor_update(self, data):
        """
        Manipula eventos de atualização de sensores

        Args:
            data (dict): Dados do evento contendo device_id, sensor_type e data
        """
        try:
            self.send_sensor_update(
                data["device_id"], data["sensor_type"], data["data"]
            )
        except Exception as e:
            Logger.log_message(f"Erro ao processar atualização de sensor: {e}")

    def send_sensor_update(self, device_id, sensor_type, data):
        """
        Envia atualização de dados de sensor para clientes WebSocket

        Args:
            device_id (str): ID do dispositivo
            sensor_type (str): Tipo de sensor
            data (dict): Dados do sensor
        """
        try:
            self.socketio.emit(
                f"sensor_update_{device_id}_{sensor_type}", data, namespace="/sensor"
            )
            Logger.log_message(
                f"Dados enviados via WebSocket para {device_id}:{sensor_type}"
            )
        except Exception as e:
            Logger.log_message(f"Erro ao enviar dados WebSocket: {e}")
