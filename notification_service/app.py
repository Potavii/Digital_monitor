# detecção_socorro/notification_service/app.py - VERSÃO COMPLETA

import os
import smtplib
from email.message import EmailMessage
from flask import Flask, request, jsonify
from dotenv import load_dotenv # Vamos usar .env para segurança
import requests
# Carrega variáveis de ambiente de um ficheiro .env na mesma pasta

load_dotenv() 

app = Flask(__name__)

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://127.0.0.1:5004")
# ==============================================================================
# CONFIGURAÇÃO DE E-MAIL (LIDO DAS VARIÁVEIS DE AMBIENTE)
# ==============================================================================

# IMPORTANTE: Use uma "SENHA DE APP" gerada pelo Google, não a sua senha normal!
# 1. Ative a Verificação de 2 Passos no seu Gmail
# 2. Vá a https://myaccount.google.com/apppasswords
# 3. Gere uma nova senha para "App" (ex: "Python") e use-a aqui.

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")       # Ex: "o.seu.email@gmail.com"
EMAIL_PASS = os.getenv("EMAIL_PASS")       # A "Senha de App" que gerou

if not EMAIL_USER or not EMAIL_PASS:
    print("="*50)
    print("!!! ERRO CRÍTICO - NOTIFICATION SERVICE !!!")
    print("As variáveis EMAIL_USER ou EMAIL_PASS não estão definidas.")
    print("Crie um ficheiro '.env' nesta pasta ou defina-as no sistema.")
    print("O serviço vai rodar, mas NÃO VAI enviar e-mails.")
    print("="*50)

# ==============================================================================
# LÓGICA DE ENVIO DE E-MAIL
# ==============================================================================

def obter_email_da_camera(camera_id):
    """
    NOVA FUNÇÃO: Pergunta ao Database Service qual é o e-mail
    configurado para esta câmera usando a nossa nova rota.
    (VERSÃO COM INDENTAÇÃO CORRETA)
    """
    # Se não houver ID, não há o que fazer
    if not camera_id:
        return None

    try:
        url = f"{DATABASE_SERVICE_URL}/cameras/{camera_id}"
        response = requests.get(url, timeout=3)

        if response.status_code == 200:
            # Se encontrou, retorna o e-mail
            return response.json().get('receiver_email')
        else:
            print(f"EMAIL: Não foi possível obter e-mail da câmera {camera_id}. DB respondeu com {response.status_code}")
            return None

    # O "except" TEM DE estar indentado aqui, dentro da função
    except Exception as e:
        print(f"EMAIL: Erro ao conectar com DB para obter e-mail: {e}")
        # Este é o erro que vai aparecer se o Firewall estiver a bloquear
        return None

def enviar_email_alerta(evento):
    """A função que realmente envia o e-mail (VERSÃO CORRIGIDA)."""
    
    # Se não configurámos as senhas, não fazemos nada
    if not EMAIL_USER or not EMAIL_PASS:
        print("EMAIL: Falha ao enviar. EMAIL_USER ou EMAIL_PASS não configurados.")
        return False

    # --- INÍCIO DA NOVA LÓGICA ---
    # Extrai os dados do evento
    cam_nome = evento.get('camera_nome', 'Câmera Desconhecida')
    cam_id = evento.get('camera_id') # Precisamos disto para procurar o email
    timestamp = evento.get('timestamp', 'Agora')
    foto_path = evento.get('foto_path')
    
    # 1. Tenta buscar o e-mail específico da câmera no banco de dados.
    # (Esta é a "ligação" que faltava!)
    email_destino_camera = obter_email_da_camera(cam_id)
    
    # 2. Se não encontrar (None ou ""), usa o e-mail global (o seu) como fallback.
    email_destino = email_destino_camera or EMAIL_USER
    # --- FIM DA NOVA LÓGICA ---

    print(f"EMAIL: A preparar e-mail para {email_destino} sobre a câmara {cam_nome}...")

    # Cria a mensagem
    msg = EmailMessage()
    msg['Subject'] = f"🚨 ALERTA DE DETEÇÃO: Pessoa detetada na {cam_nome}!"
    msg['From'] = EMAIL_USER
    msg['To'] = email_destino # <-- Agora usa o destino correto!

    # Corpo do e-mail
    msg.set_content(f"""
    Olá,
    
    O sistema de monitoramento detectou uma pessoa na câmara '{cam_nome}'.
    
    - Data/Hora do Evento: {timestamp}
    
    
    Este é um alerta automático.Fique esperto e verifique a situação
    """)

    # Tenta anexar a foto da captura (esta parte já estava boa)
    if foto_path and os.path.exists(foto_path):
        try:
            with open(foto_path, 'rb') as f:
                img_data = f.read()
                msg.add_attachment(img_data, maintype='image', subtype='jpeg', filename=os.path.basename(foto_path))
            print(f"EMAIL: Foto {foto_path} anexada com sucesso.")
        except Exception as e:
            print(f"EMAIL: Erro ao anexar foto {foto_path}: {e}")
    else:
        print(f"EMAIL: Foto {foto_path} não encontrada. A enviar e-mail sem anexo.")

    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls() # Inicia segurança
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"EMAIL: Alerta enviado com sucesso para {email_destino}!")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"!!! ERRO DE EMAIL: Falha na autenticação. Verifique o EMAIL_USER e a SENHA DE APP.")
        return False
    except Exception as e:
        print(f"!!! ERRO DE EMAIL: Falha ao enviar: {e}")
        return False
# ==============================================================================
# API DE NOTIFICAÇÃO
# ==============================================================================

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'notification_service'})

@app.route('/notify', methods=['POST'])
def notificar():
    """
    Esta é a porta que o detection_service vai chamar.
    """
    evento = request.get_json()
    if not evento or not evento.get('camera_id'):
        return jsonify({'erro': 'Dados de evento inválidos'}), 400

    # Chama a nossa nova função de envio de e-mail
    sucesso = enviar_email_alerta(evento)
    
    if sucesso:
        return jsonify({'mensagem': 'Notificação enviada com sucesso'}), 200
    else:
        return jsonify({'erro': 'Falha ao processar ou enviar notificação'}), 500

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================

if __name__ == '__main__':
    print("Notification Service - Iniciado")
    print("Porta: 5003")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5003, debug=True, use_reloader=False)