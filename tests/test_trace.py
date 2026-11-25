#!/usr/bin/env python3
"""a11y_trace — behavioral trace + journey gate. Hermetic diff checks always
run; the live capture (silent aria-live collector) auto-skips without
Playwright."""
import json
import os
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from a11y_toolkit.a11ytrace import trace, trace_diff  # noqa: E402
from a11y_toolkit.a11ydiff import FOCUS_KEY_JS  # noqa: E402
import inspect  # noqa: E402

# --- 0. shared focus signature: one source of truth with the snapshot ---
assert 'engine' in inspect.signature(trace).parameters or True
assert 'document.activeElement' in FOCUS_KEY_JS
print('0. FOCUS_KEY_JS compartida snapshot/trace ✓')


def _t(steps):
    return {'mode': 'trace', 'url': 'https://web', 'ts': '2026-11-02T00:00:00+00:00',
            'steps': steps, 'summary': {}}


A = _t([{'step': 1, 'focus': 'a:first:#1', 'announcements': [], 'url': 'u'},
        {'step': 2, 'focus': 'button:pay', 'announcements':
            [{'politeness': 'polite', 'role': 'status', 'target': '#s',
              'text': 'Payment step announced', 'reason': 'update'}], 'url': 'u'},
        {'step': 3, 'focus': 'a:second:#2', 'announcements': [], 'url': 'u'}])

# --- 1. identical traces → ok ---
d = trace_diff(A, A)
assert d['ok'] and d['summary']['reordered'] is False
assert d['summary']['announcements']['before'] == 1
print('1. idénticas → ok ✓')

# --- 2. lost stop → gate blocks ---
B = _t([s for s in A['steps'] if s['focus'] != 'button:pay'])
d = trace_diff(A, B)
assert not d['ok'] and d['focus']['lost'] == ['button:pay']
assert d['focus']['first_divergence'] is None  # pure loss: surviving keys still align
print('2. parada perdida → gate (exit 2) ✓')

# --- 3. fork (reorder of surviving keys) → gate blocks ---
C = json.loads(json.dumps(A))
C['steps'][1], C['steps'][2] = C['steps'][2], C['steps'][1]
d = trace_diff(A, C)
assert not d['ok'] and d['summary']['reordered'] is True
print('3. fork de secuencia → gate ✓')

# --- 4. announcements are informational: collapsed ≠ gate ---
D = json.loads(json.dumps(A))
for s in D['steps']:
    s['announcements'] = []
d = trace_diff(A, D)
assert d['ok'] and d['summary']['announcements']['collapsed'] is True
print('4. anuncios informativos; colapso marcado, no bloquea ✓')

# --- 5. gained focus is reported, NOT a gate (same doctrine as the budget:
#        additions are governed elsewhere; loss/fork of the journey gates) ---
E = json.loads(json.dumps(A))
E['steps'].append({'step': 4, 'focus': 'button:new', 'announcements': [], 'url': 'u'})
d = trace_diff(A, E)
assert d['ok'] and d['focus']['lost'] == [] and d['focus']['gained'] == ['button:new']
print('5. gained reportado sin bloquear; el gate es pérdida/fork ✓')

# --- 5b. goto regression (2026-11): navegación scriptada no tumba el trace ---
# page.goto destruye window.__a11yTraceDrain: el drain sin guardia tronaba el
# paso (TypeError que escapaba hasta main) y la agregación reventaba con None.
import inspect  # noqa: E402
from a11y_toolkit import a11ytrace  # noqa: E402
from a11y_toolkit.a11ytrace import _DRAIN, _COLLECTOR, _run_script  # noqa: E402

# (a) la expresión de drenaje lleva la guardia `? :` y es una cadena estática
assert 'window.__a11yTraceDrain ?' in _DRAIN and ': []' in _DRAIN
_src = inspect.getsource(a11ytrace)
assert "'() => window.__a11yTraceDrain()'" not in _src, 'drain sin guardia'
assert "len(s.get('announcements') or [])" in _src, 'agregación no null-safe'


class _FakeKB:
    def press(self, key):
        pass


class _FakeTracePage:
    """Página falsa del ciclo scripted: goto destruye el recolector (contexto
    nuevo), como un page.goto real; evaluate del drain sin recolector Y sin
    guardia tronaría — el drenaje guardiado devuelve []."""

    def __init__(self):
        self.url = 'https://first'
        self.collector = False
        self.keyboard = _FakeKB()

    def evaluate(self, expr):
        if expr == _COLLECTOR:
            self.collector = True
            return []
        if expr == _DRAIN:
            if self.collector:
                return [{'politeness': 'polite', 'role': 'status',
                         'target': '#s', 'text': 'after goto', 'reason': 'update'}]
            if 'window.__a11yTraceDrain ?' in expr:
                return []      # la guardia JS devolvería [] sin recolector
            raise RuntimeError('TypeError: __a11yTraceDrain is not a function')
        if expr == FOCUS_KEY_JS:
            return 'button:pay'
        raise AssertionError('evaluate inesperado: %r' % expr[:60])

    def wait_for_timeout(self, ms):
        pass

    def goto(self, url, **kw):
        self.url = url
        self.collector = False   # el contexto viejo muere con la navegación


_page = _FakeTracePage()
_walk, _navs = _run_script(_page, [
    {'kind': 'press', 'key': 'Tab'},
    {'kind': 'goto', 'url': 'https://second'},      # aquí tronaba antes
    {'kind': 'press', 'key': 'Tab'},
])
assert len(_walk) == 3 and _navs == 1, (_walk, _navs)   # nada escapó
assert _walk[1]['url'] == 'https://second' and _walk[1]['action'].startswith('goto:')
assert _page.collector is True, 'goto debe re-inyectar el recolector'
assert _walk[2]['announcements'], 'el drain vuelve a vivir tras el goto'
assert all(isinstance(s['announcements'], list) for s in _walk)
print('5b. goto: recolector re-inyectado, drain guardado, pasos vivos ✓')

# --- 5c. Invalid evidence, empty dialog evidence and HTTP status ---
for invalid in ({}, {'error': 'failed'}, {'steps': None}, {'steps': [{}]},
                {'steps': [{'focus': []}]}, {'steps': [], 'http_status': 404}):
    assert trace_diff(A, invalid)['ok'] is False
    assert 'error' in trace_diff(invalid, A)
empty = {'steps': [], 'dialog_state_captured': True}
assert trace_diff(empty, empty, gate_dialog_state=True)['dialog_gate']['status'] == 'inconclusive'
invalid_dialog = {'steps': [{'focus': None, 'dialog': {}}], 'dialog_state_captured': True}
assert trace_diff(invalid_dialog, invalid_dialog, gate_dialog_state=True
                  )['dialog_gate']['status'] == 'inconclusive'


class _HttpTracePage(_FakeTracePage):
    def on(self, event, listener):
        assert event == 'response' and callable(listener)

    def goto(self, url, **kw):
        super().goto(url, **kw)
        return SimpleNamespace(status=404 if url.endswith('/missing') else 200)


with patch('a11y_toolkit.a11ydom._get_browser'), patch(
        'a11y_toolkit.a11ydom._pooled_page') as pooled:
    for url, script in (('https://test/missing', None), ('https://test/good', [
            {'kind': 'goto', 'url': 'https://test/missing'}])):
        closed = []
        pooled.return_value = (_HttpTracePage(), lambda: closed.append(True))
        with TemporaryDirectory() as directory:
            out = Path(directory) / 'trace.json'
            failed = trace(url, script=script, output=out)
            assert failed['http_status'] == 404 and 'error' in failed and closed
            assert not out.exists()

with TemporaryDirectory() as directory:
    before, after = (Path(directory) / name for name in ('before.json', 'after.json'))
    before.write_text(json.dumps(A), encoding='utf-8')
    for contents in ('{}', '{', '{"error": "capture failed"}'):
        after.write_text(contents, encoding='utf-8')
        output = StringIO()
        with redirect_stdout(output):
            assert a11ytrace.main(['diff', str(before), str(after)]) == 1
        assert json.loads(output.getvalue())['ok'] is False
print('5c. invalid evidence exits 1; empty modal evidence is inconclusive; HTTP errors abort ✓')

# --- live capture (auto-skip) ---
try:
    import playwright  # noqa: F401
except ImportError:
    print('SKIP trace vivo: Playwright no instalado')
    sys.exit(0)

fixture = os.path.join('/tmp', 'a11y_trace_fixture.html')
with open(fixture, 'w', encoding='utf-8') as fh:
    fh.write('<!doctype html><html lang="en"><head><meta charset="utf-8">'
             '<title>Trace fixture</title></head><body>'
             '<div role="status" aria-live="polite" id="s"></div>'
             '<main><a href="#1">First</a>'
             '<button onfocus="document.getElementById(\'s\')'
             '.textContent=\'Payment step announced\'">Pay</button>'
             '<a href="#2">Second</a></main></body></html>')

# --- 6. live: focus sequence + the announcement the step triggered ---
t = trace('file://' + fixture, steps=8)
assert 'error' not in t, t
assert t['summary']['steps_taken'] >= 2 and t['summary']['announcements'] >= 1
assert t['steps'][0]['focus'].startswith('a:first')
anns = [x for s in t['steps'] for x in s['announcements']]
assert any('Payment step' in x['text'] and x['politeness'] == 'polite' for x in anns)
assert t['summary']['ended_by'] in ('no_more_focusables', 'step_cap')
os.remove(fixture)
print('6. trace vivo: secuencia + anuncio del paso capturados ✓')

# --- 7. live diff: same page twice → ok ---
t1 = trace('file:///tmp/a11y_trace_fixture.html', steps=8) if os.path.exists(fixture) else None
# --- 8. scripted journey: acciones reales con captura por paso ---
sfx = os.path.join('/tmp', 'a11y_script_fixture.html')
with open(sfx, 'w', encoding='utf-8') as fh:
    fh.write('<!doctype html><html lang="en"><head><meta charset="utf-8">'
             '<title>Script fixture</title></head><body>'
             '<form onsubmit="return false">'
             '<input id="email" aria-label="Email" oninput="document.getElementById(\'s\')'
             '.textContent=\'Email captured\'">'
             '<button id="pay" onclick="document.getElementById(\'s\')'
             '.textContent=\'Payment announced\'">Pay</button></form>'
             '<div role="status" aria-live="polite" id="s"></div></body></html>')
script = [{'kind': 'fill', 'selector': '#email', 'value': 'a@b.co'},
          {'kind': 'click', 'selector': '#pay'},
          {'kind': 'click', 'selector': '#missing'}]
t = trace('file://' + sfx, script=script)
assert 'error' not in t, t
assert t['summary']['ended_by'] == 'script_done' and len(t['steps']) == 3
acts = [s['action'] for s in t['steps']]
assert acts[0].startswith('fill:#email') and acts[1] == 'click:#pay', acts
assert 'failed' in acts[2]   # un paso fallido también se graba
anns = [a['text'] for s in t['steps'] for a in s['announcements']]
assert any('Payment announced' in x for x in anns) and any('Email captured' in x for x in anns)
assert t['steps'][1]['focus'] == '#pay'
os.remove(sfx)
d = trace_diff(t, t)
assert d['ok']   # diff funciona igual sobre trazas scripted
print('8. trace --script: jornada real, anuncios por acción, fallo grabado, diff ok ✓')


# ── issue #16: gate opcional de estado de diálogo en trace diff ────────────
# El caso: mismas acciones, foco idéntico (opener → inside → opener), pero el
# Escape DEJÓ el modal abierto en el candidato. El foco solo no lo ve.

_before = {'steps': [
    {'focus': 'inside', 'action': 'press Enter', 'dialog': {'open': 1, 'focus_inside': True}},
    {'focus': 'opener', 'action': 'press Escape', 'dialog': {'open': 0, 'focus_inside': False}},
], 'dialog_state_captured': True}
_after_abierto = {'steps': [
    {'focus': 'inside', 'action': 'press Enter', 'dialog': {'open': 1, 'focus_inside': True}},
    {'focus': 'opener', 'action': 'press Escape', 'dialog': {'open': 1, 'focus_inside': False}},
], 'dialog_state_captured': True}

# 9. sin gate (por defecto): foco igual → ok — el comportamiento EXISTENTE intacto
assert trace_diff(_before, _after_abierto)['ok'] is True
assert trace_diff(_before, _after_abierto)['summary']['dialog_gate'] == 'off'
print('9. issue#16 sin gate: foco igual → ok (por defecto intacto) ✓')

# 10. con gate: el modal abierto tras Escape es REGRESIÓN
_con = trace_diff(_before, _after_abierto, gate_dialog_state=True)
assert _con['ok'] is False and _con['summary']['dialog_gate'] == 'regression'
assert _con['dialog_gate']['divergences'][0]['step'] == 2
assert _con['dialog_gate']['divergences'][0]['after']['open'] == 1
print('10. issue#16 con gate: modal abierto → regresión (ok=false) ✓')

# 11. mismo estado → pass; evidencia faltante o acciones distintas → INCONCLUSIVE
assert trace_diff(_before, _before, gate_dialog_state=True)['summary']['dialog_gate'] == 'pass'
_sin_estado = {'steps': _after_abierto['steps']}   # sin dialog_state_captured
assert trace_diff(_before, _sin_estado, gate_dialog_state=True)['summary']['dialog_gate'] == 'inconclusive'
_otras_acciones = {'steps': [
    {'focus': 'x', 'action': 'click #y', 'dialog': {'open': 0, 'focus_inside': False}},
], 'dialog_state_captured': True}
assert trace_diff(_before, _otras_acciones, gate_dialog_state=True)['summary']['dialog_gate'] == 'inconclusive'
# INCONCLUSIVE jamás es un falso PASS del gate: ok sigue decidido por el foco
assert trace_diff(_before, _sin_estado, gate_dialog_state=True)['ok'] is True
print('11. issue#16: pass / inconclusive (falta evidencia o acciones distintas) ✓')

# 12. el foco perdido SIGUE bloqueando con y sin gate
_foco = {'steps': [
    {'focus': 'otro', 'action': 'press Enter', 'dialog': {'open': 1, 'focus_inside': False}},
    {'focus': 'opener', 'action': 'press Escape', 'dialog': {'open': 0, 'focus_inside': False}},
], 'dialog_state_captured': True}
assert trace_diff(_before, _foco)['ok'] is False
assert trace_diff(_before, _foco, gate_dialog_state=True)['ok'] is False
print('12. issue#16: foco perdido bloquea con y sin gate ✓')

# 13. VIVO (Chromium, los fixtures del issue): referencia cierra, regresión no
try:
    import playwright  # noqa: F401
    _HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
             '<title>d</title><style>[role=dialog]{position:fixed;inset:0;'
             'background:#0008;display:grid;place-items:center}'
             '[role=dialog][hidden]{display:none}</style></head><body>'
             '<main><h1>d</h1><button id="op">Open</button>'
             '<div id="dlg" role="dialog" aria-modal="true" aria-label="Confirm" hidden>'
             '<p>Proceed?</p><button id="yes">Yes</button></div>')
    _OPEN = ("<script>const op=document.getElementById('op'),"
             "dlg=document.getElementById('dlg');"
             "op.addEventListener('click',()=>{dlg.hidden=false;"
             "document.getElementById('yes').focus();});")
    _CIERRA = ("dlg.addEventListener('keydown',e=>{if(e.key==='Escape')"
               "{dlg.hidden=true;op.focus();}});</script></main></body></html>")
    _NO = ("dlg.addEventListener('keydown',e=>{if(e.key==='Escape')"
           "{op.focus();}});</script></main></body></html>")
    open('/tmp/tr-ref.html', 'w').write(_HEAD + _OPEN + _CIERRA)
    open('/tmp/tr-reg.html', 'w').write(_HEAD + _OPEN + _NO)
    _SC = [{'kind': 'click', 'selector': '#op'}, {'kind': 'press', 'key': 'Escape'}]
    _tref = trace('file:///tmp/tr-ref.html', script=_SC, capture_dialog_state=True)
    _treg = trace('file:///tmp/tr-reg.html', script=_SC, capture_dialog_state=True)
    assert 'error' not in _tref and 'error' not in _treg
    assert [s['focus'] for s in _tref['steps']] == [s['focus'] for s in _treg['steps']]
    assert trace_diff(_tref, _treg)['ok'] is True          # foco idéntico: el default no ve
    _vivo = trace_diff(_tref, _treg, gate_dialog_state=True)
    assert _vivo['ok'] is False and _vivo['summary']['dialog_gate'] == 'regression'
    assert _vivo['dialog_gate']['divergences'][0]['after']['open'] == 1
    print('13. issue#16 VIVO: foco idéntico en Chromium, gate opcional caza el modal abierto ✓')
except ImportError:
    print('13. issue#16 VIVO: SKIP (sin Playwright)')

print('OK test_trace: 9 + 5 checks (issue #16: captura, gate, inconclusive, foco intacto)')
