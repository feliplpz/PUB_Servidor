from datetime import datetime
import os
import time
from collections import deque
from src.utils.logging import Logger
from src.sensors.base_sensor import Sensor, ACCELEROMETER, DIVIDER, EXTENSION
from src.connection.event_bus import EventBus

class Accelerometer(Sensor):
    """Implementação do sensor de acelerômetro"""

    def initialize_data_storage(self):
        """Inicializa as estruturas de dados para armazenamento do acelerômetro"""
        self.header_time = datetime.now()
        self.start_time = time.time()
        self.data_t = deque(maxlen=self.max_data_points)
        self.data_x = deque(maxlen=self.max_data_points)
        self.data_y = deque(maxlen=self.max_data_points)
        self.data_z = deque(maxlen=self.max_data_points)

    def process_data(self, data):
        """
        Processa dados recebidos do acelerômetro

        Args:
            data (dict): Dados de aceleração nos eixos x, y e z
        """
        try:
            accel_x = data.get("x", float("nan"))
            accel_y = data.get("y", float("nan"))
            accel_z = data.get("z", float("nan"))

            if not all(
                isinstance(v, (int, float)) for v in (accel_x, accel_y, accel_z)
            ):
                return False

            with self.data_lock:
                current_time = time.time() - self.start_time
                self.data_t.append(current_time)
                self.data_x.append(accel_x)
                self.data_y.append(accel_y)
                self.data_z.append(accel_z)

            # Logger.log_message(f"Accelerometer: 📊 PUBLICANDO EVENTO: {self.device_id}: Dados: {self.get_data()}")
            # Publica os dados para quem estiver interessado
            EventBus.publish(
                "sensor_update",
                {
                    "device_id": self.device_id,
                    "sensor_type": ACCELEROMETER,
                    "data": self.get_data(),
                },
            )

            return True
        except Exception as e:
            Logger.log_message(f"Erro ao processar dados do acelerômetro: {e}")
            return False

    def get_data(self):
        """
        Retorna os dados do acelerômetro

        Returns:
            dict: Dados de tempo e aceleração nos três eixos
        """
        with self.data_lock:
            return {
                "time": list(self.data_t),
                "x": list(self.data_x),
                "y": list(self.data_y),
                "z": list(self.data_z),
            }

    def save_to_file(self, data, device_name, device_id):
        """
        Salva os dados do acelerômetro em um arquivo CSV

        Args:
            data (dict): Dados a serem salvos
            device_name (str): Nome do dispositivo
            device_id (str): ID do dispositivo
        """
        try:
            accel_x = data.get("x", float("nan"))
            accel_y = data.get("y", float("nan"))
            accel_z = data.get("z", float("nan"))
            if self.date_in_milliseconds:
                current_time_seconds = time.time()
                timestamp = round(current_time_seconds - self.start_time, 4)
            else: 
                timestamp = datetime.now().isoformat()
            start_time_formatted = datetime.fromtimestamp(self.start_time).strftime('%d_%m_%y___%H_%M_%S')
            file_path = (
                os.getenv("DATA_FILE_PATH", "")
                + ACCELEROMETER
                + DIVIDER
                + device_name
                + DIVIDER
                + device_id
                + DIVIDER
                + start_time_formatted
                + EXTENSION
            )
            is_new_file = not os.path.exists(file_path)

            with open(file_path, "a+") as f:
                if is_new_file:
                    f.write(
                        "timestamp,accel_x,accel_y,accel_z\n"
                    )
                    
                f.write(
                    f"{timestamp},{accel_x},{accel_y},{accel_z}\n"
                )
            return True
        except Exception as e:
            Logger.log_message(f"Erro ao salvar dados: {e}")
            return False
