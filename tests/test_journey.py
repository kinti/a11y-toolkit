#!/usr/bin/env python3
"""Blindfold journey tests: deterministic scoring, catalogue parity,
criterion validation and evidence-pack integration."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from a11y_toolkit.a11yjourney import verdictar, _J  # noqa: E402
from a11y_toolkit.a11yevidence import empaquetar  # noqa: E402

TAREA = {'goal': 'sign up for the newsletter', 'kind': 'sign-up'}
URL = 'https://shop.example'


# 1. clean pass: completed, no friction, no workaround
r = verdictar(TAREA, [
    {'action': 'click', 'target': 'Subscribe', 'perceived': 'button, "Subscribe"'},
    {'action': 'type', 'target': 'Email', 'perceived': 'textbox, "Email"'},
], {'completed': True}, url=URL)
assert r['verdict'] == 'pass' and r['score'] == 100 and not r['findings'], r
print('1. pase limpio 100/100 ✓')

# 2. unnamed control (high) → partial even completed
r2 = verdictar(TAREA, [
    {'action': 'click', 'target': 'button', 'perceived': 'button',
     'friction': {'pattern': 'journey_unnamed_control'}},
], {'completed': True}, url=URL)
assert r2['verdict'] == 'partial' and r2['score'] == 75, r2
assert r2['findings'][0]['criterion'] == '4.1.2'
assert r2['findings'][0]['severity'] == 'high'
assert r2['summary'] == {'high': 1, 'medium': 0, 'low': 0}
print('2. control sin nombre → parcial 75 ✓')

# 3. gave_up → blocked (aun con score alto)
r3 = verdictar(TAREA, [
    {'action': 'read', 'perceived': 'nothing announces the form',
     'friction': {'pattern': 'journey_hidden_in_tree'}},
], {'completed': False, 'gave_up': True}, url=URL)
assert r3['verdict'] == 'blocked' and r3['outcome']['gave_up'] is True, r3
print('3. gave_up → blocked ✓')

# 4. not completed sin gave_up → fail
r4 = verdictar(TAREA, [
    {'action': 'click', 'target': 'Submit', 'perceived': 'nothing happened',
     'friction': {'pattern': 'journey_error_silent'}},
], {'completed': False}, url=URL)
assert r4['verdict'] == 'fail' and r4['score'] == 75, r4
print('4. no completada → fail ✓')

# 5. workaround penaliza y tira del pass al partial
base = verdictar(TAREA, [], {'completed': True})
rw = verdictar(TAREA, [], {'completed': True, 'workaround_used': True})
assert base['verdict'] == 'pass' and rw['verdict'] == 'partial' and rw['score'] == 85
assert 'workaround_penalty' in rw['rules']
print('5. workaround → parcial 85 ✓')

# 6. criterios fuera del conjunto A/AA rechazados; severidad inválida rechazada
bad = verdictar(TAREA, [
    {'action': 'x', 'friction': {'criterion': '2.3.2', 'severity': 'high', 'issue': 'x'}},
    {'action': 'y', 'friction': {'criterion': '1.4.3', 'severity': 'muy', 'issue': 'x'}},
    {'action': 'z', 'friction': {'pattern': 'no_existe'}},
], {'completed': True}, url=URL)
assert 'error' in bad and len(bad['detalles']) == 3, bad
assert 'fuera del conjunto A/AA' in bad['detalles'][0]
print('6. validación de criterio/severidad/patrón ✓')

# 7. patrón de catálogo: criterio+issue+remediation coherentes bilingüe
r7 = verdictar(TAREA, [
    {'action': 'key', 'perceived': 'dialog', 'friction': {'pattern': 'journey_dialog_trap'}},
], {'completed': True, 'notes': 'escaped eventually'}, url=URL)
f = r7['findings'][0]
assert f['criterion'] == '2.1.2' and f['signal'] == 'journey_dialog_trap'
assert 'Escape' in f['remediation']
assert f['step'] == 0 and 'dialog' in (f.get('perceived') or '')
print('7. catálogo journey_dialog_trap ✓')

# 8. integración con el evidence pack: report:journey + matrix fail
pack = empaquetar([r2])
arts = [a['type'] for a in pack['artifacts']]
assert 'report:journey' in arts, arts
row = next(m for m in pack['criteria'] if m['criterion'].startswith('4.1.2'))
assert row['status'] == 'automated-fail', row
print('8. evidence pack integra report:journey ✓ (4.1.2 → automated-fail)')

# 9. paridad es/en del catálogo J: mismas claves, mismo criterio y severidad
es, en = _J['es'], _J['en']
assert set(es) == set(en), f'catálogo J desparejo: {sorted(set(es) ^ set(en))}'
for k in es:
    assert es[k][0] == en[k][0] and es[k][1] == en[k][1], f'{k}: criterio/severidad divergen'
    assert es[k][2] and en[k][2] and es[k][3] and en[k][3], f'{k}: texto vacío'
assert all(k.startswith('journey_') for k in es)
print(f'9. catálogo J parejo ({len(es)} patrones) ✓')

# 10. CLI end-to-end (la vía pública real)
log = os.path.join('/tmp', 'journey_log.json')
with open(log, 'w') as fh:
    json.dump({'task': TAREA, 'steps': [
        {'action': 'click', 'target': 'Submit', 'perceived': 'button',
         'friction': {'pattern': 'journey_focus_lost'}}],
        'outcome': {'completed': True}, 'url': URL}, fh)
out = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11yjourney', log],
                     capture_output=True, text=True, cwd=ROOT, timeout=30)
d = json.loads(out.stdout)
assert d['verdict'] == 'partial' and d['score'] == 75, d
out2 = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y', 'journey', log],
                      capture_output=True, text=True, cwd=ROOT, timeout=30)
d2 = json.loads(out2.stdout)
assert d2['verdict'] == 'partial' and d2['findings'][0]['criterion'] == '2.4.3'
print('10. CLI -m módulo y dispatcher ✓')

print('JOURNEY OK ✓ (scoring determinista, catálogo parejo, criterios validados, pack integra, CLI real)')
