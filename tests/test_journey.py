#!/usr/bin/env python3
"""Blindfold journey tests: deterministic scoring, catalogue parity,
criterion validation and evidence-pack integration."""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from a11y_toolkit.a11yjourney import verdict, _J  # noqa: E402
from a11y_toolkit.a11yevidence import build_pack  # noqa: E402

TAREA = {'goal': 'sign up for the newsletter', 'kind': 'sign-up'}
URL = 'https://shop.example'


# 1. clean pass: completed, no friction, no workaround
r = verdict(TAREA, [
    {'action': 'click', 'target': 'Subscribe', 'perceived': 'button, "Subscribe"'},
    {'action': 'type', 'target': 'Email', 'perceived': 'textbox, "Email"'},
], {'completed': True}, url=URL)
assert r['verdict'] == 'pass' and r['score'] == 100 and not r['findings'], r
print('1. pase limpio 100/100 ✓')

# 2. unnamed control (high) → partial even completed
r2 = verdict(TAREA, [
    {'action': 'click', 'target': 'button', 'perceived': 'button',
     'friction': {'pattern': 'journey_unnamed_control'}},
], {'completed': True}, url=URL)
assert r2['verdict'] == 'partial' and r2['score'] == 75, r2
assert r2['findings'][0]['criterion'] == '4.1.2'
assert r2['findings'][0]['severity'] == 'high'
assert r2['summary'] == {'high': 1, 'medium': 0, 'low': 0}
print('2. control sin name → parcial 75 ✓')

# 3. gave_up → blocked (aun con score alto)
r3 = verdict(TAREA, [
    {'action': 'read', 'perceived': 'nothing announces the form',
     'friction': {'pattern': 'journey_hidden_in_tree'}},
], {'completed': False, 'gave_up': True}, url=URL)
assert r3['verdict'] == 'blocked' and r3['outcome']['gave_up'] is True, r3
print('3. gave_up → blocked ✓')

# 4. not completed sin gave_up → fail
r4 = verdict(TAREA, [
    {'action': 'click', 'target': 'Submit', 'perceived': 'nothing happened',
     'friction': {'pattern': 'journey_error_silent'}},
], {'completed': False}, url=URL)
assert r4['verdict'] == 'fail' and r4['score'] == 75, r4
print('4. no completada → fail ✓')

# 5. workaround penaliza y tira del pass al partial
base = verdict(TAREA, [], {'completed': True})
rw = verdict(TAREA, [], {'completed': True, 'workaround_used': True})
assert base['verdict'] == 'pass' and rw['verdict'] == 'partial' and rw['score'] == 85
assert 'workaround_penalty' in rw['rules']
print('5. workaround → parcial 85 ✓')

# 6. criterios removed del conjunto A/AA rechazados; severidad inválida rechazada
bad = verdict(TAREA, [
    {'action': 'x', 'friction': {'criterion': '2.3.2', 'severity': 'high', 'issue': 'x'}},
    {'action': 'y', 'friction': {'criterion': '1.4.3', 'severity': 'muy', 'issue': 'x'}},
    {'action': 'z', 'friction': {'pattern': 'no_existe'}},
], {'completed': True}, url=URL)
assert 'error' in bad and len(bad['details']) == 3, bad
# bilingüe: default en, es explícito (antes el español llegaba al usuario en)
assert "outside the A/AA 2.2 set" in bad['details'][0]
bad_es = verdict(TAREA, [
    {'action': 'x', 'friction': {'criterion': '9.9.9', 'severity': 'high', 'issue': 'x'}},
], {'completed': True}, url=URL, lang='es')
assert 'fuera del conjunto A/AA' in bad_es['details'][0]
print('6. validación de criterion/severidad/patrón ✓')

# 7. patrón de catálogo: criterion+issue+remediation coherentes bilingüe
r7 = verdict(TAREA, [
    {'action': 'key', 'perceived': 'dialog', 'friction': {'pattern': 'journey_dialog_trap'}},
], {'completed': True, 'notes': 'escaped eventually'}, url=URL)
f = r7['findings'][0]
assert f['criterion'] == '2.1.2' and f['signal'] == 'journey_dialog_trap'
assert 'Escape' in f['remediation']
assert f['step'] == 0 and 'dialog' in (f.get('perceived') or '')
print('7. catálogo journey_dialog_trap ✓')

# 8. integración con el evidence pack: report:journey + matrix fail
pack = build_pack([r2])
arts = [a['type'] for a in pack['artifacts']]
assert 'report:journey' in arts, arts
row = next(m for m in pack['criteria'] if m['criterion'].startswith('4.1.2'))
assert row['status'] == 'automated-fail', row
print('8. evidence pack integra report:journey ✓ (4.1.2 → automated-fail)')

# 9. paridad es/en del catálogo J: mismas claves, mismo criterion y severidad
es, en = _J['es'], _J['en']
assert set(es) == set(en), f'catálogo J desparejo: {sorted(set(es) ^ set(en))}'
for k in es:
    assert es[k][0] == en[k][0] and es[k][1] == en[k][1], f'{k}: criterion/severidad divergen'
    assert es[k][2] and en[k][2] and es[k][3] and en[k][3], f'{k}: text vacío'
assert all(k.startswith('journey_') for k in es)
assert {'journey_heading_nav_broken', 'journey_landmark_missing', 'journey_mode_confusion',
        'journey_duplicate_targets', 'journey_dynamic_stale'} <= set(en), 'faltan patrones SR-nativos'
crit = {en[k][0] for k in en}
# derivado del catálogo A/AA, nunca una lista hardcodeada (los patrones nuevos
# del catálogo entran solos: 1.4.4/1.4.10/1.4.13/2.4.7/2.5.7/3.3.3, 11-2026)
from a11y_toolkit.a11ycrit import _C  # noqa: E402
AA22 = {k for k, v in _C.items() if v[0] in ('A', 'AA')}
assert crit <= AA22, crit - AA22
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


# ── presupuesto de journeys: solo la fricción NUEVA bloquea (5.6.0) ──
from a11y_toolkit.a11yjourney import budget_init, budget_compare  # noqa: E402

vb = verdict(TAREA, [{'friction': {'pattern': 'journey_status_silent'}}], {'completed': True}, url=URL)
bb = budget_init(vb)
assert bb['format'] == 'a11y-journey-budget/1'
assert bb['friction'] == ['4.1.3:journey_status_silent']
assert budget_compare(bb, vb)['verdict'] == 'GO'

v_alta = verdict(TAREA, [{'friction': {'pattern': 'journey_status_silent'}},
                           {'friction': {'pattern': 'journey_unnamed_control'}}], {'completed': True}, url=URL)
r_alta = budget_compare(bb, v_alta)
assert r_alta['verdict'] == 'NO-GO' and '4.1.2:journey_unnamed_control' in r_alta['new_blocking']

v_degrada = verdict(TAREA, [{'friction': {'pattern': 'journey_status_silent'}}],
                      {'completed': False, 'gave_up': True}, url=URL)
assert budget_compare(bb, v_degrada)['degraded'] is True

v_media = verdict(TAREA, [{'friction': {'pattern': 'journey_generic_link'}}], {'completed': True}, url=URL)
r_media = budget_compare(bb, v_media)
assert r_media['verdict'] == 'GO' and r_media['new_friction'] and r_media['resolved']

otra = verdict({'goal': 'checkout', 'kind': 'checkout'}, [], {'completed': True})
assert 'error' in budget_compare(bb, otra)
print('11. journey budget: GO/NO-GO/degradación/resueltas/otra-tarea ✓')

# --- 12. fricción 2026-11: 6 patrones nuevos (walk/reflow/zoom/hover/foco/drag) ---
NUEVOS = {'journey_drag_only': '2.5.7', 'journey_error_no_suggestion': '3.3.3',
          'journey_focus_not_visible': '2.4.7', 'journey_hover_only': '1.4.13',
          'journey_reflow_breaks': '1.4.10', 'journey_zoom_blocked': '1.4.4'}
assert all(p in _J['en'] for p in NUEVOS) and all(p in _J['es'] for p in NUEVOS)
for pat, crit in NUEVOS.items():
    v = verdict(TAREA, [{'friction': {'pattern': pat}}], {'completed': True}, url=URL)
    assert v['findings'][0]['criterion'] == crit, (pat, v['findings'][0])
    assert v['findings'][0]['signal'] == pat
    assert v['findings'][0]['remediation']  # bilingual catalog fills it
v_mix = verdict({'goal': 'export data', 'kind': 'data-export'},
                [{'friction': [{'pattern': 'journey_zoom_blocked'},
                               {'pattern': 'journey_reflow_breaks'}]}],
                {'completed': True}, url=URL)
assert {f['criterion'] for f in v_mix['findings']} == {'1.4.4', '1.4.10'}
print('12. fricción nueva: 6 patrones → criterio correcto + remedio bilingüe ✓')
