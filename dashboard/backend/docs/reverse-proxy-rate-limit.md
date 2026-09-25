# Runbook: reverse proxy y rate limiting (TRUSTED_PROXIES)

Card 5025917d (iteración de revisión 1). Este runbook fija los dos invariantes
de despliegue que el middleware de rate limit asume, y el motivo exacto por el
que `TRUSTED_PROXIES` de la aplicación debe ser la única decisión de confianza.

## Invariante 1: nginx appendea la IP real

Toda capa de proxy propia DEBE añadir la IP del peer inmediato a
`X-Forwarded-For`, nunca sobrescribir el header con contenido de otra fuente:

```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

`$proxy_add_x_forwarded_for` concatena el `X-Forwarded-For` entrante con
`$remote_addr` (la IP del TCP peer visto por ese proxy). El middleware recorre
el header de derecha a izquierda saltando hops confiados: si nuestros proxies
no appendean `$remote_addr`, el hop "real" que el middleware selecciona sería
controlable por el cliente y la derivación de identidad se degrada.

## Invariante 2: pin de uvicorn con FORWARDED_ALLOW_IPS explícito

Arrancar uvicorn siempre con la lista de proxies confiados explícita, en
paridad exacta con `TRUSTED_PROXIES` de la app:

```bash
uvicorn main:app --proxy-headers \
  --forwarded-allow-ips "<mismas IPs/CIDRs que TRUSTED_PROXIES>"
```

Ejemplo con docker-compose.unified.yml: si `TRUSTED_PROXIES=10.0.0.5`, entonces
`--forwarded-allow-ips "10.0.0.5"`.

## Por qué: uvicorn reescribe request.client antes del middleware

Con `--proxy-headers` activo, uvicorn 0.32 reescribe `request.client` desde
`X-Forwarded-For` ANTES de que cualquier middleware se ejecute, siempre que el
TCP peer esté en `FORWARDED_ALLOW_IPS`. Dos consecuencias:

1. La reescritura usa el contenido del header, no la topología real, y su
   fallback cuando todos los hops son confiados devuelve el hop MÁS IZQUIERDO
   del XFF, que es precisamente la parte controlada por el cliente.
2. Por tanto, si la lista de uvicorn fuese `*` (su default) o divergiera de la
   de la app, existirían dos decisiones de confianza distintas y la del
   servidor web es más débil que la del middleware.

Conclusión operativa: `TRUSTED_PROXIES` (aplicación) y
`--forwarded-allow-ips` (uvicorn) deben contener la misma lista, y esa lista
es la ÚNICA decisión de confianza del sistema. El middleware ignora XFF por
completo para peers no confiados y deriva la identidad hop a hop solo tras un
peer confiado (ver `middleware/rate_limit.py`, `_ip_identity`).

## Verificación rápida

1. Sin proxy (`TRUSTED_PROXIES=` vacío): cualquier `X-Forwarded-For` entrante
   se ignora; el bucket usa la IP del socket.
2. Tras el proxy: `curl -H "X-Forwarded-For: 1.2.3.4, 9.9.9.9" ...` con peer
   confiado debe bucketear por la IP real del cliente, no por `1.2.3.4`.
3. Arranque con `MAX_BUCKET_MEMBERS` menor que el mayor límite de
   `RATE_LIMITS`: el import de `core.rate_limit_config.py` lanza `ValueError`
   (guard W1).
