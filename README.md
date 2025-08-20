# MGV_E.S.E — Receptor Epsilon (Semáforo 3 luces)
- Receptor Flask en RPi, modo *snapshot* (aplica lo que envía Epsilon sin lógica extra).
- Escucha en :5002; expuesto por Nginx en :80. Acceso por mDNS: http://semaforo.local

## Endpoints
- POST /post  (EN/ES; "1"/"0", 1/0, true/false, on/off; acepta `state`/`estado`)
- GET  /api/status
- GET  /api/epsilon/logs?n=50

## Logs
- ~/MGV_E.S.E/logs/epsilon_posts.log (rotativo)

## GPIO (BCM)
- RED=22, YELLOW=23, GREEN=25 (usuario del servicio en grupo `gpio`)

## Operación
- Servicio: `sudo systemctl status mgv_ese.service`
- Proxy: `curl http://127.0.0.1/api/status` o `http://semaforo.local/api/status`
- Epsilon: configurar destino `semaforo.local` (sin IP)

## Despliegue rápido nueva RPi
1) Copiar proyecto a `~/MGV_E.S.E`
2) `sudo bash bootstrap.sh`  (crea venv, servicio, nginx, mDNS)
3) Probar: `curl http://semaforo.local/api/status`

---

## 🚀 Instalación rápida (Raspberry Pi OS)

Requiere `git` y `sudo`. El script crea/usa un virtualenv, instala dependencias y configura los servicios.

### Opción A — Usuario **Argos**
```bash
sudo apt update && sudo apt install -y git python3-venv
bash -lc 'set -e; REPO=https://github.com/MauroVillalva/MGV_Apolo_Epsilon_Base.git; DIR=$HOME/MGV_Apolo_Epsilon_Base; [ -d "$DIR/.git" ] || git clone "$REPO" "$DIR"; git -C "$DIR" pull --ff-only; cd "$DIR"; ./bootstrap.sh'
```

---

## 🔌 Integración con Epsilon

- Endpoint recomendado del semáforo: **`semaforo.local:80`** (o `IP:80`).
- En `config.json` de Epsilon:

```json
{
  "repetidores": {
    "activo": true,
    "bascula1": ["semaforo.local:80"]
  }
}
```

### Verificación
- `curl -s http://semaforo.local/api/status | python3 -m json.tool`
- `sudo tail -n 20 /var/log/nginx/access.log` debe mostrar `POST /post` 200 desde la IP de Epsilon.


<!-- EPSILON_CONN_START -->
## Cambio importante — Epsilon → Placa por IP (no `semaforo.local`)

**Qué cambió**
- El vhost de Nginx responde **sólo** si el encabezado `Host` coincide con la **IP de la placa** (ej.: `192.168.1.105`).
- El endpoint **`/post`** permite únicamente la IP del Epsilon (por defecto `192.168.1.100`).
- Hay rate limit: **60 req/min** con `burst=20` → devuelve **429** si se excede.
- Éxitos 2xx de `/post` no se loguean; sólo errores en `/var/log/nginx/post_access.log`.

**Cómo debe conectar Epsilon**
- POST a: `http://<IP_DE_PLACA>/post`
- GET health: `http://<IP_DE_PLACA>/api/status`
- Usar la IP de cada placa; **no** usar `semaforo.local`.
  > Nota: la mayoría de librerías HTTP ponen `Host: <IP>` automáticamente al usar una URL con IP.

**Variables por sitio**
- **IP de placa** (vhost): editar `server_name` en `/etc/nginx/conf.d/mgv_ese-vhost.conf`
- **IP de Epsilon permitida**: editar `allow` en `/etc/nginx/snippets/mgv_ese-locations.conf`

**Pruebas rápidas**
```bash
IP=192.168.1.105  # IP de la placa

# Debe responder 200 con el estado
curl -s -H "Host: $IP" http://$IP/api/status | python3 -m json.tool

# /post desde hosts NO-Epsilon debe dar 403 (allow/deny)
curl -i -H "Host: $IP" -X POST http://$IP/post || true
```

**Códigos y diagnóstico**
- **444**: `Host` incorrecto (usaste `semaforo.local` u otro nombre). Solución: llamar por IP o ajustar `server_name`.
- **403**: IP no permitida en `/post` (allow/deny). Solución: actualizar `allow` y recargar Nginx.
- **429**: excediste rate limit (60/min, burst 20). Solución: reducir frecuencia o ajustar política.
- **200**: OK (no se registra en `post_access.log` por silenciamiento de 2xx).

**Multi-placa**
- Cada placa debe tener su propia IP y `server_name` con esa IP.
- Epsilon debe enviar comandos a **cada IP** de placa por separado.
<!-- EPSILON_CONN_END -->
