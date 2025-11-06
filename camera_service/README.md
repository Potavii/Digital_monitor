# Camera Service

Serviço responsável pela captura e streaming de câmeras IP.

## Funcionalidades
- Captura de vídeo RTSP
- Streaming em tempo real
- Controle de câmeras (iniciar/parar)

## Porta
5001

## API Endpoints
- `GET /cameras` - Listar câmeras
- `POST /cameras/{id}/start` - Iniciar câmera
- `POST /cameras/{id}/stop` - Parar câmera
- `GET /cameras/{id}/stream` - Stream de vídeo