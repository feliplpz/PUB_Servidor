import os
from datetime import datetime

from src.utils.logging import Logger


class Gyroscope:
    """Sensor de giroscópio"""

    def __init__(self, device_id, max_data_points):
        """
        Inicializa o sensor de giroscópio

        Args:
            device_id (str): ID do dispositivo
            max_data_points (int): Número máximo de pontos de dados
        """
        self.device_id = device_id
        self.max_data_points = max_data_points
        self.data_points = []

    def process_data(self, data):
        """
        Processa os dados do giroscópio

        Args:
            data (dict): Dados do giroscópio

        Returns:
            bool: True se os dados foram processados com sucesso
        """
        if "type" not in data or data["type"] != "gyroscope":
            return False

        if "x" not in data or "y" not in data or "z" not in data:
            return False

        # Adiciona timestamp
        data["timestamp"] = datetime.now().isoformat()

        # Limita o número de pontos armazenados
        if len(self.data_points) >= self.max_data_points:
            self.data_points.pop(0)

        self.data_points.append(data)
        return True

    def save_to_file(self, data, device_name, device_id):
        """
        Salva os dados do giroscópio em um arquivo

        Args:
            data (dict): Dados do giroscópio
            device_name (str): Nome do dispositivo
            device_id (str): ID do dispositivo
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"data/gyroscope_{device_id}_{timestamp}.csv"

            # Cria diretório se não existir
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # Verifica se o arquivo já existe
            file_exists = os.path.isfile(filename)

            with open(filename, "a") as f:
                # Escreve o cabeçalho se for um novo arquivo
                if not file_exists:
                    f.write("timestamp,device_id,device_name,x,y,z\n")

                # Escreve os dados
                f.write(f"{data['timestamp']},{device_id},{device_name},{data['x']},{data['y']},{data['z']}\n")

            Logger.log_message(f"Dados do giroscópio salvos em {filename}")
        except Exception as e:
            Logger.log_message(f"Erro ao salvar dados do giroscópio: {e}")