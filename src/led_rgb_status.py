#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LED de ESTADO DEL SISTEMA/RED (solo VERDE/ROJO). Cátodo común.
- Arranque sin READY -> VERDE parpadeando (0.5 s).
- READY + red OK     -> VERDE fijo.
- READY + sin red    -> alterna VERDE/ROJO cada 2 s.
NOTA: NO usa el pin AZUL (reservado al LED de heartbeat).
"""

import os, time, signal, subprocess
from shutil import which
import RPi.GPIO as GPIO

# Pines BCM
PIN_GREEN = 24   # verde
PIN_RED   = 12   # rojo
# ¡OJO! NO configurar PIN_BLUE aquí (lo usa el servicio de heartbeat)

# Flags/tiempos
READY_FLAG   = "/tmp/mgv_ready"
BLINK_S      = 0.5
ALT_STEP_S   = 2.0
MAX_NET_DOWN = 180.0  # 3 min

_terminated = False
def _sigterm(*_):
    global _terminated
    _terminated = True
signal.signal(signal.SIGTERM, _sigterm)
signal.signal(signal.SIGINT,  _sigterm)

def okno(b): return "OK" if b else "NO"

def gpio_setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIN_GREEN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_RED,   GPIO.OUT, initial=GPIO.LOW)

def led(r=False, g=False):
    # Cátodo común: HIGH = encendido
    GPIO.output(PIN_RED,   GPIO.HIGH if r else GPIO.LOW)
    GPIO.output(PIN_GREEN, GPIO.HIGH if g else GPIO.LOW)

def cleanup_gpio():
    led(False, False)
    GPIO.cleanup()

def has_default_route() -> bool:
    try:
        out = subprocess.check_output(["ip", "route"], text=True, stderr=subprocess.DEVNULL)
        return any(ln.startswith("default ") for ln in out.splitlines())
    except Exception:
        return False

def try_recover_network():
    cmds = []
    if which("networkctl"): cmds.append(["/usr/bin/sudo","networkctl","reconfigure","--all"])
    if which("nmcli"):
        cmds.append(["/usr/bin/sudo","nmcli","networking","off"])
        cmds.append(["/usr/bin/sudo","nmcli","networking","on"])
    if which("systemctl"):
        cmds.append(["/usr/bin/sudo","systemctl","restart","dhcpcd.service"])
    for cmd in cmds:
        try: subprocess.run(cmd, timeout=15, check=False)
        except Exception: pass

def main_loop():
    print("[led SYS] init")
    gpio_setup()
    net_down_since = None
    alt_epoch = time.monotonic()
    try:
        while not _terminated:
            ready = os.path.exists(READY_FLAG)
            netok = has_default_route()
            if not ready:
                led(g=True);  time.sleep(BLINK_S)
                led(g=False); time.sleep(BLINK_S)
                continue
            if netok:
                led(g=True, r=False)
                net_down_since = None
                time.sleep(0.3)
                continue
            # READY pero sin red: alterna
            if net_down_since is None: net_down_since = time.monotonic()
            now = time.monotonic()
            phase = int((now - alt_epoch) // ALT_STEP_S) % 2
            if phase == 0: led(g=True,  r=False)
            else:          led(g=False, r=True)
            if (now - net_down_since) > MAX_NET_DOWN:
                print("[led SYS] sin red >3min -> reintento")
                try_recover_network()
                time.sleep(5)
                net_down_since = time.monotonic()
            time.sleep(0.1)
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main_loop()
