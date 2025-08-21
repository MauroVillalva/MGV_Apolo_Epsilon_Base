#!/usr/bin/env bash
set -euo pipefail

# ==== Variables (podés exportarlas antes de correr el script) ====
EPSILON_IP="${EPSILON_IP:-192.168.1.100}"     # IP del Epsilon que hace POST /post
APP_DIR="${APP_DIR:-$HOME/MGV_Apolo_Epsilon_Base}"
REPO_URL="${REPO_URL:-https://github.com/MauroVillalva/MGV_Apolo_Epsilon_Base.git}"

# Pines por defecto para LEDs de estado (BCM)
PIN_RED="${PIN_RED:-17}"       # LED A -> ROJO (estado)
PIN_GREEN="${PIN_GREEN:-27}"   # LED A -> VERDE (estado)
PIN_BLUE="${PIN_BLUE:-26}"     # LED B -> AZUL (actividad Epsilon)

echo "[INFO] EPSILON_IP=$EPSILON_IP  APP_DIR=$APP_DIR"
echo "[INFO] PIN_RED=$PIN_RED PIN_GREEN=$PIN_GREEN PIN_BLUE=$PIN_BLUE"

# ==== Paquetes base ====
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip python3-dev nginx curl jq

# ==== Código + venv ====
if [ ! -d "$APP_DIR/.git" ]; then
  rm -rf "$APP_DIR" || true
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
python3 -m venv venv
"$APP_DIR/venv/bin/pip" install --upgrade pip
[ -f requirements.txt ] && "$APP_DIR/venv/bin/pip" install -r requirements.txt

# ==== Usuario con acceso a GPIO (los servicios systemd no necesitan relogin) ====
sudo usermod -aG gpio "$USER" || true

# ==== Ajuste: permitir setear pines por variable de entorno (idempotente) ====
# led_rgb_status.py -> usa PIN_RED/PIN_GREEN desde env si existen (no falla si no matchea)
sed -ri 's/^(PIN_RED\s*=\s*)([0-9]+)/\1int(__import__("os").getenv("PIN_RED","\\2"))/' src/led_rgb_status.py || true
sed -ri 's/^(PIN_GREEN\s*=\s*)([0-9]+)/\1int(__import__("os").getenv("PIN_GREEN","\\2"))/' src/led_rgb_status.py || true
# heartbeat_led.py -> usa PIN_BLUE desde env si existe
sed -ri 's/^(PIN_BLUE\s*=\s*)([0-9]+)/\1int(__import__("os").getenv("PIN_BLUE","\\2"))/' src/heartbeat_led.py || true

# ==== Config común (/etc/default/semaforos) ====
sudo tee /etc/default/semaforos >/dev/null <<EOC
EPSILON_IP=${EPSILON_IP}
PIN_RED=${PIN_RED}
PIN_GREEN=${PIN_GREEN}
PIN_BLUE=${PIN_BLUE}
EOC

# ==== Backend (gunicorn en 127.0.0.1:5001) ====
sudo tee /etc/systemd/system/mgv_ese.service >/dev/null <<'EOS'
[Unit]
Description=MGV_E.S.E API (Receptor Epsilon)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=%i
Group=%i
WorkingDirectory=__APPDIR__
Environment=PYTHONUNBUFFERED=1
ExecStart=__APPDIR__/venv/bin/gunicorn --chdir __APPDIR__ --workers 2 --threads 2 --bind 127.0.0.1:5001 --timeout 30 wsgi:app
Restart=on-failure
RestartSec=2
SupplementaryGroups=gpio

[Install]
WantedBy=multi-user.target
EOS
sudo sed -i "s|__APPDIR__|$APP_DIR|g; s|%i|$USER|g" /etc/systemd/system/mgv_ese.service
sudo systemctl daemon-reload
sudo systemctl enable --now mgv_ese.service

# ==== Nginx (rate limit + /post sólo desde Epsilon + vhost por IP) ====
# http-level: map + limit_req_zone + log_format
sudo tee /etc/nginx/conf.d/mgv_ese-http.conf >/dev/null <<'EON'
map $status $log_post_errors { ~^2 0; default 1; }
limit_req_zone $binary_remote_addr zone=post_ese:10m rate=60r/m;
log_format post_err '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"';
EON

# locations con allow/deny y rate limit
sudo tee /etc/nginx/snippets/mgv_ese-locations.conf >/dev/null <<EOF2
location /api/ {
    proxy_pass http://127.0.0.1:5001;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP        \$remote_addr;
    proxy_read_timeout 10s;
}
location = /post {
    allow ${EPSILON_IP};
    deny  all;
    limit_req zone=post_ese burst=20 nodelay;
    limit_req_status 429;
    access_log /var/log/nginx/post_access.log post_err if=\$log_post_errors;
    proxy_pass http://127.0.0.1:5001;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP        \$remote_addr;
    proxy_read_timeout 10s;
}
EOF2

# vhost que sólo responde al Host=IP local
MYIP="$(hostname -I | awk '{print $1}')"
sudo tee /etc/nginx/conf.d/mgv_ese-vhost.conf >/dev/null <<EOF3
server {
    listen 80;
    listen [::]:80;
    server_name ${MYIP};

    include /etc/nginx/snippets/mgv_ese-locations.conf;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_read_timeout 10s;
    }
}
EOF3

# default 444 para bloquear nombres inesperados y quitar default de Debian
sudo tee /etc/nginx/conf.d/00-default-444.conf >/dev/null <<'EO444'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    return 444;
}
EO444
sudo rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default || true

sudo nginx -t
sudo systemctl reload nginx
sudo systemctl enable --now nginx

# ==== Wrapper para ejecutar scripts del repo con venv ====
tee "$APP_DIR/src/venv-python-wrapper.sh" >/dev/null <<'EOW'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT="$1"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/../venv/bin/python3" "$DIR/$SCRIPT"
EOW
chmod +x "$APP_DIR/src/venv-python-wrapper.sh"

# ==== Servicios de LEDs de estado ====
sudo tee /etc/systemd/system/led_rgb_status.service >/dev/null <<'EOS2'
[Unit]
Description=LED A (Rojo/Verde) - estado del sistema/red
After=mgv_ese.service
Wants=mgv_ese.service

[Service]
Type=simple
User=%i
Group=%i
WorkingDirectory=__APPDIR__
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/default/semaforos
ExecStart=__APPDIR__/src/venv-python-wrapper.sh led_rgb_status.py
Restart=always
RestartSec=2
SupplementaryGroups=gpio

[Install]
WantedBy=multi-user.target
EOS2
sudo sed -i "s|__APPDIR__|$APP_DIR|g; s|%i|$USER|g" /etc/systemd/system/led_rgb_status.service

sudo tee /etc/systemd/system/heartbeat_led.service >/dev/null <<'EOS3'
[Unit]
Description=LED B (Azul) - actividad Epsilon / heartbeat
After=mgv_ese.service
Wants=mgv_ese.service

[Service]
Type=simple
User=%i
Group=%i
WorkingDirectory=__APPDIR__
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/default/semaforos
ExecStart=__APPDIR__/src/venv-python-wrapper.sh heartbeat_led.py
Restart=always
RestartSec=2
SupplementaryGroups=gpio

[Install]
WantedBy=multi-user.target
EOS3
sudo sed -i "s|__APPDIR__|$APP_DIR|g; s|%i|$USER|g" /etc/systemd/system/heartbeat_led.service

sudo systemctl daemon-reload
sudo systemctl enable --now led_rgb_status.service heartbeat_led.service

# ==== Pruebas rápidas ====
echo "[TEST] Backend directo (gunicorn) :5001"
curl -s http://127.0.0.1:5001/api/status | jq . || true

echo "[TEST] Nginx con Host=$MYIP"
curl -s -H "Host: ${MYIP}" "http://${MYIP}/api/status" | jq . || true

echo "[TEST] /post desde localhost (debería 403)"
curl -i -H "Host: ${MYIP}" -X POST "http://${MYIP}/post" || true

echo "[INFO] Servicios LED (resumen):"
systemctl --no-pager -l status led_rgb_status.service | sed -n '1,12p' || true
systemctl --no-pager -l status heartbeat_led.service | sed -n '1,12p' || true

echo "[OK] bootstrap terminado. Para cambiar IP/pines: editar /etc/default/semaforos y reiniciar servicios LED."
