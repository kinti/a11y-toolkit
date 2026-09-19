#!/usr/bin/env python3
"""webapp suite: SSRF/rate guards (unit) + full service smoke (offline)."""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, 'webapp'))

# ---------- unit: guards ----------
from analizador import _privado, _url_valida, _rate_ok  # noqa: E402
import analizador  # noqa: E402

for host in ('127.0.0.1', 'localhost', '10.0.0.1', '192.168.1.1', '::1',
             '169.254.1.1', '172.16.0.5', 'no-dominio-xxx-invalido.test'):
    assert _privado(host), host
for ip in ('93.184.216.34', '8.8.8.8', '1.1.1.1'):
    assert not _privado(ip), ip
assert _url_valida('https://x.com') and _url_valida('http://x.com')
assert not _url_valida('file:///etc/passwd') and not _url_valida('ftp://x')
analizador.RATE_MAX = 2
assert _rate_ok('1.1.1.1') and _rate_ok('1.1.1.1') and not _rate_ok('1.1.1.1')
assert _rate_ok('2.2.2.2')
print('✓ guardas SSRF + esquema + rate-limit')

# ---------- integration: full service against a local fixture ----------
FIXTURE = ('<!doctype html><html lang="es"><head><title>T</title></head><body><main><h1>a</h1>'
           '<img src="x.png"><div onclick="f()">c</div></main></body></html>')


class _Fij(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(FIXTURE.encode())

    def log_message(*a):
        pass


fix = ThreadingHTTPServer(('127.0.0.1', 0), _Fij)
pf = fix.server_address[1]
threading.Thread(target=fix.serve_forever, daemon=True).start()

proc = subprocess.Popen([sys.executable, os.path.join(AQUI, 'webapp', 'analizador.py'),
                         '--port', '8791', '--allow-private', '--rate', '50'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.5)
try:
    base = 'http://127.0.0.1:8791'
    ui = urllib.request.urlopen(base + '/', timeout=10).read().decode()
    assert 'Evidence pack' in ui and 'a11y' in ui
    r = json.load(urllib.request.urlopen(f'{base}/analizar?url=http://127.0.0.1:{pf}/', timeout=30))
    assert r['score'] < 100 and r['manual_pendiente_n'] >= 10
    sen = {h['senal'] for h in r['hallazgos']}
    assert 'imgs_alt' in sen
    p = json.load(urllib.request.urlopen(f'{base}/pack?url=http://127.0.0.1:{pf}/', timeout=30))
    assert p['formato'] == 'a11y-evidence-pack/1' and len(p['sha256']) == 64
    b = urllib.request.urlopen(base + '/badge?score=90', timeout=10).read().decode()
    assert b.startswith('<svg') and '90/100' in b
    print('✓ webapp integral: UI + auditoría + pack hasheado + badge')
finally:
    proc.terminate()
    fix.shutdown()
