#!/usr/bin/env python3
"""
heartbeat.py
-------------
Este script define una función para que la aplicación principal avise
que el sistema está recibiendo datos (“latido”).

💡 ¿Qué es un latido?
Un archivo en /tmp (HEARTBEAT_PATH) cuya fecha de modificación
se actualiza cada vez que la app recibe o procesa información válida.

El LED de estado (led_rgb_status.py) revisa este archivo para saber
si el sistema está activo:
- Si el archivo se actualiza seguido → el LED sabe que “hay vida”.
- Si pasan más de HEARTBEAT_TTL segundos sin actualizarlo → se asume que no hay datos.
"""

import os

# Archivo que usará el LED para saber si hay actividad
HEARTBEAT_PATH = "/tmp/mgv_ae_heartbeat"

def send_heartbeat():
    """
    Actualiza la fecha/hora de modificación del archivo de latido.

    📌 Cómo usar:
    Llamar a esta función cada vez que la app reciba datos de los semáforos.
    Ejemplo:
        from heartbeat import send_heartbeat
        send_heartbeat()
    """
    try:
        # Abrir o crear el archivo y actualizar su fecha de modificación
        with open(HEARTBEAT_PATH, "a"):
            os.utime(HEARTBEAT_PATH, times=None)
    except Exception as e:
        print(f"Error al enviar latido: {e}")
