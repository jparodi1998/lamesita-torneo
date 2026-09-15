from flask import Flask, render_template, request, jsonify
import random
import socket
import webbrowser
import threading

app = Flask(__name__)

jugadores = []
rondas_generadas = []
ronda_actual_idx = 0 # Memoria de la ronda que se está jugando

def obtener_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

IP_LOCAL = obtener_ip_local()

@app.route('/')
def pantalla():
    return render_template('pantalla.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/estado', methods=['GET'])
def obtener_estado():
    return jsonify({
        "jugadores": jugadores,
        "rondas": rondas_generadas,
        "ronda_activa": ronda_actual_idx, # Le avisamos a la pantalla qué ronda iluminar
        "ip_admin": f"http://{IP_LOCAL}:5000/admin"
    })

@app.route('/api/agregar', methods=['POST'])
def agregar_jugador():
    nombre = request.json.get('nombre')
    if nombre and nombre not in jugadores:
        jugadores.append(nombre)
    return jsonify({"status": "ok"})

@app.route('/api/eliminar', methods=['POST'])
def eliminar_jugador():
    global rondas_generadas, ronda_actual_idx
    nombre = request.json.get('nombre')
    if nombre in jugadores:
        jugadores.remove(nombre)
    rondas_generadas = []
    ronda_actual_idx = 0
    return jsonify({"status": "ok"})

@app.route('/api/armar_partidos', methods=['POST'])
def generar_fixture():
    global rondas_generadas, ronda_actual_idx
    rondas_generadas = []
    ronda_actual_idx = 0 # Si sorteamos de nuevo, volvemos a iluminar la Ronda 1
    
    if len(jugadores) < 2:
        return jsonify({"status": "error"})

    CANTIDAD_MESAS = 4 if len(jugadores) >= 9 else 3

    jugadores_rr = jugadores.copy()
    random.shuffle(jugadores_rr)
    
    if len(jugadores_rr) % 2 != 0:
        jugadores_rr.append("DESCANSO")
        
    n = len(jugadores_rr)
    total_rondas = n - 1
    
    for i in range(total_rondas):
        matchups_temporales = []
        descansan_ronda = []
        
        for j in range(n // 2):
            p1 = jugadores_rr[j]
            p2 = jugadores_rr[n - 1 - j]
            
            if p1 == "DESCANSO":
                descansan_ronda.append(p2)
            elif p2 == "DESCANSO":
                descansan_ronda.append(p1)
            else:
                matchups_temporales.append((p1, p2))
                
        partidos_a_jugar = []
        if len(matchups_temporales) > CANTIDAD_MESAS:
            partidos_a_jugar = matchups_temporales[:CANTIDAD_MESAS]
            for p1, p2 in matchups_temporales[CANTIDAD_MESAS:]:
                descansan_ronda.extend([p1, p2])
        else:
            partidos_a_jugar = matchups_temporales
            
        partidos_ronda = []
        for idx, (p1, p2) in enumerate(partidos_a_jugar):
            mesa_asignada = ((idx + i) % CANTIDAD_MESAS) + 1
            if random.choice([True, False]):
                partidos_ronda.append({"mesa": mesa_asignada, "jugador1": p1, "jugador2": p2})
            else:
                partidos_ronda.append({"mesa": mesa_asignada, "jugador1": p2, "jugador2": p1})
        
        partidos_ronda = sorted(partidos_ronda, key=lambda x: x["mesa"])
        
        rondas_generadas.append({
            "numero": i + 1,
            "partidos": partidos_ronda,
            "descansan": descansan_ronda
        })
        
        jugadores_rr = [jugadores_rr[0]] + [jugadores_rr[-1]] + jugadores_rr[1:-1]

    return jsonify({"status": "ok"})

# NUEVA RUTA PARA EL CELULAR: Avanzar o retroceder la iluminación
@app.route('/api/cambiar_ronda', methods=['POST'])
def cambiar_ronda():
    global ronda_actual_idx
    direccion = request.json.get('dir')
    
    if direccion == 'sig' and ronda_actual_idx < len(rondas_generadas) - 1:
        ronda_actual_idx += 1
    elif direccion == 'ant' and ronda_actual_idx > 0:
        ronda_actual_idx -= 1
        
    return jsonify({"status": "ok"})

def abrir_navegador():
    webbrowser.open_new(f"http://{IP_LOCAL}:5000/")

if __name__ == '__main__':
    threading.Timer(1.5, abrir_navegador).start()
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)