# web_interface/app.py - Versão Completa e Funcional

import os
import requests
import sys
from flask import Flask, render_template, request, jsonify, Response, url_for
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ==============================================================================
# CONFIGURAÇÕES DO SERVIÇO
# ==============================================================================
app = Flask(__name__)

# URLs dos outros serviços
CAMERA_SERVICE_URL = os.getenv("CAMERA_SERVICE_URL", "http://127.0.0.1:5001")
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://127.0.0.1:5004")

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def obter_cameras_db():
    """Obtém a lista de todas as câmeras do banco de dados."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/cameras", timeout=5)
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        print(f"Erro ao obter câmeras do banco: {e}")
        return []

def obter_cameras_ativas():
    """Obtém a lista de câmeras ativas do Camera Service."""
    try:
        response = requests.get(f"{CAMERA_SERVICE_URL}/cameras/active", timeout=5)
        return response.json() if response.status_code == 200 else {'cameras': []}
    except Exception as e:
        print(f"Erro ao obter câmeras ativas: {e}")
        return {'cameras': []}

# ==============================================================================
# ROTAS DA INTERFACE WEB
# ==============================================================================

@app.context_processor
def inject_now():
    """Disponibiliza a função now() para os templates."""
    return {'now': datetime.utcnow}

@app.route('/')
def index():
    """Redireciona para a página de câmeras."""
    return cameras()

@app.route('/cameras')
def cameras():
    """Página de gerenciamento e visualização de câmeras."""
    cameras_db = obter_cameras_db()
    cameras_ativas = obter_cameras_ativas()
    
    return render_template('cameras.html',
                           cameras_db=cameras_db,
                           cameras_ativas=cameras_ativas,
                           camera_service_url=CAMERA_SERVICE_URL)

# ==============================================================================
# APIs DA INTERFACE WEB (Ponte para os outros microsserviços)
# ==============================================================================

@app.route('/api/cameras', methods=['POST'])
def adicionar_camera():
    try:
        data = request.get_json() # <-- O 'data' que vem do JavaScript
        print(f"API: Recebido pedido para adicionar câmera: {data.get('nome')}")

        # O JavaScript agora envia 'receiver_email',
        # e o database_service (Porta 5004) recebe 'receiver_email'.
        # A "ponte" está correta!

        response = requests.post(f"{DATABASE_SERVICE_URL}/cameras", json=data, timeout=10)

        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"API ERRO: Falha ao adicionar câmera - {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/cameras/<camera_id>', methods=['DELETE'])
def remover_camera(camera_id):
    """Remove uma câmera do sistema"""
    try:
        print(f"[DELETE] Recebido pedido para remover câmera: {camera_id}")

        # 1. Tenta parar no Camera Service, mas não trava se demorar.
        # Usamos um timeout bem curto (ex: 2 segundos).
        try:
            requests.post(f"{CAMERA_SERVICE_URL}/cameras/{camera_id}/stop", timeout=2)
            print(f"[DELETE] Comando para parar a câmera {camera_id} enviado.")
        except requests.exceptions.RequestException as e:
            # Se o camera_service estiver offline ou demorar, apenas registramos e continuamos.
            print(f"[DELETE] Aviso: Não foi possível contatar o Camera Service para parar a câmera: {e}")

        # 2. Remove do banco de dados (a parte mais importante).
        db_response = requests.delete(f"{DATABASE_SERVICE_URL}/cameras/{camera_id}", timeout=10)

        if db_response.status_code == 200:
            return jsonify({'mensagem': f'Câmera {camera_id} removida com sucesso'}), 200
        elif db_response.status_code == 404:
            return jsonify({'erro': 'Câmera não encontrada no banco de dados'}), 404
        else:
            # Tenta pegar mais detalhes do erro, se possível.
            try:
                error_detail = db_response.json()
                return jsonify({'erro': f"Erro no Database Service: {error_detail.get('erro', db_response.text)}"}), db_response.status_code
            except:
                return jsonify({'erro': 'Erro desconhecido no Database Service'}), db_response.status_code

    except Exception as e:
        print(f"[DELETE] Erro interno inesperado: {str(e)}")
        return jsonify({'erro': f'Erro interno no servidor: {str(e)}'}), 500

@app.route('/api/cameras/<camera_id>/start', methods=['POST'])
def iniciar_camera(camera_id):
    """Busca os detalhes da câmera no banco e manda o camera_service iniciar."""
    try:
        print(f"API: Recebido pedido para iniciar câmera: {camera_id}")
        # 1. Pega os detalhes da câmera no banco
        db_response = requests.get(f"{DATABASE_SERVICE_URL}/cameras", timeout=5)
        if db_response.status_code != 200:
            return jsonify({'erro': 'Não foi possível obter detalhes da câmera'}), 500
            
        camera_config = next((cam for cam in db_response.json() if cam['cam_id'] == camera_id), None)
        if not camera_config:
            return jsonify({'erro': 'Câmera não encontrada no banco'}), 404

        # 2. Manda o Camera Service iniciar a captura
        cam_service_data = {
            'id': camera_config['cam_id'],
            'nome': camera_config['nome'],
            'url': camera_config['url']
        }
        
        response = requests.post(f"{CAMERA_SERVICE_URL}/cameras", json=cam_service_data, timeout=25)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"API ERRO: Falha ao iniciar câmera - {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/cameras/<camera_id>/stop', methods=['POST'])
def parar_camera(camera_id):
    """Repassa o comando de parar para o camera_service."""
    try:
        print(f"API: Recebido pedido para parar câmera: {camera_id}")
        response = requests.post(f"{CAMERA_SERVICE_URL}/cameras/{camera_id}/stop", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"API ERRO: Falha ao parar câmera - {e}")
        return jsonify({'erro': str(e)}), 500
    
@app.route('/api/events/latest')
def obter_eventos_recentes():
    """
    Atua como um proxy para o database_service, buscando os 
    eventos de deteção mais recentes.
    O JavaScript da página vai chamar esta rota.
    """
    try:
        # Vamos pedir ao banco os 20 eventos mais recentes
        params = {'limit': 20}
        response = requests.get(
            f"{DATABASE_SERVICE_URL}/events", 
            params=params, 
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"API ERRO: Falha ao buscar eventos do DB. Status: {response.status_code}")
            return jsonify({'erro': 'Falha ao buscar eventos do banco'}), response.status_code
            
    except Exception as e:
        print(f"API ERRO: Falha ao conectar com database_service: {e}")
        return jsonify({'erro': str(e)}), 500

# ==============================================================================
# PROXY PARA O STREAMING DE VÍDEO
# ==============================================================================

# web_interface/app.py - A CORREÇÃO ESTÁ AQUI

@app.route('/video_feed/<camera_id>')
def video_feed(camera_id):
    """
    Atua como um proxy para o stream do Camera Service.
    Esta versão corrigida usa um gerador para repassar os chunks
    de forma eficiente e sem corromper os frames.
    """
    stream_url = f"{CAMERA_SERVICE_URL}/cameras/{camera_id}/stream"
    
    try:
        # 1. Inicia a requisição para o serviço da câmera em modo 'stream'
        req = requests.get(stream_url, stream=True, timeout=10)

        # 2. Verifica se o serviço da câmera respondeu com sucesso
        if req.status_code != 200:
            print(f"Proxy ERRO: Camera Service (porta 5001) respondeu com {req.status_code}")
            return "Erro ao conectar ao serviço de câmera (Stream não disponível).", 503

        # 3. Esta é a parte importante:
        # Criamos uma função geradora interna ('generate').
        # O Flask vai chamar esta função para ir buscar os dados
        # "on-demand" (à medida que são precisos).
        def generate():
            try:
                # 4. Iteramos sobre os "pedaços" da resposta.
                # Um chunk_size maior (ex: 64KB) é mais eficiente
                # do que os 1024B que tinhas, pois permite que frames
                # inteiros passem de uma só vez.
                for chunk in req.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk
            except Exception as e:
                # Esta exceção é normal e acontece quando o utilizador
                # fecha a página (o navegador fecha a conexão).
                print(f"Proxy: Erro no gerador de streaming (cliente desconectou?): {e}")

        # 5. Retornamos uma Resposta do Flask, passando o nosso gerador
        # e o 'Content-Type' original do camera_service.
        # O 'content_type' é crucial (multipart/x-mixed-replace; boundary=frame)
        return Response(generate(), content_type=req.headers['content-type'])

    except requests.exceptions.RequestException as e:
        # Esta exceção acontece se o 'web_interface' (porta 5000)
        # não conseguir sequer ligar-se ao 'camera_service' (porta 5001).
        print(f"Proxy ERRO: Falha total ao conectar ao stream da câmera {camera_id}: {e}")
        return "Erro ao conectar ao serviço de câmera (Serviço offline?).", 503

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================
if __name__ == '__main__':
    print("Web Interface - Dashboard Principal")
    print("=" * 50)
    print(f"Conectando ao Camera Service em: {CAMERA_SERVICE_URL}")
    print(f"Conectando ao Database Service em: {DATABASE_SERVICE_URL}")
    print("Porta: 5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False, threaded=True)