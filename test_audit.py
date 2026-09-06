#!/usr/bin/env python3
"""Tests del auditor exprés con fixtures HTML (es/en, remediación incluida)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a11yaudit import audit_html

# Página limpia: sin hallazgos (tiene <main> → 2.4.1 cubierto)
limpia = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Ok</title></head>
<body><main><h1>Título</h1><p><img src="a.png" alt="descripción"></p>
<a href="/x">Enlace con texto</a> <button>Botón</button>
<label>Nombre <input type="text" name="q"></label></main></body></html>'''
r = audit_html(limpia)
assert r['hallazgos'] == [], [(h['criterio'], h['hallazgo']) for h in r['hallazgos']]

# Página problemática: todos los fallos nuevos + antiguos, salida en inglés
mala = '''<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="30">
<meta name="viewport" content="width=device-width, user-scalable=no">
<title></title></head><body>
<h1>Uno</h1><h3>Salto</h3><h4></h4>
<img src="x.png"><a href="/y"></a><button></button>
<input type="text" name="sin"><select name="sel"><option>1</option></select><textarea></textarea>
<input type="image" src="b.png"><label>Suelto</label>
<div onclick="x()">clic</div><button aria-hidden="true">oculto</button>
<video src="v.mp4"></video>
<table><tr><td>a</td></tr></table>
<a href="https://x" target="_blank">Más info</a>
<div id="d"></div><div id="d"></div>
<iframe src="e.html"></iframe>
<button tabindex="3">raro</button>
</body></html>'''
r2 = audit_html(mala, lang='en')
crit = {h['criterio'] for h in r2['hallazgos']}
for esperado in ['1.1.1', '1.2.2', '1.3.1', '1.4.4', '2.1.1', '2.2.1', '2.4.1', '2.4.2',
                 '2.4.3', '3.1.1', '3.2.5', '3.3.2', '4.1.2']:
    assert any(c.startswith(esperado + ' ') for c in crit), f'falta {esperado}: {sorted(crit)}'
assert all('remediacion' in h and h['remediacion'] for h in r2['hallazgos'])
assert r2['hallazgos'][0]['criterio'].endswith('Non-text Content')  # alta primero, en inglés
assert r2['resumen']['alta'] >= 6
print('TESTS AUDITOR PASAN ✓ (13 criterios, remediación, orden por severidad, salida EN)')

# Botón cuyo nombre es solo una imagen con alt (válido)
img_alt = '<html lang="es"><head><title>t</title></head><body><button><img src="i.png" alt="Buscar"></button></body></html>'
r3 = audit_html(img_alt)
assert not any(h['criterio'].startswith('4.1.2') for h in r3['hallazgos'])

# select y textarea SÍ se auditan ahora (antes solo input)
st = audit_html('<html lang="es"><head><title>t</title></head><body>'
                '<select name="s"></select><textarea name="ta"></textarea></body></html>')
assert any(h['criterio'].startswith('3.3.2') and '2' in h['hallazgo'] for h in st['hallazgos']), st['hallazgos']

# lang inválido vs válido
li = audit_html('<html lang="xx-YY"><head><title>t</title></head><body><h1>a</h1><main></main></body></html>')
assert any('BCP-47' in h['hallazgo'] for h in li['hallazgos'])
lv = audit_html('<html lang="pt-BR"><head><title>t</title></head><body><h1>a</h1><main></main></body></html>')
assert not any(h['criterio'].startswith('3.1.1') for h in lv['hallazgos'])

# saltar contenido: con <main> ya no hay hallazgo 2.4.1; ancla interna con texto tampoco
sk = audit_html('<html lang="es"><head><title>t</title></head><body>'
                '<a href="#c">Saltar al contenido</a><h1>a</h1><div id="c"></div></body></html>')
assert not any(h['criterio'].startswith('2.4.1') for h in sk['hallazgos'])

# target=_blank CON aviso: sin hallazgo 3.2.5
tb = audit_html('<html lang="es"><head><title>t</title></head><body><h1>a</h1><main>'
                '<a href="https://x" target="_blank">Docs (nueva ventana)</a></main></body></html>')
assert not any(h['criterio'].startswith('3.2.5') for h in tb['hallazgos'])

# labels huérfanos detectados (el label for= el de verdad; el suelto, no)
lo = audit_html('<html lang="es"><head><title>t</title></head><body><h1>a</h1><main>'
                '<label>Sin campo</label><input id="ok" type="text"><label for="ok">Ok</label>'
                '</main></body></html>')
hu = [h for h in lo['hallazgos'] if h['criterio'].startswith('3.3.2')]
assert len(hu) == 1 and '1 ' in hu[0]['hallazgo'], lo['hallazgos']

print('CASOS LIMITE AUDITOR OK ✓ (nombre por imagen, select/textarea, lang, skip, _blank avisado, label huérfano)')
