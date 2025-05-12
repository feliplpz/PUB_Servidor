from threading import Lock
from abc import ABC, abstractmethod
import os

ACCELEROMETER = "accelerometer"
GYROSCOPE = "gyroscope"
DIVIDER = "_"
EXTENSION = ".csv"
class Sensor(ABC):
    """Classe abstrata para sensores"""

    def __init__(self, device_id, max_data_points=100):
        """
        Inicializa um sensor
        Args:
            device_id (str): ID do dispositivo ao qual o sensor pertence
            max_data_points (int): Número máximo de pontos a serem mantidos em memória
        """
        self.device_id = device_id
        self.max_data_points = max_data_points
        self.data_lock = Lock()
        self.date_in_milliseconds = (os.getenv('DADOS_MILISSEGUNDOS', 'False') == 'True')
        self.initialize_data_storage()

    @abstractmethod
    def initialize_data_storage(self):
        """Inicializa as estruturas de dados para armazenamento"""
        pass

    @abstractmethod
    def process_data(self, data):
        """
        Processa dados recebidos do sensor

        Args:
            data (dict): Dados recebidos do sensor
        """
        pass

    @abstractmethod
    def get_data(self):
        """
        Retorna os dados armazenados do sensor

        Returns:
            dict: Dados armazenados
        """
        pass

    @abstractmethod
    def save_to_file(self, data, device_name, device_id):
        """
        Salva os dados em um arquivo

        Args:
            data (dict): Dados a serem salvos
            device_name (str): Nome do dispositivo
        """
        pass
