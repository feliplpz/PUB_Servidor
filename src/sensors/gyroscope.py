import os
from datetime import datetime
import time

from src.connection.event_bus import EventBus
from src.sensors.accelerometer import Accelerometer
from src.sensors.base_sensor import GYROSCOPE, DIVIDER, EXTENSION
from src.utils.logging import Logger


class Gyroscope(Accelerometer):
    """Sensor de giroscópio"""

    def process_data(self, data):
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

            EventBus.publish(
                "sensor_update",
                {
                    "device_id": self.device_id,
                    "sensor_type": GYROSCOPE,
                    "data": self.get_data(),
                },
            )

            return True
        except Exception as e:
            Logger.log_message(f"Erro ao processar dados do giroscópio: {e}")
            return False

    def save_to_file(self, data, device_name, device_id):
        """
        Salva os dados do giroscópio em um arquivo

        Args:
            data (dict): Dados do giroscópio
            device_name (str): Nome do dispositivo
            device_id (str): ID do dispositivo
        """
        try:
            gyro_x = data.get("x", float("nan"))
            gyro_y = data.get("y", float("nan"))
            gyro_z = data.get("z", float("nan"))

            if self.date_in_milliseconds:
                current_time_seconds = time.time()
                timestamp = round(current_time_seconds - self.start_time, 4)
            else:
                timestamp = datetime.now().isoformat()

            file_path = (
                    os.getenv("DATA_FILE_PATH", "")
                    + GYROSCOPE
                    + DIVIDER
                    + device_name
                    + DIVIDER
                    + device_id
                    + EXTENSION
            )
            is_new_file = not os.path.exists(file_path)

            with open(file_path, "a+") as f:
                if is_new_file:
                    f.write(
                        "timestamp,device_id,device_name,sensor_type,gyro_x,gyro_y,gyro_z\n"
                    )
                f.write(
                    f"{timestamp},{self.device_id},{device_name},{GYROSCOPE},{gyro_x},{gyro_y},{gyro_z}\n"
                )
            return True
        except Exception as e:
            Logger.log_message(f"Erro ao salvar dados do giroscópio: {e}")
            return False