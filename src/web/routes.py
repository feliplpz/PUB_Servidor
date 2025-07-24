from src.connection.bluetooth_server import DeviceManager
from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import json
import time
from src.utils.logging import Logger

def register_routes(app, templates, websocket_manager):

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Rota principal que lista todos os dispositivos conectados"""
        devices = DeviceManager.get_serializable_devices()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "devices": devices
        })

    @app.get("/device/{device_id}", response_class=HTMLResponse)
    async def device_page(request: Request, device_id: str):
        """Rota para página específica de um dispositivo"""
        devices = DeviceManager.get_all_devices()
        if device_id not in devices:
            return RedirectResponse(url="/")

        device = devices[device_id]

        try:
            sensor_keys = list(device.get("sensors", {}).keys())
            Logger.log_message(f"Renderizando página do dispositivo {device_id} com sensores: {sensor_keys}")
        except Exception as e:
            Logger.log_message(f"Erro ao listar sensores para template: {e}")
            sensor_keys = []

        return templates.TemplateResponse("device.html", {
            "request": request,
            "device": device,
            "device_id": device_id
        })

    @app.get("/api/devices")
    async def get_all_devices():
        """API para obter lista de todos os dispositivos"""
        devices = DeviceManager.get_serializable_devices()
        return devices

    @app.get("/api/device/{device_id}/info")
    async def get_device_info(device_id: str):
        """API para obter informações detalhadas de um dispositivo incluindo status dos sensores"""
        devices = DeviceManager.get_all_devices()

        if device_id not in devices:
            return JSONResponse({"error": "Dispositivo não encontrado"}, status_code=404)

        device = devices[device_id]
        current_time = time.time()

        RECENT_DATA_THRESHOLD = 4.0

        sensor_info = {}
        for sensor_type, sensor in device.get("sensors", {}).items():
            try:
                data = sensor.get_data()

                has_data = len(data.get("time", [])) > 0

                last_data_time = None
                time_since_update = None
                is_recent = False

                if has_data and data.get("time"):
                    last_relative_time = data["time"][-1]
                    sensor_start_time = getattr(sensor, 'start_time', current_time)
                    last_data_time = sensor_start_time + last_relative_time

                    time_since_update = current_time - last_data_time

                    is_recent = time_since_update < RECENT_DATA_THRESHOLD

                data_stats = None
                if has_data and data.get("x") and data.get("y") and data.get("z"):
                    try:
                        import statistics
                        data_stats = {
                            "x": {
                                "latest": data["x"][-1] if data["x"] else None
                            },
                            "y": {
                                "latest": data["y"][-1] if data["y"] else None
                            },
                            "z": {
                                "latest": data["z"][-1] if data["z"] else None
                            }
                        }
                    except Exception:
                        data_stats = None

                sensor_info[sensor_type] = {
                    "type": sensor_type,
                    "has_data": has_data,
                    "is_active": has_data and is_recent,
                    "data_points": len(data.get("time", [])),
                    "last_update_absolute": last_data_time,
                    "time_since_last_update": time_since_update,
                    "is_recent": is_recent,
                    "recent_threshold": RECENT_DATA_THRESHOLD,
                    "time_range": {
                        "start": data.get("time", [None])[0],
                        "end": data.get("time", [None])[-1],
                        "duration": data.get("time", [None])[-1] - data.get("time", [None])[0]
                                   if len(data.get("time", [])) > 0 else None
                    } if data.get("time") else None,
                    "data_stats": data_stats,
                    "sensor_start_time": getattr(sensor, 'start_time', None)
                }

                sensor_info[sensor_type]["debug_info"] = {
                    "sensor_start_time": getattr(sensor, 'start_time', None),
                    "current_time": current_time,
                    "last_relative_time": data.get("time", [None])[-1] if data.get("time") else None,
                    "calculated_absolute_time": last_data_time,
                    "threshold_used": RECENT_DATA_THRESHOLD
                }

            except Exception as e:
                Logger.log_message(f"Erro ao processar sensor {sensor_type}: {e}")
                sensor_info[sensor_type] = {
                    "type": sensor_type,
                    "has_data": False,
                    "is_active": False,
                    "data_points": 0,
                    "error": str(e),
                    "time_since_last_update": None,
                    "is_recent": False
                }

        active_sensors = len([s for s in sensor_info.values() if s.get("is_active", False)])
        total_sensors = len(sensor_info)

        response_data = {
            "device_id": device_id,
            "device_name": device["name"],
            "connected_at": device["connected_at"],
            "sensors": sensor_info,
            "total_sensors": total_sensors,
            "active_sensors": active_sensors,
            "timestamp": current_time,
            "server_config": {
                "recent_data_threshold": RECENT_DATA_THRESHOLD,
                "check_time": current_time
            }
        }

        return response_data

    @app.get("/api/device/{device_id}/data/{sensor_type}")
    async def get_device_data(device_id: str, sensor_type: str):
        """Rota API para obter dados de um sensor específico"""
        devices = DeviceManager.get_all_devices()

        if device_id not in devices or sensor_type not in devices[device_id]["sensors"]:
            return JSONResponse({"error": "Dispositivo ou sensor não encontrado"}, status_code=404)

        sensor = devices[device_id]["sensors"][sensor_type]
        data = sensor.get_data()

        current_time = time.time()
        last_update_time = None
        time_since_update = None

        if data.get("time") and len(data["time"]) > 0:
            last_relative_time = data["time"][-1]
            sensor_start_time = getattr(sensor, 'start_time', current_time)
            last_update_time = sensor_start_time + last_relative_time
            time_since_update = current_time - last_update_time

        return {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "data_points": len(data.get("time", [])),
            "data": data,
            "metadata": {
                "last_update_time": last_update_time,
                "time_since_update": time_since_update,
                "sensor_start_time": getattr(sensor, 'start_time', None),
                "is_recent": time_since_update < 5.0 if time_since_update else False,
                "current_server_time": current_time
            }
        }

    @app.websocket("/ws/device/{device_id}/sensor/{sensor_type}")
    async def websocket_endpoint(websocket: WebSocket, device_id: str, sensor_type: str):
        Logger.log_message(f"CONEXÃO WEBSOCKET: {device_id}_{sensor_type}")
        await websocket_manager.connect(websocket, device_id, sensor_type)

        try:
            while True:
                # Recebe mensagens do cliente (pode ser usado para heartbeat)
                message = await websocket.receive_text()
                Logger.log_message(f"websocket_endpoint:  MENSAGEM RECEBIDA: {message}")
                if message == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            Logger.log_message(f" WEBSOCKET DESCONECTADO: {device_id}_{sensor_type}")
            websocket_manager.disconnect(websocket, device_id, sensor_type)

    @app.websocket("/ws/devices")
    async def device_list_websocket(websocket: WebSocket):
        """WebSocket para atualizações da lista de dispositivos"""
        Logger.log_message("CONEXÃO WEBSOCKET: lista de dispositivos")
        await websocket_manager.connect_device_list(websocket)

        try:
            while True:
                message = await websocket.receive_text()
                Logger.log_message(f"device_list_websocket: MENSAGEM RECEBIDA: {message}")

                if message == "ping":
                    await websocket.send_text("pong")
                elif message == "request_update":
                    Logger.log_message(" liente solicitou atualização manual da lista")
                    await websocket_manager.send_device_list_update(websocket)
                elif message.startswith("{"):
                    try:
                        cmd = json.loads(message)
                        if cmd.get("type") == "request_update":
                            await websocket_manager.send_device_list_update(websocket)
                    except json.JSONDecodeError:
                        pass

        except WebSocketDisconnect as web_socket_disconnect_err:
            Logger.log_message(f"WebSocket da lista de dispositivos desconectado: {web_socket_disconnect_err}")
            websocket_manager.disconnect_device_list(websocket)
        except Exception as err:
            Logger.log_message(f"Exceção ocorreu em device_list_websocket: {err}")