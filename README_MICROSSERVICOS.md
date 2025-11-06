# Sistema de Monitoramento - Arquitetura de Microsserviços

Este documento descreve a arquitetura de microsserviços implementada para o sistema de monitoramento de segurança.

## 🏗️ Arquitetura Geral

O sistema foi reestruturado em **5 microsserviços independentes**:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Camera Service │    │ Detection Service│
│   (Porta 5000)  │    │  (Porta 5001)   │    │  (Porta 5002)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │Notification Svc │
                    │  (Porta 5003)   │
                    └─────────────────┘
                              │
                    ┌─────────────────┐
                    │ Database Service│
                    │  (Porta 5004)   │
                    └─────────────────┘
```

## 📁 Estrutura de Diretórios

```
📦 projeto/
├── 📁 camera_service/          # Captura de câmeras IP
├── 📁 detection_service/       # Detecção com IA (YOLO)
├── 📁 notification_service/    # Envio de alertas/e-mails
├── 📁 web_interface/           # Interface web principal
├── 📁 database_service/        # API do banco de dados
├── 📄 docker-compose.yml       # Orquestração
└── 📄 README_MICROSSERVICOS.md # Esta documentação
```

## 🚀 Serviços Detalhados

### 1. Camera Service (Porta 5001)
**Responsabilidades:**
- Captura de streams RTSP
- Controle de câmeras (start/stop)
- Streaming de vídeo
- Gerenciamento de conexões

**APIs:**
- `GET /cameras` - Listar câmeras
- `POST /cameras/{id}/start` - Iniciar câmera
- `GET /cameras/{id}/stream` - Stream de vídeo

### 2. Detection Service (Porta 5002)
**Responsabilidades:**
- Processamento com YOLOv8
- Detecção de pessoas
- Definição de áreas de monitoramento
- Envio de alertas

**APIs:**
- `POST /detect` - Processar frame
- `POST /areas/{camera_id}` - Definir área
- `POST /models/load` - Carregar modelo

### 3. Notification Service (Porta 5003)
**Responsabilidades:**
- Envio de e-mails
- Alarmes sonoros
- Templates de notificação
- Log de eventos

**APIs:**
- `POST /alert` - Enviar alerta
- `POST /email` - Enviar e-mail
- `POST /test-email` - Testar configuração

### 4. Database Service (Porta 5004)
**Responsabilidades:**
- API REST para banco de dados
- CRUD de câmeras, eventos, configurações
- Estatísticas
- Backup e limpeza

**APIs:**
- `GET /cameras` - Listar câmeras
- `GET /events` - Listar eventos
- `GET /stats` - Estatísticas

### 5. Web Interface (Porta 5000)
**Responsabilidades:**
- Dashboard principal
- Interface de controle
- Visualização de streams
- Configurações via web

## 🐳 Executando com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Passos
1. **Configurar variáveis de ambiente:**
   ```bash
   # Editar cada requirements.txt com as dependências
   # Configurar URLs das câmeras no camera_service
   ```

2. **Construir e executar:**
   ```bash
   docker-compose up --build
   ```

3. **Acessar:**
   - Interface web: http://localhost:5000
   - Camera service: http://localhost:5001
   - Detection service: http://localhost:5002
   - Notification service: http://localhost:5003
   - Database service: http://localhost:5004

## 🔧 Executando Individualmente

Cada serviço pode ser executado independentemente:

```bash
# Terminal 1 - Database Service
cd database_service
pip install -r requirements.txt
python app.py

# Terminal 2 - Camera Service
cd camera_service
pip install -r requirements.txt
python app.py

# E assim por diante...
```

## 🔄 Comunicação entre Serviços

Os serviços se comunicam via **HTTP REST APIs**:

- **Web Interface** → **Camera Service**: Controle de câmeras
- **Camera Service** → **Detection Service**: Detecção em frames
- **Detection Service** → **Notification Service**: Envio de alertas
- **Todos os serviços** → **Database Service**: Persistência de dados

## 📊 Benefícios da Arquitetura

### ✅ Vantagens
- **Escalabilidade**: Cada serviço pode ser escalado independentemente
- **Manutenibilidade**: Código organizado por responsabilidade
- **Resiliência**: Falha em um serviço não derruba todo o sistema
- **Desenvolvimento**: Times podem trabalhar em serviços diferentes
- **Deploy**: Atualização de um serviço sem afetar os outros

### ⚠️ Considerações
- **Complexidade**: Mais complexo que aplicação monolítica
- **Latência**: Comunicação entre serviços adiciona delay
- **Debug**: Mais difícil debugar sistema distribuído
- **Infraestrutura**: Requer mais recursos (múltiplos containers)

## 🎯 Próximos Passos

1. **Implementar código** em cada serviço
2. **Configurar banco de dados** no database_service
3. **Implementar YOLO** no detection_service
4. **Configurar e-mail** no notification_service
5. **Criar interface** no web_interface
6. **Testar integração** entre todos os serviços

## 📝 Notas de Implementação

- **Variáveis de ambiente** devem ser configuradas para URLs dos serviços
- **Volumes Docker** para persistir dados (banco, fotos, logs)
- **Health checks** para monitorar status dos serviços
- **Logging centralizado** para facilitar debug
- **API Gateway** (opcional) para roteamento de requests

---

**Status**: ✅ Estrutura criada | ⏳ Aguardando implementação do código