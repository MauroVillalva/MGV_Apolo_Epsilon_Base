#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LED de HEARTBEAT (AZUL). Cátodo común.
- Azul ON  si el archivo /tmp/mgv_ae_heartbeat es reciente (<= TTL).
- Azul OFF si no llegan comandos (stale).
"""

import os, time, signal
import RPi.GPIO as GPIO

PIN_BLUE = 6                   # azul (cátodo común)
HEARTBEAT_PATH = "/tmp/mgv_ae_heartbeat"
HEARTBEAT_TTL  = float(os.getenv("MGV_HB_TTL", "10.0"))  # s

_terminated = False
def _sigterm(*_):
    global _terminated
    _terminated = True
signal.signal(signal.SIGTERM, _sigterm)
signal.signal(signal.SIGINT,  _sigterm)

def gpio_setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIN_BLUE, GPIO.OUT, initial=GPIO.LOW)

def led_blue(on: bool):
    GPIO.output(PIN_BLUE, GPIO.HIGH if on else GPIO.LOW)  # HIGH=encendido

def is_fresh(path: str, ttl: float) -> bool:
    try:
        mtime = os.path.getmtime(path)
        return (time.time() - mtime) <= ttl
    except FileNotFoundError:
        return False
    except Exception:
        return False

def main():
    print("[led HB] init (TTL=%.1fs)" % HEARTBEAT_TTL)
    gpio_setup()
    prev = None
    try:
        while not _terminated:
            alive = is_fresh(HEARTBEAT_PATH, HEARTBEAT_TTL)
            if alive != prev:
                print(f"[led HB] heartbeat = {'OK' if alive else 'NO'}")
                led_blue(alive)
                prev = alive
            time.sleep(1.0)
    finally:
        led_blue(False)
        GPIO.cleanup()

if __name__ == "__main__":
    main()
