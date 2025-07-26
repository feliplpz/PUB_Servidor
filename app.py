import asyncio
import logging
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.connection.bluetooth_server import BluetoothConnection
from src.connection.websocket_manager import WebSocketManager
from src.utils.logging import Logger
from src.web.routes import register_routes

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
websocket_manager = WebSocketManager()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

register_routes(app, templates, websocket_manager)


async def main():
    """
    Start the application server with Bluetooth and web services.

    Initializes and runs:
    - Bluetooth server for device connections
    - FastAPI web server for the user interface
    """
    bluetooth_server = BluetoothConnection()
    config = uvicorn.Config(app, host="0.0.0.0", port=5000)
    server = uvicorn.Server(config)

    asyncio.create_task(bluetooth_server.start_server())

    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        Logger.log_message("Server interrupted by user")
    except Exception as e:
        Logger.log_error(f"Fatal error: {e}")
        logging.exception("Fatal error occurred")