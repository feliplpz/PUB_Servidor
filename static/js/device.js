let graphData = {
    time: [],
    x: [],
    y: [],
    z: []
};

const device_id = window.DEVICE_ID;

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

// Botões para alternar gráficos
document.getElementById('toggle-x').addEventListener('click', () => toggleGraph('x'));
document.getElementById('toggle-y').addEventListener('click', () => toggleGraph('y'));
document.getElementById('toggle-z').addEventListener('click', () => toggleGraph('z'));

// Função para buscar dados do servidor
async function fetchData() {
    const loading = document.getElementById('loading');
    loading.style.display = 'block'; // Mostra o indicador de carregamento

    try {
        const response = await fetch(`/api/device/${device_id}/data/accelerometer`);
        if (!response.ok) {
            throw new Error(`Erro na requisição: ${response.statusText
                }`);
        }
        const data = await response.json();
        graphData = data;

        // Atualiza os dados do gráfico
        plotlyData[0].x = graphData.time;
        plotlyData[0].y = graphData.x;
        plotlyData[1].x = graphData.time;
        plotlyData[1].y = graphData.y;
        plotlyData[2].x = graphData.time;
        plotlyData[2].y = graphData.z;

        updateGraph();
    } catch (error) {
        console.error('Erro ao buscar dados:', error);
    } finally {
        loading.style.display = 'none'; // Oculta o indicador de carregamento
    }
}

// Atualiza o gráfico periodicamente
setInterval(fetchData, 500);

// Inicializa o gráfico
Plotly.newPlot('graph', plotlyData, layout);