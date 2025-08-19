# auth.py
from flask import Request

def auth_ok(req: Request) -> bool:
    """
    Autenticación desactivada: permite todas las solicitudes.
    (Útil cuando Epsilon no puede enviar token)
    """
    return True
