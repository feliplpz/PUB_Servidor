import os
from datetime import datetime
import time

from src.connection.event_bus import EventBus
from src.sensors.accelerometer import Accelerometer
from src.sensors.base_sensor import GYROSCOPE, DIVIDER, EXTENSION
from src.utils.logging import Logger


class Gyroscope(Accelerometer):
    """Gyroscope sensor implementation."""

    def process_data(self, data):
        """
        Process received gyroscope data.

        Args:
            data (dict): Gyroscope data for x, y and z axes

        Returns:
            bool: True if data processed successfully
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
            Logger.log_error(f"Error processing gyroscope data: {e}")
            return False

    def save_to_file(self, data, device_name, device_id):
        """
        Save gyroscope data to CSV file.

        Args:
            data (dict): Gyroscope data to be saved
            device_name (str): Device name
            device_id (str): Device identifier

        Returns:
            bool: True if data saved successfully
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
            start_time_formatted = datetime.fromtimestamp(self.start_time).strftime('%d_%m_%y___%H_%M_%S')
            file_path = (
                    os.getenv("DATA_FILE_PATH", "")
                    + GYROSCOPE
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
                        "timestamp,gyro_x,gyro_y,gyro_z\n"
                    )
                f.write(
                    f"{timestamp},{gyro_x},{gyro_y},{gyro_z}\n"
                )
            return True
        except Exception as e:
            Logger.log_error(f"Error saving gyroscope data: {e}")
            return False