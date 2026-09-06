#!/usr/bin/env python3
"""Tests de la auditoría renderizada (a11ydom) contra un fixture local file://.

Se auto-omiten si Playwright no está instalado (CI no lo instala: la auditoría
estática ya cubre el núcleo; esto valida el camino renderizado donde exista).
"""
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

try:
    import playwright  # noqa: F401
except ImportError:
    print('SKIP test_dom: Playwright no instalado')
    sys.exit(0)

FIXTURE = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Fixture DOM</title>
<style>.malo{color:#999;background:#fff}.mini{font-size:10px;padding:0;width:14px;height:14px}
a:focus{outline:none}.chico{padding:1px 2px}</style></head>
<body><main>
<h1>Fixture</h1>
<p class="malo">Texto con contraste insuficiente 2.85</p>
<p style="color:#777;background:#bbb">Otro malo</p>
<p style="color:#333;background:#fff">Este está bien 12.6</p>
<button class="mini">X</button>
<a href="#s" class="chico" style="display:inline-block">ir</a>
<img src="x.png"><input type="text" name="sinlabel">
</main></body></html>'''

ruta = os.path.join('/tmp', 'a11ydom_fixture.html')
with open(ruta, 'w', encoding='utf-8') as f:
    f.write(FIXTURE)

r = subprocess.run([sys.executable, os.path.join(AQUI, 'a11ydom.py'),
                    'file://' + ruta, '--lang', 'en'],
                   capture_output=True, text=True, timeout=120)
d = json.loads(r.stdout)
assert 'error' not in d, d

crit = {h['criterio'] for h in d['hallazgos']}
assert any(c.startswith('1.4.3') for c in crit), sorted(crit)          # contraste real
assert any(c.startswith('2.5.8') for c in crit), sorted(crit)          # target size (nuevo WCAG 2.2)
assert any(c.startswith('3.3.2') for c in crit), sorted(crit)          # campo sin label
assert any(c.startswith('1.1.1') for c in crit), sorted(crit)          # img sin alt
assert d['modo'] == 'rendered'
# el párrafo con buen contraste NO provoca hallazgo: solo 2 zonas malas agrupadas
f14 = next(h for h in d['hallazgos'] if h['criterio'].startswith('1.4.3'))
assert '2.85:1' in f14['hallazgo'] and 'remediacion' in f14
# el botón mini aparece en los ejemplos de 2.5.8
f25 = next(h for h in d['hallazgos'] if h['criterio'].startswith('2.5.8'))
assert any('14×14' in e for e in f25.get('ejemplos', [])), f25
print('TESTS DOM RENDERIZADO PASAN ✓ (1.4.3 computado, 2.5.8, 3.3.2, 1.1.1, modo rendered)')
