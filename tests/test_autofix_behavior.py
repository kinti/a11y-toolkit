#!/usr/bin/env/python3
"""Comportamiento REAL de la capa de errores inyectada por autofix (P1, 3ª
pasada de la revisión externa 2026-11-22).

La capa activaba noValidate y solo miraba descendientes: «Guardar borrador»
con formnovalidate dejaba de enviar, y un campo obligatorio asociado con
form= fuera del árbol permitía el envío vacío. Aquí se cargan los HTML
CORREGIDOS en Chromium contra un servidor local y se pulsa de verdad.

Se auto-omite si Playwright no está instalado (doctrina test_dom).
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

try:
    import playwright  # noqa: F401
except ImportError:
    print('SKIP test_autofix_behavior: Playwright no instalado')
    sys.exit(0)

from a11y_toolkit.a11yfix import autofix  # noqa: E402

PAGINA = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>f</title></head><body>
<form action="/done" method="get" id="f1">
<input type="text" name="campo" required>
<button type="submit">Enviar</button>
<button type="submit" formnovalidate name="borrador">Guardar borrador</button>
</form>
<input type="text" name="fuera" required form="f2">
<form action="/done" method="get" id="f2">
<button type="submit">Enviar f2</button>
</form>
</body></html>"""


_PAGINA_FIJA = {}

class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/page':
            body = _PAGINA_FIJA['html'].encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith('/done'):
            body = b'<html><body>DONE</body></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


srv = HTTPServer(('127.0.0.1', 0), _H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{srv.server_port}'

res = autofix(PAGINA, url='https://x/form', lang='en')
assert 'error' not in res, res.get('error')
fixed = res['fixed_html']
assert 'data-a11yfx' in fixed and '<script>' in fixed, 'capa no insertada'
_PAGINA_FIJA['html'] = fixed   # servida por http: data: URL bloquea el submit

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch(headless=True)
    page = nav.new_page()
    page.goto(BASE + '/page')

    # 1) formnovalidate: «Guardar borrador» DEBE enviar (nativo lo permitía;
    #    la capa vieja lo bloqueaba)
    page.click('button[name=borrador]')
    page.wait_for_timeout(500)
    assert '/done' in page.url, f'formnovalidate bloqueado: {page.url}'
    assert 'DONE' in page.content(), 'el envío del borrador no llegó'
    print('1. formnovalidate envía ✓')

    # 2) submit normal con campo vacío: bloqueado CON mensaje (la capa sirve
    #    para esto) — y aria-invalid presente
    page.goto(BASE + '/page')
    page.click('#f1 button:not([formnovalidate])')
    page.wait_for_timeout(300)
    assert '/page' in page.url and 'DONE' not in page.content(), 'envío con campo required vacío permitido'
    assert page.locator('#f1 [aria-invalid=true]').count() >= 1
    assert page.locator('.a11yfx-err:not([hidden])').count() >= 1
    print('2. envío inválido bloqueado con mensaje + aria-invalid ✓')

    # 3) campo asociado con form= FUERA del árbol: el envío de f2 con el
    #    campo externo vacío DEBE bloquearse (la capa vieja lo permitía)
    page.click('#f2 button')
    page.wait_for_timeout(300)
    assert '/page' in page.url and 'DONE' not in page.content(), 'form=: envío permitido con campo required vacío'
    assert page.locator('[name=fuera][aria-invalid=true]').count() == 1
    print('3. campo form= asociado fuera del árbol validado ✓')

    nav.close()
srv.shutdown()

# 4) fragmento sin </body>: la capa se declara aplicada → el script DEBE
#    estar (antes: aria-describedby colgantes sin script)
frag = autofix('<form><input required name="q"><button>ok</button></form>',
               url='https://x/frag', lang='en')
assert 'error' not in frag
assert '<script>' in frag['fixed_html'], 'sin </body>: script ausente con capa declarada'
print('4. fragmento sin </body>: script insertado al final ✓')

print('AUTOFIX COMPORTAMIENTO OK ✓ (formnovalidate envía, vacío bloqueado, '
      'form= validado, fragmento sin </body> completo)')
