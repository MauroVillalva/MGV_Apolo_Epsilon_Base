#!/usr/bin/env python3
"""
ready.py
Marca que la aplicación está LISTA para recibir órdenes,
creando (o actualizando) el archivo /tmp/mgv_ready.
"""

import os

READY_PATH = "/tmp/mgv_ready"

def send_ready():
    """
    Llamar a esta función cuando tu app termine de iniciar
    y esté en estado "esperando órdenes".
    """
    try:
        with open(READY_PATH, "a"):
            os.utime(READY_PATH, times=None)
    except Exception as e:
        print(f"Error al marcar READY: {e}")
