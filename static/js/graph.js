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
        
        // Estado da conexão
        this.websocket = null;
        this.reconnectInterval = null;
        this.isConnected = false;
        
        // Dados do gráfico
        this.graphData = {
            time: [],
            x: [],
            y: [],
            z: []
        };
        
        // Configuração do layout Plotly
        this.layout = {
            title: this.title,
            xaxis: {
                title: 'Tempo (s)',
                showgrid: true,
                gridcolor: '#444'
            },
            yaxis: {
                title: this.yAxisTitle,
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
        
        // Dados do Plotly
        this.plotlyData = [
            {
                x: this.graphData.time,
                y: this.graphData.x,
                mode: 'lines',
                name: `${this.axisLabels[0]} ${this.unit}`,
                line: { color: this.colors[0] },
                visible: true
            },
            {
                x: this.graphData.time,
                y: this.graphData.y,
                mode: 'lines',
                name: `${this.axisLabels[1]} ${this.unit}`,
                line: { color: this.colors[1] },
                visible: true
            },
            {
                x: this.graphData.time,
                y: this.graphData.z,
                mode: 'lines',
                name: `${this.axisLabels[2]} ${this.unit}`,
                line: { color: this.colors[2] },
                visible: true
            }
        ];
        
        this.init();
    }
    
    /**
     * Inicializa o gráfico e conecta o WebSocket
     */
    init() {
        this.createGraph();
        this.connectWebSocket();
        this.setupEventListeners();
    }
    
    /**
     * Cria o gráfico inicial
     */
    createGraph() {
        try {
            Plotly.newPlot(this.containerId, this.plotlyData, this.layout);
            console.log(`Gráfico criado para ${this.sensorType} no container ${this.containerId}`);
        } catch (error) {
            console.error('Erro ao criar gráfico:', error);
        }
    }
    
    /**
     * Atualiza o gráfico com novos dados
     */
    updateGraph() {
        try {
            Plotly.react(this.containerId, this.plotlyData, this.layout);
        } catch (error) {
            console.error('Erro ao atualizar gráfico:', error);
        }
    }
    
    /**
     * Alterna visibilidade de um eixo específico
     */
    toggleAxis(axis) {
        const index = { x: 0, y: 1, z: 2 }[axis];
        if (index !== undefined && this.plotlyData[index]) {
            this.plotlyData[index].visible = !this.plotlyData[index].visible;
            this.updateGraph();
        }
    }
    
    /**
     * Conecta ao WebSocket
     */
    connectWebSocket() {
        console.log(`Conectando WebSocket para ${this.deviceId}:${this.sensorType}`);
        
        const loadingEl = document.getElementById(`loading-${this.sensorType}`) || 
                         document.getElementById('loading-current');
        
        if (loadingEl) {
            loadingEl.style.display = 'block';
            loadingEl.textContent = 'Conectando...';
        }
        
        // Detecta protocolo e host
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = window.location.host;
        const wsUrl = `${wsProtocol}//${wsHost}/ws/device/${this.deviceId}/sensor/${this.sensorType}`;
        
        console.log(`URL WebSocket: ${wsUrl}`);
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = (event) => {
                console.log(`WebSocket conectado para ${this.sensorType}`);
                if (loadingEl) loadingEl.style.display = 'none';
                this.isConnected = true;
                
                // Para o intervalo de reconexão se existir
                if (this.reconnectInterval) {
                    clearInterval(this.reconnectInterval);
                    this.reconnectInterval = null;
                }
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log(`Dados recebidos para ${this.sensorType}:`, message);
                    
                    if (message.type === 'historical' || message.type === 'update') {
                        this.updateData(message.data);
                    }
                } catch (error) {
                    console.error(`Erro ao processar dados do ${this.sensorType}:`, error);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error(`Erro WebSocket ${this.sensorType}:`, error);
                this.isConnected = false;
                if (loadingEl) {
                    loadingEl.style.display = 'block';
                    loadingEl.textContent = 'Erro na conexão...';
                }
            };
            
            this.websocket.onclose = (event) => {
                console.log(`WebSocket ${this.sensorType} desconectado:`, event.code, event.reason);
                this.isConnected = false;
                if (loadingEl) {
                    loadingEl.style.display = 'block';
                    loadingEl.textContent = 'Reconectando...';
                }
                
                // Só reconecta se não foi fechado intencionalmente
                if (event.code !== 1000 && !this.reconnectInterval) {
                    this.reconnectInterval = setInterval(() => {
                        console.log(`Tentando reconectar ${this.sensorType}...`);
                        this.connectWebSocket();
                    }, 2000);
                }
            };
            
        } catch (error) {
            console.error('Erro ao criar WebSocket:', error);
            this.isConnected = false;
        }
    }
    
    /**
     * Atualiza os dados do gráfico
     */
    updateData(data) {
        if (!data) return;
        
        this.graphData = data;
        
        // Atualiza arrays do Plotly
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
    
    /**
     * Desconecta o WebSocket
     */
    disconnect() {
        if (this.websocket && this.isConnected) {
            this.websocket.close(1000, 'Fechando gráfico');
            this.websocket = null;
            this.isConnected = false;
        }
        if (this.reconnectInterval) {
            clearInterval(this.reconnectInterval);
            this.reconnectInterval = null;
        }
    }
    
    /**
     * Reconecta quando necessário
     */
    reconnect() {
        if (!this.isConnected) {
            console.log(`Reconectando ${this.sensorType}...`);
            this.connectWebSocket();
        }
    }
    
    /**
     * Configura event listeners para o ciclo de vida da página
     */
    setupEventListeners() {
        // Desconecta quando sai da página
        window.addEventListener('beforeunload', () => {
            this.disconnect();
        });
        
        // Reconecta quando volta para a página
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && !this.isConnected) {
                console.log(`Página voltou ao foco, reconectando ${this.sensorType}...`);
                this.reconnect();
            }
        });
    }
    
    /**
     * Obtém informações sobre o estado da conexão
     */
    getConnectionInfo() {
        return {
            sensorType: this.sensorType,
            deviceId: this.deviceId,
            isConnected: this.isConnected,
            hasData: this.graphData.time && this.graphData.time.length > 0
        };
    }
}