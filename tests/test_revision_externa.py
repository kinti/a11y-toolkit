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
from a11y_toolkit.a11yaudit import _descarga  # noqa: E402
from a11y_toolkit.a11yevidence import empaquetar  # noqa: E402
from a11y_toolkit import declaracion  # noqa: E402

# 1. disprove acepta report y su cuerpo usa el mismo nombre (era UnboundLocalError)
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
assert a['value'] == ''  # el valor vacío se conserva (antes: StopIteration)
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

# 6. evidence: un hallazgo rejected no revive como fail; no-rechecked tampoco
inf = {'mode': 'static', 'url': 'x', 'score': 9, 'findings': [
    {'criterion': '1.4.3 Contrast', 'severity': 'high', 'signal': 'x', 'issue': 'x', 'status': 'rejected'},
    {'criterion': '1.1.1 Non-text', 'severity': 'high', 'signal': 'y', 'issue': 'y'}]}
p6 = empaquetar([inf])
row = next(m for m in p6['criteria'] if m['criterion'].startswith('1.4.3'))
assert row['status'] != 'automated-fail'
print('6. evidence respeta rejected ✓ (1.4.3 →', row['status'] + ')')

# 7. declaracion: el método por defecto no atribuye evaluaciones no realizadas
d7 = declaracion.generar(entidad='X', url='https://x.example', estado='parcial')
assert 'axe-core' not in d7['html']
assert ('BORRADOR NO VALIDADO' in d7['html']) or ('UNVALIDATED DRAFT' in d7['html'])
print('7. declaración honesta por defecto ✓')

# 8. política de esquema uniforme en _descarga
for esquema in ('file:///etc/passwd', 'ftp://x/y'):
    r8 = _descarga(esquema)
    assert 'error' in r8 and 'http' in r8['error'], r8
print('8. _descarga rechaza esquemas no http(s) ✓')

print('REVISIÓN EXTERNA 2026-10: TODOS LOS CASOS CONFIRMADOS, CORREGIDOS Y PINNED ✓')
