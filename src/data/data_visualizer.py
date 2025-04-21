from io import BytesIO
from src.utils.logging import Logger
from src.connection.bluetooth_server import DeviceManager


class DataVisualizer:
    """Gerencia a visualização de dados dos sensores"""

    @staticmethod
    def generate_plot_data(device_id, sensor_type):
        """
        Gera dados para o gráfico

        Args:
            device_id (str): ID do dispositivo
            sensor_type (str): Tipo de sensor

        Returns:
            BytesIO: Objeto contendo a imagem do gráfico em formato PNG
        """
        try:
            # Importa aqui para evitar problemas em threads
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            devices = DeviceManager.get_all_devices()

            if (
                device_id not in devices
                or sensor_type not in devices[device_id]["sensors"]
            ):
                return None

            sensor = devices[device_id]["sensors"][sensor_type]
            data = sensor.get_data()

            if sensor_type == "accelerometer":
                fig, axes = plt.subplots(3, 1, figsize=(10, 8))

                for ax, data_axis, label, color in zip(
                    axes,
                    [data["x"], data["y"], data["z"]],
                    ["X", "Y", "Z"],
                    ["blue", "orange", "green"],
                ):
                    ax.plot(
                        data["time"],
                        data_axis,
                        color=color,
                        label=f"Aceleração {label}",
                    )
                    ax.legend()
                    ax.set_xlabel("Tempo (s)")
                    ax.set_ylabel("Aceleração (m/s²)")
                    ax.grid(True)

                plt.tight_layout()
                img = BytesIO()
                plt.savefig(img, format="png")
                plt.close(fig)
                img.seek(0)
                return img

            return None

        except Exception as e:
            Logger.log_message(f"Erro ao gerar gráfico: {e}")
            return None
