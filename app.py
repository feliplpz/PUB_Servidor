# app.py
import logging
import asyncio
from flask import Flask
from dotenv import load_dotenv
from src.bluetooth.bluetooth_server import BluetoothConnection
from src.utils.logging import Logger
from src.web.routes import register_routes


# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Inicializa o Flask
app = Flask(__name__, template_folder="src/web/templates")


async def main():
    """
    Função principal que inicia o servidor Bluetooth e o servidor Flask

    Returns:
        None
    """
    register_routes(app)
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
