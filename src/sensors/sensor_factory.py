from src.utils.logging import Logger

class SensorFactory:
    """Factory for creating sensors."""

    @staticmethod
    def create_sensor(sensor_type, device_id, max_data_points):
        """
        Create a sensor based on type.

        Args:
            sensor_type (str): Sensor type
            device_id (str): Device identifier
            max_data_points (int): Maximum number of data points

        Returns:
            Sensor: Sensor instance

        Raises:
            ValueError: If sensor type is not supported
        """
        try:
            if sensor_type == "accelerometer":
                from src.sensors.accelerometer import Accelerometer
                sensor = Accelerometer(device_id, max_data_points)
                Logger.log_message(f"Accelerometer sensor created for device {device_id}")
                return sensor
            elif sensor_type == "gyroscope":
                from src.sensors.gyroscope import Gyroscope
                sensor = Gyroscope(device_id, max_data_points)
                Logger.log_message(f"Gyroscope sensor created for device {device_id}")
                return sensor
            elif sensor_type == "magnetometer":
                from src.sensors.magnetometer import Magnetometer
                sensor = Magnetometer(device_id, max_data_points)
                Logger.log_message(f"Magnetometer sensor created for device {device_id}")
                return sensor
            else:
                error_msg = f"Unsupported sensor type: {sensor_type}"
                Logger.log_error(error_msg)
                raise ValueError(error_msg)
        except ImportError as e:
            error_msg = f"Error importing sensor {sensor_type}: {e}"
            Logger.log_error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error creating sensor {sensor_type}: {e}"
            Logger.log_error(error_msg)
            raise ValueError(error_msg)