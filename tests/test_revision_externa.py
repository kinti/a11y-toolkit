#!/usr/bin/env python3
"""Regression tests from the October 2026 external review (every claim
verified first; the false ones are pinned as false)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from a11y_toolkit.a11ydisprove import disprove  # noqa: E402
from a11y_toolkit.a11yfix import autofix, _attrs  # noqa: E402
from a11y_toolkit import contrast  # noqa: E402
from a11y_toolkit import a11ydiff  # noqa: E402
from a11y_toolkit.a11yaudit import _fetch  # noqa: E402
from a11y_toolkit.a11yevidence import build_pack  # noqa: E402
from a11y_toolkit import a11ystatement as declaracion  # noqa: E402

# 1. disprove acepta report y su body usa el mismo name (era UnboundLocalError)
r = disprove('https://nonexistent.example',
             report={'mode': 'scroll', 'url': 'x', 'score': 9,
                     'findings': [{'criterion': '4.1.3', 'severity': 'high'}]},
             timeout=5)
assert r['disprover']['executed'] is False and r['findings'][0]['disprover_status'] == 'not-rechecked'
print('1. disprove report= OK, modo sin verificador → not-rechecked ✓')

# 2. autofix no corrompe elementos con contenido (textarea/select) y conserva opciones
r = autofix('<form><textarea required>Original</textarea></form>', lang='en')
import re
inner = re.search(r'<textarea[^>]*>(.*?)</textarea>', r['fixed_html'], re.S).group(1)
assert inner == 'Original', inner
assert 'a11yfx-err' in r['fixed_html']
r = autofix('<form><select required><option value="a">A</option></select></form>', lang='en')
assert '<option value="a">A</option>' in r['fixed_html']
print('2. autofix conserva valores y opciones ✓')

# 3. _attrs no revienta con atributos vacíos y los conserva
a = _attrs('<input value="" required>')
assert a['value'] == ''  # el valor vacío se conserva (before: StopIteration)
print('3. _attrs con value="" ✓')

# 4. parse_color: sintaxis moderna con '/' y channels negativos acotados
c = contrast.parse_color('rgb(0 0 0 / 50%)')
assert c == {'r': 0, 'g': 0, 'b': 0, 'a': 0.5}, c
c2 = contrast.parse_color('rgba(-5, 0, 0, 1)')
assert c2['r'] == 0
print('4. parse_color espacio+alfa y clamp ✓')

# 5. a11ydiff: perder un elemento del Tab es regresión (ok:false)
d = a11ydiff.diff({'elements': [], 'focus_order': ['#pay', '#cancel']},
                  {'elements': [], 'focus_order': ['#cancel']})
assert d['ok'] is False and d['focus']['removed'] == ['#pay']
print('5. a11ydiff detecta foco eliminado ✓')

# 6. evidence: un finding rejected no revive como fail; no-rechecked tampoco
inf = {'mode': 'static', 'url': 'x', 'score': 9, 'findings': [
    {'criterion': '1.4.3 Contrast', 'severity': 'high', 'signal': 'x', 'issue': 'x', 'status': 'rejected'},
    {'criterion': '1.1.1 Non-text', 'severity': 'high', 'signal': 'y', 'issue': 'y'}]}
p6 = build_pack([inf])
row = next(m for m in p6['criteria'] if m['criterion'].startswith('1.4.3'))
assert row['status'] != 'automated-fail'
print('6. evidence respects rejected ✓ (1.4.3 →', row['status'] + ')')

# 7. declaracion: el método por defecto no atribuye evaluaciones no realizadas
d7 = declaracion.generate(entity='X', url='https://x.example', status='partial')
assert 'axe-core' not in d7['html']
assert ('BORRADOR NO VALIDADO' in d7['html']) or ('UNVALIDATED DRAFT' in d7['html'])
print('7. declaración honesta por defecto ✓')

# 8. política de esquema uniforme en _fetch
for esquema in ('file:///etc/passwd', 'ftp://x/y'):
    r8 = _fetch(esquema)
    assert 'error' in r8 and 'http' in r8['error'], r8
print('8. _fetch rechaza esquemas no http(s) ✓')


# ── Ronda 2 (re-revisión de v5.4.0): lo que el changelog afirmaba en falso ──

# 9. autofix: el contenido de <script> es intocable (el caso de comillas
#    dobles era el que rompía; el de simples sobrevivía por accidente)
SCRIPT = '<script>var t = \'<form id="f"><input type="email" required></form>\';</script>'
r9 = autofix(SCRIPT, lang='en', title='T')
assert "var t = '<form id=\"f\"><input type=\"email\" required></form>'" in r9['fixed_html'], r9['fixed_html']
assert 'autocomplete' not in r9['fixed_html']
print('9. autofix: <script> intocable (comillas dobles) ✓')

# 10. _attrs: comillas simples (regresión del findall: rellenaba con '')
a10 = _attrs("<input type='email' required>")
assert a10.get('type') == 'email', a10
print('10. _attrs lee comillas simples ✓')

# 11. viewport: eliminar el meta respects comillas al buscar el cierre
r11 = autofix('<html><head><meta name="viewport" content="user-scalable=no" '
              'data-note="a>b"></head><body>x</body></html>', lang='en')
assert '<head></head>' in r11['fixed_html'] and '<head>>' not in r11['fixed_html']
assert '<body>x</body>' in r11['fixed_html']
print('11. viewport removal quote-safe ✓')

# 12. detección de navegadores: la cadena chrome/msedge usa el parámetro real
src_chain = open(os.path.join(ROOT, 'a11y_toolkit', 'a11ydom.py')).read()
assert 'lambda pw: p.' not in src_chain, 'lambda con variable inexistente'
print('12. cadena de navegadores sin NameError latente ✓')

# 13. el contraste del pase principal compone el alfa del TEXTO
main_js = src_chain if 'ratioOf(over_' in src_chain else None
import a11y_toolkit.a11ydom as _dom
src_dom = open(os.path.join(ROOT, 'a11y_toolkit', 'a11ydom.py')).read()
assert 'ratioOf(over_(fgE, bg), bg)' in src_dom, 'el pase principal no compone el alfa del text (con opacidad del elemento)'
# y la definición de over_ precede a su uso en el mismo block
i_over = src_dom.index('const over_ =')
i_use = src_dom.index('ratioOf(over_(fgE, bg), bg)')
assert i_over < i_use
print('13. pase principal: alfa del text compuesto (over_ before del uso) ✓')


# ── Ronda 3 (noviembre 2026): segunda revisión externa de a11yfix ──

# 14. máscara anidada: un <script> DENTRO de un comentario se enmascara dos
#     veces; el unmask en orden de creación restauraba el interno dentro del
#     ORIGINAL almacenado del externo y el token quedaba en la salida
r14 = autofix('A<!-- <script>old()</script> -->B<p>x</p>')
assert 'A11YFXMASK' not in r14['fixed_html'], r14['fixed_html']
assert '<!-- <script>old()</script> -->' in r14['fixed_html']
print('14. unmask en orden inverso: script en comentario sin token filtrado ✓')

# 15. el guard "la página ya maneja sus errores" mira los scripts ORIGINALES:
#     en el texto vivo ya están enmascarados y el findall no veía NADA — la
#     capa se inyectaba aunque la página hiciera setCustomValidity
H15 = ('<html><head><title>t</title></head><body>'
       "<script>document.querySelector('form').addEventListener('submit',"
       "function(e){e.preventDefault();el.setCustomValidity('bad')})</script>"
       '<form><input type="email" required></form></body></html>')
r15 = autofix(H15)
assert not any(a['signal'] == 'form_error_missing' for a in r15['applied']), r15['applied']
assert 'a11yfx-err' not in r15['fixed_html']
print('15. guard 3.3.1 sobre scripts reales: setCustomValidity propio se respeta ✓')

# 16. la apertura de <form> respeta comillas: un `>` dentro de action= no
#     cierra el tag (el prefijo ingenuo mutilaba la URL)
r16 = autofix('<html><body><form action="/search?q=a>b">'
              '<input type="email" required></form></body></html>')
assert 'action="/search?q=a>b"' in r16['fixed_html'], r16['fixed_html']
assert '<form action="/search?q=a>b" data-a11yfx>' in r16['fixed_html']
# hostil: un block que ACABA dentro de una cita (action="x</form>") no es
# delimitable con apertura quote-aware — se deja intacto, jamás caer
r16b = autofix('<html><body><form action="x</form>">'
               '<input type="email" required></form></body></html>')
assert 'data-a11yfx' not in r16b['fixed_html']
print('16. <form action="…a>b"> quote-aware: la URL sobrevive byte a byte ✓')

# 17. textarea con `>` citado en un atributo: contenido intacto, capa tras el
#     cierre y sin fragmento suelto del opening ingenuo
r17 = autofix('<form><textarea required placeholder="Use > 8 chars">x</textarea></form>')
assert '>x</textarea>' in r17['fixed_html'], r17['fixed_html']
assert '> 8 chars">' not in r17['fixed_html'], r17['fixed_html']   # fragmento del opening ingenuo
assert re.search(r'</textarea>\n<p class="a11yfx-err"', r17['fixed_html'])
print('17. textarea con ">" citado: contenido intacto, capa tras el cierre ✓')

# 18. autocomplete tras autocierre: la barra no es un atributo; y un value
#     citado que ACABA en / es dato, nunca markup
tag_a = re.search(r'<input[^>]*>', autofix('<form><input type="email" required></form>')['fixed_html']).group(0)
tag_b = re.search(r'<input[^>]*>', autofix('<form><input type="email"/></form>')['fixed_html']).group(0)
assert 'autocomplete="email"' in tag_a and '/ autocomplete' not in tag_a
assert 'autocomplete="email"' in tag_b and '/ autocomplete' not in tag_b, tag_b
r18c = autofix('<form><input type="email" value="a/" required></form>')
assert 'value="a/"' in r18c['fixed_html'] and 'autocomplete="email"' in r18c['fixed_html']
print('18. autocierre y value="a/": el token entra sin romper el tag ✓')

# 19. viewport fantasma: maximum-scale=5 NO bloquea el zoom — no hay fix;
#     maximum-scale<2 sí se quita y se registra
r19a = autofix('<html><head><meta name="viewport" content="width=device-width, maximum-scale=5">'
               '<title>t</title></head><body>x</body></html>')
assert not any(a['signal'] == 'zoom_no' for a in r19a['applied']), r19a['applied']
assert 'maximum-scale=5' in r19a['fixed_html']
r19b = autofix('<html><head><meta name="viewport" content="width=device-width, maximum-scale=1">'
               '<title>t</title></head><body>x</body></html>')
assert any(a['signal'] == 'zoom_no' for a in r19b['applied'])
print('19. viewport: maximum-scale=5 sin fix fantasma; <2 sigue arreglándose ✓')

# 20. lang es el ATRIBUTO lang: xml:lang= / lang="" no cumplían 3.1.1 y el
#     test de sucadena los daba por buenos; lang="es" no se toca
r20a = autofix('<html xml:lang="es"><body>x</body></html>', lang='en')
r20b = autofix('<html lang=""><body>x</body></html>', lang='en')
r20c = autofix('<html lang="es"><body>x</body></html>', lang='en')
assert any(a['signal'] == 'lang_missing' for a in r20a['applied'])
assert '<html lang="en" xml:lang="es">' in r20a['fixed_html']
assert any(a['signal'] == 'lang_missing' for a in r20b['applied'])
assert '<html lang="en">' in r20b['fixed_html']       # se RELLENA, no se duplica
assert r20b['fixed_html'].count('lang=') == 1
assert not any(a['signal'] == 'lang_missing' for a in r20c['applied'])
print('20. lang real (no subcadena): xml:lang y lang="" arreglados; lang="es" no ✓')

# 21. hint tel con límite de palabra: "hotel"/"intel" NO son campos tel
r21a = autofix('<form><input type="text" name="hotel"></form>')
r21b = autofix('<form><input type="text" name="tel"></form>')
assert 'autocomplete="tel"' not in r21a['fixed_html'], r21a['fixed_html']
assert 'autocomplete="tel"' in r21b['fixed_html']
assert 'autocomplete="tel"' in autofix('<form><input type="text" name="telefono"></form>')['fixed_html']
assert 'autocomplete="tel"' in autofix('<form><input type="text" name="phone"></form>')['fixed_html']
print('21. hint tel con \\btel\\b: hotel NO; tel/telefono/phone SÍ ✓')

# 22. </BODY> mayúscula: el JS de la capa se inyecta igual — antes se perdía
#     y `applied` seguía declarando form_error_missing (ids colgantes)
H22 = ('<html><head><title>t</title></head><body>'
       '<form><input type="email" required></form></BODY></html>')
r22 = autofix(H22)
cuerpo22 = r22['fixed_html'].rsplit('</BODY>', 1)[0]
assert any(a['signal'] == 'form_error_missing' for a in r22['applied'])
assert 'noValidate' in cuerpo22 and 'data-a11yfx-err' in cuerpo22
print('22. inyección de la capa case-insensitive: </BODY> también la recibe ✓')

print('REVISIÓN EXTERNA — RONDA 3: CONFIRMADO, CORREGIDO Y FIJADO ✓')
print('REVISIÓN EXTERNA — RONDA 2: CONFIRMADO, CORREGIDO Y FIJADO ✓')
print('REVISIÓN EXTERNA 2026-10: TODOS LOS CASOS CONFIRMADOS, CORREGIDOS Y PINNED ✓')
