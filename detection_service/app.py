# detection_service/app.py

import cv2
import numpy as np
from ultralytics import YOLO
import os
import datetime
import requests
import io
import time
from flask import Flask, request, jsonify

# ==============================================================================
# CONFIGURAÇÕES DO SERVIÇO
# ==============================================================================

app = Flask(__name__)

CAPTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fotos_capturadas")
os.makedirs(CAPTURES_DIR, exist_ok=True)


MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modelo", "yolov8s.pt")
modelo = YOLO(MODEL_PATH)

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://127.0.0.1:5004")

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://127.0.0.1:5003")

alert_cooldown = {}
COOLDOWN_SECONDS = 10

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def salvar_foto(frame, camera_id):
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"deteccao_{camera_id}_{timestamp}.jpg"
        filepath = os.path.join(CAPTURES_DIR, filename)
        
        cv2.imwrite(filepath, frame)
        print(f"DETECTION: Foto da deteção salva em {filepath}")
        return filepath
    except Exception as e:
        print(f"DETECTION: Erro ao salvar foto: {e}")
        return None

def salvar_evento_database(camera_id, camera_nome, confianca, bbox, foto_path):
    """
    Esta função agora faz DUAS coisas:
    1. Salva o evento no Banco de Dados (como antes)
    2. Tenta enviar uma notificação (NOVO)
    """

    # 1. Prepara os dados do evento
    data = {
        'camera_id': camera_id,
        'camera_nome': camera_nome,
        'confianca': confianca,
        'bbox': bbox,
        'foto_path': foto_path,
        # NOTA: O email_destino será o teu EMAIL_USER (configurado no .env)
    }

    # 2. Tenta salvar no Banco de Dados (como antes)
    try:
        response = requests.post(f"{DATABASE_SERVICE_URL}/events", json=data, timeout=5)

        if response.status_code == 201:
            print(f"DETECTION: Evento da câmara {camera_nome} salvo no banco de dados!")
        else:
            print(f"DETECTION: Erro ao salvar evento no banco. Status: {response.status_code}")

    except Exception as e:
        print(f"DETECTION: Erro de conexão com Database Service: {e}")
        # Se nem salvou no DB, provavelmente não vale a pena notificar.
        return # Sai da função

    # 3. Tenta enviar a notificação (NOVO!)
    # (Só chegamos aqui se o passo 2 funcionou)
    try:
        # Vamos usar a mesma 'data' que enviámos para o DB
        notify_response = requests.post(f"{NOTIFICATION_SERVICE_URL}/notify", json=data, timeout=10) # Damos 10s para o email

        if notify_response.status_code == 200:
            print(f"DETECTION: Pedido de notificação enviado com sucesso.")
        else:
            print(f"DETECTION: AVISO! O Notification Service respondeu com erro: {notify_response.status_code}")

    except Exception as e:
        print(f"DETECTION: AVISO! Falha ao conectar com Notification Service: {e}")

# ==============================================================================
# API DE DETEÇÃO
# ==============================================================================

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'detection_service'})

@app.route('/detect', methods=['POST'])
def detectar():
    try:
        if 'frame' not in request.files:
            return jsonify({'erro': 'Nenhum frame enviado'}), 400

        camera_id = request.form.get('camera_id', 'unknown')
        camera_nome = request.form.get('camera_nome', 'Câmera Desconhecida')
        
        frame_file = request.files['frame'].read()
        np_arr = np.frombuffer(frame_file, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'erro': 'Frame inválido'}), 400

        resultados = modelo(frame, verbose=False)
        
        pessoas_detectadas = []
        
        for resultado in resultados:
            for caixa in resultado.boxes:
                
                # --- NOSSA LINHA DE DEPURAÇÃO ---
                classe_id = int(caixa.cls[0])
                confianca = float(caixa.conf[0])
                print(f"!!! DEBUG YOLO: VI a classe {classe_id} com {confianca*100:.0f}% de confiança.")
                # --- FIM DA DEPURAÇÃO ---

                # Classe 0 = Pessoa
                if classe_id == 0 and confianca > 0.25:
                    bbox = [int(c) for c in caixa.xyxy[0]]
                    pessoas_detectadas.append({
                        'bbox': bbox,
                        'confianca': confianca
                    })
                    
                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, f"Pessoa {confianca:.2f}", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if pessoas_detectadas:
            current_time = time.time()
            last_alert = alert_cooldown.get(camera_id, 0)
            
            if (current_time - last_alert) > COOLDOWN_SECONDS:
                print(f"DETECTION: Detetada pessoa na câmara {camera_nome}! A guardar evento...")
                alert_cooldown[camera_id] = current_time
                
                primeira_deteccao = pessoas_detectadas[0]
                
                foto_path = salvar_foto(frame, camera_id)
                
                salvar_evento_database(
                    camera_id,
                    camera_nome,
                    primeira_deteccao['confianca'],
                    primeira_deteccao['bbox'],
                    foto_path
                )
            
            return jsonify({'detectado': True, 'pessoas': pessoas_detectadas})

        return jsonify({'detectado': False, 'pessoas': []})

    except Exception as e:
        print(f"DETECTION: Erro grave na API /detect: {e}")
        return jsonify({'erro': str(e)}), 500

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================

if __name__ == '__main__':
    print("Detection Service - Iniciado (Modo de Depuracao)")
    print(f"Fotos de captura salvas em: {CAPTURES_DIR}")
    print(f"Database Service URL: {DATABASE_SERVICE_URL}")
    print("Porta: 5002")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False)