// static/js/monitoramento.js - Scripts para interface de monitoramento

class SistemaMonitoramento {
    constructor() {
        this.socket = io();
        this.inicializarEventos();
        this.inicializarControles();
    }

    inicializarEventos() {
        this.socket.on('connect', () => {
            console.log('🟢 Conectado ao servidor WebSocket');
        });

        this.socket.on('disconnect', () => {
            console.log('🔴 Desconectado do servidor WebSocket');
        });

        this.socket.on('novo_evento', (data) => {
            this.tratarNovoEvento(data);
        });

        this.socket.on('atualizacao_camera', (data) => {
            this.atualizarCamera(data);
        });
    }

    inicializarControles() {
        // Botões de controle de câmera
        document.querySelectorAll('[onclick*="controlarCamera"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const partes = e.target.getAttribute('onclick').split("'");
                const camId = partes[1];
                const acao = partes[3];
                this.controlarCamera(camId, acao);
            });
        });

        // Botão atualizar página
        const btnAtualizar = document.querySelector('button[onclick="atualizarPagina"]');
        if (btnAtualizar) {
            btnAtualizar.addEventListener('click', () => {
                location.reload();
            });
        }
    }

    controlarCamera(camId, acao) {
        fetch(`/api/cameras/${camId}/controle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ acao: acao })
        })
        .then(response => response.json())
        .then(data => {
            console.log(`${acao} para ${camId}:`, data.mensagem);
            this.mostrarNotificacao(data.mensagem, 'success');
        })
        .catch(error => {
            console.error('Erro:', error);
            this.mostrarNotificacao('Erro ao executar ação', 'error');
        });
    }

    tratarNovoEvento(data) {
        console.log('🚨 Novo evento detectado:', data);

        // Atualiza interface se for desta câmera
        const cameraElement = document.querySelector(`[data-cam-id="${data.camera_id}"]`);
        if (cameraElement) {
            this.destacarCamera(cameraElement);

            // Toca som de alerta (se suportado)
            this.tocarAlerta();

            // Remove destaque após alguns segundos
            setTimeout(() => {
                this.removerDestaqueCamera(cameraElement);
            }, 10000);
        }
    }

    atualizarCamera(data) {
        const cameraElement = document.querySelector(`[data-cam-id="${data.camera_id}"]`);
        if (cameraElement) {
            // Atualiza informações da câmera
            const infoElement = cameraElement.querySelector('.camera-info');
            if (infoElement) {
                infoElement.innerHTML = `
                    <span>Status: <strong>${data.detectando ? '🚨 ALERTA' : '✅ MONITORANDO'}</strong></span>
                    <span>FPS: ${data.fps.toFixed(1)}</span>
                    <span>Detecções: ${data.total_deteccoes}</span>
                    <span>Última: ${new Date().toLocaleTimeString('pt-BR')}</span>
                `;
            }

            // Atualiza indicador de status
            const statusIndicator = cameraElement.querySelector('.status-indicator');
            if (statusIndicator) {
                statusIndicator.className = `status-indicator status-${data.detectando ? 'alerta' : 'online'}`;
            }

            // Adiciona/remove classe de alerta
            if (data.detectando) {
                cameraElement.classList.add('alerta');
            } else {
                cameraElement.classList.remove('alerta');
            }
        }
    }

    destacarCamera(cameraElement) {
        cameraElement.classList.add('alerta');
        const statusIndicator = cameraElement.querySelector('.status-indicator');
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator status-alerta';
        }
    }

    removerDestaqueCamera(cameraElement) {
        cameraElement.classList.remove('alerta');
        const statusIndicator = cameraElement.querySelector('.status-indicator');
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator status-online';
        }
    }

    tocarAlerta() {
        try {
            // Tenta tocar som de alerta se o navegador suportar
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(1000, audioContext.currentTime + 0.1);

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (e) {
            console.log('Não foi possível tocar som de alerta:', e);
        }
    }

    mostrarNotificacao(mensagem, tipo = 'info') {
        // Cria elemento de notificação
        const notificacao = document.createElement('div');
        notificacao.className = `notificacao notificacao-${tipo}`;
        notificacao.textContent = mensagem;
        notificacao.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${tipo === 'success' ? '#28a745' : tipo === 'error' ? '#dc3545' : '#17a2b8'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            font-weight: bold;
            animation: slideIn 0.3s ease;
        `;

        document.body.appendChild(notificacao);

        // Remove após 3 segundos
        setTimeout(() => {
            notificacao.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(notificacao);
            }, 300);
        }, 3000);
    }
}

// Inicializa quando DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    const sistema = new SistemaMonitoramento();
});

// Funções globais para compatibilidade
function atualizarPagina() {
    location.reload();
}

function controlarCamera(camId, acao) {
    fetch(`/api/cameras/${camId}/controle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ acao: acao })
    })
    .then(response => response.json())
    .then(data => {
        console.log(`${acao} para ${camId}:`, data.mensagem);
    })
    .catch(error => {
        console.error('Erro:', error);
    });
}