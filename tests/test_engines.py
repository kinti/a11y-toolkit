#!/usr/bin/env python3
"""a11y_engines — cross-engine behavioral matrix. Hermetic: the engine capture
is injected, so no browser launches here (the live path is one CLI call in
test_dom-tier suites). Focus: pairwise divergence, honest engine failures,
insufficient-engine semantics, tree-as-informational."""
import io
import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from a11y_toolkit.a11yengines import matrix, ENGINES, DEFAULT_ENGINES  # noqa: E402
from a11y_toolkit.a11ydiff import snapshot as real_snapshot  # noqa: E402

BASE = [{'key': '#pay', 'tag': 'button', 'name': 'Pay', 'role': 'button'},
        {'key': 'a:Home:/home', 'tag': 'a', 'name': 'Home', 'role': 'link'}]
ORDER = ['#pay', 'a:Home:/home']


def snap(els=None, order=None):
    return {'url': 'https://web', 'elements': els if els is not None else BASE,
            'focus_order': order if order is not None else ORDER}


# --- 0. engine param landed on the real snapshot signature ---
import inspect  # noqa: E402
assert 'engine' in inspect.signature(real_snapshot).parameters
assert DEFAULT_ENGINES == ('chromium', 'firefox', 'webkit')
assert set(DEFAULT_ENGINES) <= set(ENGINES) <= {'chromium', 'firefox', 'webkit', 'chrome', 'msedge'}
print('0. snapshot(engine=) exists; engine registry sane ✓')


def divergent(url, engine, auth_state=None):
    if engine == 'webkit':
        raise Exception('engine executable missing')
    if engine == 'firefox':  # firefox shows an extra control: behavioral divergence
        return snap(BASE + [{'key': '#xtra', 'tag': 'button', 'name': 'Xtra', 'role': 'button'}],
                    ORDER + ['#xtra'])
    return snap()


# --- 1. divergence between engines is caught and pinned to the pair ---
r = matrix('https://web', capture=divergent)
assert [e['engine'] for e in r['engines_ok']] == ['chromium', 'firefox']
assert r['engines_failed'] and r['engines_failed'][0]['engine'] == 'webkit'
assert r['engines_failed'][0]['error']
assert len(r['pairs']) == 1 and not r['pairs'][0]['ok']
assert r['pairs'][0]['engines'] == ['chromium', 'firefox']
assert r['pairs'][0]['added'] == ['#xtra']
assert not r['ok'] and len(r['divergences']) == 1 and not r['insufficient_engines']
assert r['mode'] == 'engines' and r['url'] == 'https://web'
print('1. behavioral divergence caught, tagged with the pair ✓')

# --- 2. identical engines → clean matrix ---
r = matrix('https://web', capture=lambda url, engine, auth_state=None: snap())
assert r['ok'] and not r['divergences'] and len(r['pairs']) == 3
assert all(p['ok'] for p in r['pairs'])
print('2. identical behavior across 3 engines → ok ✓')

# --- 3. focus-order fork is a divergence even with identical element sets ---
def fork(url, engine, auth_state=None):
    return snap(order=list(reversed(ORDER))) if engine == 'firefox' else snap()

r = matrix('https://web', capture=fork)
assert not r['ok'] and r['pairs'][0]['focus']['reordered'] is True
assert not r['pairs'][0]['added'] and not r['pairs'][0]['removed']
print('3. focus-order fork detected without element churn ✓')

# --- 4. fewer than 2 engines → honest insufficient, never a fake pass ---
r = matrix('https://web', capture=lambda url, engine, auth_state=None:
           snap() if engine == 'chromium' else (_ for _ in ()).throw(Exception('dead')))
assert r['insufficient_engines'] and not r['ok'] and 'note' in r
assert r['pairs'] == []
print('4. single engine → insufficient_engines + note ✓')

# --- 5. unknown engine names are reported, not silently dropped ---
r = matrix('https://web', engines=['chromium', 'bogus'],
           capture=lambda url, engine, auth_state=None: snap())
errs = {f['engine']: f['error'] for f in r['engines_failed']}
assert 'bogus' in errs and 'unknown engine' in errs['bogus']
print('5. unknown engine reported ✓')

# --- 6. accessibility-tree divergence is informational, NEVER blocks ---
def tree_shift(url, engine, auth_state=None):
    s = snap()
    s['arbol_accesible'] = '- heading [level=1]\n  engine: ' + engine
    return s

r = matrix('https://web', capture=tree_shift)
assert r['ok'] and not r['divergences']
assert all(p['tree_changed'] for p in r['pairs'])
assert r['limits'] and 'informational' in r['limits']
print('6. tree divergence informational ✓')

# --- 7. report shape: required keys always present ---
for key in ('mode', 'url', 'ts', 'engines_ok', 'engines_failed', 'pairs',
            'divergences', 'ok', 'insufficient_engines', 'limits'):
    assert key in r, key
print('7. report shape complete ✓')

# --- 8. CLI exit codes: insufficient engines → 1 (works without Playwright too) ---
from a11y_toolkit.a11yengines import main as engines_main  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    code = engines_main(['https://web', '--engines', 'bogus'])  # nothing launches → insufficient
assert code == 1, code
print('8. CLI: insufficient engines → exit 1 ✓')

print('OK test_engines: 9 checks')
