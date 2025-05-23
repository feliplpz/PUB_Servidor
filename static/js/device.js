let graphData = {
    time: [],
    x: [],
    y: [],
    z: []
};

const device_id = window.DEVICE_ID;
let websocket = null;
let reconnectInterval = null;

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
    
   
    websocket = new WebSocket(`ws://127.0.0.1:5000/ws/device/${device_id}/sensor/accelerometer`);
      websocket.onopen = function(event) {
        console.log('WebSocket conectado');
        loading.style.display = 'none';
        
       
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    websocket.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Dados recebidos via WebSocket:', data);
            
            // Atualizar dados do gráfico
            graphData = data;
            
            // Atualizar arrays do Plotly
            plotlyData[0].x = graphData.time;
            plotlyData[0].y = graphData.x;
            plotlyData[1].x = graphData.time;
            plotlyData[1].y = graphData.y;
            plotlyData[2].x = graphData.time;
            plotlyData[2].y = graphData.z;
            
           
            updateGraph();
            
        } catch (error) {
            console.error('Erro ao processar dados WebSocket:', error);
        }
    };
    
    
    websocket.onerror = function(error) {
        console.error('Erro WebSocket:', error);
        loading.style.display = 'block';
        loading.textContent = 'Erro na conexão...';
    };
    
    websocket.onclose = function(event) {
        console.log('WebSocket desconectado:', event.code, event.reason);
        loading.style.display = 'block';
        loading.textContent = 'Reconectando...';
        
        if (!reconnectInterval) {
            reconnectInterval = setInterval(function() {
                console.log('Tentando reconectar...');
                connectWebSocket();
            }, 2000);
        }
    };
}

// Função para desconectar WebSocket
function disconnectWebSocket() {
    if (websocket) {
        websocket.close();
        websocket = null;
    }
    if (reconnectInterval) {
        clearInterval(reconnectInterval);
        reconnectInterval = null;
    }
}
document.getElementById('toggle-x').addEventListener('click', () => toggleGraph('x'));
document.getElementById('toggle-y').addEventListener('click', () => toggleGraph('y'));
document.getElementById('toggle-z').addEventListener('click', () => toggleGraph('z'));
window.addEventListener('beforeunload', function() {
    disconnectWebSocket();
});

Plotly.newPlot('graph', plotlyData, layout);
connectWebSocket();