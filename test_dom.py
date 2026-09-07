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
<button aria-hidden="true" tabindex="-1">honeypot-btn</button>
<div aria-hidden="true" class="robots"><label>robots only <input type="text" tabindex="-1"></label></div>
<a href="#s" style="position:absolute;width:1px;height:1px;overflow:hidden">skip oculto</a>
<mi-tarjeta></mi-tarjeta>
<iframe src="dom_fixture_hijo.html" title="hijo"></iframe>
</main></body></html>'''

HIJO = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Hijo</title></head>
<body><img src="y.png"></body></html>'''
with open(os.path.join('/tmp', 'dom_fixture_hijo.html'), 'w', encoding='utf-8') as f:
    f.write(HIJO)
SHADOW_JS = '''<script>
customElements.define('mi-tarjeta', class extends HTMLElement {
  connectedCallback() {
    const r = this.attachShadow({mode: 'open'});
    r.innerHTML = '<img src="dentro.png"><button></button>' +
      '<p style="color:#999;background:#fff">Contraste del shadow DOM</p>';
  }
});
</script>'''
ruta = os.path.join('/tmp', 'a11ydom_fixture.html')
with open(ruta, 'w', encoding='utf-8') as f:
    f.write(FIXTURE.replace('</head>', SHADOW_JS + '</head>'))

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
assert d.get('shadow_roots', 0) >= 1, d.get('shadow_roots')
assert any('mi-tarjeta' in str(e) for h in d['hallazgos'] for e in h.get('ejemplos', [])), \
    'los fallos del shadow root no aparecen'
assert d.get('iframes_anidados', 0) == 1, d.get('iframes_anidados')   # iframe same-origin
assert any('iframe: y.png' in str(e) for h in d['hallazgos'] for e in h.get('ejemplos', []))
# FPs corregidos tras el bench: honeypot aria-hidden, tabindex=-1 y skip oculto no se reportan
senales = {h['senal']: h for h in d['hallazgos']}
assert 'aria_hidden_focusable' not in senales, senales.get('aria_hidden_focusable')
f258 = senales.get('target_small')
assert f258 is None or not any('1×1' in str(e) for e in f258.get('ejemplos', []))
# el párrafo con buen contraste NO provoca hallazgo: solo 2 zonas malas agrupadas
f14 = next(h for h in d['hallazgos'] if h['criterio'].startswith('1.4.3'))
assert '2.85:1' in f14['hallazgo'] and 'remediacion' in f14
# el botón mini aparece en los ejemplos de 2.5.8
f25 = next(h for h in d['hallazgos'] if h['criterio'].startswith('2.5.8'))
assert any('14×14' in e for e in f25.get('ejemplos', [])), f25
print('TESTS DOM RENDERIZADO PASAN ✓ (1.4.3 computado, 2.5.8, 3.3.2, 1.1.1, modo rendered)')
