class SensorGraph {
    constructor(config) {
        this.deviceId = config.deviceId;
        this.sensorType = config.sensorType;
        this.containerId = config.containerId;
        this.title = config.title || `Dados do ${config.sensorType}`;
        this.yAxisTitle = config.yAxisTitle || 'Valores';
        this.colors = config.colors || ['blue', 'orange', 'green'];
        this.axisLabels = config.axisLabels || ['X', 'Y', 'Z'];
        this.unit = config.unit || '';
        this.mode = config.mode || 'graph'; // 'graph' ou 'monitoring'

        this.websocket = null;
        this.isConnected = false;

        this.graphData = { time: [], x: [], y: [], z: [] };

        this.layout = {
            title: this.title,
            xaxis: { title: 'Tempo (s)', showgrid: true, gridcolor: '#444' },
            yaxis: { title: this.yAxisTitle, showgrid: true, gridcolor: '#444' },
            showlegend: true,
            plot_bgcolor: "#121212",
            paper_bgcolor: "#121212",
            font: { color: 'white' },
            legend: { orientation: 'h', x: 0.5, xanchor: 'center', y: -0.1 }
        };

        this.plotlyData = [
            { x: this.graphData.time, y: this.graphData.x, mode: 'lines', name: `${this.axisLabels[0]} ${this.unit}`, line: { color: this.colors[0] }, visible: true },
            { x: this.graphData.time, y: this.graphData.y, mode: 'lines', name: `${this.axisLabels[1]} ${this.unit}`, line: { color: this.colors[1] }, visible: true },
            { x: this.graphData.time, y: this.graphData.z, mode: 'lines', name: `${this.axisLabels[2]} ${this.unit}`, line: { color: this.colors[2] }, visible: true }
        ];

        this.init();
    }

    init() {
        this.createGraph();
        this.connectWebSocket();
    }

    createGraph() {
        try {
            Plotly.newPlot(this.containerId, this.plotlyData, this.layout);
            console.log(`Gráfico criado: ${this.sensorType}`);
        } catch (error) {
            console.error('Erro ao criar gráfico:', error);
        }
    }

    updateGraph() {
        try {
            Plotly.react(this.containerId, this.plotlyData, this.layout);
        } catch (error) {
            console.error('Erro ao atualizar gráfico:', error);
        }
    }

    toggleAxis(axis) {
        const index = { x: 0, y: 1, z: 2 }[axis];
        if (index !== undefined && this.plotlyData[index]) {
            this.plotlyData[index].visible = !this.plotlyData[index].visible;
            this.updateGraph();
        }
    }

    connectWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = window.location.host;
        const wsUrl = `${wsProtocol}//${wsHost}/ws/device/${this.deviceId}/sensor/${this.sensorType}?mode=${this.mode}`;

        console.log(`Conectando WebSocket ${this.mode}: ${this.sensorType}`);

        try {
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log(`✅ WebSocket ${this.mode} conectado: ${this.sensorType}`);
                this.isConnected = true;
            };

            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);

                    if (message.type === 'historical' || message.type === 'update') {
                        this.updateData(message.data);
                    }
                } catch (error) {
                    console.error(`Erro ao processar dados ${this.mode}:`, error);
                }
            };

            this.websocket.onerror = (error) => {
                console.error(`Erro WebSocket ${this.mode}:`, error);
                this.isConnected = false;
            };

            this.websocket.onclose = (event) => {
                console.log(`WebSocket ${this.mode} desconectado: ${this.sensorType} (${event.code})`);
                this.isConnected = false;
            };

        } catch (error) {
            console.error(`Erro ao criar WebSocket ${this.mode}:`, error);
            this.isConnected = false;
        }
    }

    updateData(data) {
        if (!data) return;

        this.graphData = data;

        if (this.plotlyData[0]) {
            this.plotlyData[0].x = this.graphData.time || [];
            this.plotlyData[0].y = this.graphData.x || [];
        }
        if (this.plotlyData[1]) {
            this.plotlyData[1].x = this.graphData.time || [];
            this.plotlyData[1].y = this.graphData.y || [];
        }
        if (this.plotlyData[2]) {
            this.plotlyData[2].x = this.graphData.time || [];
            this.plotlyData[2].y = this.graphData.z || [];
        }

        this.updateGraph();
    }

    disconnect() {
        if (this.websocket && this.isConnected) {
            this.websocket.close(1000, `Fechando ${this.mode}`);
            this.websocket = null;
            this.isConnected = false;
        }
    }

    reconnect() {
        if (!this.isConnected) {
            console.log(`Reconectando ${this.mode}: ${this.sensorType}`);
            this.connectWebSocket();
        }
    }

    getConnectionInfo() {
        return {
            sensorType: this.sensorType,
            deviceId: this.deviceId,
            mode: this.mode,
            isConnected: this.isConnected,
            hasData: this.graphData.time && this.graphData.time.length > 0
        };
    }
}