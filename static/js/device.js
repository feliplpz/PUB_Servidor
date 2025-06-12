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
    startSensorStatusCheck();
    
    // Primeira verificação imediata
    setTimeout(() => {
        console.log('⚡ Executando verificação inicial...');
        checkSensorStates();
    }, 100);
}

/**
 * Verifica estado atual dos sensores com lógica melhorada
 */
async function checkSensorStates() {
    if (isCheckingStatus) {
        console.log(' Verificação já em andamento, pulando...');
        return;
    }
    
    isCheckingStatus = true;
    lastCheckTime = Date.now();
    
    // Atualiza indicador visual de verificação
    updateCheckingIndicator(true);
    
    try {
        console.log(`🔍 Verificando sensores... (tentativa ${consecutiveErrors + 1})`);
        
        const response = await fetch(`/api/device/${device_id}/info`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const deviceInfo = await response.json();
        
        // Reset contador de erros em caso de sucesso
        consecutiveErrors = 0;
        
        // Atualiza lista de sensores disponíveis se necessário
        if (availableSensors.length === 0 && deviceInfo.sensors) {
            const apiSensors = Object.keys(deviceInfo.sensors);
            availableSensors.splice(0, 0, ...apiSensors);
            console.log(' Sensores detectados:', availableSensors);
        }
        
        let hasActiveSensors = false;
        let activeSensorCount = 0;
        
        // Processa cada sensor
        availableSensors.forEach(sensorType => {
            const sensorInfo = deviceInfo.sensors[sensorType];
            const previousState = sensorStates[sensorType];
            
            if (!sensorInfo) {
                console.warn(`Sensor ${sensorType} não encontrado na resposta`);
                updateSensorState(sensorType, false, 0);
                return;
            }
            
            // Lógica de detecção melhorada
            const hasData = sensorInfo.has_data || false;
            const dataPoints = sensorInfo.data_points || 0;
            const timeSinceUpdate = sensorInfo.time_since_last_update;
            
            // Considera ativo se:
            // 1. Tem dados E
            // 2. Foi atualizado recentemente (últimos 4 segundos)
            const isCurrentlyActive = hasData && 
                                    timeSinceUpdate !== null && 
                                    timeSinceUpdate < CONFIG.RECENT_DATA_WINDOW;
            
            // Lógica de transição para evitar flicker
            let finalActiveState = isCurrentlyActive;
            
            if (!isCurrentlyActive && previousState.active) {
                // Sensor pode estar transitioning de ativo para inativo
                if (!previousState.isTransitioning) {
                    console.log(`${sensorType}: Iniciando transição para inativo`);
                    sensorStates[sensorType].isTransitioning = true;
                    sensorStates[sensorType].transitionStartTime = Date.now();
                    finalActiveState = true; // Mantém ativo durante transição
                } else {
                    // Verifica se tempo de transição passou
                    const transitionTime = Date.now() - previousState.transitionStartTime;
                    if (transitionTime > CONFIG.STATUS_TRANSITION_DELAY) {
                        console.log(`${sensorType}: Transição completa, sensor inativo`);
                        finalActiveState = false;
                        sensorStates[sensorType].isTransitioning = false;
                    } else {
                        console.log(` ${sensorType}: Ainda em transição (${transitionTime}ms)`);
                        finalActiveState = true; // Ainda em transição
                    }
                }
            } else if (isCurrentlyActive && previousState.isTransitioning) {
                // Sensor voltou a ficar ativo durante transição
                console.log(`✅ ${sensorType}: Voltou a ficar ativo, cancelando transição`);
                sensorStates[sensorType].isTransitioning = false;
                finalActiveState = true;
            } else if (isCurrentlyActive) {
                // Sensor ativo normalmente
                sensorStates[sensorType].isTransitioning = false;
                if (previousState.lastActiveTime === null || !previousState.active) {
                    console.log(`${sensorType}: Sensor ativado`);
                }
                sensorStates[sensorType].lastActiveTime = Date.now();
            }
            
            updateSensorState(sensorType, finalActiveState, dataPoints, {
                timeSinceUpdate,
                debugInfo: sensorInfo.debug_info,
                isRecent: sensorInfo.is_recent
            });
            
            if (finalActiveState) {
                hasActiveSensors = true;
                activeSensorCount++;
            }
        });
        
        // Atualiza status geral
        updateOverallStatus(hasActiveSensors, activeSensorCount);
        
        // Verifica se o sensor atual foi desligado
        if (currentScreen === 'graph' && currentSensor) {
            const currentSensorState = sensorStates[currentSensor];
            if (!currentSensorState || !currentSensorState.active) {
                console.log(`Sensor atual (${currentSensor}) foi desligado, retornando à seleção`);
                returnToSelection();
            }
        }
        
        console.log(`✅ Verificação concluída: ${activeSensorCount}/${availableSensors.length} sensores ativos`);
        
    } catch (error) {
        consecutiveErrors++;
        console.error(` Erro na verificação ${consecutiveErrors}:`, error);
        
        // Em caso de erro, marca todos como inativos após algumas tentativas
        if (consecutiveErrors >= CONFIG.MAX_CONSECUTIVE_ERRORS) {
            console.warn('🚫 Múltiplos erros detectados, marcando sensores como inativos');
            availableSensors.forEach(sensorType => {
                updateSensorState(sensorType, false, 0, { error: error.message });
            });
            updateOverallStatus(false, 0);
        }
        
    } finally {
        isCheckingStatus = false;
        updateCheckingIndicator(false);
        
        // Reagenda próxima verificação com backoff em caso de erro
        scheduleNextCheck();
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
    
    if (hasActiveSensors) {
        statusElement.innerHTML = `
            <strong>${activeSensorCount}/${totalSensors} sensores ativos</strong><br>
            <small>Última verificação: ${timeSinceLastCheck} | Selecione um sensor para visualizar</small>
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
            <small>Última verificação: ${timeSinceLastCheck} | Ative sensores no app móvel</small>
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
    
    console.log(`Próxima verificação em ${interval}ms (erros: ${consecutiveErrors})`);
    
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
    
    console.log(`Mostrando gráfico para: ${sensorType}`);
    
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
        statusElement.textContent = '🔗 Conectando...';
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
                statusElement.textContent = '✅ Conectado ao WebSocket';
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
    });
    
    // Re-verificar quando volta para a página
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            console.log('👁️ Página voltou ao foco, verificando sensores...');
            consecutiveErrors = 0; // Reset erros
            setTimeout(checkSensorStates, 500);
        }
    });
}

/**
 * Inicia verificação periódica do status dos sensores
 */
function startSensorStatusCheck() {
    console.log(`Iniciando verificação periódica (${CONFIG.CHECK_INTERVAL}ms)`);
    scheduleNextCheck();
}

// Funções globais para serem chamadas pelo HTML
window.showGraph = showGraph;
window.returnToSelection = returnToSelection;
window.reconnectCurrentGraph = reconnectCurrentGraph;

// Debug - expõe funções para console
window.sensorStates = sensorStates;
window.checkSensorStates = checkSensorStates;
window.CONFIG = CONFIG;

// Função de debug para testar estados
window.debugSensorStates = function() {
    console.table(sensorStates);
    console.log('Configuração:', CONFIG);
    console.log('Últimos erros:', consecutiveErrors);
    console.log('Próxima verificação em:', statusCheckInterval ? 'agendada' : 'não agendada');
};

// Inicialização quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', initializeApp);