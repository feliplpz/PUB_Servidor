from threading import Lock
from src.utils.logging import Logger
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
        env_value = os.getenv('DATE_IN_MILLISECONDS')
        if env_value is not None and env_value not in ('True', 'False'):
            Logger.log_message(
                f"ERRO: Formato inválido para DATE_IN_MILLISECONDS: '{env_value}'. "
                f"O valor deve ser exatamente 'True' ou 'False'. Usando o padrão: False."
            )
            # Define como False por segurança
            self.date_in_milliseconds = False
        else:
            # Define o valor correto
            self.date_in_milliseconds = (env_value == 'True')
            Logger.log_message(f"Configuração: DATE_IN_MILLISECONDS={self.date_in_milliseconds}")
        
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
