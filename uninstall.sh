#!/usr/bin/env bash
set -euo pipefail
SERVICE=mgv_ese.service
sudo systemctl disable --now "$SERVICE" || true
sudo rm -f /etc/systemd/system/"$SERVICE"
sudo systemctl daemon-reload
sudo rm -f /etc/nginx/sites-enabled/mgv-ese /etc/nginx/sites-available/mgv-ese
sudo nginx -t && sudo systemctl reload nginx || true
echo "[ok] Limpieza hecha. (Opcional) rm -rf ~/MGV_E.S.E/venv ~/MGV_E.S.E/logs"
