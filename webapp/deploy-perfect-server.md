# Deploy: PERFECT-SERVER + Cloudflare Tunnel (recommended topology)

Your reality: **jquin.net is Cloudflare Pages (static — no Python)** and
**PERFECT-SERVER is tailnet-private**. The analyzer needs a public Python
runtime. The clean path that respects both: run it as a container on the
PERFECT-SERVER box and expose it through a **Cloudflare Tunnel** — public
HTTPS on `analizador.jquin.net`, zero open ports, home IP invisible.

## 1. Build and run (in PERFECT-SERVER's docker-compose.yml)

From the a11y-toolkit repo, the image builds itself:

```yaml
# docker-compose.override.yml or appended service
  a11y-analyzer:
    build: /home/YOU/Dev/A11Y-MCP          # Dockerfile lives in webapp/
    container_name: a11y-analyzer
    restart: unless-stopped
    ports:
      - "127.0.0.1:8790:8080"              # tailnet/Caddy can reach it; not public
    networks:
      - internal
```

`docker compose up -d --build a11y-analyzer` — verify on the tailnet:
`curl http://127.0.0.1:8790/badge?score=90` (SVG).

## 2. Public URL via Cloudflare Tunnel (cloudflared)

One-time: Cloudflare dashboard → Zero Trust → Networks → Tunnels → create
`a11y-analyzer` → note the token. Then:

```yaml
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token <TUNNEL_TOKEN>
    networks:
      - internal
```

In the tunnel's public-hostname config (dashboard or ingress rules):

```
analizador.jquin.net  →  http://a11y-analyzer:8080
```

Cloudflare handles HTTPS and the edge; the box opens no ports.

## 3. The front door (JQUIN, the Astro site)

The lab page (`public/lab/`) links to it — one line:

```html
<a class="cta" href="https://analizador.jquin.net/">
  🎯 Online analyzer — free full report + evidence pack</a>
```

And in every article: "pruébalo aquí mismo".

## Ops notes

- **Rate limiting**: the service self-limits (6/min/IP). Behind Cloudflare
  you can also add a WAF rate rule — belt and suspenders.
- **Cloudflare caching**: `/badge` responses are tiny SVGs; a 1-min edge TTL
  is harmless and free. `/analizar` must stay uncached (default for query
  strings).
- **Alternative for tailnet-only use**: skip the tunnel and just add to the
  existing Caddyfile `handle_path /analizador/* { reverse_proxy
  localhost:8790 }` — private version for your own audits on the go.
- **Self-hosted vnu** for the future paid tier: add a `vnu` service
  (`ghcr.io/validator/validator`) on the internal network and pass its URL
  as `base_url` — the W3C privacy caveat disappears for your users.
