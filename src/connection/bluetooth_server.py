import secrets
import re
import os
import asyncio
import bluetooth
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
from src.utils.logging import Logger
from src.connection.event_bus import EventBus
from src.sensors.sensor_factory import SensorFactory


class DeviceManager:
    """Manages Bluetooth device registration and tracking."""
    devices = {}

    @staticmethod
    def generate_device_id():
        """
        Generate a unique hex ID for connected devices.

        Returns:
            str: 8-character uppercase hex string
        """
        return secrets.token_hex(4).upper()

    @classmethod
    def register_device(cls, device_id, device_name):
        """
        Register a new device in the system.

        Args:
            device_id (str): Unique device identifier
            device_name (str): Human-readable device name
        """
        if device_id not in cls.devices:
            cls.devices[device_id] = {
                "name": device_name,
                "connected_at": datetime.now().isoformat(),
                "sensors": {},
            }
            Logger.log_message(f"Device registered: {device_name} ({device_id})")

            EventBus.publish("device_connected", {
                "device_id": device_id,
                "device_name": device_name,
                "connected_at": cls.devices[device_id]["connected_at"]
            })

    @classmethod
    def unregister_device(cls, device_id):
        """
        Remove a device from the system.

        Args:
            device_id (str): Unique device identifier to remove
        """
        if device_id in cls.devices:
            device_name = cls.devices[device_id]["name"]
            del cls.devices[device_id]
            Logger.log_message(f"Device removed: {device_name} ({device_id})")

            EventBus.publish("device_disconnected", {
                "device_id": device_id,
                "device_name": device_name
            })

    @classmethod
    def get_all_devices(cls):
        """
        Get all connected devices.

        Returns:
            dict: Dictionary containing all registered devices
        """
        return cls.devices

    @classmethod
    def get_serializable_devices(cls):
        """
        Get a serializable version of all devices with sensor status.

        Returns:
            dict: Dictionary with device info and sensor summaries
        """
        serializable_devices = {}
        current_time = time.time()

        for device_id, device_info in cls.devices.items():
            sensor_summary = {}

            for sensor_type, sensor_obj in device_info.get("sensors", {}).items():
                try:
                    data = sensor_obj.get_data()
                    data_points = len(data.get("time", []))

                    has_recent_data = False
                    time_since_update = None

                    if data_points > 0 and data.get("time"):
                        last_relative_time = data["time"][-1]
                        sensor_start_time = getattr(sensor_obj, 'start_time', current_time)
                        last_data_time = sensor_start_time + last_relative_time
                        time_since_update = current_time - last_data_time
                        has_recent_data = time_since_update < 5.0

                    sensor_summary[sensor_type] = {
                        "type": sensor_type,
                        "data_points": data_points,
                        "has_data": data_points > 0,
                        "has_recent_data": has_recent_data,
                        "time_since_update": time_since_update,
                        "last_values": {
                            "x": data.get("x", [None])[-1] if data.get("x") else None,
                            "y": data.get("y", [None])[-1] if data.get("y") else None,
                            "z": data.get("z", [None])[-1] if data.get("z") else None,
                        } if data_points > 0 else None
                    }

                except Exception as e:
                    Logger.log_error(f"Error serializing sensor {sensor_type}: {e}")
                    sensor_summary[sensor_type] = {
                        "type": sensor_type,
                        "data_points": 0,
                        "has_data": False,
                        "has_recent_data": False,
                        "error": str(e)
                    }

            active_sensors = sum(1 for s in sensor_summary.values() if s.get("has_recent_data", False))

            serializable_devices[device_id] = {
                "name": device_info["name"],
                "connected_at": device_info["connected_at"],
                "sensors": sensor_summary,
                "sensor_count": len(sensor_summary),
                "active_sensor_count": active_sensors,
                "last_updated": current_time
            }

        return serializable_devices


class BluetoothMessageParser:
    """
    Specialized parser for concurrent JSON messages in Bluetooth streams.

    Handles message interleaving, fragmentation, and corruption that occurs
    when multiple sensors send data simultaneously through the same socket.
    """

    def __init__(self, json_start_pattern: str, max_buffer_size: int, fallback_size: int):
        """
        Initialize the message parser.

        Args:
            json_start_pattern (str): Pattern to identify JSON message start
            max_buffer_size (int): Maximum buffer size before cleanup
            fallback_size (int): Size to keep during buffer cleanup
        """
        self.json_start_pattern = json_start_pattern.encode('utf-8')
        self.max_buffer_size = max_buffer_size
        self.fallback_size = fallback_size

        # Regex for potential valid JSON messages
        self.json_regex = re.compile(
            rb'\{\s*"type"\s*:\s*"[^"]+"\s*,.*?\}',
            re.DOTALL
        )

    def extract_complete_jsons(self, buffer: bytes) -> Tuple[List[bytes], bytes]:
        """
        Extract complete JSON messages from buffer.

        Args:
            buffer (bytes): Raw data buffer containing potential JSON messages

        Returns:
            Tuple[List[bytes], bytes]: List of valid JSON messages and remaining buffer
        """
        complete_jsons = []

        matches = list(self.json_regex.finditer(buffer))

        if matches:
            last_end = 0
            for match in matches:
                json_candidate = match.group()

                if self._is_valid_json(json_candidate):
                    complete_jsons.append(json_candidate)
                    last_end = match.end()

            remaining_buffer = buffer[last_end:] if last_end > 0 else buffer
        else:
            # Fallback: manual extraction when regex fails
            complete_jsons, remaining_buffer = self._manual_json_extraction(buffer)

        return complete_jsons, remaining_buffer

    def _manual_json_extraction(self, buffer: bytes) -> Tuple[List[bytes], bytes]:
        """
        Extract JSON messages manually when regex approach fails.

        Args:
            buffer (bytes): Raw data buffer

        Returns:
            Tuple[List[bytes], bytes]: List of valid JSON messages and remaining buffer
        """
        complete_jsons = []
        start = 0

        while True:
            json_start = buffer.find(self.json_start_pattern, start)
            if json_start == -1:
                break

            json_end = self._find_json_end(buffer, json_start)
            if json_end == -1:
                # Incomplete JSON remains in buffer
                break

            json_candidate = buffer[json_start:json_end + 1]

            if self._is_valid_json(json_candidate):
                complete_jsons.append(json_candidate)

            start = json_end + 1

        remaining_buffer = buffer[start:] if start < len(buffer) else b""

        return complete_jsons, remaining_buffer

    def _find_json_end(self, buffer: bytes, start: int) -> int:
        """
        Find JSON end using brace balancing.

        Args:
            buffer (bytes): Data buffer
            start (int): Starting position for search

        Returns:
            int: Position of JSON end or -1 if incomplete
        """
        brace_count = 0
        in_string = False
        escape_next = False

        for i in range(start, len(buffer)):
            byte_char = chr(buffer[i]) if buffer[i] < 128 else None

            if escape_next:
                escape_next = False
                continue

            if byte_char == '\\':
                escape_next = True
                continue

            if byte_char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if byte_char == '{':
                    brace_count += 1
                elif byte_char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return i

        return -1  # Incomplete JSON

    def _is_valid_json(self, json_bytes: bytes) -> bool:
        """
        Validate if bytes represent syntactically valid JSON with expected structure.

        Args:
            json_bytes (bytes): Bytes to validate as JSON

        Returns:
            bool: True if valid JSON with required structure
        """
        try:
            data = json.loads(json_bytes.decode('utf-8'))
            return isinstance(data, dict) and "type" in data
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return False

    def cleanup_buffer(self, buffer: bytes) -> bytes:
        """
        Clean buffer while preserving potentially useful data.

        Args:
            buffer (bytes): Buffer to clean

        Returns:
            bytes: Cleaned buffer
        """
        if len(buffer) <= self.max_buffer_size:
            return buffer

        # Find last JSON end marker
        last_brace = buffer.rfind(b'}')

        if last_brace != -1 and last_brace < len(buffer) - 1:
            # Keep data after last complete JSON
            return buffer[last_brace + 1:]
        else:
            # Fallback: keep only last bytes
            return buffer[-self.fallback_size:]


class BluetoothConnection:
    """
    Manages Bluetooth connections with support for concurrent sensors.

    Resolves message interleaving issues that occur when multiple sensors
    send data simultaneously through the same Bluetooth socket, causing
    fragmentation and message overlap.
    """

    def __init__(self):
        """Initialize Bluetooth connection manager with environment configurations."""
        # Buffer and network settings loaded from .env
        self.recv_chunk_size = int(os.getenv("BT_RECV_CHUNK_SIZE", 1024))
        self.max_buffer_size = int(os.getenv("BT_MAX_BUFFER_SIZE", 8192))
        self.buffer_cleanup_threshold = int(os.getenv("BT_BUFFER_CLEANUP_THRESHOLD", 4096))
        self.buffer_fallback_size = int(os.getenv("BT_BUFFER_FALLBACK_SIZE", 256))
        self.max_message_size = int(os.getenv("BT_MAX_MESSAGE_SIZE", 2048))
        self.connection_timeout = int(os.getenv("BT_CONNECTION_TIMEOUT", 30))
        self.json_start_pattern = os.getenv("BT_JSON_START_PATTERN", '{"type"')

        self.message_parser = BluetoothMessageParser(
            json_start_pattern=self.json_start_pattern,
            max_buffer_size=self.max_buffer_size,
            fallback_size=self.buffer_fallback_size
        )

        Logger.log_message(f"BluetoothConnection initialized with buffer_size={self.max_buffer_size}, "
                           f"chunk_size={self.recv_chunk_size}, timeout={self.connection_timeout}s")

    async def handle_client(self, socket, device_id: str):
        """
        Handle Bluetooth client connection with multi-sensor support.

        Resolves:
        - Message interleaving (overlapping messages)
        - Data fragmentation
        - Buffer overflow
        - Concurrent JSON parsing

        Args:
            socket: Bluetooth socket for the connected client
            device_id (str): Unique identifier for the device
        """
        device_name = "Unknown"
        buffer = b""
        message_count = 0
        error_count = 0

        try:
            device_name = bluetooth.lookup_name(socket.getpeername()[0]) or "Unknown"
            DeviceManager.register_device(device_id, device_name)
            Logger.log_message(f"Connected: {device_name} (ID: {device_id})")

            sensors = await self._initialize_sensors(device_id)
            DeviceManager.devices[device_id]["sensors"].update(sensors)

            while True:
                try:
                    data = await asyncio.wait_for(
                        asyncio.to_thread(socket.recv, self.recv_chunk_size),
                        timeout=self.connection_timeout
                    )
                    if not data:
                        Logger.log_message(f"Connection closed by client: {device_name}")
                        break
                    buffer += data

                    complete_jsons, buffer = self.message_parser.extract_complete_jsons(buffer)
                    for json_data in complete_jsons:
                        success = await self._process_sensor_message(
                            json_data, sensors, device_name, device_id
                        )
                        if success:
                            message_count += 1
                        else:
                            error_count += 1
                    if len(buffer) > self.buffer_cleanup_threshold:
                        old_size = len(buffer)
                        buffer = self.message_parser.cleanup_buffer(buffer)
                        Logger.log_message(f"Buffer cleaned: {old_size} -> {len(buffer)} bytes")

                except asyncio.TimeoutError as timeout_err:
                    Logger.log_error(f"Connection timeout with {device_name}. Error: {timeout_err}")
                    break
                except bluetooth.btcommon.BluetoothError as bluetooth_err:
                    Logger.log_error(f"Bluetooth error with {device_name}: {bluetooth_err}")
                    break
                except Exception as e:
                    error_count += 1
                    Logger.log_error(f"Error in {device_name} loop: {e}")

                    if error_count > 10:
                        Logger.log_error(f"Too many errors ({error_count}), terminating {device_name}")
                        break

        except Exception as e:
            Logger.log_error(f"Critical error with {device_name}: {e}")
        finally:
            await self._cleanup_connection(socket, device_id, device_name, message_count, error_count)

    async def _initialize_sensors(self, device_id: str) -> Dict:
        """
        Initialize sensors for the device.

        Args:
            device_id (str): Unique device identifier

        Returns:
            Dict: Dictionary of initialized sensor objects
        """
        max_data_points = int(os.getenv("MAX_DATA_POINTS", 100))
        sensors = {
            "accelerometer": SensorFactory.create_sensor("accelerometer", device_id, max_data_points),
            "gyroscope": SensorFactory.create_sensor("gyroscope", device_id, max_data_points),
            "magnetometer": SensorFactory.create_sensor("magnetometer", device_id, max_data_points)
        }

        Logger.log_message(f"Sensors initialized for {device_id}: {list(sensors.keys())}")
        return sensors

    async def _process_sensor_message(self, json_data: bytes, sensors: Dict,
                                      device_name: str, device_id: str) -> bool:
        """
        Process an individual sensor message.

        Args:
            json_data (bytes): Raw JSON message data
            sensors (Dict): Available sensor objects
            device_name (str): Human-readable device name
            device_id (str): Unique device identifier

        Returns:
            bool: True if message processed successfully
        """
        try:
            message = json.loads(json_data.decode('utf-8'))

            if not isinstance(message, dict) or "type" not in message:
                Logger.log_warning(f"Invalid message from {device_name}: incorrect structure")
                return False

            sensor_type = message.get("type")

            if sensor_type not in sensors:
                Logger.log_warning(f"Unknown sensor type from {device_name}: {sensor_type}")
                return False

            sensor = sensors[sensor_type]

            if sensor.process_data(message):
                sensor.save_to_file(message, device_name, device_id)
                return True
            else:
                Logger.log_warning(f"Failed to process {sensor_type} data from {device_name}")
                return False

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            Logger.log_error(f"Decoding error from {device_name}: {e}")
            return False
        except Exception as e:
            Logger.log_error(f"Error processing message from {device_name}: {e}")
            return False

    async def _cleanup_connection(self, socket, device_id: str, device_name: str,
                                  message_count: int, error_count: int):
        """
        Clean up connection resources.

        Args:
            socket: Bluetooth socket to close
            device_id (str): Device identifier
            device_name (str): Device name for logging
            message_count (int): Number of processed messages
            error_count (int): Number of errors encountered
        """
        try:
            socket.close()
            DeviceManager.unregister_device(device_id)
            Logger.log_message(f"Connection with {device_name} (ID: {device_id}) terminated. "
                               f"Stats: {message_count} messages, {error_count} errors")
        except Exception as e:
            Logger.log_error(f"Cleanup error for {device_name}: {e}")

    async def start_server(self):
        """Start the Bluetooth server and accept incoming connections."""
        server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_socket.bind(("", bluetooth.PORT_ANY))
        server_socket.listen(1)
        port = server_socket.getsockname()[1]
        Logger.log_message(f"Bluetooth server active on port {port}")

        # Non-blocking socket
        server_socket.setblocking(False)

        try:
            while True:
                try:
                    client_sock, address = server_socket.accept()
                    device_id = DeviceManager.generate_device_id()
                    Logger.log_message(f"New connection from {address} -> ID: {device_id}")
                    asyncio.create_task(self.handle_client(client_sock, device_id))
                except (BlockingIOError, bluetooth.btcommon.BluetoothError):
                    # No pending connection, short sleep and continue
                    await asyncio.sleep(0.1)
                    continue
        except asyncio.CancelledError:
            Logger.log_warning("Bluetooth server cancelled")
        finally:
            server_socket.close()