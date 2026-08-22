#!/usr/bin/env python3
"""Tests del auditor exprés con fixtures HTML."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a11yaudit import audit_html

# Página limpia: sin hallazgos
limpia = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Ok</title></head>
<body><h1>Título</h1><p><img src="a.png" alt="descripción"></p>
<a href="/x">Enlace con texto</a> <button>Botón</button>
<label>Nombre <input type="text" name="q"></label></body></html>'''
r = audit_html(limpia)
assert r['hallazgos'] == [], [h['hallazgo'] for h in r['hallazgos']]

# Página problemática: todos los fallos
mala = '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, user-scalable=no">
<title></title></head><body>
<h1>Uno</h1><h3>Salto</h3>
<img src="x.png"><a href="/y"></a><button></button>
<input type="text" name="sin">
<iframe src="e.html"></iframe>
<button tabindex="3">raro</button>
</body></html>'''
r2 = audit_html(mala)
crit = {h['criterio'] for h in r2['hallazgos']}
assert any('1.1.1' in c for c in crit)
assert any('4.1.2' in c for c in crit)   # botón/a sin nombre (por texto vacío)
assert any('3.3.2' in c for c in crit)   # input sin label
assert any('3.1.1' in c for c in crit)   # sin lang
assert any('2.4.2' in c for c in crit)   # title vacío
assert any('1.4.4' in c for c in crit)   # user-scalable=no
assert any('2.4.3' in c for c in crit)   # tabindex positivo
assert any('1.3.1' in c for c in crit)   # salto h1→h3
assert r2['resumen']['alta'] >= 3

# Botón cuyo nombre es solo una imagen con alt (válido)
img_alt = '<html lang="es"><head><title>t</title></head><body><button><img src="i.png" alt="Buscar"></button></body></html>'
r3 = audit_html(img_alt)
assert not any('4.1.2' in h['criterio'] for h in r3['hallazgos'])

print('TESTS AUDITOR PASAN ✓ (limpia sin hallazgos, mala detecta 8 criterios, nombre por imagen)')

# Enlace dentro de encabezado (patrón tarjetas): el nombre cuenta para ambos
h_con_link = '<html lang="es"><head><title>t</title></head><body><h1>uno</h1><h2><a href="/g">Guías</a></h2></body></html>'
r4 = audit_html(h_con_link)
assert not any('4.1.2' in h['criterio'] for h in r4['hallazgos']), r4['hallazgos']
assert r4['hallazgos'] == []
print('ENLACE-EN-ENCABEZADO OK ✓')
