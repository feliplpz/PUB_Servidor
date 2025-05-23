let graphData = {
    time: [],
    x: [],
    y: [],
    z: []
};

const device_id = window.DEVICE_ID;
let websocket = null;
let reconnectInterval = null;
let isConnected = false;

const layout = {
    title: 'Aceleração nos Eixos X, Y e Z',
    xaxis: {
        title: 'Tempo (s)',
        showgrid: true,
        gridcolor: '#444'
    },
    yaxis: {
        title: 'Aceleração (m/s²)',
        showgrid: true,
        gridcolor: '#444'
    },
    showlegend: true,
    plot_bgcolor: "#121212",
    paper_bgcolor: "#121212",
    font: {
        color: 'white'
    },
    legend: {
        orientation: 'h',
        x: 0.5,
        xanchor: 'center',
        y: -0.1
    }
};

const plotlyData = [
    {
        x: graphData.time,
        y: graphData.x,
        mode: 'lines',
        name: 'Aceleração X',
        line: {
            color: 'blue'
        },
        visible: true
    }, {
        x: graphData.time,
        y: graphData.y,
        mode: 'lines',
        name: 'Aceleração Y',
        line: {
            color: 'orange'
        },
        visible: true
    }, {
        x: graphData.time,
        y: graphData.z,
        mode: 'lines',
        name: 'Aceleração Z',
        line: {
            color: 'green'
        },
        visible: true
    }
];

// Função para atualizar o gráfico
function updateGraph() {
    Plotly.react('graph', plotlyData, layout);
}

// Função para alternar visibilidade de cada gráfico
function toggleGraph(axis) {
    const index = {
        x: 0,
        y: 1,
        z: 2
    }[axis];
    plotlyData[index].visible = !plotlyData[index].visible;
    updateGraph();
}

function connectWebSocket() {
    console.log('TENTANDO CONECTAR WEBSOCKET:', device_id);  
    const loading = document.getElementById('loading');
    
    // Detecta se está rodando local ou não
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/ws/device/${device_id}/sensor/accelerometer`;
    
    console.log('URL WebSocket:', wsUrl);
    loading.style.display = 'block';
    loading.textContent = 'Conectando...';
   
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = function(event) {
        console.log('WebSocket conectado com sucesso');
        loading.style.display = 'none';
        isConnected = true;
        
        // Para o intervalo de reconexão se existir
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    websocket.onmessage = function(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('Mensagem WebSocket recebida:', message);
            
            if (message.type === 'historical' || message.type === 'update') {
                // Atualizar dados do gráfico
                graphData = message.data;
                
                // Atualizar arrays do Plotly
                plotlyData[0].x = graphData.time;
                plotlyData[0].y = graphData.x;
                plotlyData[1].x = graphData.time;
                plotlyData[1].y = graphData.y;
                plotlyData[2].x = graphData.time;
                plotlyData[2].y = graphData.z;
                
                // Atualizar gráfico
                updateGraph();
            }
            
        } catch (error) {
            console.error('Erro ao processar dados WebSocket:', error);
        }
    };
    
    websocket.onerror = function(error) {
        console.error('Erro WebSocket:', error);
        isConnected = false;
        loading.style.display = 'block';
        loading.textContent = 'Erro na conexão...';
    };
    
    websocket.onclose = function(event) {
        console.log('WebSocket desconectado:', event.code, event.reason);
        isConnected = false;
        loading.style.display = 'block';
        loading.textContent = 'Reconectando...';
        
        // Só reconecta se não foi fechado intencionalmente
        if (event.code !== 1000 && !reconnectInterval) {
            reconnectInterval = setInterval(function() {
                console.log('Tentando reconectar...');
                connectWebSocket();
            }, 2000);
        }
    };
}

// Função para desconectar WebSocket
function disconnectWebSocket() {
    if (websocket && isConnected) {
        websocket.close(1000, 'Fechando página');
        websocket = null;
        isConnected = false;
    }
    if (reconnectInterval) {
        clearInterval(reconnectInterval);
        reconnectInterval = null;
    }
}

// Event listeners para os botões
document.getElementById('toggle-x').addEventListener('click', () => toggleGraph('x'));
document.getElementById('toggle-y').addEventListener('click', () => toggleGraph('y'));
document.getElementById('toggle-z').addEventListener('click', () => toggleGraph('z'));

// Desconecta quando sai da página
window.addEventListener('beforeunload', function() {
    disconnectWebSocket();
});

// Reconecta quando volta para a página
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible' && !isConnected) {
        console.log('Página voltou ao foco, reconectando...');
        connectWebSocket();
    }
});

// Inicializa o gráfico e conecta o WebSocket
Plotly.newPlot('graph', plotlyData, layout);
connectWebSocket();