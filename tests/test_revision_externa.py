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

# 4. parse_color: sintaxis moderna con '/' y canales negativos acotados
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
print('6. evidence respeta rejected ✓ (1.4.3 →', row['status'] + ')')

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

# 11. viewport: eliminar el meta respeta comillas al buscar el cierre
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
assert 'ratioOf(over_(fg, bg), bg)' in src_dom, 'el pase principal no compone el alfa del text'
# y la definición de over_ precede a su uso en el mismo block
i_over = src_dom.index('const over_ =')
i_use = src_dom.index('ratioOf(over_(fg, bg), bg)')
assert i_over < i_use
print('13. pase principal: alfa del text compuesto (over_ before del uso) ✓')

print('REVISIÓN EXTERNA — RONDA 2: CONFIRMADO, CORREGIDO Y FIJADO ✓')
print('REVISIÓN EXTERNA 2026-10: TODOS LOS CASOS CONFIRMADOS, CORREGIDOS Y PINNED ✓')
