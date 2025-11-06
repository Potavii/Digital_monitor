# Web Interface

Interface web principal do sistema de monitoramento.

## Funcionalidades
- Dashboard principal
- Controle de câmeras
- Visualização de streams
- Configurações do sistema
- Histórico de eventos

## Porta
5000

## API Endpoints
- `GET /` - Dashboard principal
- `GET /cameras` - Lista de câmeras
- `GET /events` - Histórico de eventos
- `GET /settings` - Configurações
- WebSocket para atualizações em tempo real