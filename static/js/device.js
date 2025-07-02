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
        if (document.getElementById('card-magnetometer')) {
        availableSensors.push('magnetometer');
    }

}

// Estado da aplicação
let currentScreen = 'selection'; // 'selection' ou 'graph'
let currentSensor = null;
let currentGraph = null;
let sensorStates = {}; // Estado de cada sensor (ativo/inativo)
let statusCheckInterval = null;
let lastCheckTime = null;
let consecutiveErrors = 0;
let isCheckingStatus = false;

// WebSockets de monitoramento para cada sensor
let monitoringWebSockets = {};

// Configurações reativas
const CONFIG = {
    CHECK_INTERVAL: 500,       
    RECENT_DATA_WINDOW: 0.005,     // Dados são "recentes"  
    MAX_CONSECUTIVE_ERRORS: 3,     // Máximo de erros antes de aumentar intervalo
    ERROR_BACKOFF_MULTIPLIER: 2,   // Multiplica intervalo por 2 quando há erros
    MAX_CHECK_INTERVAL: 10000,     // Intervalo máximo durante erros (10s)
    STATUS_TRANSITION_DELAY: 0.01  // Delay antes de considerar sensor realmente inativo
};

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
    },
    magnetometer: {
        title: 'Magnetômetro - Campo Magnético',
        yAxisTitle: 'Campo Magnético (μT)',
        colors: ['#ff6b6b', '#4ecdc4', '#45b7d1'],
        axisLabels: ['Magnético X', 'Magnético Y', 'Magnético Z'],
        unit: '(μT)',
        containerId: 'current-graph'
    }
};


/**
 * Inicializa a aplicação
 */
function initializeApp() {
    console.log('Inicializando aplicação de sensores...');
    
    if (availableSensors.length === 0) {
        availableSensors = ['accelerometer', 'gyroscope', 'magnetometer'];
    }
    
    // Inicializa estado dos sensores
    availableSensors.forEach(sensor => {
        sensorStates[sensor] = {
            active: false,
            hasData: false,
            lastCheck: Date.now(),
            dataPoints: 0,
            consecutiveInactive: 0,
            lastActiveTime: null,
            isTransitioning: false
        };
        console.log(`${sensor}: inicializado`);
    });
    setupEventListeners();
    createMonitoringWebSockets();
    startSensorStatusCheck();

    
    // Primeira verificação imediata
    setTimeout(() => {
        // console.log('⚡ Executando verificação inicial...');
        checkSensorStates();
    }, 100);
}

/**
 * Verifica estado atual dos sensores com fallback para WebSockets)
 */
async function checkSensorStates() {
    if (isCheckingStatus) {
        return;
    }

    isCheckingStatus = true;
    lastCheckTime = Date.now();

    try {
        // Primeiro, verifica se temos dados recentes dos WebSockets
        let hasRecentWebSocketData = false;
        let activeSensorCount = 0;

        availableSensors.forEach(sensorType => {
            const wsData = monitoringWebSockets[sensorType];
            const sensorState = sensorStates[sensorType];

            if (wsData && wsData.isConnected && wsData.lastDataTime) {
                const timeSinceLastData = (Date.now() - wsData.lastDataTime) / 1000;

                if (timeSinceLastData < CONFIG.RECENT_DATA_WINDOW) {
                    hasRecentWebSocketData = true;
                    // Mantém estado ativo se dados são recentes
                    if (!sensorState.active) {
                        updateSensorState(sensorType, true, sensorState.dataPoints, {
                            timeSinceUpdate: timeSinceLastData,
                            isRecent: true,
                            source: 'websocket_fallback'
                        });
                    }
                    activeSensorCount++;
                } else {
                    // Marca como inativo se dados são antigos
                    updateSensorState(sensorType, false, sensorState.dataPoints, {
                        timeSinceUpdate: timeSinceLastData,
                        isRecent: false,
                        source: 'websocket_timeout'
                    });
                }
            }
        });

        // Se não há dados recentes do WebSocket, faz verificação HTTP como fallback
        if (!hasRecentWebSocketData) {
            console.log('📡 Sem dados recentes do WebSocket, usando fallback HTTP...');
            await checkSensorStatesHTTP();
            return;
        }

        // Reset contador de erros se WebSocket está funcionando
        consecutiveErrors = 0;
        updateOverallStatus(activeSensorCount > 0, activeSensorCount);

    } catch (error) {
        console.error('❌ Erro na verificação de sensores:', error);
        // Em caso de erro, tenta HTTP como fallback
        await checkSensorStatesHTTP();
    } finally {
        isCheckingStatus = false;
        scheduleNextCheck();
    }
}

/**
 * NOVA FUNÇÃO: Verificação HTTP como fallback
 */
async function checkSensorStatesHTTP() {
    try {
        console.log('🌐 Verificação HTTP de sensores...');

        const response = await fetch(`/api/device/${device_id}/info`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const deviceInfo = await response.json();
        consecutiveErrors = 0;

        let hasActiveSensors = false;
        let activeSensorCount = 0;

        availableSensors.forEach(sensorType => {
            const sensorInfo = deviceInfo.sensors[sensorType];

            if (!sensorInfo) {
                updateSensorState(sensorType, false, 0);
                return;
            }

            const hasData = sensorInfo.has_data || false;
            const dataPoints = sensorInfo.data_points || 0;
            const timeSinceUpdate = sensorInfo.time_since_last_update;
            const isCurrentlyActive = hasData &&
                                    timeSinceUpdate !== null &&
                                    timeSinceUpdate < CONFIG.RECENT_DATA_WINDOW;

            updateSensorState(sensorType, isCurrentlyActive, dataPoints, {
                timeSinceUpdate,
                isRecent: sensorInfo.is_recent,
                source: 'http'
            });

            if (isCurrentlyActive) {
                hasActiveSensors = true;
                activeSensorCount++;
            }
        });

        updateOverallStatus(hasActiveSensors, activeSensorCount);

    } catch (error) {
        consecutiveErrors++;
        console.error(`❌ Erro na verificação HTTP ${consecutiveErrors}:`, error);

        if (consecutiveErrors >= CONFIG.MAX_CONSECUTIVE_ERRORS) {
            availableSensors.forEach(sensorType => {
                updateSensorState(sensorType, false, 0, { error: error.message });
            });
            updateOverallStatus(false, 0);
        }
    }
}

/**
 * Atualiza estado de um sensor específico
 */
function updateSensorState(sensorType, isActive, dataPoints, extra = {}) {
    const previousState = sensorStates[sensorType];
    
    sensorStates[sensorType] = {
        ...previousState,
        active: isActive,
        hasData: dataPoints > 0,
        dataPoints: dataPoints,
        lastCheck: Date.now(),
        timeSinceUpdate: extra.timeSinceUpdate,
        debugInfo: extra.debugInfo,
        isRecent: extra.isRecent,
        error: extra.error
    };
    
    // Atualiza UI do card apenas se houve mudança
    if (previousState.active !== isActive || 
        previousState.dataPoints !== dataPoints ||
        previousState.error !== extra.error) {
        updateSensorCard(sensorType, isActive);
    }
}

/**
 * Atualiza o card visual de um sensor com feedback detalhado
 */
function updateSensorCard(sensorType, isActive) {
    const card = document.getElementById(`card-${sensorType}`);
    const status = document.getElementById(`status-${sensorType}`);
    const button = document.getElementById(`btn-${sensorType}`);
    
    if (!card || !status || !button) {
        console.warn(` Elementos UI não encontrados para sensor: ${sensorType}`);
        return;
    }
    
    const sensorState = sensorStates[sensorType];
    const timeSinceCheck = Date.now() - sensorState.lastCheck;
    
    if (sensorState.error) {
        // Estado de erro
        card.className = 'sensor-card inactive';
        status.className = 'sensor-status inactive';
        status.textContent = `Erro: ${sensorState.error.substring(0, 30)}...`;
        button.disabled = true;
        button.textContent = 'Erro de Conexão';
    } else if (sensorState.isTransitioning) {
        // Estado de transição
        card.className = 'sensor-card active';
        status.className = 'sensor-status active';
        status.textContent = `Verificando... (${sensorState.dataPoints} pontos)`;
        button.disabled = false;
        button.textContent = 'Ver Gráfico';
    } else if (isActive) {
        // Estado ativo
        card.className = 'sensor-card active';
        status.className = 'sensor-status active';
        
        const updateTime = sensorState.timeSinceUpdate ? 
                          `${sensorState.timeSinceUpdate.toFixed(1)}s` : 'agora';
        status.textContent = `✅ Ativo (${sensorState.dataPoints} pontos, ${updateTime})`;
        button.disabled = false;
        button.textContent = 'Ver Gráfico';
    } else {
        // Estado inativo
        card.className = 'sensor-card inactive';
        status.className = 'sensor-status inactive';
        
        // Feedback específico baseado no estado
        if (sensorState.hasData && sensorState.timeSinceUpdate) {
            const timeAgo = sensorState.timeSinceUpdate.toFixed(1);
            status.textContent = ` Pausado há ${timeAgo}s (${sensorState.dataPoints} pontos)`;
        } else if (sensorState.hasData) {
            status.textContent = ` Dados antigos (${sensorState.dataPoints} pontos)`;
        } else {
            status.textContent = ' Sem dados - Ative no app';
        }
        
        button.disabled = true;
        button.textContent = 'Sensor Inativo';
    }
}

/**
 * Atualiza indicador de verificação
 */
function updateCheckingIndicator(isChecking) {
    const statusElement = document.getElementById('connection-status');
    if (!statusElement) return;
    
    if (isChecking) {
        const currentText = statusElement.textContent;
        if (!currentText.includes('🔄')) {
            statusElement.textContent = '🔄 ' + currentText;
        }
    } else {
        statusElement.textContent = statusElement.textContent.replace('🔄 ', '');
    }
}

/**
 * Atualiza o status geral da aplicação
 */
function updateOverallStatus(hasActiveSensors, activeSensorCount = 0) {
    const statusElement = document.getElementById('connection-status');
    const noSensorsMessage = document.getElementById('no-sensors-message');
    const sensorGrid = document.getElementById('sensor-grid');
    
    if (!statusElement) return;
    
    const totalSensors = availableSensors.length;
    const timeSinceLastCheck = lastCheckTime ? 
                             `${Math.round((Date.now() - lastCheckTime) / 1000)}s` : 'N/A';
    const connectedWS = Object.values(monitoringWebSockets).filter(ws => ws.isConnected).length;

    if (hasActiveSensors) {
        statusElement.innerHTML = `
            <strong>${activeSensorCount}/${totalSensors} sensores ativos</strong><br>
            <small>WebSockets: ${connectedWS}/${totalSensors} | Última verificação: ${timeSinceLastCheck}</small>
        `;
        
        if (noSensorsMessage) {
            noSensorsMessage.style.display = 'none';
        }
        if (sensorGrid) {
            sensorGrid.style.display = 'grid';
        }
    } else {
        const errorInfo = consecutiveErrors > 0 ? 
                         ` (${consecutiveErrors} erros)` : '';
        
        statusElement.innerHTML = `
            <strong>Nenhum sensor ativo${errorInfo}</strong><br>
            <small>WebSockets: ${connectedWS}/${totalSensors} | Última verificação: ${timeSinceLastCheck}</small>
        `;
        
        if (noSensorsMessage && totalSensors > 0) {
            noSensorsMessage.style.display = 'block';
        }
        if (sensorGrid && totalSensors === 0) {
            sensorGrid.style.display = 'none';
        }
    }
}

/**
 * Reagenda próxima verificação com backoff
 */
function scheduleNextCheck() {
    if (statusCheckInterval) {
        clearTimeout(statusCheckInterval);
    }
    
    // Calcula intervalo com backoff exponencial em caso de erros
    let interval = CONFIG.CHECK_INTERVAL;
    if (consecutiveErrors > 0) {
        interval = Math.min(
            CONFIG.CHECK_INTERVAL * Math.pow(CONFIG.ERROR_BACKOFF_MULTIPLIER, consecutiveErrors - 1),
            CONFIG.MAX_CHECK_INTERVAL
        );
    }
    
    // console.log(`Próxima verificação em ${interval}ms (erros: ${consecutiveErrors})`);
    
    statusCheckInterval = setTimeout(() => {
        checkSensorStates();
    }, interval);
}

/**
 * Mostra o gráfico de um sensor específico
 */
function showGraph(sensorType) {
    const sensorState = sensorStates[sensorType];

    if (!sensorState || !sensorState.active) {
        alert(`O sensor ${sensorType} não está ativo no momento.\n\nPor favor, ative-o no aplicativo móvel.`);
        return;
    }

    console.log(`📊 Mostrando gráfico para: ${sensorType}`);

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
        statusElement.textContent = '🔗 Conectando ao gráfico...';
    }

    // Cria nova instância do gráfico
    if (sensorConfigs[sensorType]) {
        const config = {
            deviceId: device_id,
            sensorType: sensorType,
            ...sensorConfigs[sensorType]
        };

        currentGraph = new SensorGraph(config);

        // Atualiza status quando gráfico conectar
        setTimeout(() => {
            if (statusElement && currentGraph && currentGraph.isConnected) {
                statusElement.textContent = '✅ Conectado ao WebSocket do gráfico';
            }
        }, 1000);
    }

    // Configura event listeners para controles do gráfico
    setupGraphControls();
}

/**
 * Retorna à tela de seleção
 */
function returnToSelection() {
    console.log('🔙 Retornando à tela de seleção');
    
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
    
    // Re-verifica status dos sensores imediatamente
    setTimeout(checkSensorStates, 200);
}

/**
 * Reconecta o gráfico atual
 */
function reconnectCurrentGraph() {
    if (currentGraph && currentSensor) {
        console.log(`Reconectando gráfico: ${currentSensor}`);
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
        console.log('👋 Limpando recursos antes de sair...');
        if (currentGraph) {
            currentGraph.disconnect();
        }
        if (statusCheckInterval) {
            clearTimeout(statusCheckInterval);
        }
        disconnectMonitoringWebSockets();
    });
    
    // Re-verificar quando volta para a página
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            consecutiveErrors = 0; // Reset erros

            // Reconecta WebSockets de monitoramento se necessário
            availableSensors.forEach(sensorType => {
                const wsData = monitoringWebSockets[sensorType];
                if (!wsData || !wsData.isConnected) {
                    console.log(`🔄 Reconectando WebSocket de monitoramento: ${sensorType}`);
                    createSensorMonitoringWebSocket(sensorType);
                }
            });

            setTimeout(checkSensorStates, 500);
        }
    });
}

/**
 * Inicia verificação periódica do status dos sensores
 */
function startSensorStatusCheck() {
    // console.log(`Iniciando verificação periódica (${CONFIG.CHECK_INTERVAL}ms)`);
    scheduleNextCheck();
}

/**
 * Cria WebSockets de monitoramento para todos os sensores
 */
function createMonitoringWebSockets() {
    console.log('🔌 Criando WebSockets de monitoramento para sensores:', availableSensors);

    availableSensors.forEach(sensorType => {
        createSensorMonitoringWebSocket(sensorType);
    });
}

/**
 * Cria WebSocket de monitoramento para um sensor específico
 */
function createSensorMonitoringWebSocket(sensorType) {
    if (monitoringWebSockets[sensorType]) {
        console.log(`⚠️ WebSocket de monitoramento para ${sensorType} já existe`);
        return;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/ws/device/${device_id}/sensor/${sensorType}`;

    console.log(`🔗 Conectando WebSocket de monitoramento: ${sensorType}`);

    try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log(`✅ WebSocket de monitoramento conectado: ${sensorType}`);
            monitoringWebSockets[sensorType] = {
                websocket: ws,
                isConnected: true,
                lastDataTime: null
            };
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                if (message.type === 'historical' || message.type === 'update') {
                    const dataPoints = message.data ? (message.data.time ? message.data.time.length : 0) : 0;
                    const hasData = dataPoints > 0;

                    // Atualiza timestamp da última mensagem
                    monitoringWebSockets[sensorType].lastDataTime = Date.now();

                    // Atualiza estado do sensor com base nos dados recebidos
                    updateSensorState(sensorType, hasData, dataPoints, {
                        timeSinceUpdate: 0, // Dados acabaram de chegar
                        isRecent: true,
                        source: 'websocket'
                    });
                }
            } catch (error) {
                console.error(`❌ Erro ao processar dados WebSocket de ${sensorType}:`, error);
            }
        };

        ws.onerror = (error) => {
            console.error(`❌ Erro WebSocket de monitoramento ${sensorType}:`, error);
            if (monitoringWebSockets[sensorType]) {
                monitoringWebSockets[sensorType].isConnected = false;
            }
        };

        ws.onclose = (event) => {
            console.log(`🔌 WebSocket de monitoramento ${sensorType} desconectado:`, event.code);

            if (monitoringWebSockets[sensorType]) {
                monitoringWebSockets[sensorType].isConnected = false;

                // Reconecta automaticamente se não foi fechado intencionalmente
                if (event.code !== 1000) {
                    setTimeout(() => {
                        console.log(`🔄 Reconectando WebSocket de monitoramento: ${sensorType}`);
                        createSensorMonitoringWebSocket(sensorType);
                    }, 2000);
                }
            }
        };

    } catch (error) {
        console.error(`❌ Erro ao criar WebSocket de monitoramento para ${sensorType}:`, error);
    }
}

/**
 * Limpa todos os WebSockets de monitoramento
 */
function disconnectMonitoringWebSockets() {
    console.log('🔌 Desconectando WebSockets de monitoramento...');

    Object.keys(monitoringWebSockets).forEach(sensorType => {
        const wsData = monitoringWebSockets[sensorType];
        if (wsData && wsData.websocket) {
            wsData.websocket.close(1000, 'Limpeza de recursos');
        }
    });

    monitoringWebSockets = {};
}

// Funções globais para serem chamadas pelo HTML
window.showGraph = showGraph;
window.returnToSelection = returnToSelection;
window.reconnectCurrentGraph = reconnectCurrentGraph;

// Debug - expõe funções para console
window.sensorStates = sensorStates;
window.monitoringWebSockets = monitoringWebSockets;
window.checkSensorStates = checkSensorStates;
window.CONFIG = CONFIG;

// Função de debug para testar estados
window.debugSensorStates = function() {
    console.table(sensorStates);
    console.log('WebSockets de Monitoramento:', monitoringWebSockets);
    console.log('Configuração:', CONFIG);
    console.log('Últimos erros:', consecutiveErrors);
};

// Inicialização quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', initializeApp);