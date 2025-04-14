from datetime import datetime
import logging
import os


class Logger:
    """Classe responsável pelo gerenciamento de logs do sistema"""

    @staticmethod
    def log_message(message):
        """
        Registra uma mensagem no console e no arquivo de log

        Args:
            message (str): Mensagem a ser registrada
        """
        logging.info(message)

        with open(os.getenv("SERVER_LOG_FILE_PATH", "server.log"), "a+") as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")
