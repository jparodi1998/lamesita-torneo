import cv2
import numpy as np
import time
import requests

# Prendemos la cámara con resolución baja para cuidar el Pentium
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

# Variables de control
fondo_referencia = None
tiempo_que_tapo = 0
en_espera = False
tiempo_espera = 0

print("🤖 SENSOR ÓPTICO DE LA MESITA (PYTHON 3.14 COMPATIBLE) 🤖")
print("Acercá la mano a la cámara y tapá el centro durante 2 segundos para avanzar.")

while True:
    time.sleep(0.1) # Pausa para no ahogar al procesador
    
    exito, frame = cap.read()
    if not exito:
        continue

    frame = cv2.flip(frame, 1)
    tiempo_actual = time.time()

    # Si acabamos de cambiar de ronda, dormimos el sensor 5 segundos para evitar dobles toques
    if en_espera:
        if tiempo_actual - tiempo_espera > 5.0:
            en_espera = False
            print("🟢 Sensor activo nuevamente.")
        continue

    # Definimos una zona de control en el centro de la imagen (un recuadro de 100x100 píxeles)
    # Ajustá estos números si querés que el "botón" esté en otro lado
    h, w, _ = frame.shape
    x1, y1 = int(w/2 - 50), int(h/2 - 50)
    x2, y2 = int(w/2 + 50), int(h/2 + 50)
    
    zona_sensor = frame[y1:y2, x1:x2]
    
    # Convertimos a escala de grises y sacamos el brillo promedio de esa zona
    gris = cv2.cvtColor(zona_sensor, cv2.COLOR_BGR2GRAY)
    brillo_promedio = np.mean(gris)

    # Si el brillo baja drásticamente (porque alguien puso la mano oscura muy cerca de la lente)
    # o si hay un objeto estático tapando (esto lo podés calibrar según la luz de tu salón)
    # Umbral de oscuridad: si el promedio de gris es menor a 60 (es una mano tapando de cerca)
    if brillo_promedio < 60:
        if tiempo_que_tapo == 0:
            tiempo_que_tapo = tiempo_actual
            print("🟡 Objeto detectado cubriendo el sensor... Mantenelo...")
        elif tiempo_actual - tiempo_que_tapo >= 2.0:
            print("⏩ ¡2 SEGUNDOS CUMPLIDOS! Avanzando de ronda...")
            try:
                requests.post('http://127.0.0.1:5000/api/cambiar_ronda', json={'dir': 'sig'})
                print("✅ Orden enviada al tablero con éxito.")
            except Exception as e:
                print("❌ Error: Asegurate de que el servidor (app.py) esté abierto.")
            
            en_espera = True
            tiempo_espera = tiempo_actual
            tiempo_que_tapo = 0
    else:
        # Si saca la mano antes de tiempo, se cancela
        if tiempo_que_tapo != 0:
            print("🔴 Cancelado: Retiró la mano antes de los 2 segundos.")
        tiempo_que_tapo = 0

    # Para salir del script desde la consola apretando Ctrl+C o cerrando
    # (No abrimos ninguna ventana gráfica para no gastar recursos)