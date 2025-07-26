from threading import Lock
from src.utils.logging import Logger
from abc import ABC, abstractmethod
import os

# Constants for sensor types
ACCELEROMETER = "accelerometer"
GYROSCOPE = "gyroscope"
MAGNETOMETER = "magnetometer"

# Constants for file formatting
DIVIDER = "_"
EXTENSION = ".csv"


class Sensor(ABC):
    """Abstract base class for sensors."""

    def __init__(self, device_id, max_data_points=100):
        """
        Initialize a sensor.

        Args:
            device_id (str): Device identifier that the sensor belongs to
            max_data_points (int): Maximum number of data points to keep in memory
        """
        self.device_id = device_id
        self.max_data_points = max_data_points
        self.data_lock = Lock()

        # Timestamp configuration
        env_value = os.getenv('DATE_IN_MILLISECONDS')
        if env_value is not None and env_value not in ('True', 'False'):
            Logger.log_error(
                f"Invalid format for DATE_IN_MILLISECONDS: '{env_value}'. "
                f"Value must be exactly 'True' or 'False'. Using default: False."
            )
            self.date_in_milliseconds = False
        else:
            self.date_in_milliseconds = (env_value == 'True')
            Logger.log_message(f"Configuration: DATE_IN_MILLISECONDS={self.date_in_milliseconds}")

        self.initialize_data_storage()

    @abstractmethod
    def initialize_data_storage(self):
        """Initialize data storage structures."""
        pass

    @abstractmethod
    def process_data(self, data):
        """
        Process received sensor data.

        Args:
            data (dict): Data received from sensor

        Returns:
            bool: True if data processed successfully
        """
        pass

    @abstractmethod
    def get_data(self):
        """
        Get stored sensor data.

        Returns:
            dict: Stored sensor data
        """
        pass

    @abstractmethod
    def save_to_file(self, data, device_name, device_id):
        """
        Save data to file.

        Args:
            data (dict): Data to be saved
            device_name (str): Device name
            device_id (str): Device identifier

        Returns:
            bool: True if data saved successfully
        """
        pass