import os
import random
import threading
import webbrowser
import socket
import logging
from flask import Flask, render_template, request, jsonify

# Silenciamos la consola para no saturar
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=os.path.join(BASE_DIR, 'static'))

estado_global = {
    "estado": "setup", 
    "jugadores": [],
    "fixture": [],            # Acá guardaremos TODAS las rondas pre-armadas
    "ronda_actual_idx": 0,    # Índice para saber en qué ronda estamos
    "ronda_actual": None,
    "proxima_ronda": None,
    "numero_ronda": 0,
    "ticker_msg": "BIENVENIDOS A LA MESITA ARENA /// MANTENER LA LIMPIEZA DEL SALÓN",
    "ip_local": get_ip()
}

def generar_fixture_perfecto(jugadores):
    if len(jugadores) < 2:
        return []

    jugadores_rot = jugadores.copy()
    
    # Si la cantidad es impar, agregamos un "FANTASMA" para manejar los descansos
    if len(jugadores_rot) % 2 != 0:
        jugadores_rot.append("FANTASMA")
        
    n = len(jugadores_rot)
    total_rondas = n - 1
    fixture_completo = []
    
    for i in range(total_rondas):
        partidos_ronda = []
        descansan_ronda = []
        mitad = n // 2
        enfrentamientos_validos = []
        
        # Emparejamiento Round-Robin (Método del círculo)
        for j in range(mitad):
            p1 = jugadores_rot[j]
            p2 = jugadores_rot[n - 1 - j]
            
            if p1 == "FANTASMA":
                descansan_ronda.append(p2)
            elif p2 == "FANTASMA":
                descansan_ronda.append(p1)
            else:
                # Alternamos quién sale de local/visitante para variar visualmente
                if random.choice([True, False]):
                    enfrentamientos_validos.append({"jugador1": p1, "jugador2": p2})
                else:
                    enfrentamientos_validos.append({"jugador1": p2, "jugador2": p1})
        
        # Rotación de mesas: desplazamos los partidos para que nadie se ancle a la Mesa 1
        desplazamiento = i % len(enfrentamientos_validos) if enfrentamientos_validos else 0
        enfrentamientos_rotados = enfrentamientos_validos[desplazamiento:] + enfrentamientos_validos[:desplazamiento]
        
        # Asignación final de mesas
        for idx, enf in enumerate(enfrentamientos_rotados):
            partidos_ronda.append({
                "mesa": idx + 1,
                "jugador1": enf["jugador1"],
                "jugador2": enf["jugador2"]
            })
            
        fixture_completo.append({
            "numero": i + 1,
            "partidos": partidos_ronda,
            "descansan": descansan_ronda
        })
        
        # Rotación de jugadores (el índice 0 queda fijo, el último pasa a la posición 1)
        jugadores_rot.insert(1, jugadores_rot.pop())
        
    return fixture_completo

def actualizar_rondas_desde_fixture():
    idx = estado_global['ronda_actual_idx']
    fixture = estado_global['fixture']
    max_rondas = len(fixture)
    
    if max_rondas > 0:
        estado_global['ronda_actual'] = fixture[idx]
        estado_global['numero_ronda'] = fixture[idx]['numero']
        
        # Magia del loop: Si estamos en la última ronda, la próxima vuelve a ser la 1
        prox_idx = (idx + 1) % max_rondas
        estado_global['proxima_ronda'] = fixture[prox_idx]

@app.route('/')
def index():
    return render_template('pantalla.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/estado', methods=['GET'])
def get_estado():
    return jsonify(estado_global)

@app.route('/api/agregar_jugador', methods=['POST'])
def agregar_jugador():
    data = request.get_json(silent=True) or {}
    jugador = data.get('jugador', '').strip()
    if jugador and jugador not in estado_global['jugadores']:
        estado_global['jugadores'].append(jugador)
    return jsonify({"status": "ok"})

@app.route('/api/quitar_jugador', methods=['POST'])
def quitar_jugador():
    data = request.get_json(silent=True) or {}
    jugador = data.get('jugador', '').strip()
    
    if jugador in estado_global['jugadores']:
        estado_global['jugadores'].remove(jugador)
        
        # Si sacamos a un jugador a mitad del torneo, no rompemos el algoritmo.
        # Lo reemplazamos por un "FANTASMA" en los partidos futuros para darle descanso a su rival.
        if estado_global['estado'] == 'jugando':
            for ronda in estado_global['fixture'][estado_global['ronda_actual_idx']:]:
                partidos_validos = []
                for partido in ronda['partidos']:
                    if partido['jugador1'] == jugador:
                        ronda['descansan'].append(partido['jugador2'])
                    elif partido['jugador2'] == jugador:
                        ronda['descansan'].append(partido['jugador1'])
                    else:
                        partidos_validos.append(partido)
                
                # Reasignar números de mesas para que no queden huecos (Ej: Mesa 1, Mesa 3)
                for i, p in enumerate(partidos_validos):
                    p['mesa'] = i + 1
                    
                ronda['partidos'] = partidos_validos
                
            actualizar_rondas_desde_fixture()
            
    return jsonify({"status": "ok"})

@app.route('/api/iniciar', methods=['POST'])
def iniciar():
    if len(estado_global['jugadores']) < 2:
        return jsonify({"error": "Mínimo 2 jugadores"}), 400
    
    # 1. Generamos TODA la estructura del torneo matemáticamente
    estado_global['fixture'] = generar_fixture_perfecto(estado_global['jugadores'])
    
    # 2. Seteamos los estados iniciales
    estado_global['estado'] = 'jugando'
    estado_global['ronda_actual_idx'] = 0
    actualizar_rondas_desde_fixture()
    
    return jsonify({"status": "ok"})

@app.route('/api/avanzar', methods=['POST'])
def avanzar_ronda():
    if estado_global['estado'] == 'jugando':
        max_rondas = len(estado_global['fixture'])
        
        if max_rondas > 0:
            # Suma 1 a la ronda actual, pero si llega al máximo, vuelve a 0 (Ronda 1)
            estado_global['ronda_actual_idx'] = (estado_global['ronda_actual_idx'] + 1) % max_rondas
            actualizar_rondas_desde_fixture()
            
    return jsonify({"status": "ok"})

@app.route('/api/ticker', methods=['POST'])
def actualizar_ticker():
    data = request.get_json(silent=True) or {}
    estado_global['ticker_msg'] = data.get('ticker', '')
    return jsonify({"status": "ok"})

def abrir_navegador():
    # ACÁ ESTÁ EL TRUCO: Usamos 127.0.0.1 para que Chrome NO bloquee la cámara.
    webbrowser.open('http://127.0.0.1:5050/')

if __name__ == '__main__':
    ip_real = estado_global['ip_local']
    print(f"🚀 INICIANDO SISTEMA LMI...")
    print(f"📱 ADMIN (Celu):  http://{ip_real}:5050/admin")
    threading.Timer(1.2, abrir_navegador).start()
    app.run(host='0.0.0.0', port=5050, debug=False)