#!/usr/bin/env python3
"""Tests v3.2: señal estable, SARIF, insignia SVG, presupuesto, crawl de enlaces."""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from a11yaudit import audit_html, _enlaces_internos  # noqa: E402
from a11ysarif import desde_informe  # noqa: E402
from a11ybadge import badge  # noqa: E402
from a11ybudget import init, comparar  # noqa: E402

# --- 1. señal estable en hallazgos ---
r = audit_html('<html lang="es"><head><title>t</title></head><body><img src="x.png"></body></html>')
assert all('senal' in h for h in r['hallazgos']), r['hallazgos']
assert any(h['senal'] == 'imgs_alt' for h in r['hallazgos'])

# --- 2. SARIF: estructura y niveles ---
mal = audit_html('<html lang="es"><head><title>t</title></head><body><main>'
                 '<img src="x.png"><div onclick="ir()">clic</div>'
                 '<a href="/x">Más</a></main></body></html>', lang='en')
s = desde_informe(mal)
assert s['version'] == '2.1.0' and s['runs'][0]['tool']['driver']['name'] == 'a11y-toolkit'
res = s['runs'][0]['results']
niveles = {x['level'] for x in res}
assert 'error' in niveles and 'note' in niveles, niveles
reglas = {x['id'] for x in s['runs'][0]['tool']['driver']['rules']}
assert any(x.startswith('WCAG-1.1.1') for x in reglas)
for x in res:
    assert x['locations'][0]['physicalLocation']['artifactLocation']['uri'] == mal['url']
    assert 'Fix:' in x['message']['text']
# formato site: pagina agregada
site = dict(mal, informes=[mal], resumen=mal['resumen'])
s2 = desde_informe(site)
assert len(s2['runs'][0]['results']) >= len(res)

# --- 3. insignia SVG: honesta y accesible ---
svg = badge(92, fecha='2026-09-07', lang='en')
assert 'role="img"' in svg and '<title>' in svg and '92/100' in svg and 'screening' in svg
assert '#2da44e' in svg                       # ≥90 verde
assert '#cf222e' in badge(30)                 # <50 rojo
assert 'not conformance' in svg               # la promesa que NO hace
svg_es = badge(60, lang='es')
assert 'cribado automático' in svg_es and '#d29922' in svg_es

# --- 4. presupuesto: solo lo NUEVO bloquea ---
base_html = '<html lang="es"><head><title>t</title></head><body><main><h1>a</h1><img src="x.png"></main></body></html>'
base_audit = audit_html(base_html, 'https://t.example')
budget = init(base_audit)
assert 'imgs_alt' in budget['senales'] and budget['max_nuevos'] == 0

mismo = comparar(budget, audit_html(base_html, 'https://t.example'))
assert mismo['ok'] and mismo['nuevos'] == [] and mismo['resueltos'] == []

peor = audit_html('<html lang="es"><head><title>t</title></head><body><main><h1>a</h1>'
                  '<img src="x.png"><button></button><select name="s"></select></main></body></html>',
                  'https://t.example')
v = comparar(budget, peor)
assert not v['ok'] and 'ctrl_name' in v['nuevos_bloqueantes'], v
assert 'imgs_alt' not in v['nuevos']           # la base se acepta

mejor = audit_html('<html lang="es"><head><title>t</title></head><body><main><h1>a</h1></main></body></html>',
                   'https://t.example')
m = comparar(budget, mejor)
assert m['ok'] and 'imgs_alt' in m['resueltos']  # arreglo → baja de la lista de pendientes

# base caducada bloquea aunque no haya novedades
budget['fecha_revision'] = '2020-01-01'
assert comparar(budget, base_audit)['ok'] is False
budget['fecha_revision'] = '2099-01-01'
assert comparar(budget, base_audit)['ok'] is True

# --- 5. descubrimiento de enlaces internos (crawl) ---
html_links = '''<a href="/a">1</a><a href="https://t.example/b#frag">2</a>
<a href="https://otro.dom/c">3</a><a href="mailto:x@y">4</a>
<a href="/doc.pdf">5</a><a href="relativa">6</a>'''
ls = _enlaces_internos(html_links, 'https://t.example/base/', 'https://t.example')
assert 'https://t.example/a' in ls and 'https://t.example/b' in ls
assert 'https://t.example/base/relativa' in ls
assert all('otro.dom' not in x and '.pdf' not in x for x in ls)

print('TESTS V3.2 PASAN ✓ (señal estable, SARIF 2.1.0, insignia honesta SVG, presupuesto ok/bloqueo, crawl de enlaces)')
