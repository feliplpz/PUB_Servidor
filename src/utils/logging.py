from datetime import datetime
import logging
import os


class Logger:
    """System logging management class."""

    @staticmethod
    def log_message(message):
        """
        Log an info message to console and log file.

        Args:
            message (str): Message to be logged
        """
        logging.info(message)
        with open(os.getenv("SERVER_LOG_FILE_PATH", "server.log"), "a+") as f:
            f.write(f"{datetime.now().isoformat()} - [INFO] - {message}\n")

    @staticmethod
    def log_error(message):
        """
        Log an error message to console and log file.

        Args:
            message (str): Error message to be logged
        """
        logging.error(message)
        with open(os.getenv("SERVER_LOG_FILE_PATH", "server.log"), "a+") as f:
            f.write(f"{datetime.now().isoformat()} - [ERROR] - {message}\n")

    @staticmethod
    def log_warning(message):
        """
        Log a warning message to console and log file.

        Args:
            message (str): Warning message to be logged
        """
        logging.warning(message)
        with open(os.getenv("SERVER_LOG_FILE_PATH", "server.log"), "a+") as f:
            f.write(f"{datetime.now().isoformat()} - [WARNING] - {message}\n")