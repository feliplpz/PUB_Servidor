import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.fftpack import fft
from scipy.stats import skew, kurtosis

# Função para carregar e limpar os dados
def load_and_clean_data(file_path):
    try:
        data = pd.read_csv(file_path)
        required_columns = ['timestamp', 'accel_x', 'accel_y', 'accel_z']
        
        # Verifica se as colunas existem
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"Coluna {col} ausente no arquivo.")
        
        # Converte timestamp
        data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')
        
        # Remove linhas com NaN
        data = data.dropna()
        
        # Verifica se há dados restantes
        if data.empty:
            raise ValueError("O arquivo CSV não contém dados válidos após limpeza.")
        
        return data
    except Exception as e:
        print(f"Erro ao carregar o arquivo {file_path}: {e}")
        return None
# Cálculo de estatísticas com rótulos em português
def calculate_statistics(data):
    stats = {
        'accel_x_mean': np.mean(data['accel_x']),
        'accel_y_mean': np.mean(data['accel_y']),
        'accel_z_mean': np.mean(data['accel_z']),
        'accel_x_std': np.std(data['accel_x'], ddof=1),
        'accel_y_std': np.std(data['accel_y'], ddof=1),
        'accel_z_std': np.std(data['accel_z'], ddof=1),
        'accel_x_skew': skew(data['accel_x']),
        'accel_y_skew': skew(data['accel_y']),
        'accel_z_skew': skew(data['accel_z']),
        'accel_x_kurt': kurtosis(data['accel_x']),
        'accel_y_kurt': kurtosis(data['accel_y']),
        'accel_z_kurt': kurtosis(data['accel_z'])
    }
    return stats

## Função para plotar acelerações interativas com estatísticas na legenda
def plot_acceleration(data, stats):
    fig = go.Figure()

    for axis in ['x', 'y', 'z']:
        # Cria a string da legenda com as estatísticas formatadas com quebras de linha
        legend_info = (
            f"Aceleração {axis.upper()}<br>"
            f"Média: {stats[f'accel_{axis}_mean']:.2f} m/s²<br>"
            f"Desvio: {stats[f'accel_{axis}_std']:.2f} m/s²<br>"
            f"Assimetria: {stats[f'accel_{axis}_skew']:.2f}<br>"
            f"Curtose: {stats[f'accel_{axis}_kurt']:.2f}"
        )
        fig.add_trace(go.Scatter(
            x=np.array(data['timestamp']),
            y=data[f'accel_{axis}'],
            mode='lines',
            name=legend_info,
            hovertemplate=f'Aceleração {axis.upper()}<br>Tempo: %{{x}}<br>Aceleração: %{{y}} m/s²<extra></extra>',
            line=dict(width=2)
        ))

    fig.update_layout(
        title="Análise de Aceleração",
        xaxis_title="Tempo",
        yaxis_title="Aceleração (m/s²)",
        template="plotly_dark",
        xaxis_rangeslider_visible=True
    )

    fig.show()
## Função para realizar a analise de Fourier
def fourier_analysis(data, fs=50):
    fig_fft = go.Figure()

    for axis in ['x', 'y', 'z']:
        signal = np.array(data[f'accel_{axis}'])
        N = len(signal)

        # Verifica se há dados suficientes para FFT
        if N == 0:
            print(f"Aviso: Nenhum dado para FFT em accel_{axis}.")
            continue

        freq = np.fft.fftfreq(N, d=1/fs)
        fft_values = np.abs(fft(signal))[:N // 2]  
        freq = freq[:N // 2]  

        # Normaliza a FFT
        fft_values_normalized = fft_values / N

        # Gráfico da FFT
        fig_fft.add_trace(go.Scatter(
            x=freq,
            y=fft_values_normalized,
            mode='lines',
            name=f'FFT - Aceleração {axis.upper()}',
            hovertemplate=f'Freq: %{{x}} Hz<br>Amplitude Normalizada: %{{y}}<extra></extra>'
        ))

    if not fig_fft.data:
        print("Nenhum dado válido para plotar FFT.")
        return

    # Gráfico da FFT
    fig_fft.update_layout(
        title="Análise de Fourier (FFT)",
        xaxis_title="Frequência (Hz)",
        yaxis_title="Amplitude Normalizada",
        template="plotly_dark"
    )
    fig_fft.show()

# Função principal
def main(file_path):
    data = load_and_clean_data(file_path)
    if data is None:
        return
    stats = calculate_statistics(data)
    plot_acceleration(data, stats)
    fourier_analysis(data)

if __name__ == "__main__":
    file_path = 'data.csv'  # Caminho do arquivo CSV
    main(file_path)
