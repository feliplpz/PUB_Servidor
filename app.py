import logging
import asyncio
from flask import Flask
from dotenv import load_dotenv
from src.connection.bluetooth_server import BluetoothConnection
from src.utils.logging import Logger
from src.web.routes import register_routes

# from flask_socketio import SocketIO
# from src.web.socket_events import register_socket_events

# from src.connection.websocket_manager import WebSocketManager

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Inicializa o Flask
app = Flask(
    __name__,
)

# Inicializa socket para consumir dados emitidos por WebSocket
# socketio = SocketIO(app, cors_allowed_origins="*")

# Cria o gerenciador WebSocket
# websocket_manager = WebSocketManager(socketio)

# Registra rotas e eventos de socket
register_routes(app)
# register_socket_events(socketio)


async def main():
    """Função principal que inicia o servidor Bluetooth e o servidor Flask com WebSockets"""
    bluetooth_server = BluetoothConnection()
    await asyncio.gather(
        bluetooth_server.start_server(),
        asyncio.to_thread(
            app.run, host="0.0.0.0", port=5000, use_reloader=False, threaded=True
        ),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        Logger.log_message("Servidor encerrado")
