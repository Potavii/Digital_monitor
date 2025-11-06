import subprocess
import time
import sys
import os

# ==============================================================================
# CONFIGURAÇÃO DOS MICROSSERVIÇOS
# ==============================================================================
# Dicionário com os serviços a serem executados.
# A ordem aqui é importante! Serviços dos quais outros dependem devem vir primeiro.
# Ex: web_interface depende de database_service, então database_service vem antes.
services = {
    "Database Service": {
        "path": "database_service",
        "command": [sys.executable, "app.py"],
        "port": 5004
    },
    "Camera Service": {
        "path": "camera_service",
        "command": [sys.executable, "app.py"],
        "port": 5001
    },
    "Detection Service": {
        "path": "detection_service",
        "command": [sys.executable, "app.py"],
        "port": 5002
    },
    "Notification Service": {
        "path": "notification_service",
        "command": [sys.executable, "app.py"],
        "port": 5003
    },
    "Web Interface": {
        "path": "web_interface",
        "command": [sys.executable, "app.py"],
        "port": 5000
    }
}

processes = {}

def start_services():
    """Inicia todos os serviços definidos no dicionário 'services'."""
    print("="*50)
    print("INICIANDO ARQUITETURA DE MICROSSERVIÇOS")
    print("="*50)
    
    for name, config in services.items():
        try:
            print(f"\n---> Iniciando: {name}...")
            # Popen inicia o processo em segundo plano
            
            # --- CORREÇÃO AQUI ---
            # Removemos 'stdout=subprocess.PIPE' e 'stderr=subprocess.PIPE'
            # para permitir que o output apareça na NOVA consola.
            process = subprocess.Popen(
                config["command"],
                cwd=config["path"],
                text=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            # --- FIM DA CORREÇÃO ---

            processes[name] = process
            print(f"[OK] {name} iniciado com PID: {process.pid}")
            
            # PAUSA ESTRATÉGICA: Dá ao serviço um momento para inicializar
            print("     Aguardando 2 segundos para estabilização...")
            time.sleep(2)

        except FileNotFoundError:
            print(f"[ERRO] O diretório '{config['path']}' ou o comando '{config['command'][1]}' não foi encontrado para o serviço {name}.")
        except Exception as e:
            print(f"[ERRO] Falha ao iniciar {name}: {e}")

def stop_services():
    """Para todos os processos iniciados."""
    print("\n" + "="*50)
    print("PARANDO TODOS OS SERVIÇOS")
    print("="*50)
    for name, process in reversed(list(processes.items())):
        try:
            print(f"---> Parando: {name} (PID: {process.pid})...")
            process.terminate()  # Envia um sinal para terminar
            process.wait(timeout=5)  # Espera até 5 segundos
            print(f"[OK] {name} parado.")
        except subprocess.TimeoutExpired:
            print(f"[AVISO] {name} não respondeu, forçando o encerramento.")
            process.kill() # Força o encerramento
            print(f"[OK] {name} forçado a parar.")
        except Exception as e:
            print(f"[ERRO] Falha ao parar {name}: {e}")
    print("\nTodos os serviços foram encerrados.")

if __name__ == "__main__":
    start_services()
    try:
        # Mantém o script principal rodando para poder interceptar o Ctrl+C
        print("\n" + "="*50)
        print("Todos os serviços foram iniciados em seus próprios consoles.")
        print("Pressione Ctrl+C nesta janela para encerrar todos os serviços de forma limpa.")
        print("="*50)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Quando Ctrl+C é pressionado, o bloco try é interrompido e o finally é executado
        pass
    finally:
        stop_services()