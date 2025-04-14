from src.sensors.accelerometer import Accelerometer


class SensorFactory:
    """Fábrica para criar instâncias de sensores com base no tipo"""

    @staticmethod
    def create_sensor(sensor_type, device_id, max_data_points=100):
        """
        Cria uma instância do sensor especificado

        Args:
            sensor_type (str): Tipo de sensor a ser criado
            device_id (str): ID do dispositivo
            max_data_points (int): Número máximo de pontos de dados

        Returns:
            Sensor: Instância do sensor criado

        Raises:
            ValueError: Se o tipo de sensor não for suportado
        """
        if sensor_type.lower() == "accelerometer":
            return Accelerometer(device_id, max_data_points)
        else:
            raise ValueError(f"Tipo de sensor não suportado: {sensor_type}")
