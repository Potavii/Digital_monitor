# app_monitor.py

import cv2
from ultralytics import YOLO
import threading
import time
import os
import datetime
import winsound
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from flask import Flask, Response, render_template

# ==============================================================================
# --- 1. CONFIGURAÇÕES GERAIS E DAS CÂMERAS ---
# ==============================================================================

# --- Configurações de E-mail (GMAIL) ---
SENDER_EMAIL = "detector.milagroso@gmail.com"  
SENDER_PASSWORD = "sqljzyeuqizedcfj" # Use uma "Senha de App" do Google

# --- Configurações Globais do Sistema ---
PHOTOS_LOCAL_DIR = "invasor_fotos_pc"
if not os.path.exists(PHOTOS_LOCAL_DIR):
    os.makedirs(PHOTOS_LOCAL_DIR)

MODELO = YOLO('modelo/yolov8n.pt') # Garanta que o modelo está no caminho correto
app = Flask(__name__)
PROCESS_EVERY_N_FRAMES = 4  # Processa 1 a cada 4 frames para otimização
ALERT_COOLDOWN_SECONDS = 30 # Tempo de espera em segundos para um novo alerta

# --- Dicionário de Configuração das Câmeras ---
# Adicione ou remova câmeras aqui.
CAMERA_CONFIGS = {
    "cam1": {
        "nome": "Câmera Garagem",
        "url": "rtsp://admin:Mota2102@192.168.216.52:554/onvif1", # SEU URL RTSP REAL
        "area": [137, 92, 399, 478], # Área de detecção [x1, y1, x2, y2]
        "receiver_email": "paulo.otaviiosilva@gmail.com", # E-mail para receber alertas desta câmera
        "frame": None,
        "detectando": False,
        "last_alert_time": 0,
        "is_alarm_beeping": False
    },
    "cam2": {
        "nome": "Câmera Entrada (Exemplo)",
        "url": "rtsp://admin:Mota2102@192.168.216.52:554/onvif1", # SUBSTITUA PELO URL DA SUA SEGUNDA CÂMERA
        "area": [0, 0, 640, 480],
        "receiver_email": "outro.email@exemplo.com",
        "frame": None,
        "detectando": False,
        "last_alert_time": 0,
        "is_alarm_beeping": False
    }
}

# ==============================================================================
# --- 2. FUNÇÕES DE ALERTA (Adaptadas do socorro2.py) ---
# ==============================================================================

def alarme_sonoro(cam_id):
     """Executa o som do alarme enquanto a detecção estiver ativa para uma câmera."""
     config = CAMERA_CONFIGS[cam_id]
     print(f"Alarme sonoro INICIADO para: {config['nome']}")
     while config.get("is_alarm_beeping", False):
       winsound.Beep(2500, 300) 
       time.sleep(0.7) 
     print(f"Alarme sonoro PARADO para: {config['nome']}")

def enviar_email_alerta(photo_paths, receiver_email, camera_nome):
    """Envia um e-mail de alerta com as fotos capturadas."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = f"ALERTA DE SEGURANÇA: Invasor Detectado por '{camera_nome}'!"

        body = f"Um possível invasor foi detectado na área monitorada pela câmera '{camera_nome}'.\nVeja as fotos anexadas."
        msg.attach(MIMEText(body, 'plain'))

        for photo_path in photo_paths:
            with open(photo_path, 'rb') as fp:
                img_mime = MIMEImage(fp.read(), _subtype="jpeg")
                img_mime.add_header('Content-Disposition', 'attachment', filename=os.path.basename(photo_path))
                msg.attach(img_mime)
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"Email de alerta para '{camera_nome}' enviado com sucesso para {receiver_email}!")
    except Exception as e:
        print(f"ERRO ao enviar email para '{camera_nome}': {e}")

# ==============================================================================
# --- 3. PROCESSAMENTO DE VÍDEO E DETECÇÃO ---
# ==============================================================================

def processar_camera_stream(cam_id):
    """
    Loop principal que lê o stream da câmera, processa com YOLO,
    atualiza o frame para o Flask e dispara os alertas.
    """
    config = CAMERA_CONFIGS[cam_id]
    video = cv2.VideoCapture(config["url"], cv2.CAP_FFMPEG)
    frame_count = 0

    if not video.isOpened():
        print(f"ERRO: Não foi possível acessar a câmera {config['nome']} ({cam_id}). Verifique o URL RTSP.")
        return

    print(f"Iniciando processamento para {config['nome']}...")

    while True:
        check, img = video.read()
        if not check:
            print(f"Stream da câmera {config['nome']} perdido. Tentando reconectar em 5 segundos...")
            video.release()
            time.sleep(5)
            video = cv2.VideoCapture(config["url"], cv2.CAP_FFMPEG)
            continue
            
        frame_count += 1
        if frame_count % PROCESS_EVERY_N_FRAMES != 0:
            continue

        largura_video, altura_video = 640, 480
        frame_resized = cv2.resize(img, (largura_video, altura_video))
        img_display = frame_resized.copy()
        
        resultado = MODELO(frame_resized, verbose=False)
        pessoa_na_area = False

        for objetos in resultado:
            for dados in objetos.boxes:
                x1, y1, x2, y2 = [int(i) for i in dados.xyxy[0]]
                cls = int(dados.cls[0])
                
                if cls == 0: # Classe 0 é 'person' no modelo COCO
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    
                    area_x1, area_y1, area_x2, area_y2 = config["area"]
                    if area_x1 <= cx <= area_x2 and area_y1 <= cy <= area_y2:
                        pessoa_na_area = True
                        cv2.rectangle(img_display, (x1, y1), (x2, y2), (0, 0, 255), 2) # Bounding box vermelha
                        cv2.putText(img_display, 'INVASOR', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # --- Lógica de Disparo de Alerta ---
        current_time = time.time()
        if pessoa_na_area:
            config["detectando"] = True
            if (current_time - config["last_alert_time"]) > ALERT_COOLDOWN_SECONDS:
                print(f"\n>>> ALERTA! Invasor detectado por: {config['nome']}!")
                config["last_alert_time"] = current_time

                # 1. Ativar Alarme Sonoro
                if not config["is_alarm_beeping"]:
                    config["is_alarm_beeping"] = True
                    threading.Thread(target=alarme_sonoro, args=(cam_id,)).start()

                # 2. Capturar Fotos e Enviar E-mail
                def capturar_e_enviar():
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Captura foto 1
                    foto1_path = os.path.join(PHOTOS_LOCAL_DIR, f"invasor_{cam_id}_{timestamp}_1.jpg")
                    cv2.imwrite(foto1_path, frame_resized)
                    print(f"Foto 1 salva: {foto1_path}")
                    
                    # Espera 2 segundos para a segunda foto
                    time.sleep(2)
                    
                    # Captura foto 2
                    foto2_path = os.path.join(PHOTOS_LOCAL_DIR, f"invasor_{cam_id}_{timestamp}_2.jpg")
                    cv2.imwrite(foto2_path, img_display) # Usa a imagem com a caixa de detecção
                    print(f"Foto 2 salva: {foto2_path}")
                    
                    # Envia e-mail em uma nova thread para não bloquear
                    threading.Thread(target=enviar_email_alerta, args=([foto1_path, foto2_path], config["receiver_email"], config["nome"])).start()
                
                threading.Thread(target=capturar_e_enviar).start()

        else: # Se não há pessoa na área
            if config["detectando"]:
                print(f"Invasor saiu da área da câmera {config['nome']}. Sistema rearmado.")
            config["detectando"] = False
            config["is_alarm_beeping"] = False # Para o alarme sonoro

        # --- Desenha a Área de Detecção no Vídeo ---
        area_x1, area_y1, area_x2, area_y2 = config["area"]
        cor_area = (0, 0, 255) if config["detectando"] else (0, 255, 0)
        texto_status = "ALERTA" if config["detectando"] else "SEGURO"
        cv2.rectangle(img_display, (area_x1, area_y1), (area_x2, area_y2), cor_area, 2)
        cv2.putText(img_display, texto_status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, cor_area, 2)
        
        # Codifica o frame final para ser exibido na web
        ret, buffer = cv2.imencode('.jpg', img_display)
        config["frame"] = buffer.tobytes()
        
    video.release()

# ==============================================================================
# --- 4. ROTAS DO FLASK (Interface Web) ---
# ==============================================================================

@app.route('/')
def index():
    """Rota principal que serve a página HTML com as câmeras."""
    return render_template('index.html', camera_configs=CAMERA_CONFIGS)

def gerar_frames_web(cam_id):
    """Gerador que fornece os frames de uma câmera específica para a página web."""
    while True:
        frame_bytes = CAMERA_CONFIGS[cam_id].get("frame")
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.05) # Pequeno delay para não sobrecarregar

@app.route('/video_feed/<cam_id>')
def video_feed(cam_id):
    """Endpoint de vídeo que uma tag <img> no HTML irá acessar."""
    if cam_id not in CAMERA_CONFIGS:
        return "Câmera não encontrada", 404
    return Response(gerar_frames_web(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

# ==============================================================================
# --- 5. INICIALIZAÇÃO DO SERVIDOR ---
# ==============================================================================

if __name__ == '__main__':
    # Inicia uma thread de processamento para cada câmera configurada
    for cam_id in CAMERA_CONFIGS:
        thread = threading.Thread(target=processar_camera_stream, args=(cam_id,))
        thread.daemon = True # Garante que as threads fechem junto com o app principal
        thread.start()
        
    print("\nServidor Flask iniciando... Acesse http://127.0.0.1:5000 no seu navegador.")
    # 'host="0.0.0.0"' permite acesso de outros dispositivos na sua rede local
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)