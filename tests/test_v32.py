#!/usr/bin/env python3
"""Tests v3.2: señal estable, SARIF, insignia SVG, presupuesto, crawl de enlaces."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from a11y_toolkit.a11yaudit import audit_html, _internal_links  # noqa: E402
from a11y_toolkit.a11ysarif import from_report  # noqa: E402
from a11y_toolkit.a11ybadge import badge  # noqa: E402
from a11y_toolkit.a11ybudget import init, compare  # noqa: E402

# --- 1. señal estable en findings ---
r = audit_html('<html lang="es"><head><title>t</title></head><body><img src="x.png"></body></html>')
assert all('signal' in h for h in r['findings']), r['findings']
assert any(h['signal'] == 'img_no_alt' for h in r['findings'])

# --- 2. SARIF: estructura y levels ---
mal = audit_html('<html lang="es"><head><title>t</title></head><body><main>'
                 '<img src="x.png"><div onclick="ir()">clic</div>'
                 '<a href="/x">Más</a><a href="/y">aquí</a><span id="d1"></span><span id="d1"></span></main></body></html>', lang='en')
s = from_report(mal)
assert s['version'] == '2.1.0' and s['runs'][0]['tool']['driver']['name'] == 'a11y-toolkit'
res = s['runs'][0]['results']
levels = {x['level'] for x in res}
assert 'error' in levels and 'note' in levels, levels
rules = {x['id'] for x in s['runs'][0]['tool']['driver']['rules']}
assert any(x.startswith('WCAG-1.1.1') for x in rules)
for x in res:
    assert x['locations'][0]['physicalLocation']['artifactLocation']['uri'] == mal['url']
    assert 'Fix:' in x['message']['text']
# formato site: pagina agregada
site = dict(mal, reports=[mal], summary=mal['summary'])
s2 = from_report(site)
assert len(s2['runs'][0]['results']) >= len(res)

# --- 3. insignia SVG: honesta y accesible ---
svg = badge(92, date='2026-09-07', lang='en')
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
assert 'img_no_alt' in budget['signals'] and budget['max_new'] == 0

mismo = compare(budget, audit_html(base_html, 'https://t.example'))
assert mismo['ok'] and mismo['new'] == [] and mismo['resolved'] == []

worst = audit_html('<html lang="es"><head><title>t</title></head><body><main><h1>a</h1>'
                  '<img src="x.png"><button></button><select name="s"></select></main></body></html>',
                  'https://t.example')
v = compare(budget, worst)
assert not v['ok'] and 'ctrl_name' in v['new_blocking'], v
assert 'img_no_alt' not in v['new']         # la base se acepta

best = audit_html('<html lang="es"><head><title>t</title></head><body><main><h1>a</h1></main></body></html>',
                   'https://t.example')
m = compare(budget, best)
assert m['ok'] and 'img_no_alt' in m['resolved']  # arreglo → baja de la lista de pendientes

# base caducada bloquea aunque no haya novedades
budget['review_date'] = '2020-01-01'
assert compare(budget, base_audit)['ok'] is False
budget['review_date'] = '2099-01-01'
assert compare(budget, base_audit)['ok'] is True

# --- 5. descubrimiento de enlaces internos (crawl) ---
html_links = '''<a href="/a">1</a><a href="https://t.example/b#frag">2</a>
<a href="https://otro.dom/c">3</a><a href="mailto:x@y">4</a>
<a href="/doc.pdf">5</a><a href="relativa">6</a>'''
ls = _internal_links(html_links, 'https://t.example/base/', 'https://t.example')
assert 'https://t.example/a' in ls and 'https://t.example/b' in ls
assert 'https://t.example/base/relativa' in ls
assert all('otro.dom' not in x and '.pdf' not in x for x in ls)

print('TESTS V3.2 PASAN ✓ (señal estable, SARIF 2.1.0, insignia honesta SVG, presupuesto ok/bloqueo, crawl de enlaces)')
