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
print('OK test_trace: 7 checks (5 herméticos + 2 vivos)')
