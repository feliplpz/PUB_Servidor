from src.bluetooth.bluetooth_server import DeviceManager
from src.data.data_visualizer import DataVisualizer
from flask import jsonify, render_template, Response, redirect, url_for


def register_routes(app):
    """Registra as rotas da aplicação Flask"""

    @app.route("/")
    def index():
        """
        Rota principal que lista todos os dispositivos conectados

        Returns:
            str: Página HTML com a lista de dispositivos
        """
        devices = DeviceManager.get_all_devices()
        return render_template("index.html", devices=devices)

    @app.route("/device/<device_id>")
    def device_page(device_id):
        """
        Rota para página específica de um dispositivo

        Args:
            device_id (str): ID do dispositivo

        Returns:
            str: Página HTML com detalhes do dispositivo e seus sensores
        """
        devices = DeviceManager.get_all_devices()
        if device_id not in devices:
            return redirect(url_for("index"))

        return render_template(
            "device.html",
            device=devices[device_id],
            device_id=device_id,
        )

    @app.route("/api/device/<device_id>/data/<sensor_type>")
    def get_device_data(device_id, sensor_type):
        """
        Rota API para obter dados de um sensor específico

        Args:
            device_id (str): ID do dispositivo
            sensor_type (str): Tipo de sensor

        Returns:
            json: Dados do sensor
        """
        devices = DeviceManager.get_all_devices()

        if device_id not in devices or sensor_type not in devices[device_id]["sensors"]:
            return jsonify({"error": "Dispositivo ou sensor não encontrado"}), 404

        sensor = devices[device_id]["sensors"][sensor_type]
        return jsonify(sensor.get_data())

    @app.route("/api/device/<device_id>/plot/<sensor_type>.png")
    def get_device_plot(device_id, sensor_type):
        """
        Rota para obter o gráfico de um sensor específico

        Args:
            device_id (str): ID do dispositivo
            sensor_type (str): Tipo de sensor

        Returns:
            Response: Imagem do gráfico em formato PNG
        """
        img = DataVisualizer.generate_plot_data(device_id, sensor_type)

        if img:
            return Response(img.getvalue(), mimetype="image/png")
        else:
            return Response(status=404)
