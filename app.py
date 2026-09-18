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
    "ronda_actual": None,
    "proxima_ronda": None,
    "numero_ronda": 0,
    "ticker_msg": "BIENVENIDOS A LA MESITA ARENA /// MANTENER LA LIMPIEZA DEL SALÓN",
    "ip_local": get_ip()
}

def generar_ronda(jugadores, num_ronda):
    j_mezclados = list(jugadores)
    random.shuffle(j_mezclados)
    partidos = []
    
    while len(j_mezclados) >= 2 and len(partidos) < 4:
        partidos.append({
            "mesa": len(partidos) + 1,
            "jugador1": j_mezclados.pop(0),
            "jugador2": j_mezclados.pop(0)
        })
    return {
        "numero": num_ronda,
        "partidos": partidos,
        "descansan": j_mezclados
    }

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
        if estado_global['estado'] == 'jugando':
            estado_global['proxima_ronda'] = generar_ronda(estado_global['jugadores'], estado_global['numero_ronda'] + 1)
    return jsonify({"status": "ok"})

@app.route('/api/iniciar', methods=['POST'])
def iniciar():
    if len(estado_global['jugadores']) < 2:
        return jsonify({"error": "Mínimo 2 jugadores"}), 400
    
    estado_global['estado'] = 'jugando'
    estado_global['numero_ronda'] = 1
    estado_global['ronda_actual'] = generar_ronda(estado_global['jugadores'], 1)
    estado_global['proxima_ronda'] = generar_ronda(estado_global['jugadores'], 2)
    return jsonify({"status": "ok"})

@app.route('/api/avanzar', methods=['POST'])
def avanzar_ronda():
    if estado_global['estado'] == 'jugando':
        estado_global['numero_ronda'] += 1
        estado_global['ronda_actual'] = estado_global['proxima_ronda']
        estado_global['proxima_ronda'] = generar_ronda(estado_global['jugadores'], estado_global['numero_ronda'] + 1)
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