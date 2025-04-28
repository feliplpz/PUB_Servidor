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
        if sensor_type == "accelerometer":
            from src.sensors.accelerometer import Accelerometer
            return Accelerometer(device_id, max_data_points)
        elif sensor_type == "gyroscope":
            from src.sensors.gyroscope import Gyroscope
            return Gyroscope(device_id, max_data_points)
        else:
            raise ValueError(f"Tipo de sensor não suportado: {sensor_type}")
