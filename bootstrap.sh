#!/usr/bin/env bash
SERVICE_NAME="${SERVICE_NAME:-mgv_apollo_epsilon_base.service}"
NGINX_SITE="${NGINX_SITE:-mgv-apollo-epsilon-base}"
set -euo pipefail
SERVICE_NAME="${SERVICE_NAME:-mgv_apollo_epsilon_base.service}"
NGINX_SITE="${NGINX_SITE:-mgv-apollo-epsilon-base}"
USER_NAME=${SUDO_USER:-$USER}
SERVICE_NAME="${SERVICE_NAME:-mgv_apollo_epsilon_base.service}"
NGINX_SITE="${NGINX_SITE:-mgv-apollo-epsilon-base}"
APP_DIR="${APP_DIR:-$(pwd)}"
PORT="${PORT:-5002}"
HOSTNAME_TAG="${HOSTNAME_TAG:-semaforo}"

echo "[i] Usuario: $USER_NAME  App: $APP_DIR  Hostname: $HOSTNAME_TAG  Puerto: $PORT"

sudo apt-get update
sudo apt-get install -y python3-venv nginx avahi-daemon avahi-utils libnss-mdns

# Hostname/mDNS
if [[ "$(hostnamectl --static | tr -d '\n')" != "$HOSTNAME_TAG" ]]; then
  sudo hostnamectl set-hostname "$HOSTNAME_TAG"
fi
grep -q "^127\.0\.1\.1.*$HOSTNAME_TAG" /etc/hosts || echo "127.0.1.1 $HOSTNAME_TAG" | sudo tee -a /etc/hosts >/dev/null
sudo systemctl enable --now avahi-daemon
sudo sed -i 's/^hosts:.*/hosts: files mdns4_minimal [NOTFOUND=return] dns mdns4/' /etc/nsswitch.conf

# App + venv
mkdir -p "$APP_DIR/logs"
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# GPIO
sudo usermod -aG gpio "$USER_NAME"

# systemd
sudo tee /etc/systemd/system/mgv_ese.service >/dev/null <<EOF
[Unit]
Description=MGV_E.S.E API (Receptor Epsilon)
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$APP_DIR
Environment=PYTHONPATH=$APP_DIR/src
Environment=HOST=0.0.0.0
Environment=PORT=$PORT
Environment=PYTHONUNBUFFERED=1
SupplementaryGroups=gpio
ExecStart=$APP_DIR/venv/bin/python -m mgv_ese
Restart=on-failure
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now mgv_ese.service

# Nginx (80→5002) + hardening LAN + loopback
sudo tee /etc/nginx/sites-available/mgv-ese >/dev/null <<'EOF'
server {
  listen 80 default_server;
  listen [::]:80 default_server;
  server_name _;
  location / {
    allow 127.0.0.1; allow ::1;
    allow 10.0.0.0/8; allow 172.16.0.0/12; allow 192.168.0.0/16;
    deny all;
    proxy_pass http://127.0.0.1:5002;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_http_version 1.1;
  }
}
EOF

sudo ln -sf /etc/nginx/sites-available/mgv-ese /etc/nginx/sites-enabled/mgv-ese
sudo unlink /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo nginx -t && sudo systemctl restart nginx

echo "[ok] Listo. Probar: curl -s http://$HOSTNAME_TAG.local/api/status | python3 -m json.tool || true"
