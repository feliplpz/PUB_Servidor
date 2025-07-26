const device_id = window.DEVICE_ID;
let availableSensors = window.AVAILABLE_SENSORS || [];

if (!availableSensors.length) {
    ['accelerometer', 'gyroscope', 'magnetometer'].forEach(sensor => {
        if (document.getElementById(`card-${sensor}`)) {
            availableSensors.push(sensor);
        }
    });
}

let currentScreen = 'selection';
let currentSensor = null;
let currentGraph = null;
let sensorStates = {};
let monitoringGraphs = {};

const sensorConfigs = {
    accelerometer: {
        title: 'Accelerometer - Linear Acceleration',
        yAxisTitle: 'Acceleration (m/s²)',
        colors: ['#1f77b4', '#ff7f0e', '#2ca02c'],
        axisLabels: ['Acceleration X', 'Acceleration Y', 'Acceleration Z'],
        unit: '(m/s²)'
    },
    gyroscope: {
        title: 'Gyroscope - Angular Velocity',
        yAxisTitle: 'Angular Velocity (rad/s)',
        colors: ['#d62728', '#9467bd', '#8c564b'],
        axisLabels: ['Gyroscope X', 'Gyroscope Y', 'Gyroscope Z'],
        unit: '(rad/s)'
    },
    magnetometer: {
        title: 'Magnetometer - Magnetic Field',
        yAxisTitle: 'Magnetic Field (μT)',
        colors: ['#ff6b6b', '#4ecdc4', '#45b7d1'],
        axisLabels: ['Magnetic X', 'Magnetic Y', 'Magnetic Z'],
        unit: '(μT)'
    }
};

function initializeApp() {
    console.log('App initialized: generic class + active data');

    availableSensors.forEach(sensor => {
        sensorStates[sensor] = {
            hasData: false,
            dataPoints: 0,
            isActive: false,
            lastDataTime: 0
        };
    });

    setupEventListeners();
    createMonitoringGraphs();
    startActiveCheck();
    updateOverallStatus();
}

/**
 * Creates hidden SensorGraph instances for monitoring each sensor
 */
function createMonitoringGraphs() {
    availableSensors.forEach(sensorType => {
        const tempContainer = document.createElement('div');
        tempContainer.id = `monitoring-${sensorType}`;
        tempContainer.style.display = 'none';
        document.body.appendChild(tempContainer);

        monitoringGraphs[sensorType] = new SensorGraph({
            deviceId: device_id,
            sensorType: sensorType,
            containerId: `monitoring-${sensorType}`,
            mode: 'monitoring',
            ...sensorConfigs[sensorType]
        });

        const originalUpdateData = monitoringGraphs[sensorType].updateData;
        monitoringGraphs[sensorType].updateData = function(data) {
            handleMonitoringData(sensorType, data);
            originalUpdateData.call(this, data);
        };
    });
}

function handleMonitoringData(sensorType, data) {
    const dataPoints = data?.time?.length || 0;
    const now = Date.now();

    sensorStates[sensorType].dataPoints = dataPoints;
    sensorStates[sensorType].hasData = dataPoints > 0;
    sensorStates[sensorType].lastDataTime = now;
    sensorStates[sensorType].isActive = dataPoints > 0;

    updateSensorCard(sensorType);
    updateOverallStatus();
}

/**
 * Checks if sensor data is recent to determine active status
 */
function startActiveCheck() {
    setInterval(() => {
        const now = Date.now();
        let anyChanged = false;

        availableSensors.forEach(sensorType => {
            const state = sensorStates[sensorType];
            const timeSinceData = now - state.lastDataTime;
            const wasActive = state.isActive;

            // Inactive if no data for >3s
            state.isActive = state.hasData && timeSinceData < 3000;

            if (wasActive !== state.isActive) {
                anyChanged = true;
                updateSensorCard(sensorType);
            }
        });

        if (anyChanged) {
            updateOverallStatus();
        }
    }, 1000);
}

function updateSensorCard(sensorType) {
    const card = document.getElementById(`card-${sensorType}`);
    const status = document.getElementById(`status-${sensorType}`);
    const button = document.getElementById(`btn-${sensorType}`);

    if (!card || !status || !button) return;

    const state = sensorStates[sensorType];
    const graph = monitoringGraphs[sensorType];

    if (!graph?.isConnected) {
        card.className = 'sensor-card inactive';
        status.className = 'sensor-status inactive';
        status.textContent = 'Connecting...';
        button.disabled = true;
        button.textContent = 'Connecting...';

    } else if (!state.hasData) {
        card.className = 'sensor-card inactive';
        status.className = 'sensor-status inactive';
        status.textContent = 'No data';
        button.disabled = true;
        button.textContent = 'No Data';

    } else if (state.isActive) {
        card.className = 'sensor-card active';
        status.className = 'sensor-status active';
        status.textContent = `Active (${state.dataPoints} points)`;
        button.disabled = false;
        button.textContent = 'View Graph';

    } else {
        card.className = 'sensor-card inactive';
        status.className = 'sensor-status inactive';
        status.textContent = `Paused (${state.dataPoints} points)`;
        button.disabled = true;
        button.textContent = 'Inactive';
    }
}

function updateOverallStatus() {
    const statusElement = document.getElementById('connection-status');
    const noSensorsMessage = document.getElementById('no-sensors-message');
    const sensorGrid = document.getElementById('sensor-grid');

    if (!statusElement) return;

    const activeSensors = availableSensors.filter(sensor => sensorStates[sensor]?.isActive).length;
    const connectedGraphs = Object.values(monitoringGraphs).filter(g => g?.isConnected).length;

    if (activeSensors > 0) {
        statusElement.innerHTML = `<strong>${activeSensors}/${availableSensors.length} active sensors</strong>`;
        if (noSensorsMessage) noSensorsMessage.style.display = 'none';
        if (sensorGrid) sensorGrid.style.display = 'grid';
    } else {
        statusElement.innerHTML = `<strong>No active sensors (${connectedGraphs} connected)</strong>`;
        if (noSensorsMessage) noSensorsMessage.style.display = 'block';
    }
}

function showGraph(sensorType) {
    const state = sensorStates[sensorType];

    if (!state?.isActive) {
        alert(`Sensor ${sensorType} is not active.\nActivate it in the mobile app.`);
        return;
    }

    console.log(`Showing graph: ${sensorType}`);

    currentScreen = 'graph';
    currentSensor = sensorType;

    document.getElementById('selection-screen')?.classList.add('hidden');
    document.getElementById('graph-screen')?.classList.add('active');

    const titleElement = document.getElementById('current-graph-title');
    const statusElement = document.getElementById('current-graph-status');

    if (titleElement) {
        titleElement.textContent = sensorConfigs[sensorType].title;
    }

    if (statusElement) {
        statusElement.className = 'sensor-status active';
        statusElement.textContent = 'Ready!';
    }

    const container = document.getElementById('current-graph');
    if (container) {
        container.innerHTML = '';

        const config = sensorConfigs[sensorType];
        const emptyData = [
            { x: [], y: [], mode: 'lines', name: `${config.axisLabels[0]} ${config.unit}`, line: { color: config.colors[0] } },
            { x: [], y: [], mode: 'lines', name: `${config.axisLabels[1]} ${config.unit}`, line: { color: config.colors[1] } },
            { x: [], y: [], mode: 'lines', name: `${config.axisLabels[2]} ${config.unit}`, line: { color: config.colors[2] } }
        ];

        const layout = {
            title: config.title,
            xaxis: { title: 'Time (s)', showgrid: true, gridcolor: '#444' },
            yaxis: { title: config.yAxisTitle, showgrid: true, gridcolor: '#444' },
            plot_bgcolor: "#121212",
            paper_bgcolor: "#121212",
            font: { color: 'white' }
        };

        Plotly.newPlot('current-graph', emptyData, layout);
    }

    setTimeout(() => {
        if (currentGraph) {
            currentGraph.disconnect();
        }
        currentGraph = new SensorGraph({
            deviceId: device_id,
            sensorType: sensorType,
            containerId: 'current-graph',
            mode: 'graph',
            ...sensorConfigs[sensorType]
        });
    }, 100);

    setupGraphControls();
}

function returnToSelection() {
    if (currentGraph) {
        currentGraph.disconnect();
        currentGraph = null;
    }

    currentScreen = 'selection';
    currentSensor = null;

    document.getElementById('graph-screen')?.classList.remove('active');
    document.getElementById('selection-screen')?.classList.remove('hidden');

    const graphContainer = document.getElementById('current-graph');
    if (graphContainer) graphContainer.innerHTML = '';
}

function reconnectCurrentGraph() {
    if (currentGraph && currentSensor) {
        currentGraph.reconnect();
    }
}

function setupGraphControls() {
    ['x', 'y', 'z'].forEach(axis => {
        const button = document.getElementById(`toggle-${axis}`);
        if (button) {
            button.replaceWith(button.cloneNode(true));
            document.getElementById(`toggle-${axis}`)?.addEventListener('click', () => {
                currentGraph?.toggleAxis(axis);
            });
        }
    });
}

function setupEventListeners() {
    window.addEventListener('beforeunload', () => {
        Object.values(monitoringGraphs).forEach(graph => graph?.disconnect());
        currentGraph?.disconnect();
    });

    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            Object.values(monitoringGraphs).forEach(graph => {
                if (!graph?.isConnected) {
                    graph?.reconnect();
                }
            });
        }
    });
}

window.showGraph = showGraph;
window.returnToSelection = returnToSelection;
window.reconnectCurrentGraph = reconnectCurrentGraph;

window.sensorStates = sensorStates;
window.monitoringGraphs = monitoringGraphs;

document.addEventListener('DOMContentLoaded', initializeApp);