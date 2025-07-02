from src.connection.bluetooth_server import DeviceManager
from src.data.data_visualizer import DataVisualizer
from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
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
        devices = DeviceManager.get_all_devices()  # Aqui mantemos get_all_devices pois precisamos dos objetos sensores
        if device_id not in devices:
            return RedirectResponse(url="/")
        
        device = devices[device_id]
        
        # Para o template, vamos garantir que device.sensors existe e é serializável para JavaScript
        try:
            # Verifica se os sensores podem ser listados
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
        
        # Configuração mais reativa - dados "recentes" se atualizados nos últimos 4 segundos
        RECENT_DATA_THRESHOLD = 4.0  # Era 10 segundos, agora 4 segundos
        
        # Coleta informações detalhadas sobre cada sensor
        sensor_info = {}
        for sensor_type, sensor in device.get("sensors", {}).items():
            try:
                data = sensor.get_data()
                
                # Verifica se tem dados
                has_data = len(data.get("time", [])) > 0
                
                # Calcula tempo desde última atualização
                last_data_time = None
                time_since_update = None
                is_recent = False
                
                if has_data and data.get("time"):
                    # Pega o último timestamp relativo e converte para tempo absoluto
                    last_relative_time = data["time"][-1]
                    sensor_start_time = getattr(sensor, 'start_time', current_time)
                    last_data_time = sensor_start_time + last_relative_time
                    
                    # Calcula tempo decorrido desde última atualização
                    time_since_update = current_time - last_data_time
                    
                    # Considera recente se foi atualizado dentro do threshold
                    is_recent = time_since_update < RECENT_DATA_THRESHOLD
                
                # Calcula estatísticas dos dados se disponíveis
                data_stats = None
                if has_data and data.get("x") and data.get("y") and data.get("z"):
                    try:
                        import statistics
                        data_stats = {
                            "x": {
                                "min": min(data["x"]),
                                "max": max(data["x"]),
                                "avg": statistics.mean(data["x"]),
                                "latest": data["x"][-1] if data["x"] else None
                            },
                            "y": {
                                "min": min(data["y"]),
                                "max": max(data["y"]),
                                "avg": statistics.mean(data["y"]),
                                "latest": data["y"][-1] if data["y"] else None
                            },
                            "z": {
                                "min": min(data["z"]),
                                "max": max(data["z"]),
                                "avg": statistics.mean(data["z"]),
                                "latest": data["z"][-1] if data["z"] else None
                            }
                        }
                    except Exception:
                        data_stats = None
                
                sensor_info[sensor_type] = {
                    "type": sensor_type,
                    "has_data": has_data,
                    "is_active": has_data and is_recent,  # Ativo = tem dados recentes
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
                
                # Debug info adicional
                sensor_info[sensor_type]["debug_info"] = {
                    "sensor_start_time": getattr(sensor, 'start_time', None),
                    "current_time": current_time,
                    "last_relative_time": data.get("time", [None])[-1] if data.get("time") else None,
                    "calculated_absolute_time": last_data_time,
                    "threshold_used": RECENT_DATA_THRESHOLD
                }
                
            except Exception as e:
                print(f"Erro ao processar sensor {sensor_type}: {e}")
                sensor_info[sensor_type] = {
                    "type": sensor_type,
                    "has_data": False,
                    "is_active": False,
                    "data_points": 0,
                    "error": str(e),
                    "time_since_last_update": None,
                    "is_recent": False
                }
        
        # Conta sensores ativos
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

         # print(f"Info para {device_id}: {active_sensors}/{total_sensors} sensores ativos")
        return response_data

    @app.get("/api/device/{device_id}/status")
    async def get_device_status(device_id: str):
        """API rápida para verificar apenas o status dos sensores (sem dados completos)"""
        devices = DeviceManager.get_all_devices()
        
        if device_id not in devices:
            return JSONResponse({"error": "Dispositivo não encontrado"}, status_code=404)
        
        device = devices[device_id]
        current_time = time.time()
        
        # Threshold mais responsivo para verificação rápida
        QUICK_CHECK_THRESHOLD = 3.0  # 3 segundos para verificação rápida
        
        sensor_status = {}
        for sensor_type, sensor in device.get("sensors", {}).items():
            try:
                data = sensor.get_data()
                has_data = len(data.get("time", [])) > 0
                
                # Verifica se dados são recentes
                is_recent = False
                time_since_update = None
                
                if has_data and data.get("time"):
                    last_relative_time = data["time"][-1]
                    sensor_start_time = getattr(sensor, 'start_time', current_time)
                    last_data_time = sensor_start_time + last_relative_time
                    time_since_update = current_time - last_data_time
                    is_recent = time_since_update < QUICK_CHECK_THRESHOLD
                
                sensor_status[sensor_type] = {
                    "active": has_data and is_recent,
                    "data_points": len(data.get("time", [])),
                    "has_data": has_data,
                    "is_recent": is_recent,
                    "time_since_update": time_since_update
                }
                
            except Exception as e:
                print(f"Erro no status rápido {sensor_type}: {e}")
                sensor_status[sensor_type] = {
                    "active": False,
                    "data_points": 0,
                    "has_data": False,
                    "is_recent": False,
                    "error": str(e)
                }
        
        active_count = sum(1 for s in sensor_status.values() if s.get("active", False))
        
        return {
            "device_id": device_id,
            "sensors": sensor_status,
            "active_count": active_count,
            "total_count": len(sensor_status),
            "timestamp": current_time,
            "threshold_used": QUICK_CHECK_THRESHOLD
        }

    @app.get("/api/device/{device_id}/data/{sensor_type}") 
    async def get_device_data(device_id: str, sensor_type: str):  
        """Rota API para obter dados de um sensor específico"""
        devices = DeviceManager.get_all_devices()
        
        if device_id not in devices or sensor_type not in devices[device_id]["sensors"]:
            return JSONResponse({"error": "Dispositivo ou sensor não encontrado"}, status_code=404)  
        
        sensor = devices[device_id]["sensors"][sensor_type]
        data = sensor.get_data()
        
        # Calcula metadados dos dados
        current_time = time.time()
        last_update_time = None
        time_since_update = None
        
        if data.get("time") and len(data["time"]) > 0:
            last_relative_time = data["time"][-1]
            sensor_start_time = getattr(sensor, 'start_time', current_time)
            last_update_time = sensor_start_time + last_relative_time
            time_since_update = current_time - last_update_time
        
        # Adiciona metadados aos dados
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

    @app.get("/api/device/{device_id}/plot/{sensor_type}.png")  
    async def get_device_plot(device_id: str, sensor_type: str): 
        """Rota para obter o gráfico de um sensor específico"""
        img = DataVisualizer.generate_plot_data(device_id, sensor_type)
        
        if img:
            return Response(content=img.getvalue(), media_type="image/png")  
        else:
            return Response(status_code=404)  
        
    @app.websocket("/ws/device/{device_id}/sensor/{sensor_type}")
    async def websocket_endpoint(websocket: WebSocket, device_id: str, sensor_type: str):
        print(f"CONEXÃO WEBSOCKET: {device_id}_{sensor_type}") 
        await websocket_manager.connect(websocket, device_id, sensor_type) 
        
        try:
            while True:
                # Recebe mensagens do cliente (pode ser usado para heartbeat)
                message = await websocket.receive_text()
                print(f"websocket_endpoint: 📨 MENSAGEM RECEBIDA: {message}")
                if message == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            print(f" WEBSOCKET DESCONECTADO: {device_id}_{sensor_type}")
            websocket_manager.disconnect(websocket, device_id, sensor_type) 

    @app.websocket("/ws/devices")
    async def device_list_websocket(websocket: WebSocket):
        """WebSocket para atualizações da lista de dispositivos"""
        print("CONEXÃO WEBSOCKET: lista de dispositivos")
        await websocket_manager.connect_device_list(websocket)
        
        try:
            while True:
                # Recebe mensagens do cliente
                message = await websocket.receive_text()
                print(f"device_list_websocket: 📨 MENSAGEM RECEBIDA: {message}")
                
                # Suporte a comandos especiais
                if message == "ping":
                    await websocket.send_text("pong")
                elif message == "request_update":
                    # Cliente solicitou atualização manual
                    print(" liente solicitou atualização manual da lista")
                    await websocket_manager.send_device_list_update(websocket)
                elif message.startswith("{"):
                    # Tenta parsear como JSON para comandos mais complexos
                    try:
                        cmd = json.loads(message)
                        if cmd.get("type") == "request_update":
                            await websocket_manager.send_device_list_update(websocket)
                    except json.JSONDecodeError:
                        pass
                        
        except WebSocketDisconnect as web_socket_disconnect_err:
            print(f"WebSocket da lista de dispositivos desconectado: {web_socket_disconnect_err}")
            websocket_manager.disconnect_device_list(websocket)
        except Exception as err:
            print(f"Exceção ocorreu em device_list_websocket: {err}")