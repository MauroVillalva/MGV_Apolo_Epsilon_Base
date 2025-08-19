import os

def str2bool(v: str) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

class Config:
    PORT = int(os.getenv("PORT", "5001"))
    HOST = os.getenv("HOST", "0.0.0.0")
    JWT_SECRET = os.getenv("JWT_SECRET", "condidoSecretoQueJamasVasASaver")
    JWT_ALG = os.getenv("JWT_ALG", "HS256")
    PIN_RED = int(os.getenv("PIN_RED", "22"))
    PIN_YELLOW = int(os.getenv("PIN_YELLOW", "23"))
    PIN_GREEN = int(os.getenv("PIN_GREEN", "25"))
    FOLLOW_EPSILON = str2bool(os.getenv("FOLLOW_EPSILON", "true"))
