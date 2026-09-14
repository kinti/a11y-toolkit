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

# v3.9: 2.5.3 label-in-name, 3.1.2 idioma de partes, 2.5.2 down-event, 3.3.8 captcha
v39 = '''<html lang="es"><head><title>t</title></head><body><main><h1>a</h1>
<a href="/x" aria-label="Más información promocional">Ver ofertas</a>
<a href="/y" aria-label="Ver ofertas y más">Ver ofertas</a>
<blockquote lang="xx">cita</blockquote>
<button onmousedown="go()">Rápido</button>
<script src="https://www.google.com/recaptcha/api.js"></script>
</main></body></html>'''
rv39 = audit_html(v39, lang='en')
sv39 = {x['senal'] for x in rv39['hallazgos']}
for esperada in ('label_in_name', 'lang_partes', 'down_event', 'captcha'):
    assert esperada in sv39, f'falta {esperada}: {sorted(sv39)}'
ok253 = audit_html('<html lang="es"><head><title>t</title></head><body><main><h1>a</h1>'
                   '<a href="/x" aria-label="Ver ofertas y más">Ver ofertas</a></main></body></html>')
assert not any(h['senal'] == 'label_in_name' for h in ok253['hallazgos'])

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
# v3.12: partial signals on previously manual-only criteria
v312 = '''<html lang="es"><head><title>t</title></head><body><main><h1>a</h1>
<marquee>oferta</marquee>
<div ontouchmove="swipe()">card</div>
<script>screen.orientation.lock('portrait'); addEventListener('devicemotion', s);</script>
<p>haz clic en el botón de la derecha</p>
<video src="v.mp4"></video>
</main></body></html>'''
rv312 = audit_html(v312, lang='en')
sv312 = {x['senal'] for x in rv312['hallazgos']}
for esperada in ('motion_moving', 'gesture_no_click', 'motion_actuation',
                 'orientation_lock', 'audio_desc_missing', 'sensory_text'):
    assert esperada in sv312, f'{esperada} missing: {sorted(sv312)}'
limpio312 = audit_html('<html lang="es"><head><title>t</title></head><body><main><h1>a</h1><p>x</p></main></body></html>', lang='en')
assert not (sv312 & {x['senal'] for x in limpio312['hallazgos']})
# site-level: pure function separates consistent from drifting nav
from a11yaudit import _Auditor, evaluar_sitio
paginas = ['<nav><a href="/">H</a><a href="/x">X</a></nav>' for _ in range(2)] + ['<nav><a href="/">H</a><a href="/y">Y</a></nav>']
parsers = []
for cuerpo in paginas:
    p = _Auditor(); p.feed(f'<html lang="en"><head><title>t</title></head><body>{cuerpo}<main><h1>a</h1></main></body></html>'); p.close(); parsers.append(p)
sen_sitio = {f['senal'] for f in evaluar_sitio(parsers, lang='en')}
assert {'nav_inconsistent', 'no_multiple_ways'} <= sen_sitio
parsers_ok = [_p for _p in [(_Auditor()) for _ in range(3)]]
for _p, cuerpo in zip(parsers_ok, ['<nav><a href="/">H</a></nav><input type="search">' for _ in range(3)]):
    _p.feed(f'<html lang="en"><head><title>t</title></head><body>{cuerpo}<main><h1>a</h1></main></body></html>'); _p.close()
assert evaluar_sitio(parsers_ok, lang='en') == []

# v3.9.2: pureza de idioma — la salida EN no contiene español
import re as _re
_ES = _re.compile(r'\b(sobre|entero|número|revisar|elementos|enlaces|ventana|campos)\b')
kitchen = audit_html('''<html lang="es"><head><title>t</title></head><body><main><h1>a</h1>
<div aria-level="cero">x</div><div aria-valuenow="alto">y</div>
<table><tr><td>a</td></tr></table></main></body></html>''', lang='en')
for _h in kitchen['hallazgos']:
    for _campo in ('hallazgo', 'remediacion'):
        assert not _ES.search(_h[_campo]), f"fuga ES en {_h['senal']}.{_campo}: {_h[_campo][:80]}"
    for _e in _h.get('ejemplos', []):
        assert not _ES.search(str(_e)), f"fuga ES en ej de {_h['senal']}: {_e}"
# v3.9.2: audit_url rechaza esquemas no http(s) (lectura local vía URL bloqueada)
from a11yaudit import audit_url as _au
_r = _au('file:///etc/passwd', lang='en')
assert 'error' in _r and 'http/https' in _r['error'], _r
_r2 = _au('ftp://x/y', lang='es')
assert 'error' in _r2

print('V3.1 OK ✓ (ARIA roto/desconocido, autocomplete 1.3.5, autoplay 1.4.2, enlaces 2.4.4, landmarks, accesskey, multi-label, score 0-100, valores ARIA)')
