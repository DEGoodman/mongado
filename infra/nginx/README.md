# nginx (production droplet)

Host-level nginx that fronts the Docker containers. **Not** deployed by the
GitHub Actions workflow — changes must be applied manually.

## Topology

```
Visitor
  └─ Cloudflare edge (TLS, proxied DNS: mongado.com / api.mongado.com)
       └─ nginx on droplet :80/:443 (Let's Encrypt via certbot)
            ├─ mongado.com      → 127.0.0.1:3000 (frontend container)
            └─ api.mongado.com  → 127.0.0.1:8000 (backend container)
```

Container ports (including Neo4j 7474/7687) are bound to `127.0.0.1` in
`docker-compose.prod.yml` — Docker-published ports bypass ufw, so anything on
`0.0.0.0` is internet-reachable regardless of firewall rules (#226).

## Applying changes

```bash
scp infra/nginx/mongado.conf <droplet>:/etc/nginx/sites-available/mongado
ssh <droplet> "nginx -t && systemctl reload nginx"
```

`sites-enabled/mongado` is a symlink to `sites-available/mongado`.

## Key decisions

- **Client IPs**: `CF-Connecting-IP` (with `$remote_addr` fallback) is passed
  as `X-Forwarded-For`; uvicorn runs with `--proxy-headers` so slowapi
  rate-limits per real visitor. `$proxy_add_x_forwarded_for` was deliberately
  replaced — it preserves client-spoofable XFF values.
- **HSTS** is set at nginx for both origins (HTTP→HTTPS redirects already in
  place via certbot).
- **Security headers** for the frontend origin live here; the API sets its own
  via FastAPI `SecurityHeadersMiddleware`. CSP for the frontend is tracked in
  #172.
- **certbot** manages the `# managed by Certbot` lines and renewals; keep them
  intact when editing.

## Droplet admin access to Neo4j

Ports are loopback-only. From your machine, tunnel:

```bash
ssh -L 7474:localhost:7474 -L 7687:localhost:7687 <droplet>
# then browse http://localhost:7474
```
