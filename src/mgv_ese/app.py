#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from .config import Config
from .state import State
from .gpio_driver import GPIODriver
from .auth import auth_ok
import signal, sys, atexit
import ready


import heartbeat
app = Flask(__name__)

# =========================
# Logging de Epsilon
# =========================
import os, json, logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = os.getenv("MGV_LOG_DIR") or str(ROOT_DIR / "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "epsilon_posts.log")

_handler = RotatingFileHandler(LOG_PATH, maxBytes=262_144, backupCount=3, encoding="utf-8")
_handler.setFormatter(logging.Formatter('%(message)s'))
if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == _handler.baseFilename for h in app.logger.handlers):
    app.logger.addHandler(_handler)
app.logger.setLevel(logging.INFO)

def _log_epsilon(raw_text: str, parsed: dict, applied: dict, ip: str):
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "ip": ip,
        "raw": raw_text,
        "parsed": parsed,    # lo que interpretamos del body
        "applied": applied,  # lo que efectivamente aplicamos
    }
    app.logger.info(json.dumps(entry, ensure_ascii=False))

# =========================
# Mapeos idioma
# =========================
EN_TO_ES = {"red": "rojo", "yellow": "amarillo", "green": "verde"}
ES_TO_EN = {v: k for k, v in EN_TO_ES.items()}

def to_spanish_state(snapshot_en: dict) -> dict:
    return {
        EN_TO_ES["red"]: snapshot_en["red"],
        EN_TO_ES["yellow"]: snapshot_en["yellow"],
        EN_TO_ES["green"]: snapshot_en["green"],
        "peso": snapshot_en.get("last_peso"),
        "fuente": snapshot_en.get("last_update_source"),
        "actualizado": snapshot_en.get("last_update_at"),
        "seguir_epsilon": snapshot_en.get("follow_epsilon"),
    }

# =========================
# Instancias
# =========================
gpio = GPIODriver(Config.PIN_RED, Config.PIN_YELLOW, Config.PIN_GREEN)
state = State(Config.FOLLOW_EPSILON)

def apply_gpio(key, value):
    gpio.apply(key, value)

# Arranque: todo OFF
state.update({"red": "OFF", "yellow": "OFF", "green": "OFF"}, "boot", apply_gpio)

# Marca READY para el LED de estado
try:
    ready.send_ready()
    app.logger.info("READY flag created at /tmp/mgv_ready")
except Exception as e:
    app.logger.error(f"READY flag error: {e}")

# =========================
# Helpers de respuesta y red
# =========================
def response_with_bilingual_state(extra: dict = None):
    snap = state.snapshot()
    body = {
        "state_en": {
            "red": snap["red"],
            "yellow": snap["yellow"],
            "green": snap["green"],
            "last_peso": snap["last_peso"],
            "follow_epsilon": snap["follow_epsilon"],
            "last_update_source": snap["last_update_source"],
            "last_update_at": snap["last_update_at"],
        },
        "state_es": to_spanish_state(snap),
    }
    if extra:
        body.update(extra)
    return jsonify(body), 200

def _set_light(color_en: str, on: bool):
    desired = "ON" if on else "OFF"
    changed = state.update({color_en: desired}, "api", apply_gpio)
    changed_es = {EN_TO_ES[k]: v for k, v in changed.items()}
    return response_with_bilingual_state({"ok": True, "changed_en": changed, "changed_es": changed_es})

def _client_ip() -> str:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return (request.headers.get("X-Real-IP") or request.remote_addr or "").strip()

def _is_local() -> bool:
    ip = _client_ip()
    if ip in ("127.0.0.1", "::1") or ip.startswith("10.") or ip.startswith("192.168."):
        return True
    # 172.16.0.0 – 172.31.255.255
    parts = ip.split(".")
    if len(parts) >= 2 and parts[0] == "172":
        try:
            second = int(parts[1])
            if 16 <= second <= 31:
                return True
        except ValueError:
            pass
    return False

# =========================
# Healthcheck (nuevo) + API en inglés
# =========================
@app.get("/")
def root():
    # Healthcheck simple y abierto (para LED/monitor local)
    return "OK", 200

@app.get("/api/status")
def api_status():
    # Permitir sin auth si es localhost/red local; exigir auth para accesos externos
    if not (_is_local() or auth_ok(request)):
        return jsonify({"error": "unauthorized"}), 401
    return response_with_bilingual_state()

@app.get("/api/epsilon/logs")
def api_epsilon_logs():
    if not auth_ok(request):
        return jsonify({"error": "unauthorized"}), 401
    n = int((request.args.get("n") or "50").strip() or "50")
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        return jsonify({"ok": True, "path": LOG_PATH, "lines": [ln.strip() for ln in lines]})
    except FileNotFoundError:
        return jsonify({"ok": True, "path": LOG_PATH, "lines": []})

@app.post("/api/follow_epsilon")
def api_follow_epsilon():
    if not auth_ok(request):
        return jsonify({"error": "unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    enable = bool(body.get("enable", True))
    state.update({}, "api")
    with state.lock:
        state.follow_epsilon = enable
    return response_with_bilingual_state({"ok": True, "follow_epsilon": enable})

@app.post("/api/red_on")
def red_on():
    if not auth_ok(request): return jsonify({"error":"unauthorized"}), 401
    return _set_light("red", True)

@app.post("/api/red_off")
def red_off():
    if not auth_ok(request): return jsonify({"error":"unauthorized"}), 401
    changed = state.update({"red": "OFF", "green": "ON"}, "api", apply_gpio)
    return response_with_bilingual_state({
        "ok": True,
        "changed_en": changed,
        "changed_es": {EN_TO_ES[k]: v for k, v in changed.items()}
    })

@app.post("/api/green_on")
def green_on():
    if not auth_ok(request): return jsonify({"error":"unauthorized"}), 401
    return _set_light("green", True)

@app.post("/api/green_off")
def green_off():
    if not auth_ok(request): return jsonify({"error":"unauthorized"}), 401
    changed = state.update({"green": "OFF", "red": "ON"}, "api", apply_gpio)
    return response_with_bilingual_state({
        "ok": True,
        "changed_en": changed,
        "changed_es": {EN_TO_ES[k]: v for k, v in changed.items()}
    })

@app.post("/api/yellow_on")
def yellow_on():
    if not auth_ok(request): return jsonify({"error":"unauthorized"}), 401
    return _set_light("yellow", True)

@app.post("/api/yellow_off")
def yellow_off():
    if not auth_ok(request): return jsonify({"error":"unauthorized"}), 401
    return _set_light("yellow", False)

# =========================
# Recepción desde Epsilon (EN o ES -> EN) - MODO SNAPSHOT
# =========================
def _to_onoff(v) -> str:
    """
    Normaliza valor a 'ON'/'OFF'.
    Acepta: "1"/"0", 1/0, true/false, "on"/"off", "ON"/"OFF".
    Default: OFF.
    """
    if v is None:
        return "OFF"
    s = str(v).strip().lower()
    if s in ("1", "true", "on", "high", "sí", "si"):
        return "ON"
    return "OFF"

def _pick(body: dict, es_key: str, en_key: str) -> str:
    """
    Snapshot: devuelve 'ON'/'OFF'. Si la clave no viene, OFF.
    """
    if es_key in body:
        return _to_onoff(body.get(es_key))
    if en_key in body:
        return _to_onoff(body.get(en_key))
    return "OFF"

def _extract_payload(raw: dict) -> dict:
    """
    Acepta plano o anidado en 'estado'/'state'.
    """
    if isinstance(raw.get("estado"), dict):
        return raw["estado"]
    if isinstance(raw.get("state"), dict):
        return raw["state"]
    return raw

@app.post("/post")
def post_from_epsilon():
    """
    Acepta JSON EN o ES, plano o anidado, con '1'/'0' (también 1/0, true/false, on/off).
    Modo SNAPSHOT: se aplican SIEMPRE las 3 luces según lo recibido (faltantes = OFF).
    """
    if not auth_ok(request):
        return jsonify({"error": "unauthorized"}), 401

    # capturamos el cuerpo crudo para log
    raw_text = request.get_data(cache=True, as_text=True) or ""

    raw = request.get_json(silent=True) or {}
    body = _extract_payload(raw)
    peso = raw.get("peso") or body.get("peso")

    # Snapshot: siempre definimos las 3
    red    = _pick(body, "rojo", "red")
    green  = _pick(body, "verde", "green")
    yellow = _pick(body, "amarillo", "yellow")

    incoming_en = {
        "red":    red,
        "green":  green,
        "yellow": yellow,
    }
    if peso is not None:
        incoming_en["last_peso"] = peso

    with state.lock:
        apply = state.follow_epsilon

    if apply:
        changed = state.update(incoming_en, "epsilon", apply_gpio)
    else:
        # aunque no apliquemos GPIO, guardamos peso si vino
        changed = state.update({"last_peso": peso} if peso is not None else {}, "epsilon")

    heartbeat.send_heartbeat()
    # log de lo recibido y aplicado
    ip = request.headers.get("X-Real-IP") or request.remote_addr or "-"
    _log_epsilon(
        raw_text=raw_text,
        parsed={"red": red, "green": green, "yellow": yellow, "peso": peso},
        applied=incoming_en,
        ip=ip,
    )

    return response_with_bilingual_state({
        "ok": True,
        "applied": apply,
        "changed_en": changed,
        "changed_es": {EN_TO_ES.get(k, k): v for k, v in changed.items()}
    })

# Alias por si Epsilon llama a "/"
@app.post("/")
def post_root():
    return post_from_epsilon()

# =========================
# Limpieza
# =========================
def _cleanup(*_):
    try:
        # borrar READY para que el LED vuelva a “arranque”
        try:
            os.unlink("/tmp/mgv_ready")
        except FileNotFoundError:
            pass
        gpio.cleanup()
    finally:
        sys.exit(0)

signal.signal(signal.SIGINT, _cleanup)
signal.signal(signal.SIGTERM, _cleanup)
atexit.register(_cleanup)

def run():
    app.run(host=Config.HOST, port=Config.PORT)

if __name__ == "__main__":
    run()
