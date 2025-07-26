import asyncio
import json
import time
from typing import Dict, List, Set
from fastapi import WebSocket
from src.utils.logging import Logger
from src.connection.event_bus import EventBus


class WebSocketManager:
    """Manages WebSocket connections and reactive data distribution."""

    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.device_list_connections: Set[WebSocket] = set()

        self.connection_stats = {
            "total_sensor_connections": 0,
            "total_device_list_connections": 0,
            "messages_sent": 0,
            "last_device_update": None,
            "failed_sends": 0
        }

        self.last_device_list_update = None
        self.device_update_debounce_time = 0.5  # 500ms debounce

        EventBus.subscribe("sensor_update", self.handle_sensor_update)
        EventBus.subscribe("device_connected", self.handle_device_connected)
        EventBus.subscribe("device_disconnected", self.handle_device_disconnected)

        Logger.log_message("WebSocketManager initialized with reactive configuration")

    async def connect(self, websocket: WebSocket, device_id: str, sensor_type: str):
        """
        Connect a new WebSocket for specific sensor.

        Args:
            websocket (WebSocket): WebSocket connection
            device_id (str): Device identifier
            sensor_type (str): Sensor type
        """
        await websocket.accept()

        client_key = f"{device_id}_{sensor_type}"
        if client_key not in self.active_connections:
            self.active_connections[client_key] = []

        self.active_connections[client_key].append(websocket)
        self.connection_stats["total_sensor_connections"] += 1

        Logger.log_message(f"WebSocket connected: {client_key} (total: {len(self.active_connections[client_key])})")

        await self.send_historical_data(websocket, device_id, sensor_type)
        await self.send_connection_stats(websocket)

    async def connect_device_list(self, websocket: WebSocket):
        """
        Connect a WebSocket to receive device list updates.

        Args:
            websocket (WebSocket): WebSocket connection
        """
        await websocket.accept()
        self.device_list_connections.add(websocket)
        self.connection_stats["total_device_list_connections"] += 1

        Logger.log_message(f"WebSocket connected for device list (total: {len(self.device_list_connections)})")

        await self.send_device_list_update(websocket)

    def disconnect(self, websocket: WebSocket, device_id: str, sensor_type: str):
        """
        Disconnect a WebSocket from specific sensor.

        Args:
            websocket (WebSocket): WebSocket connection
            device_id (str): Device identifier
            sensor_type (str): Sensor type
        """
        client_key = f"{device_id}_{sensor_type}"

        if client_key in self.active_connections:
            if websocket in self.active_connections[client_key]:
                self.active_connections[client_key].remove(websocket)
                self.connection_stats["total_sensor_connections"] -= 1

            if not self.active_connections[client_key]:
                del self.active_connections[client_key]

        Logger.log_message(f"WebSocket disconnected: {client_key}")

    def disconnect_device_list(self, websocket: WebSocket):
        """
        Disconnect a WebSocket from device list.

        Args:
            websocket (WebSocket): WebSocket connection
        """
        self.device_list_connections.discard(websocket)
        self.connection_stats["total_device_list_connections"] -= 1
        Logger.log_message(f"Device list WebSocket disconnected (remaining: {len(self.device_list_connections)})")

    async def send_historical_data(self, websocket: WebSocket, device_id: str, sensor_type: str):
        """
        Send historical data when connecting.

        Args:
            websocket (WebSocket): WebSocket connection
            device_id (str): Device identifier
            sensor_type (str): Sensor type
        """
        try:
            from src.connection.bluetooth_server import DeviceManager

            devices = DeviceManager.get_all_devices()
            if device_id in devices and sensor_type in devices[device_id]["sensors"]:
                sensor = devices[device_id]["sensors"][sensor_type]
                data = sensor.get_data()

                current_time = time.time()
                data_points = len(data.get("time", []))

                message = {
                    "type": "historical",
                    "device_id": device_id,
                    "sensor_type": sensor_type,
                    "data": data,
                    "metadata": {
                        "data_points": data_points,
                        "timestamp": current_time,
                        "has_data": data_points > 0
                    }
                }

                await websocket.send_text(json.dumps(message))
                self.connection_stats["messages_sent"] += 1
            else:
                await websocket.send_text(json.dumps({
                    "type": "no_data",
                    "device_id": device_id,
                    "sensor_type": sensor_type,
                    "message": "Sensor not found or no data available"
                }))

        except Exception as e:
            Logger.log_error(f"Error sending historical data: {e}")
            self.connection_stats["failed_sends"] += 1

    async def send_connection_stats(self, websocket: WebSocket):
        """
        Send connection statistics to client.

        Args:
            websocket (WebSocket): WebSocket connection
        """
        try:
            stats_message = {
                "type": "connection_stats",
                "stats": self.connection_stats.copy(),
                "timestamp": time.time()
            }
            await websocket.send_text(json.dumps(stats_message))
        except Exception as e:
            Logger.log_error(f"Error sending statistics: {e}")

    async def send_device_list_update(self, websocket: WebSocket = None):
        """
        Send device list update with debounce.

        Args:
            websocket (WebSocket, optional): Specific WebSocket. If None, sends to all.
        """
        current_time = time.time()

        # Debounce to avoid update spam
        if (self.last_device_list_update and
                current_time - self.last_device_list_update < self.device_update_debounce_time):
            Logger.log_message("Device update in debounce, skipping...")
            return

        self.last_device_list_update = current_time

        try:
            from src.connection.bluetooth_server import DeviceManager

            devices = DeviceManager.get_serializable_devices()

            message = {
                "type": "device_list_update",
                "devices": devices,
                "metadata": {
                    "device_count": len(devices),
                    "timestamp": current_time,
                    "active_connections": len(self.device_list_connections)
                }
            }

            message_json = json.dumps(message)

            if websocket:
                await websocket.send_text(message_json)
                self.connection_stats["messages_sent"] += 1
                Logger.log_message(f"Device list sent to specific client ({len(devices)} devices)")
            else:
                failed_connections = []
                sent_count = 0

                for ws in self.device_list_connections.copy():
                    try:
                        await ws.send_text(message_json)
                        sent_count += 1
                        self.connection_stats["messages_sent"] += 1
                    except Exception as e:
                        Logger.log_message(f"Error sending device list: {e}")
                        failed_connections.append(ws)
                        self.connection_stats["failed_sends"] += 1

                for ws in failed_connections:
                    self.device_list_connections.discard(ws)
                    self.connection_stats["total_device_list_connections"] -= 1

            self.connection_stats["last_device_update"] = current_time

        except Exception as e:
            Logger.log_message(f"Error sending device list: {e}")
            self.connection_stats["failed_sends"] += 1

    def handle_sensor_update(self, event_data):
        """
        Handle sensor update events (Event Bus callback).

        Args:
            event_data (dict): Event data containing device_id, sensor_type and data
        """
        try:
            device_id = event_data["device_id"]
            sensor_type = event_data["sensor_type"]
            data = event_data["data"]

            task = asyncio.create_task(
                self.send_sensor_update(device_id, sensor_type, data)
            )

            task.add_done_callback(lambda t: self._handle_task_result(t, f"sensor_update_{device_id}_{sensor_type}"))

        except Exception as e:
            Logger.log_error(f"Error processing sensor update: {e}")

    def handle_device_connected(self, event_data):
        """
        Handle device connection events.

        Args:
            event_data (dict): Event data
        """
        try:
            device_name = event_data.get('device_name', 'Unknown')
            Logger.log_message(f"Device connected: {device_name}")

            task = asyncio.create_task(self.send_device_list_update())
            task.add_done_callback(lambda t: self._handle_task_result(t, "device_connected"))

        except Exception as e:
            Logger.log_error(f"Error processing device connection: {e}")

    def handle_device_disconnected(self, event_data):
        """
        Handle device disconnection events.

        Args:
            event_data (dict): Event data
        """
        try:
            device_name = event_data.get('device_name', 'Unknown')
            Logger.log_message(f"Device disconnected: {device_name}")

            task = asyncio.create_task(self.send_device_list_update())
            task.add_done_callback(lambda t: self._handle_task_result(t, "device_disconnected"))

        except Exception as e:
            Logger.log_message(f"Error processing device disconnection: {e}")

    def _handle_task_result(self, task, context):
        """
        Handle asynchronous task results.

        Args:
            task: Completed task
            context: Context for logging
        """
        try:
            if task.exception():
                Logger.log_error(f"Error in task {context}: {task.exception()}")
                self.connection_stats["failed_sends"] += 1
        except Exception:
            pass  # Ignore logging errors

    async def send_sensor_update(self, device_id: str, sensor_type: str, data: dict):
        """
        Send sensor data update to WebSocket clients.

        Args:
            device_id (str): Device identifier
            sensor_type (str): Sensor type
            data (dict): Sensor data
        """
        client_key = f"{device_id}_{sensor_type}"

        if client_key not in self.active_connections:
            return

        current_time = time.time()
        data_points = len(data.get("time", []))

        message = {
            "type": "update",
            "device_id": device_id,
            "sensor_type": sensor_type,
            "data": data,
            "metadata": {
                "data_points": data_points,
                "timestamp": current_time,
                "latest_value": {
                    "x": data.get("x", [None])[-1] if data.get("x") else None,
                    "y": data.get("y", [None])[-1] if data.get("y") else None,
                    "z": data.get("z", [None])[-1] if data.get("z") else None,
                } if data_points > 0 else None
            }
        }

        message_json = json.dumps(message)

        # Copy to avoid modification during iteration
        connections_copy = self.active_connections[client_key].copy()
        failed_connections = []
        sent_count = 0

        for websocket in connections_copy:
            try:
                await websocket.send_text(message_json)
                sent_count += 1
                self.connection_stats["messages_sent"] += 1
            except Exception as e:
                Logger.log_error(f"Error sending WebSocket data to {client_key}: {e}")
                failed_connections.append(websocket)
                self.connection_stats["failed_sends"] += 1

        for websocket in failed_connections:
            self.disconnect(websocket, device_id, sensor_type)

    def get_connection_count(self):
        """
        Get total number of active connections.

        Returns:
            dict: Detailed connection statistics
        """
        sensor_connections = sum(len(connections) for connections in self.active_connections.values())
        device_list_connections = len(self.device_list_connections)

        return {
            "sensor_connections": sensor_connections,
            "device_list_connections": device_list_connections,
            "total_connections": sensor_connections + device_list_connections,
            "active_sensor_types": len(self.active_connections),
            "stats": self.connection_stats.copy()
        }

    def get_health_status(self):
        """
        Get WebSocket Manager health status.

        Returns:
            dict: Health status information
        """
        current_time = time.time()
        stats = self.get_connection_count()

        total_attempts = self.connection_stats["messages_sent"] + self.connection_stats["failed_sends"]
        failure_rate = (self.connection_stats["failed_sends"] / total_attempts * 100) if total_attempts > 0 else 0

        return {
            "status": "healthy" if failure_rate < 10 else "degraded" if failure_rate < 50 else "unhealthy",
            "timestamp": current_time,
            "connections": stats,
            "failure_rate_percent": round(failure_rate, 2),
            "last_device_update": self.connection_stats["last_device_update"],
            "uptime_seconds": current_time - (self.connection_stats.get("start_time", current_time))
        }