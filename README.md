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
