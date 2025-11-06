# Database Service

API REST para acesso ao banco de dados do sistema.

## Funcionalidades
- CRUD de câmeras
- CRUD de eventos
- CRUD de configurações
- Estatísticas do sistema
- Backup e limpeza

## Porta
5004

## API Endpoints
- `GET /cameras` - Listar câmeras
- `POST /cameras` - Adicionar câmera
- `PUT /cameras/{id}` - Atualizar câmera
- `DELETE /cameras/{id}` - Remover câmera
- `GET /events` - Listar eventos
- `GET /stats` - Estatísticas gerais