from src.connection.bluetooth_server import DeviceManager
from src.data.data_visualizer import DataVisualizer
from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
def register_routes(app, templates,websocket_manager):
    
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
        
        return templates.TemplateResponse("device.html", {
            "request": request,
            "device": devices[device_id],
            "device_id": device_id
        })

    @app.get("/api/device/{device_id}/data/{sensor_type}") 
    async def get_device_data(device_id: str, sensor_type: str):  
        """Rota API para obter dados de um sensor específico"""
        devices = DeviceManager.get_all_devices()
        
        if device_id not in devices or sensor_type not in devices[device_id]["sensors"]:
            return JSONResponse({"error": "Dispositivo ou sensor não encontrado"}, status_code=404)  
        
        sensor = devices[device_id]["sensors"][sensor_type]
        return sensor.get_data() 

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
        print(f"ENTATIVA DE CONEXÃO: {device_id}_{sensor_type}") 
        await websocket_manager.connect(websocket, device_id, sensor_type) 
        
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket, device_id, sensor_type) 

    @app.websocket("/ws/devices")
    async def device_list_websocket(websocket: WebSocket):
            await websocket.accept()
        