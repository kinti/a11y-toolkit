#!/usr/bin/env python3
"""a11y-toolkit free online analyzer — the machine half, free forever.

Self-contained stdlib service (drop into jquin.net/lab or any host):

  GET  /            the analyzer UI (index.html)
  GET  /analizar    ?url=…&lang=en|es  → full static audit report (JSON)
  GET  /pack        ?url=…             → countersignature-ready evidence pack
  GET  /badge       ?score=N           → honest SVG badge

Public-service hardening (absent from the local CLI on purpose — auditing
internal staging locally is legitimate; publishing that to the world is not):
  - http/https only, private/loopback/reserved IPs blocked (SSRF)
  - per-IP rate limit (default 6 requests/minute)
  - single-page fetch cap inherited from the engine (3 MB)

Run:  python3 analizador.py [--port 8080] [--allow-private] [--rate 6]
Deploy: reverse-proxy to it; see webapp/README.md.
"""

import argparse
import ipaddress
import json
import os
import socket
import sys
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

from a11yaudit import audit_url                     # noqa: E402
from a11yevidence import empaquetar, MANUAL_AA      # noqa: E402
from a11ybadge import badge as badge_svg            # noqa: E402

_RATE: dict = {}
RATE_MAX = 6
RATE_VENTANA = 60
ALLOW_PRIVATE = False


def _privado(host):
    """True if the host resolves to any non-public address (SSRF guard)."""
    if not host:
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return True
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local \
                or ip.is_multicast or ip.is_unspecified:
            return True
    return False


def _rate_ok(ip):
    ahora = time.time()
    cola = _RATE.setdefault(ip, deque())
    while cola and cola[0] < ahora - RATE_VENTANA:
        cola.popleft()
    if len(cola) >= RATE_MAX:
        return False
    cola.append(ahora)
    return True


def _url_valida(url):
    return url.split(':')[0].lower() in ('http', 'https')


class Manejador(BaseHTTPRequestHandler):
    server_version = 'a11y-analyzer/1.0'

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write('%s %s\n' % (self.address_string(), fmt % args))

    def _res(self, cuerpo, code=200, ctype='application/json; charset=utf-8'):
        data = cuerpo.encode('utf-8') if isinstance(cuerpo, str) else cuerpo
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._res(json.dumps(obj, ensure_ascii=False), code)

    def _parametros(self):
        q = parse_qs(urlparse(self.path).query)
        return q.get('url', [''])[0].strip(), q.get('lang', ['en'])[0]

    def _guardas(self, url):
        """Common public-service guards; returns an error response or None."""
        if not _url_valida(url):
            self._json({'error': 'only http/https URLs are accepted'}, 400)
            return True
        host = urlparse(url).hostname
        if not ALLOW_PRIVATE and _privado(host):
            self._json({'error': 'private or unresolvable addresses are not audited'}, 403)
            return True
        return False

    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta in ('/', '/index.html'):
            with open(os.path.join(AQUI, 'index.html'), 'rb') as f:
                self._res(f.read(), 200, 'text/html; charset=utf-8')
            return
        if not _rate_ok(self.client_address[0]):
            self._json({'error': 'rate limit exceeded — try again in a minute'}, 429)
            return
        if ruta == '/analizar':
            url, lang = self._parametros()
            if self._guardas(url):
                return
            informe = audit_url(url, lang=lang if lang in ('es', 'en') else 'en')
            informe['manual_pendiente_n'] = len(MANUAL_AA)
            self._json(informe)
            return
        if ruta == '/pack':
            url, _ = self._parametros()
            if self._guardas(url):
                return
            informe = audit_url(url, lang='en')
            pack = empaquetar([informe])
            self._res(json.dumps(pack, ensure_ascii=False, indent=1), 200,
                      'application/json; charset=utf-8')
            self.wfile.flush()
            return
        if ruta == '/badge':
            q = parse_qs(urlparse(self.path).query)
            try:
                score = int(float(q.get('score', ['0'])[0]))
            except ValueError:
                score = 0
            self._res(badge_svg(score), 200, 'image/svg+xml; charset=utf-8')
            return
        self._json({'error': 'not found'}, 404)


def main():
    global RATE_MAX, ALLOW_PRIVATE
    ap = argparse.ArgumentParser(description='free online a11y analyzer')
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--rate', type=int, default=6, help='requests per minute per IP')
    ap.add_argument('--allow-private', action='store_true',
                    help='DEV/TEST ONLY: allow private addresses')
    a = ap.parse_args()
    RATE_MAX = a.rate
    ALLOW_PRIVATE = a.allow_private
    srv = ThreadingHTTPServer(('', a.port), Manejador)
    print(f'a11y analyzer on http://0.0.0.0:{a.port}  (rate {RATE_MAX}/min per IP, '
          f'private IPs {"ALLOWED (dev)" if ALLOW_PRIVATE else "blocked"})')
    srv.serve_forever()


if __name__ == '__main__':
    sys.exit(main())
