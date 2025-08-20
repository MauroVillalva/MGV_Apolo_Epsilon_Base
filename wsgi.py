import os, sys, importlib

BASE = os.path.dirname(__file__)
# Asegurar repo y src/ en sys.path
for p in (BASE, os.path.join(BASE, "src")):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

# Probar rutas típicas de tu proyecto
CANDIDATOS = (
    ("mgv_ese.app", "app"),   # package/submodule
    ("mgv_ese", "app"),       # módulo con atributo app
    ("app", "app"),           # archivo app.py en raíz
)

app = None
errores = []
for mod, attr in CANDIDATOS:
    try:
        m = importlib.import_module(mod)
        app = getattr(m, attr)
        break
    except Exception as e:
        errores.append(f"{mod}:{attr} -> {e!r}")

if app is None:
    raise RuntimeError("No pude localizar la Flask app. Intentos:\n" + "\n".join(errores))
