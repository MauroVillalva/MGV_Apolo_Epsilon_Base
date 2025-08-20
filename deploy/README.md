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
