# Arquivo src/web/routes.py atualizado para suportar verificação de status de sensores

from src.connection.bluetooth_server import DeviceManager
from src.data.data_visualizer import DataVisualizer
from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
import json
import time

def register_routes(app, templates, websocket_manager):
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Rota principal que lista todos os dispositivos conectados"""
        devices = DeviceManager.get_all_devices()
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
        
        return templates.TemplateResponse("device.html", {
            "request": request,
            "device": device,
            "device_id": device_id
        })

    @app.get("/api/devices")
    async def get_all_devices():
        """API para obter lista de todos os dispositivos"""
        devices = DeviceManager.get_all_devices()
        return devices

    @app.get("/api/device/{device_id}/info")
    async def get_device_info(device_id: str):
        """API para obter informações detalhadas de um dispositivo incluindo status dos sensores"""
        devices = DeviceManager.get_all_devices()
        
        if device_id not in devices:
            return JSONResponse({"error": "Dispositivo não encontrado"}, status_code=404)
        
        device = devices[device_id]
        current_time = time.time()
        
        # Coleta informações detalhadas sobre cada sensor
        sensor_info = {}
        for sensor_type, sensor in device.get("sensors", {}).items():
            try:
                data = sensor.get_data()
                
                # Considera sensor ativo se:
                # 1. Tem dados
                # 2. Dados foram atualizados recentemente (últimos 10 segundos)
                has_data = len(data.get("time", [])) > 0
                
                # Verifica se dados são recentes
                last_data_time = None
                is_recent = False
                
                if has_data and data.get("time"):
                    # Pega o último timestamp e converte para tempo absoluto
                    last_relative_time = data["time"][-1]
                    sensor_start_time = getattr(sensor, 'start_time', current_time)
                    last_data_time = sensor_start_time + last_relative_time
                    
                    # Considera recente se foi atualizado nos últimos 10 segundos
                    is_recent = (current_time - last_data_time) < 10.0
                
                sensor_info[sensor_type] = {
                    "type": sensor_type,
                    "has_data": has_data,
                    "is_active": has_data and is_recent,  # Sensor ativo = tem dados recentes
                    "data_points": len(data.get("time", [])),
                    "last_update": last_data_time,
                    "is_recent": is_recent,
                    "time_since_last_update": current_time - last_data_time if last_data_time else None,
                    "time_range": {
                        "start": data.get("time", [None])[0],
                        "end": data.get("time", [None])[-1]
                    } if data.get("time") else None,
                    "data_ranges": {
                        "x": {
                            "min": min(data.get("x", [0])) if data.get("x") else None,
                            "max": max(data.get("x", [0])) if data.get("x") else None
                        },
                        "y": {
                            "min": min(data.get("y", [0])) if data.get("y") else None,
                            "max": max(data.get("y", [0])) if data.get("y") else None
                        },
                        "z": {
                            "min": min(data.get("z", [0])) if data.get("z") else None,
                            "max": max(data.get("z", [0])) if data.get("z") else None
                        }
                    } if data.get("x") and data.get("y") and data.get("z") else None
                }
            except Exception as e:
                print(f"Erro ao processar sensor {sensor_type}: {e}")
                sensor_info[sensor_type] = {
                    "type": sensor_type,
                    "has_data": False,
                    "is_active": False,
                    "error": str(e)
                }
        
        active_sensors = len([s for s in sensor_info.values() if s.get("is_active", False)])
        
        return {
            "device_id": device_id,
            "device_name": device["name"],
            "connected_at": device["connected_at"],
            "sensors": sensor_info,
            "total_sensors": len(sensor_info),
            "active_sensors": active_sensors,
            "timestamp": current_time
        }

    @app.get("/api/device/{device_id}/status")
    async def get_device_status(device_id: str):
        """API rápida para verificar apenas o status dos sensores (sem dados completos)"""
        devices = DeviceManager.get_all_devices()
        
        if device_id not in devices:
            return JSONResponse({"error": "Dispositivo não encontrado"}, status_code=404)
        
        device = devices[device_id]
        current_time = time.time()
        
        sensor_status = {}
        for sensor_type, sensor in device.get("sensors", {}).items():
            try:
                data = sensor.get_data()
                has_data = len(data.get("time", [])) > 0
                
                # Verifica se dados são recentes
                is_recent = False
                if has_data and data.get("time"):
                    last_relative_time = data["time"][-1]
                    sensor_start_time = getattr(sensor, 'start_time', current_time)
                    last_data_time = sensor_start_time + last_relative_time
                    is_recent = (current_time - last_data_time) < 10.0
                
                sensor_status[sensor_type] = {
                    "active": has_data and is_recent,
                    "data_points": len(data.get("time", [])),
                    "has_data": has_data,
                    "is_recent": is_recent
                }
            except Exception as e:
                sensor_status[sensor_type] = {
                    "active": False,
                    "error": str(e)
                }
        
        return {
            "device_id": device_id,
            "sensors": sensor_status,
            "timestamp": current_time
        }

    @app.get("/api/device/{device_id}/data/{sensor_type}") 
    async def get_device_data(device_id: str, sensor_type: str):  
        """Rota API para obter dados de um sensor específico"""
        devices = DeviceManager.get_all_devices()
        
        if device_id not in devices or sensor_type not in devices[device_id]["sensors"]:
            return JSONResponse({"error": "Dispositivo ou sensor não encontrado"}, status_code=404)  
        
        sensor = devices[device_id]["sensors"][sensor_type]
        data = sensor.get_data()
        
        # Adiciona metadados aos dados
        return {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "data_points": len(data.get("time", [])),
            "data": data,
            "timestamp": data.get("time", [None])[-1] if data.get("time") else None
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
        print(f"TENTATIVA DE CONEXÃO WEBSOCKET: {device_id}_{sensor_type}") 
        await websocket_manager.connect(websocket, device_id, sensor_type) 
        
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            print(f"WEBSOCKET DESCONECTADO: {device_id}_{sensor_type}")
            websocket_manager.disconnect(websocket, device_id, sensor_type) 

    @app.websocket("/ws/devices")
    async def device_list_websocket(websocket: WebSocket):
        """WebSocket para atualizações da lista de dispositivos"""
        await websocket_manager.connect_device_list(websocket)
        
        try:
            while True:
                # Mantém conexão viva - dispositivos são atualizados via EventBus
                await websocket.receive_text()
        except WebSocketDisconnect:
            print("WebSocket da lista de dispositivos desconectado")
            websocket_manager.disconnect_device_list(websocket)