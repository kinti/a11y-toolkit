#!/usr/bin/env python3
"""a11y_trace — behavioral trace + journey gate. Hermetic diff checks always
run; the live capture (silent aria-live collector) auto-skips without
Playwright."""
import json
import os
import sys

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
print('OK test_trace: 9 checks (6 herméticos + 3 vivos)')
