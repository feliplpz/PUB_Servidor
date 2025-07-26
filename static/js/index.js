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
        console.log('WebSocket already attempting to connect...');
        return;
    }

    const loading = document.getElementById('loading');
    const status = document.getElementById('connectionStatus');

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/ws/devices`;

    console.log(`Attempt ${reconnectAttempts + 1}: Connecting WebSocket:`, wsUrl);
    updateDebugInfo(`Connecting... (attempt ${reconnectAttempts + 1})`);

    loading.style.display = 'block';
    status.innerHTML = '<span class="status-indicator"></span>Connecting...';
    status.className = 'status reconnecting';

    try {
        websocket = new WebSocket(wsUrl);

        websocket.onopen = function(event) {
            console.log('Device list WebSocket connected');
            isConnected = true;
            reconnectAttempts = 0;
            loading.style.display = 'none';
            status.innerHTML = '<span class="status-indicator"></span>Connected';
            status.className = 'status connected';

            connectionStats.connected_at = new Date();
            updateDebugInfo('Connected via WebSocket');

            if (fallbackPollingInterval) {
                clearInterval(fallbackPollingInterval);
                fallbackPollingInterval = null;
                console.log('Fallback polling disabled');
            }

            if (reconnectInterval) {
                clearInterval(reconnectInterval);
                reconnectInterval = null;
            }
        };

        websocket.onmessage = function(event) {
            try {
                const message = JSON.parse(event.data);
                console.log('Message received:', message);

                connectionStats.last_message = new Date();
                connectionStats.message_count++;

                if (message.type === 'device_list_update') {
                    updateDeviceList(message.devices);
                    updateDebugInfo(`Last update: ${connectionStats.last_message.toLocaleTimeString()}`);
                }
            } catch (error) {
                console.error('Error processing message:', error);
            }
        };

        websocket.onerror = function(error) {
            console.error('WebSocket error:', error);
            isConnected = false;
            status.innerHTML = '<span class="status-indicator"></span>Connection error';
            status.className = 'status disconnected';
            updateDebugInfo('WebSocket connection error');
        };

        websocket.onclose = function(event) {
            console.log('WebSocket disconnected:', event.code, event.reason);
            isConnected = false;
            loading.style.display = 'none';
            status.innerHTML = '<span class="status-indicator"></span>Disconnected';
            status.className = 'status disconnected';

            updateDebugInfo(`Disconnected (code: ${event.code})`);

            if (event.code !== 1000 && event.code !== 1001 && reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                connectionStats.reconnections++;

                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts - 1), 10000);
                console.log(`Attempting reconnect in ${delay}ms...`);

                if (!reconnectInterval) {
                    reconnectInterval = setTimeout(() => {
                        reconnectInterval = null;
                        connectWebSocket();
                    }, delay);
                }
            } else if (reconnectAttempts >= maxReconnectAttempts) {
                console.log('Maximum reconnection attempts reached. Activating fallback polling.');
                updateDebugInfo('WebSocket failed. Using polling as fallback.');
                startFallbackPolling();
            }
        };

    } catch (error) {
        console.error('Error creating WebSocket:', error);
        isConnected = false;
        updateDebugInfo('Error creating WebSocket');
        startFallbackPolling();
    }
}

function startFallbackPolling() {
    if (fallbackPollingInterval) return;

    console.log('Starting fallback polling...');
    updateDebugInfo('Using HTTP polling as fallback');

    fallbackPollingInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/devices');
            if (response.ok) {
                const devices = await response.json();
                updateDeviceList(devices);

                const status = document.getElementById('connectionStatus');
                status.innerHTML = '<span class="status-indicator"></span>Connected (HTTP)';
                status.className = 'status connected';
                updateDebugInfo('HTTP polling active');
            }
        } catch (error) {
            console.error('Error in fallback polling:', error);
            updateDebugInfo('HTTP polling error');
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
                console.log(`Removing device: ${deviceId}`);
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
                <div>No devices connected.</div>
                <div class="no-devices-subtitle">
                    Connect a mobile device via Bluetooth to get started.
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
                console.log(`Adding new device: ${device.name} (${deviceId})`);

                deviceElement = document.createElement('li');
                deviceElement.className = 'device-item new';
                deviceElement.setAttribute('data-device-id', deviceId);

                deviceElement.innerHTML = `
                    <div>
                        <div class="device-name">${device.name}</div>
                        <div class="device-id">ID: ${deviceId}</div>
                        <div class="device-time">Connected at: ${device.connected_at}</div>
                        ${device.sensor_count > 0 ? `
                        <div class="sensor-info">
                            ${device.active_sensor_count}/${device.sensor_count} active sensors
                        </div>
                        ` : ''}
                    </div>
                    <a href="/device/${deviceId}" class="device-link">View details</a>
                `;

                deviceList.appendChild(deviceElement);

                setTimeout(() => {
                    deviceElement.classList.remove('new');
                }, 500);
            } else {
                const nameElement = deviceElement.querySelector('.device-name');
                const timeElement = deviceElement.querySelector('.device-time');

                if (nameElement.textContent !== device.name) {
                    nameElement.textContent = device.name;
                }

                const expectedTime = `Connected at: ${device.connected_at}`;
                if (timeElement.textContent !== expectedTime) {
                    timeElement.textContent = expectedTime;
                }

                const deviceDiv = deviceElement.querySelector('div');
                const existingSensorInfo = deviceDiv.querySelector('.sensor-info');
                const newSensorInfo = device.sensor_count > 0 ?
                    `${device.active_sensor_count}/${device.sensor_count} active sensors` : '';

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
            Reconnections: ${connectionStats.reconnections} |
            Messages: ${connectionStats.message_count}
        `;
    }
}

function manualRefresh() {
    console.log('Manual refresh requested');

    if (isConnected && websocket) {
        websocket.send(JSON.stringify({ type: 'request_update' }));
    } else {
        fetch('/api/devices')
            .then(response => response.json())
            .then(devices => {
                updateDeviceList(devices);
                updateDebugInfo('Manual refresh via HTTP');
            })
            .catch(error => {
                console.error('Error in manual refresh:', error);
                updateDebugInfo('Manual refresh error');
            });
    }
}

function setupEventListeners() {
    const refreshButton = document.getElementById('manual-refresh-btn');
    if (refreshButton) {
        refreshButton.addEventListener('click', manualRefresh);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing application...');
    setupEventListeners();
    connectWebSocket();
});