# camera_service/app.py - Versão POO com Lógica de Deteção Integrada

import cv2
import time
import threading
import os
import requests  # <-- Importado para "conversar" com o detection_service
import io        # <-- Importado para formatar os dados da imagem
from flask import Flask, Response, request, jsonify
from flask_cors import CORS

# ==============================================================================
# CLASSE DA CÂMARA (POO)
# ==============================================================================

class Camera:
    """
    Representa uma única câmara de vigilância.
    Encapsula todos os dados (atributos) e comportamentos (métodos).
    """
    def __init__(self, config):
        # --- Atributos ---
        self.id = config['id']
        self.nome = config.get('nome', self.id)
        self.url = config['url']

        self.thread = None          # A thread que executa a captura
        self.is_running = False     # Um sinalizador para controlar o estado da captura
        self.latest_frame = None    # Armazena o último frame capturado
        self._lock = threading.Lock() # "Cadeado" para acesso seguro ao frame

        # --- LINHAS CORRIGIDAS (ADICIONE ISTO) ---
        self.detection_service_url = os.getenv("DETECTION_SERVICE_URL", "http://127.0.0.1:5002")
        self.last_detection_time = 0
        self.detection_interval = 0.5  # Intervalo entre deteções (em segundos)

    def _capture_loop(self):
        """
        O método privado que corre em loop na sua própria thread.
        Responsável por conectar, capturar e agora, disparar a deteção.
        """
        print(f"THREAD {self.id}: A iniciar para {self.nome}...")
        video_capture = None
        
        while self.is_running:
            try:
                if video_capture is None or not video_capture.isOpened():
                    # Lógica de conexão/reconexão
                    print(f"THREAD {self.id}: A tentar conectar a {self.nome}...")
                    video_capture = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
                    video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    if not video_capture.isOpened():
                        print(f"THREAD {self.id}: Falha ao conectar. A tentar novamente em 10s...")
                        time.sleep(10)
                        continue

                sucesso, frame = video_capture.read()

                if not sucesso:
                    print(f"THREAD {self.id}: Perdeu frame de {self.nome}. A reconectar...")
                    video_capture.release(); video_capture = None
                    time.sleep(2)
                    continue

                # Processa e armazena o frame para o STREAMING
                frame_redimensionado = cv2.resize(frame, (640, 480))
                _, buffer = cv2.imencode('.jpg', frame_redimensionado)
                
                frame_bytes_para_stream = buffer.tobytes()
                with self._lock:
                    self.latest_frame = frame_bytes_para_stream
                
                # --- NOVA LÓGICA DE DETEÇÃO ---
                current_time = time.time()
                if current_time - self.last_detection_time > self.detection_interval:
                    self.last_detection_time = current_time
                    
                    # Copiamos o frame para enviar para deteção
                    # Usamos uma nova thread para não bloquear o loop de captura!
                    detection_thread = threading.Thread(
                        target=self._send_frame_for_detection,
                        args=(frame_bytes_para_stream,), # Passa o frame
                        daemon=True
                    )
                    detection_thread.start()
                # --- FIM DA LÓGICA DE DETEÇÃO ---

            except Exception as e:
                print(f"THREAD {self.id}: Erro inesperado: {e}")
                if video_capture: video_capture.release()
                video_capture = None; time.sleep(5)
            
            time.sleep(1 / 20) # Limita a ~20 FPS

        if video_capture: video_capture.release()
        print(f"THREAD {self.id}: Captura para {self.nome} finalizada.")

    def _send_frame_for_detection(self, frame_bytes):
        """
        NOVO MÉTODO: Envia um frame para o detection_service e imprime um alerta.
        Corre numa thread separada para não travar o vídeo.
        """
        try:
            # Prepara o ficheiro em memória para enviar
            files = {'frame': ('frame.jpg', io.BytesIO(frame_bytes), 'image/jpeg')}
            # Envia dados extra sobre a câmara
            data = {'camera_id': self.id, 'camera_nome': self.nome}
            
            # Envia a requisição para o "cérebro"
            response = requests.post(
                f"{self.detection_service_url}/detect",
                files=files,
                data=data,
                timeout=2 # Timeout curto para não prender a thread
            )
            
            if response.status_code == 200:
                resultado = response.json()
                # Se o "cérebro" disse que detetou, imprimimos o alerta!
                if resultado.get('detectado'):
                    print("\n" + "="*50)
                    print(f"!!! ALERTA DE DETEÇÃO NA CÂMARA {self.nome} !!!")
                    print(f"!!! {len(resultado.get('pessoas', []))} pessoa(s) detectada(s).")
                    print("="*50 + "\n")
            else:
                print(f"DETECTION_SERVICE: Respondeu com erro {response.status_code}")

        except requests.exceptions.ConnectionError:
            # Normal se o detection_service estiver offline
            # print(f"DETECTION_SERVICE: Offline ou a recusar conexão.")
            pass
        except requests.exceptions.Timeout:
            # Normal se a deteção demorar mais que o nosso timeout
            # print(f"DETECTION_SERVICE: Demorou muito a responder (Timeout).")
            pass
        except Exception as e:
            print(f"DETECTION_SERVICE: Erro inesperado: {e}")

    def start(self):
        if self.is_running: return
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)

    def get_frame(self):
        with self._lock:
            return self.latest_frame

# ==============================================================================
# GESTOR DE CÂMARAS E ROTAS DA API (Sem alterações)
# ==============================================================================

class CameraManager:
    def __init__(self):
        self.cameras = {}
        self._lock = threading.Lock()

    def add_camera(self, config):
        cam_id = config['id']
        with self._lock:
            if cam_id in self.cameras:
                return self.cameras[cam_id]
            nova_camera = Camera(config)
            self.cameras[cam_id] = nova_camera
            return nova_camera

    def get_camera(self, cam_id):
        with self._lock:
            return self.cameras.get(cam_id)

    def remove_camera(self, cam_id):
        with self._lock:
            if cam_id in self.cameras:
                self.cameras[cam_id].stop()
                del self.cameras[cam_id]
                return True
            return False

    def get_active_camera_ids(self):
        with self._lock:
            return [cam_id for cam_id, cam in self.cameras.items() if cam.is_running]

app = Flask(__name__)
CORS(app)
manager = CameraManager()

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'camera_service',
        'cameras_ativas': len(manager.get_active_camera_ids())
    })

@app.route('/cameras', methods=['POST'])
def iniciar_camera_api():
    data = request.get_json()
    if not data or 'id' not in data or 'url' not in data:
        return jsonify({'erro': 'ID e URL da câmara são obrigatórios'}), 400
    cam_id = data['id']
    camera_obj = manager.get_camera(cam_id)
    if not camera_obj:
        camera_obj = manager.add_camera(data)
    camera_obj.start()
    return jsonify({'mensagem': f'Câmara {camera_obj.nome} iniciada.'}), 200

@app.route('/cameras/<camera_id>/stop', methods=['POST'])
def parar_camera_api(camera_id):
    if manager.remove_camera(camera_id):
        return jsonify({'mensagem': f'Câmara {camera_id} parada e removida.'})
    else:
        return jsonify({'erro': 'Câmara não encontrada.'}), 404

def gerar_frames_stream(camera_id):
    camera_obj = manager.get_camera(camera_id)
    if not camera_obj: return
    while camera_obj.is_running:
        frame = camera_obj.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.05)

@app.route('/cameras/<camera_id>/stream')
def stream_camera(camera_id):
    camera_obj = manager.get_camera(camera_id)
    if not camera_obj or not camera_obj.is_running:
        return "Câmara não encontrada ou não está ativa.", 404
    return Response(gerar_frames_stream(camera_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cameras/active')
def listar_cameras_ativas_api():
    return jsonify({'cameras': manager.get_active_camera_ids(), 'total': len(manager.get_active_camera_ids())})

if __name__ == '__main__':
    print("Camera Service - Iniciado (Versao POO + Deteccao)")
    print("Porta: 5001")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)