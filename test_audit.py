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

# FP bench gov.uk: aria-hidden con tabindex="-1" NO se reporta (no es tabulable)
ah = audit_html('<html lang="es"><head><title>t</title></head><body><h1>a</h1><main>'
                '<button aria-hidden="true" tabindex="-1">x</button>'
                '<button aria-hidden="true">y</button></main></body></html>')
n_ah = [h for h in ah['hallazgos'] if h['senal'] == 'aria_hidden_focusable']
assert len(n_ah) == 1 and '1 ' in n_ah[0]['hallazgo'], ah['hallazgos']

# FP bench: un único enlace genérico NO se reporta (el contexto suele bastar); dos, sí
g1 = audit_html('<html lang="es"><head><title>t</title></head><body><h1>a</h1><main>'
                '<a href="/x">Más información…</a></main></body></html>')
assert not any(h['senal'] == 'generic_link' for h in g1['hallazgos'])
g2 = audit_html('<html lang="es"><head><title>t</title></head><body><h1>a</h1><main>'
                '<a href="/x">Más</a><a href="/y">leer más</a></main></body></html>')
assert any(h['senal'] == 'generic_link' for h in g2['hallazgos'])

# labels huérfanos detectados (el label for= el de verdad; el suelto, no)
lo = audit_html('<html lang="es"><head><title>t</title></head><body><h1>a</h1><main>'
                '<label>Sin campo</label><input id="ok" type="text"><label for="ok">Ok</label>'
                '</main></body></html>')
hu = [h for h in lo['hallazgos'] if h['criterio'].startswith('3.3.2')]
assert len(hu) == 1 and '1 ' in hu[0]['hallazgo'], lo['hallazgos']

# v3.1: ARIA válido, autocomplete, enlaces genéricos, landmarks dup, accesskey, autoplay, score
v31 = '''<html lang="es"><head><title>t</title></head><body><main><h1>Uno</h1>
<div role="bottun">clic</div>
<button aria-labelledby="noexiste">X</button>
<input type="email" name="correo">
<nav></nav><nav></nav>
<a href="/a">Más</a><a href="/a">leer más</a>
<a href="/1">Informes</a><a href="/2">Informes</a>
<span accesskey="k">a</span><span accesskey="k">b</span>
<video src="v.mp4" autoplay></video>
<input type="text" name="nombre" id="i1">
<label for="i1">Nombre</label><label for="i1">Nombre otra vez</label>
</main></body></html>'''
rv = audit_html(v31, lang='en')
critv = {h['criterio'].split(' ')[0] for h in rv['hallazgos']}
for esperado in ['4.1.2', '1.3.5', '1.4.2', '2.4.4', '2.1.1', '3.3.2', '1.3.1']:
    assert esperado in critv, f'falta {esperado}: {sorted(critv)}'
va = audit_html('<html lang="es"><head><title>t</title></head><body><main><h1>a</h1>'
                '<div aria-hidden="focusable">x</div><div aria-level="cero">y</div>'
                '<div aria-live="polite">ok</div></main></body></html>', lang='en')
fv = [x for x in va['hallazgos'] if x['senal'] == 'aria_value_invalid']
assert fv and '2' in fv[0]['hallazgo'] and 'aria-live' not in fv[0]['hallazgo']
assert 0 <= rv['score'] < 100 and 'score_nota' in rv
assert audit_html('<html lang="es"><head><title>t</title></head><body><main><h1>a</h1></main></body></html>')['score'] == 100

print('CASOS LIMITE AUDITOR OK ✓ (nombre por imagen, select/textarea, lang, skip, _blank avisado, label huérfano)')
print('V3.1 OK ✓ (ARIA roto/desconocido, autocomplete 1.3.5, autoplay 1.4.2, enlaces 2.4.4, landmarks, accesskey, multi-label, score 0-100, valores ARIA)')
