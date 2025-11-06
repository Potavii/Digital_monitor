# database_service/app.py - Versão com "Memória" (guarda Câmaras e Eventos)

import os
import datetime
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

# ==============================================================================
# CONFIGURAÇÕES DO SERVIÇO
# ==============================================================================

app = Flask(__name__)

# O ficheiro .db será criado na pasta raiz do projeto.
DATABASE_FILE = "monitoramento.db"
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_FILE)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==============================================================================
# MODELO DAS TABELAS (MOLDES)
# ==============================================================================

def object_as_dict(obj):
    """Função utilitária para converter objetos SQLAlchemy em dicionários"""
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}

class Camera(Base):
    """Molde para a tabela 'cameras' (isto já tínhamos)"""
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True, index=True)
    cam_id = Column(String, unique=True, nullable=False, index=True)
    nome = Column(String, nullable=False)
    url = Column(String, nullable=False)
    area_x1 = Column(Integer, default=0)
    area_y1 = Column(Integer, default=0)
    area_x2 = Column(Integer, default=640)
    area_y2 = Column(Integer, default=480)
    receiver_email = Column(String)

class Evento(Base):
    """NOVO MOLDE: A nossa 'Memória' para a tabela 'eventos'"""
    __tablename__ = "eventos"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    camera_id = Column(String, index=True)
    camera_nome = Column(String)
    tipo_deteccao = Column(String, default="pessoa")
    confianca = Column(Float)
    foto_path = Column(String) # Caminho para a foto que o detection_service vai guardar
    bbox = Column(String) # Coordenadas da deteção

# Cria AMBAS as tabelas no banco de dados se elas não existirem
Base.metadata.create_all(bind=engine)

# ==============================================================================
# APIs DO SERVIÇO (AS "PORTAS" DE COMUNICAÇÃO)
# ==============================================================================

@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "database_service"}), 200

# --- APIs de Câmaras (sem alteração) ---

@app.route('/cameras', methods=['POST'])
def adicionar_camera():
    data = request.get_json()
    if not data or not all(k in data for k in ['cam_id', 'nome', 'url']):
        return jsonify({'erro': 'Campos cam_id, nome e url são obrigatórios'}), 400
    db = SessionLocal()
    try:
        existente = db.query(Camera).filter(Camera.cam_id == data['cam_id']).first()
        if existente:
            return jsonify({'erro': f'O ID de câmera "{data["cam_id"]}" já existe.'}), 409
        
        nova_camera = Camera(
            cam_id=data['cam_id'],
            nome=data['nome'],
            url=data['url'],
            receiver_email=data.get('receiver_email', 'admin@example.com')
        )
        if 'area' in data and len(data['area']) == 4:
            nova_camera.area_x1, nova_camera.area_y1, nova_camera.area_x2, nova_camera.area_y2 = data['area']
        
        db.add(nova_camera)
        db.commit(); db.refresh(nova_camera)
        return jsonify(object_as_dict(nova_camera)), 201
    except Exception as e:
        db.rollback(); return jsonify({'erro': str(e)}), 500
    finally:
        db.close()

@app.route('/cameras', methods=['GET'])
def listar_cameras():
    db = SessionLocal()
    try:
        cameras = db.query(Camera).all()
        return jsonify([object_as_dict(cam) for cam in cameras]), 200
    finally:
        db.close()
        
@app.route('/cameras/<string:cam_id>', methods=['DELETE'])
def remover_camera(cam_id):
    db = SessionLocal()
    try:
        camera_a_remover = db.query(Camera).filter(Camera.cam_id == cam_id).first()
        if not camera_a_remover:
            return jsonify({'erro': 'Câmera não encontrada'}), 404
        db.delete(camera_a_remover)
        db.commit()
        return jsonify({'mensagem': f'Câmera {cam_id} removida com sucesso'}), 200
    except Exception as e:
        db.rollback(); return jsonify({'erro': str(e)}), 500
    finally:
        db.close()
        

        
@app.route('/cameras/<string:cam_id>', methods=['GET'])
def obter_camera(cam_id):
    """NOVA PORTA: Obtém os detalhes de uma única câmera."""
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.cam_id == cam_id).first()
        if not camera:
            return jsonify({'erro': 'Câmera não encontrada'}), 404
        # Retorna os detalhes da câmera como um dicionário
        return jsonify(object_as_dict(camera)), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    finally:
        db.close()

# --- NOVAS APIs de Eventos ---

@app.route('/events', methods=['POST'])
def adicionar_evento():
    """NOVA PORTA: O detection_service vai enviar dados para aqui."""
    data = request.get_json()
    if not data or not data.get('camera_id'):
        return jsonify({'erro': 'Dados do evento inválidos'}), 400

    db = SessionLocal()
    try:
        novo_evento = Evento(
            camera_id=data.get('camera_id'),
            camera_nome=data.get('camera_nome'),
            confianca=data.get('confianca'),
            foto_path=data.get('foto_path'),
            bbox=str(data.get('bbox', '[]')) # Guarda a BBox como string
        )
        db.add(novo_evento)
        db.commit()
        db.refresh(novo_evento)
        
        print(f"DATABASE: Novo evento registado da câmara {data.get('camera_nome')}!")
        return jsonify(object_as_dict(novo_evento)), 201
    
    except Exception as e:
        db.rollback()
        print(f"DATABASE: Erro ao registar evento: {e}")
        return jsonify({'erro': str(e)}), 500
    finally:
        db.close()

@app.route('/events', methods=['GET'])
def listar_eventos():
    """NOVA PORTA: A nossa interface web vai usar isto no Passo 3."""
    limite = request.args.get('limite', 10, type=int)
    db = SessionLocal()
    try:
        eventos = db.query(Evento).order_by(Evento.timestamp.desc()).limit(limite).all()
        return jsonify([object_as_dict(e) for e in eventos]), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    finally:
        db.close()

# ==============================================================================
# INICIALIZAÇÃO DO SERVIÇO
# ==============================================================================

if __name__ == '__main__':
    print("Database Service - Iniciado (Com Memoria de Eventos)")
    print(f"Usando base de dados em: {DATABASE_PATH}")
    print("Porta: 5004")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5004, debug=True, use_reloader=False)