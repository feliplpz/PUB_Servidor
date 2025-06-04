const device_id = window.DEVICE_ID;
let availableSensors = window.AVAILABLE_SENSORS || [];

// Fallback se window.AVAILABLE_SENSORS estiver vazio
if (!availableSensors || availableSensors.length === 0) {
    availableSensors = [];
    if (document.getElementById('card-accelerometer')) {
        availableSensors.push('accelerometer');
    }
    if (document.getElementById('card-gyroscope')) {
        availableSensors.push('gyroscope');
    }
    
}

// Estado da aplicação
let currentScreen = 'selection'; // 'selection' ou 'graph'
let currentSensor = null;
let currentGraph = null;
let sensorStates = {}; // Estado de cada sensor (ativo/inativo)
let statusCheckInterval = null;

// Configurações para diferentes tipos de sensores
const sensorConfigs = {
    accelerometer: {
        title: 'Acelerômetro - Aceleração Linear',
        yAxisTitle: 'Aceleração (m/s²)',
        colors: ['#1f77b4', '#ff7f0e', '#2ca02c'],
        axisLabels: ['Aceleração X', 'Aceleração Y', 'Aceleração Z'],
        unit: '(m/s²)',
        containerId: 'current-graph'
    },
    gyroscope: {
        title: 'Giroscópio - Velocidade Angular',
        yAxisTitle: 'Velocidade Angular (rad/s)',
        colors: ['#d62728', '#9467bd', '#8c564b'],
        axisLabels: ['Giroscópio X', 'Giroscópio Y', 'Giroscópio Z'],
        unit: '(rad/s)',
        containerId: 'current-graph'
    }
};

/**
 * Inicializa a aplicação
 */
function initializeApp() {
    if (availableSensors.length === 0) {
        availableSensors = ['accelerometer', 'gyroscope'];
    }
    availableSensors.forEach(sensor => {
        sensorStates[sensor] = {
            active: false,
            hasData: false,
            lastCheck: Date.now()
        };
        (`  - ${sensor}: inicializado`);
    });
    startSensorStatusCheck();
    setupEventListeners();
    setTimeout(checkSensorStates, 500);
}

async function checkSensorStates() {
    try {
        const response = await fetch(`/api/device/${device_id}/info`);
        if (!response.ok) {
            throw new Error('Falha ao obter informações do dispositivo');
        }
        
        const deviceInfo = await response.json();
        if (availableSensors.length === 0 && deviceInfo.sensors) {
            const apiSensors = Object.keys(deviceInfo.sensors);
            availableSensors.splice(0, 0, ...apiSensors); 
        }
        
        let hasActiveSensors = false;
        
        if (!availableSensors || availableSensors.length === 0) {
            availableSensors = Object.keys(deviceInfo.sensors || {});
        }
        
        // Atualiza estado de cada sensor
        availableSensors.forEach(sensorType => {
            const sensorInfo = deviceInfo.sensors[sensorType];
            
            const isActive = sensorInfo && sensorInfo.is_recent === true;
            
            sensorStates[sensorType] = {
                active: isActive,
                hasData: sensorInfo ? sensorInfo.has_data : false,
                dataPoints: sensorInfo ? sensorInfo.data_points : 0,
                isRecent: sensorInfo ? sensorInfo.is_recent : false,
                lastCheck: Date.now(),
                debugInfo: sensorInfo?.debug_info
            };
            
            if (isActive) hasActiveSensors = true;
            
            // Atualiza UI do card do sensor
            updateSensorCard(sensorType, isActive);
        });
        
        // Atualiza status geral
        updateOverallStatus(hasActiveSensors);
        
        // Verifica se o sensor atual foi desligado
        if (currentScreen === 'graph' && currentSensor) {
            if (!sensorStates[currentSensor] || !sensorStates[currentSensor].active) {

                returnToSelection();
            }
        }
        
    } catch (error) {
        console.error('erro ao verificar status dos sensores:', error);
        
        // Em caso de erro, marca todos como inativos
        availableSensors.forEach(sensorType => {
            if (sensorStates[sensorType]) {
                sensorStates[sensorType].active = false;
                updateSensorCard(sensorType, false);
            }
        });
        
        updateOverallStatus(false);
    }
}

/**
 * Atualiza o card visual de um sensor
 */
function updateSensorCard(sensorType, isActive) {
    const card = document.getElementById(`card-${sensorType}`);
    const status = document.getElementById(`status-${sensorType}`);
    const button = document.getElementById(`btn-${sensorType}`);
    
    if (!card || !status || !button) {
        console.warn(`Elementos não encontrados para sensor: ${sensorType}`);
        return;
    }
    
    const sensorState = sensorStates[sensorType];
    
    if (isActive) {
        card.className = 'sensor-card active';
        status.className = 'sensor-status active';
        status.textContent = `Ativo (${sensorState.dataPoints || 0} pontos)`;
        button.disabled = false;
        button.textContent = 'Ver Gráfico';
    } else {
        card.className = 'sensor-card inactive';
        status.className = 'sensor-status inactive';
        
        // Feedback mais específico baseado no estado
        if (sensorState.hasData && !sensorState.isRecent) {
            status.textContent = `Desligado (${sensorState.dataPoints} pontos antigos)`;
        } else if (sensorState.hasData) {
            status.textContent = `Inativo (${sensorState.dataPoints} pontos)`;
        } else {
            status.textContent = 'Sem dados';
        }
        
        button.disabled = true;
        button.textContent = 'Sensor Desligado';
    }
}

/**
 * Atualiza o status geral da aplicação
 */
function updateOverallStatus(hasActiveSensors) {
    const statusElement = document.getElementById('connection-status');
    const noSensorsMessage = document.getElementById('no-sensors-message');
    const sensorGrid = document.getElementById('sensor-grid');
    
    if (!statusElement) return;
    
    const activeSensors = availableSensors.filter(s => sensorStates[s] && sensorStates[s].active);
    
    if (hasActiveSensors) {
        statusElement.innerHTML = `
            <strong>${activeSensors.length} de ${availableSensors.length} sensores ativos</strong><br>
            <small>Selecione um sensor para visualizar os dados</small>
        `;
        
        if (noSensorsMessage) {
            noSensorsMessage.style.display = 'none';
        }
        if (sensorGrid) {
            sensorGrid.style.display = 'grid';
        }
    } else {
        statusElement.innerHTML = `
            <strong>Nenhum sensor ativo</strong><br>
            <small>Ative os sensores no aplicativo móvel</small>
        `;
        
        if (noSensorsMessage) {
            noSensorsMessage.style.display = 'block';

        }
        if (sensorGrid) {
            sensorGrid.style.display = 'none';

        }
    }
}

/**
 * Mostra o gráfico de um sensor específico
 */
function showGraph(sensorType) {
    if (!sensorStates[sensorType] || !sensorStates[sensorType].active) {
        alert('Este sensor não está ativo no momento.');
        return;
    }
    
    (`Mostrando gráfico para: ${sensorType}`);
    
    // Limpa gráfico anterior se existir
    if (currentGraph) {
        currentGraph.disconnect();
        currentGraph = null;
    }
    
    // Atualiza estado
    currentScreen = 'graph';
    currentSensor = sensorType;
    
    // Alterna telas
    const selectionScreen = document.getElementById('selection-screen');
    const graphScreen = document.getElementById('graph-screen');
    
    if (selectionScreen) selectionScreen.classList.add('hidden');
    if (graphScreen) graphScreen.classList.add('active');
    
    // Atualiza título do gráfico
    const titleElement = document.getElementById('current-graph-title');
    const statusElement = document.getElementById('current-graph-status');
    
    if (titleElement && sensorConfigs[sensorType]) {
        titleElement.textContent = sensorConfigs[sensorType].title;
    }
    
    if (statusElement) {
        statusElement.className = 'sensor-status active';
        statusElement.textContent = 'Conectado';
    }
    
    // Cria nova instância do gráfico
    if (sensorConfigs[sensorType]) {
        const config = {
            deviceId: device_id,
            sensorType: sensorType,
            ...sensorConfigs[sensorType]
        };
        
        currentGraph = new SensorGraph(config);
    }
    
    // Configura event listeners para controles do gráfico
    setupGraphControls();
}

/**
 * Retorna à tela de seleção
 */
function returnToSelection() {
    
    // Limpa gráfico atual
    if (currentGraph) {
        currentGraph.disconnect();
        currentGraph = null;
    }
    
    // Atualiza estado
    currentScreen = 'selection';
    currentSensor = null;
    
    // Alterna telas
    const selectionScreen = document.getElementById('selection-screen');
    const graphScreen = document.getElementById('graph-screen');
    
    if (graphScreen) graphScreen.classList.remove('active');
    if (selectionScreen) selectionScreen.classList.remove('hidden');
    
    // Limpa container do gráfico
    const graphContainer = document.getElementById('current-graph');
    if (graphContainer) {
        graphContainer.innerHTML = '';
    }
    
    // Re-verifica status dos sensores
    setTimeout(checkSensorStates, 500);
}

/**
 * Reconecta o gráfico atual
 */
function reconnectCurrentGraph() {
    if (currentGraph && currentSensor) {
        currentGraph.reconnect();
    }
}

/**
 * Configura controles do gráfico
 */
function setupGraphControls() {
    // Botões de toggle de eixos
    ['x', 'y', 'z'].forEach(axis => {
        const button = document.getElementById(`toggle-${axis}`);
        if (button) {
            // Remove listeners antigos
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
            
            // Adiciona novo listener
            newButton.addEventListener('click', () => {
                if (currentGraph) {
                    currentGraph.toggleAxis(axis);
                }
            });
        }
    });
}

/**
 * Configura event listeners gerais
 */
function setupEventListeners() {
    // Cleanup ao sair da página
    window.addEventListener('beforeunload', () => {
        if (currentGraph) {
            currentGraph.disconnect();
        }
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }
    });
    
    // Re-verificar quando volta para a página
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            setTimeout(checkSensorStates, 1000);
        }
    });
}

/**
 * Inicia verificação periódica do status dos sensores
 */
function startSensorStatusCheck() {
    // Verifica a cada 3 segundos
    statusCheckInterval = setInterval(checkSensorStates, 3000);
    ('Verificação periódica de sensores iniciada');
}

// Funções globais para serem chamadas pelo HTML
window.showGraph = showGraph;
window.returnToSelection = returnToSelection;
window.reconnectCurrentGraph = reconnectCurrentGraph;

// Inicialização quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', initializeApp);

// Debug - expõe funções para console
window.sensorStates = sensorStates;
window.checkSensorStates = checkSensorStates;