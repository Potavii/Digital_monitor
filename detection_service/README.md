# Detection Service

Serviço responsável pela detecção de objetos usando IA (YOLOv8).

## Funcionalidades
- Detecção de pessoas com YOLOv8
- Definição de áreas de monitoramento
- Processamento de frames
- Envio de alertas para outros serviços

## Porta
5002

## API Endpoints
- `POST /detect` - Processar frame para detecção
- `POST /areas/{camera_id}` - Definir área de monitoramento
- `GET /models` - Listar modelos disponíveis
- `POST /models/load` - Carregar modelo YOLO