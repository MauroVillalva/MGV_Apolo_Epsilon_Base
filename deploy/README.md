# Despliegue MGV_E.S.E

Este directorio contiene las configuraciones "vivas" exportadas desde el host.

- Nginx:
  - deploy/nginx/conf.d/mgv_ese-http.conf
  - deploy/nginx/snippets/mgv_ese-locations.conf
  - deploy/nginx/conf.d/mgv_ese-vhost.conf
  - deploy/nginx/conf.d/00-default-444.conf (opcional)

- systemd:
  - deploy/systemd/mgv_ese.service

Notas:
- /post permitido solo desde 192.168.1.100 + rate limit.
- Logs de /post silencian 2xx (solo errores).
- vhost responde a Host == 192.168.1.105; default vhost devuelve 444.


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
### Ejemplo multi-placa

```bash
# Ejemplo multi-placa (bash + curl)
# Requisitos: curl y jq
IPS=(192.168.1.105 192.168.1.106)   # IPs de las placas
PAYLOAD='{"red":"0","yellow":"1","green":"1","peso":"88888"}'

# Envío de comandos a todas las placas
for ip in "${IPS[@]}"; do
  echo "POST -> http://$ip/post"
  # Nota: usando URL con IP, el encabezado Host se envía como la IP automáticamente
  curl -sS -X POST "http://$ip/post" \
       -H "Content-Type: application/json" \
       -d "$PAYLOAD" \
    | jq -r '.state_en.last_update_at'
done

# Healthcheck rápido de todas
echo
echo "Healthcheck:"
for ip in "${IPS[@]}"; do
  printf "%s -> " "$ip"
  curl -s "http://$ip/api/status" | jq -r '.state_en.last_update_at'
done
```

```js
// Ejemplo multi-placa (Node.js + node-fetch)
// npm i node-fetch
import fetch from "node-fetch";

const ips = ["192.168.1.105", "192.168.1.106"]; // IPs de las placas
const payload = { red: "0", yellow: "1", green: "1", peso: "88888" };

(async () => {
  for (const ip of ips) {
    try {
      const res = await fetch(`http://${ip}/post`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      console.log(ip, "OK", data.state_en.last_update_at);
    } catch (e) {
      console.error(ip, "ERROR:", e.message);
    }
  }
})();
```
<!-- EPSILON_CONN_END -->
