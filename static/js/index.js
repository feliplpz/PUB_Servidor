let websocket = null;
let reconnectInterval = null;
let isConnected = false;
let reconnectAttempts = 0;
let maxReconnectAttempts = 10;
let fallbackPollingInterval = null;
let currentDevices = new Map();
let connectionStats = {
    connected_at: null,
    reconnections: 0,
    last_message: null,
    message_count: 0
};

function connectWebSocket() {
    if (websocket && websocket.readyState === WebSocket.CONNECTING) {
        console.log('WebSocket já está tentando conectar...');
        return;
    }

    const loading = document.getElementById('loading');
    const status = document.getElementById('connectionStatus');

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/ws/devices`;

    console.log(`Tentativa ${reconnectAttempts + 1}: Conectando WebSocket:`, wsUrl);
    updateDebugInfo(`Conectando... (tentativa ${reconnectAttempts + 1})`);

    loading.style.display = 'block';
    status.innerHTML = '<span class="status-indicator"></span>Conectando...';
    status.className = 'status reconnecting';

    try {
        websocket = new WebSocket(wsUrl);

        websocket.onopen = function(event) {
            console.log('WebSocket da lista de dispositivos conectado');
            isConnected = true;
            reconnectAttempts = 0;
            loading.style.display = 'none';
            status.innerHTML = '<span class="status-indicator"></span>Conectado';
            status.className = 'status connected';

            connectionStats.connected_at = new Date();
            updateDebugInfo('Conectado via WebSocket');

            if (fallbackPollingInterval) {
                clearInterval(fallbackPollingInterval);
                fallbackPollingInterval = null;
                console.log('Fallback polling desabilitado');
            }

            if (reconnectInterval) {
                clearInterval(reconnectInterval);
                reconnectInterval = null;
            }
        };

        websocket.onmessage = function(event) {
            try {
                const message = JSON.parse(event.data);
                console.log('Mensagem recebida:', message);

                connectionStats.last_message = new Date();
                connectionStats.message_count++;

                if (message.type === 'device_list_update') {
                    updateDeviceList(message.devices);
                    updateDebugInfo(`Última atualização: ${connectionStats.last_message.toLocaleTimeString()}`);
                }
            } catch (error) {
                console.error('❌ Erro ao processar mensagem:', error);
            }
        };

        websocket.onerror = function(error) {
            console.error('❌ Erro WebSocket:', error);
            isConnected = false;
            status.innerHTML = '<span class="status-indicator"></span>Erro na conexão';
            status.className = 'status disconnected';
            updateDebugInfo('Erro na conexão WebSocket');
        };

        websocket.onclose = function(event) {
            console.log('WebSocket desconectado:', event.code, event.reason);
            isConnected = false;
            loading.style.display = 'none';
            status.innerHTML = '<span class="status-indicator"></span>Desconectado';
            status.className = 'status disconnected';

            updateDebugInfo(`Desconectado (código: ${event.code})`);

            if (event.code !== 1000 && event.code !== 1001 && reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                connectionStats.reconnections++;

                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts - 1), 10000);
                console.log(`tentando reconectar em ${delay}ms...`);

                if (!reconnectInterval) {
                    reconnectInterval = setTimeout(() => {
                        reconnectInterval = null;
                        connectWebSocket();
                    }, delay);
                }
            } else if (reconnectAttempts >= maxReconnectAttempts) {
                console.log(' Máximo de tentativas de reconexão atingido. Ativando fallback polling.');
                updateDebugInfo('WebSocket falhou. Usando polling como fallback.');
                startFallbackPolling();
            }
        };

    } catch (error) {
        console.error(' Erro ao criar WebSocket:', error);
        isConnected = false;
        updateDebugInfo('Erro ao criar WebSocket');
        startFallbackPolling();
    }
}

function startFallbackPolling() {
    if (fallbackPollingInterval) return;

    console.log('Iniciando fallback polling...');
    updateDebugInfo('Usando polling HTTP como fallback');

    fallbackPollingInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/devices');
            if (response.ok) {
                const devices = await response.json();
                updateDeviceList(devices);

                const status = document.getElementById('connectionStatus');
                status.innerHTML = '<span class="status-indicator"></span>Conectado (HTTP)';
                status.className = 'status connected';
                updateDebugInfo('Polling HTTP ativo');
            }
        } catch (error) {
            console.error('❌ Erro no fallback polling:', error);
            updateDebugInfo('Erro no polling HTTP');
        }
    }, 2000);
}

function updateDeviceList(devices) {
    const deviceList = document.getElementById('deviceList');
    const noDevices = document.getElementById('noDevices');
    const deviceCount = document.getElementById('device-count');

    const deviceIds = Object.keys(devices);
    deviceCount.textContent = `(${deviceIds.length})`;

    const currentDeviceIds = new Set(Array.from(deviceList.children)
        .filter(child => child.dataset.deviceId)
        .map(child => child.dataset.deviceId));

    const newDeviceIds = new Set(deviceIds);

    currentDeviceIds.forEach(deviceId => {
        if (!newDeviceIds.has(deviceId)) {
            const deviceElement = deviceList.querySelector(`[data-device-id="${deviceId}"]`);
            if (deviceElement) {
                console.log(`Removendo dispositivo: ${deviceId}`);
                deviceElement.classList.add('removing');
                setTimeout(() => {
                    if (deviceElement.parentNode) {
                        deviceElement.remove();
                    }
                }, 300);
            }
        }
    });

    if (deviceIds.length === 0) {
        if (!document.getElementById('noDevices')) {
            const noDevDiv = document.createElement('div');
            noDevDiv.id = 'noDevices';
            noDevDiv.className = 'no-devices';
            noDevDiv.innerHTML = `
                <div class="no-devices-icon">📱</div>
                <div>Nenhum dispositivo conectado.</div>
                <div class="no-devices-subtitle">
                    Conecte um dispositivo móvel via Bluetooth para começar.
                </div>
            `;
            deviceList.appendChild(noDevDiv);
        }
    } else {
        const noDevicesElement = document.getElementById('noDevices');
        if (noDevicesElement) {
            noDevicesElement.remove();
        }

        deviceIds.forEach(deviceId => {
            const device = devices[deviceId];
            let deviceElement = deviceList.querySelector(`[data-device-id="${deviceId}"]`);

            if (!deviceElement) {
                console.log(`Adicionando novo dispositivo: ${device.name} (${deviceId})`);

                deviceElement = document.createElement('li');
                deviceElement.className = 'device-item new';
                deviceElement.setAttribute('data-device-id', deviceId);

                deviceElement.innerHTML = `
                    <div>
                        <div class="device-name">${device.name}</div>
                        <div class="device-id">ID: ${deviceId}</div>
                        <div class="device-time">Conectado em: ${device.connected_at}</div>
                        ${device.sensor_count > 0 ? `
                        <div class="sensor-info">
                            📊 ${device.active_sensor_count}/${device.sensor_count} sensores ativos
                        </div>
                        ` : ''}
                    </div>
                    <a href="/device/${deviceId}" class="device-link">Ver detalhes</a>
                `;

                deviceList.appendChild(deviceElement);

                setTimeout(() => {
                    deviceElement.classList.remove('new');
                }, 500);
            } else {
                // Atualiza dispositivo existente
                const nameElement = deviceElement.querySelector('.device-name');
                const timeElement = deviceElement.querySelector('.device-time');

                if (nameElement.textContent !== device.name) {
                    nameElement.textContent = device.name;
                }

                const expectedTime = `Conectado em: ${device.connected_at}`;
                if (timeElement.textContent !== expectedTime) {
                    timeElement.textContent = expectedTime;
                }

                // Atualiza info de sensores
                const deviceDiv = deviceElement.querySelector('div');
                const existingSensorInfo = deviceDiv.querySelector('.sensor-info');
                const newSensorInfo = device.sensor_count > 0 ?
                    `📊 ${device.active_sensor_count}/${device.sensor_count} sensores ativos` : '';

                if (newSensorInfo && !existingSensorInfo) {
                    const sensorDiv = document.createElement('div');
                    sensorDiv.className = 'sensor-info';
                    sensorDiv.textContent = newSensorInfo;
                    deviceDiv.appendChild(sensorDiv);
                } else if (existingSensorInfo) {
                    if (newSensorInfo) {
                        existingSensorInfo.textContent = newSensorInfo;
                    } else {
                        existingSensorInfo.remove();
                    }
                }
            }

            currentDevices.set(deviceId, device);
        });
    }
}

function updateDebugInfo(status) {
    const debugStatus = document.getElementById('debugStatus');
    const debugStats = document.getElementById('debugStats');

    if (debugStatus) {
        debugStatus.textContent = status;
    }

    if (debugStats && connectionStats.connected_at) {
        const uptime = Math.floor((new Date() - connectionStats.connected_at) / 1000);
        debugStats.innerHTML = `
            Uptime: ${uptime}s |
            Reconexões: ${connectionStats.reconnections} |
            Mensagens: ${connectionStats.message_count}
        `;
    }
}

function manualRefresh() {
    console.log('Atualização manual solicitada');

    if (isConnected && websocket) {
        websocket.send(JSON.stringify({ type: 'request_update' }));
    } else {
        fetch('/api/devices')
            .then(response => response.json())
            .then(devices => {
                updateDeviceList(devices);
                updateDebugInfo('Atualização manual via HTTP');
            })
            .catch(error => {
                console.error('Erro na atualização manual:', error);
                updateDebugInfo('Erro na atualização manual');
            });
    }
}

function setupEventListeners() {
    const refreshButton = document.getElementById('manual-refresh-btn');
    if (refreshButton) {
        refreshButton.addEventListener('click', manualRefresh);
    }
}

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    console.log(' Inicializando aplicação...');
    setupEventListeners();
    connectWebSocket();
});