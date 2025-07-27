# Bluetooth Sensor Data Visualization System

A real-time sensor data visualization system that receives data from mobile devices via Bluetooth and displays interactive graphs through a web interface.

## Features

- **Real-time Data Collection**: Receives accelerometer, gyroscope, and magnetometer data via Bluetooth
- **Interactive Web Interface**: View live sensor data with interactive graphs
- **Multi-device Support**: Handle multiple Bluetooth devices simultaneously
- **Data Export**: Save sensor data to CSV files
- **WebSocket Communication**: Real-time updates between server and web interface
- **Responsive Design**: Works on desktop and mobile browsers

## System Requirements

- Python 3.8+
- Bluetooth-enabled system
- Modern web browser
- Linux (Ubuntu, Linux Mint, Debian recommended)

## Installation on Linux

### 1. Install System Dependencies

For Debian-based systems (Ubuntu, Linux Mint, Debian), open terminal and run:

```bash
sudo apt update
sudo apt install git python3 libbluetooth-dev build-essential python3.12-venv python3-dev
```

### 2. Install VSCode (Optional)

1. Visit [VSCode website](https://code.visualstudio.com)
2. Download the `.deb` package
3. Install with:
```bash
cd Downloads/
sudo apt install ./code_1.99.3-1744761595_amd64.deb
```

### 3. Clone Repository

```bash
cd ~
git clone https://github.com/feliplpz/PUB_Servidor.git
cd PUB_Servidor
```

### 4. Set Up Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 5. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

1. **Copy environment file**
```bash
cp .env.example .env
```

2. **Edit `.env` file with your configurations:**

```env
# Server Configuration
SERVER_LOG_FILE_PATH=server.log
DATA_FILE_PATH=data/

# Bluetooth Configuration
BT_RECV_CHUNK_SIZE=1024
BT_MAX_BUFFER_SIZE=8192
BT_BUFFER_CLEANUP_THRESHOLD=4096
BT_BUFFER_FALLBACK_SIZE=256
BT_MAX_MESSAGE_SIZE=2048
BT_CONNECTION_TIMEOUT=30
BT_JSON_START_PATTERN={"type"

# Data Configuration
MAX_DATA_POINTS=100
DATE_IN_MILLISECONDS=False
```

3. **Create data directory** (if using custom path):
```bash
mkdir -p data
```

## Usage

1. **Start the server**
```bash
python app.py
```

2. **Access web interface**
   - Open browser and navigate to `http://localhost:5000`
   - View connected devices and their sensor data

3. **Connect mobile devices**
   - Pair your mobile device via Bluetooth
   - Send JSON sensor data to the server

## API Endpoints

### Web Interface
- `GET /` - Main dashboard with device list
- `GET /device/{device_id}` - Device-specific visualization page

### REST API
- `GET /api/devices` - Get all devices (JSON)
- `GET /api/device/{device_id}/info` - Get device details
- `GET /api/device/{device_id}/data/{sensor_type}` - Get sensor data

### WebSocket Endpoints
- `WS /ws/devices` - Device list updates
- `WS /ws/device/{device_id}/sensor/{sensor_type}` - Real-time sensor data

## Data Format

Send sensor data as JSON via Bluetooth:

```json
{
  "type": "accelerometer",
  "x": 0.123,
  "y": -0.456,
  "z": 9.789
}
```

**Supported sensor types:**
- `accelerometer` - Linear acceleration (m/s²)
- `gyroscope` - Angular velocity (rad/s)
- `magnetometer` - Magnetic field (μT)

## Troubleshooting

**Bluetooth Issues**
- Ensure Bluetooth is enabled and device is paired
- Check user permissions for Bluetooth access
- Verify port availability

**Web Interface Issues**
- Check if port 5000 is available
- Verify firewall settings
- Check browser JavaScript console for errors

**Data Issues**
- Verify JSON format matches expected structure
- Check server logs in console or log file
- Ensure sensor type names are correct

## Development

### Project Structure
```
├── src/
│   ├── connection/
│   │   ├── bluetooth_server.py
│   │   ├── websocket_manager.py
│   │   └── event_bus.py
│   ├── sensors/
│   │   ├── accelerometer.py
│   │   ├── gyroscope.py
│   │   ├── magnetometer.py
│   │   └── sensor_factory.py
│   ├── utils/
│   │   └── logging.py
│   └── web/
│       └── routes.py
├── static/js/
├── templates/
├── app.py
└── requirements.txt
```

### Logs

Monitor application through:
- Console output (real-time)
- Log files (configured in `.env`)

Log levels: `[INFO]`, `[WARNING]`, `[ERROR]`

---

# Sistema de Visualização de Dados de Sensores Bluetooth

Um sistema de visualização de dados de sensores em tempo real que recebe dados de dispositivos móveis via Bluetooth e exibe gráficos interativos através de uma interface web.

## Funcionalidades

- **Coleta de Dados em Tempo Real**: Recebe dados de acelerômetro, giroscópio e magnetômetro via Bluetooth
- **Interface Web Interativa**: Visualize dados de sensores ao vivo com gráficos interativos
- **Suporte Multi-dispositivo**: Gerencia múltiplos dispositivos Bluetooth simultaneamente
- **Exportação de Dados**: Salva dados de sensores em arquivos CSV
- **Comunicação WebSocket**: Atualizações em tempo real entre servidor e interface web
- **Design Responsivo**: Funciona em navegadores desktop e móveis

## Requisitos do Sistema

- Python 3.8+
- Sistema com Bluetooth habilitado
- Navegador web moderno
- Linux (Ubuntu, Linux Mint, Debian recomendados)

## Instalação no Linux

### 1. Instalar Dependências do Sistema

Para sistemas baseados em Debian (Ubuntu, Linux Mint, Debian), abra o terminal e execute:

```bash
sudo apt update
sudo apt install git python3 libbluetooth-dev build-essential python3.12-venv python3-dev
```

### 2. Instalar VSCode (Opcional)

1. Acesse o site do [VSCode](https://code.visualstudio.com)
2. Baixe o pacote `.deb`
3. Instale com:
```bash
cd Downloads/
sudo apt install ./code_1.99.3-1744761595_amd64.deb
```

### 3. Clonar Repositório

```bash
cd ~
git clone https://github.com/feliplpz/PUB_Servidor.git
cd PUB_Servidor
```

### 4. Configurar Ambiente Virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 5. Instalar Dependências Python

```bash
pip install -r requirements.txt
```

## Configuração

1. **Copiar arquivo de ambiente**
```bash
cp .env.example .env
```

2. **Editar arquivo `.env` com suas configurações:**

```env
# Configuração do Servidor
SERVER_LOG_FILE_PATH=server.log
DATA_FILE_PATH=data/

# Configuração Bluetooth
BT_RECV_CHUNK_SIZE=1024
BT_MAX_BUFFER_SIZE=8192
BT_BUFFER_CLEANUP_THRESHOLD=4096
BT_BUFFER_FALLBACK_SIZE=256
BT_MAX_MESSAGE_SIZE=2048
BT_CONNECTION_TIMEOUT=30
BT_JSON_START_PATTERN={"type"

# Configuração de Dados
MAX_DATA_POINTS=100
DATE_IN_MILLISECONDS=False
```

3. **Criar diretório de dados** (se usando caminho personalizado):
```bash
mkdir -p data
```

## Uso

1. **Iniciar o servidor**
```bash
python app.py
```

2. **Acessar interface web**
   - Abra o navegador e navegue para `http://localhost:5000`
   - Visualize dispositivos conectados e seus dados de sensores

3. **Conectar dispositivos móveis**
   - Emparelhe seu dispositivo móvel via Bluetooth
   - Envie dados de sensores em JSON para o servidor

## Endpoints da API

### Interface Web
- `GET /` - Dashboard principal com lista de dispositivos
- `GET /device/{device_id}` - Página de visualização específica do dispositivo

### API REST
- `GET /api/devices` - Obter todos os dispositivos (JSON)
- `GET /api/device/{device_id}/info` - Obter detalhes do dispositivo
- `GET /api/device/{device_id}/data/{sensor_type}` - Obter dados do sensor

### Endpoints WebSocket
- `WS /ws/devices` - Atualizações da lista de dispositivos
- `WS /ws/device/{device_id}/sensor/{sensor_type}` - Dados de sensor em tempo real

## Formato de Dados

Envie dados dos sensores como JSON via Bluetooth:

```json
{
  "type": "accelerometer",
  "x": 0.123,
  "y": -0.456,
  "z": 9.789
}
```

**Tipos de sensores suportados:**
- `accelerometer` - Aceleração linear (m/s²)
- `gyroscope` - Velocidade angular (rad/s)
- `magnetometer` - Campo magnético (μT)

## Solução de Problemas

**Problemas com Bluetooth**
- Certifique-se de que o Bluetooth está habilitado e o dispositivo está emparelhado
- Verifique permissões do usuário para acesso Bluetooth
- Verifique disponibilidade da porta

**Problemas com Interface Web**
- Verifique se a porta 5000 está disponível
- Verifique configurações do firewall
- Verifique console JavaScript do navegador para erros

**Problemas com Dados**
- Verifique se o formato JSON corresponde à estrutura esperada
- Verifique logs do servidor no console ou arquivo de log
- Certifique-se de que os nomes dos tipos de sensores estão corretos

## Desenvolvimento

### Estrutura do Projeto
```
├── src/
│   ├── connection/
│   │   ├── bluetooth_server.py
│   │   ├── websocket_manager.py
│   │   └── event_bus.py
│   ├── sensors/
│   │   ├── accelerometer.py
│   │   ├── gyroscope.py
│   │   ├── magnetometer.py
│   │   └── sensor_factory.py
│   ├── utils/
│   │   └── logging.py
│   └── web/
│       └── routes.py
├── static/js/
├── templates/
├── app.py
└── requirements.txt
```

### Logs

Monitore a aplicação através de:
- Saída do console (tempo real)
- Arquivos de log (configurados no `.env`)

Níveis de log: `[INFO]`, `[WARNING]`, `[ERROR]`