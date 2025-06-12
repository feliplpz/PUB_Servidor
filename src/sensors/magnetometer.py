import os
from datetime import datetime
import time

from src.connection.event_bus import EventBus
from src.sensors.accelerometer import Accelerometer
from src.sensors.base_sensor import DIVIDER, EXTENSION
from src.utils.logging import Logger

MAGNETOMETER = "magnetometer"

class Magnetometer(Accelerometer):
    """Sensor de magnetômetro"""

    def process_data(self, data):
        try:
            mag_x = data.get("x", float("nan"))
            mag_y = data.get("y", float("nan"))
            mag_z = data.get("z", float("nan"))

            if not all(
                    isinstance(v, (int, float)) for v in (mag_x, mag_y, mag_z)
            ):
                return False

            with self.data_lock:
                current_time = time.time() - self.start_time
                self.data_t.append(current_time)
                self.data_x.append(mag_x)
                self.data_y.append(mag_y)
                self.data_z.append(mag_z)

            EventBus.publish(
                "sensor_update",
                {
                    "device_id": self.device_id,
                    "sensor_type": MAGNETOMETER,
                    "data": self.get_data(),
                },
            )

            return True
        except Exception as e:
            Logger.log_message(f"Erro ao processar dados do magnetômetro: {e}")
            return False

    def save_to_file(self, data, device_name, device_id):
        """
        Salva os dados do magnetômetro em um arquivo

        Args:
            data (dict): Dados do magnetômetro
            device_name (str): Nome do dispositivo
            device_id (str): ID do dispositivo
        """
        try:
            mag_x = data.get("x", float("nan"))
            mag_y = data.get("y", float("nan"))
            mag_z = data.get("z", float("nan"))

            if self.date_in_milliseconds:
                current_time_seconds = time.time()
                timestamp = round(current_time_seconds - self.start_time, 4)
            else:
                timestamp = datetime.now().isoformat()
            
            start_time_formatted = datetime.fromtimestamp(self.start_time).strftime('%d_%m_%y___%H_%M_%S')
            file_path = (
                    os.getenv("DATA_FILE_PATH", "")
                    + MAGNETOMETER
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
                        "timestamp,mag_x,mag_y,mag_z\n"
                    )
                f.write(
                    f"{timestamp},{mag_x},{mag_y},{mag_z}\n"
                )
            return True
        except Exception as e:
            Logger.log_message(f"Erro ao salvar dados do magnetômetro: {e}")
            return False