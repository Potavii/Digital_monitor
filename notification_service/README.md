# Notification Service

Serviço responsável pelo envio de alertas e notificações.

## Funcionalidades
- Envio de e-mails
- Notificações push
- Alarmes sonoros
- Log de eventos

## Porta
5003

## API Endpoints
- `POST /alert` - Enviar alerta
- `POST /email` - Enviar e-mail
- `GET /templates` - Listar templates de e-mail
- `POST /test-email` - Testar configuração de e-mail