from src.utils.logging import Logger

class SensorFactory:
    """Factory para criar sensores"""

    @staticmethod
    def create_sensor(sensor_type, device_id, max_data_points):
        """
        Cria um sensor com base no tipo

        Args:
            sensor_type (str): Tipo de sensor
            device_id (str): ID do dispositivo
            max_data_points (int): Número máximo de pontos de dados

        Returns:
            Sensor: Instância do sensor

        Raises:
            ValueError: Se o tipo de sensor não for suportado
        """
        try:
            if sensor_type == "accelerometer":
                from src.sensors.accelerometer import Accelerometer
                sensor = Accelerometer(device_id, max_data_points)
                Logger.log_message(f"Sensor accelerometer criado para dispositivo {device_id}")
                return sensor
            elif sensor_type == "gyroscope":
                from src.sensors.gyroscope import Gyroscope
                sensor = Gyroscope(device_id, max_data_points)
                Logger.log_message(f"Sensor gyroscope criado para dispositivo {device_id}")
                return sensor
            elif sensor_type == "magnetometer":
                from src.sensors.magnetometer import Magnetometer
                sensor = Magnetometer(device_id, max_data_points)
                Logger.log_message(f"Sensor magnetometer criado para dispositivo {device_id}")
                return sensor
            else:
                error_msg = f"Tipo de sensor não suportado: {sensor_type}"
                Logger.log_message(error_msg)
                raise ValueError(error_msg)
        except ImportError as e:
            error_msg = f"Erro ao importar sensor {sensor_type}: {e}"
            Logger.log_message(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Erro ao criar sensor {sensor_type}: {e}"
            Logger.log_message(error_msg)
            raise ValueError(error_msg)