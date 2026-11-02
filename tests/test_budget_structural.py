#!/usr/bin/env python3
"""Structural budget (a11ybudget): the SRE error-budget doctrine applied to
the RENDERED structure — today's structure is accepted, only what is NEW
blocks. Hermetic: snapshots are built inline, no Playwright, no network."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from a11y_toolkit.a11ybudget import init_structural, compare_structural, STRUCTURAL_FORMAT  # noqa: E402

SNAP = {'url': 'https://web', 'elements': [
    {'key': '#pay', 'tag': 'button', 'name': 'Pay', 'role': 'button'},
    {'key': 'a:Home:/home', 'tag': 'a', 'name': 'Home', 'role': 'link'},
], 'focus_order': ['#pay', 'a:Home:/home']}

# --- 1. init: baseline of stable keys, format, defaults ---
base = init_structural(SNAP)
assert base['format'] == STRUCTURAL_FORMAT == 'a11y-budget-structural/1'
assert base['elements'] == ['#pay', 'a:Home:/home']
assert base['focus_order'] == ['#pay', 'a:Home:/home']
assert base['max_new'] == 0 and base['removed_block'] is True
assert base['review_date'] > base['generated'][:10]
print('1. init_structural: format/keys/defaults ✓')

# --- 2. same structure → ok, nothing new ---
v = compare_structural(base, SNAP)
assert v['ok'] and v['added'] == [] and v['removed'] == []
assert v['summary'] == {'baseline': 2, 'current': 2, 'added': 0, 'removed': 0}
assert v['focus_order_changed'] is False and v['focus_pinned'] is True
print('2. unchanged structure passes ✓')

# --- 3. added interactive beyond max_new blocks ---
snap2 = dict(SNAP, elements=SNAP['elements'] + [
    {'key': '#chat', 'tag': 'button', 'name': 'Chat', 'role': 'button'}])
v = compare_structural(base, snap2)
assert not v['ok'] and v['added'] == ['#chat'] and v['removed'] == []
print('3. new interactive blocks (max_new 0) ✓')

# --- 4. within max_new passes ---
tolerant = dict(base, max_new=1)
v = compare_structural(tolerant, snap2)
assert v['ok'] and v['added'] == ['#chat']
print('4. within budget passes ✓')

# --- 5. a LOST baseline element blocks (contradicts the approved baseline) ---
v = compare_structural(tolerant, dict(SNAP, elements=[SNAP['elements'][0]]))
assert not v['ok'] and v['removed'] == ['a:Home:/home']
print('5. lost baseline element blocks ✓')

# --- 6. focus doctrine: relative order of SURVIVING keys is the invariant ---
v = compare_structural(tolerant, dict(snap2, focus_order=['#pay', 'a:Home:/home', '#chat']))
assert v['ok']  # appended new element: governed by added/max_new, not focus
v = compare_structural(tolerant, dict(SNAP, focus_order=['a:Home:/home', '#pay']))
assert not v['ok'] and v['focus_order_changed'] is True and v['added'] == []
v = compare_structural(tolerant, dict(SNAP, elements=[SNAP['elements'][0]],
                                      focus_order=['#pay']))
# a loss is reported as `removed` (removed_block), never as a focus change
assert v['focus_order_changed'] is False and v['removed'] == ['a:Home:/home']
print('6. focus chain: reorder blocks, append/loss governed elsewhere ✓')

# --- 7. focus unpinned (None) → focus changes never block ---
loose = dict(base, focus_order=None)
v = compare_structural(loose, dict(SNAP, focus_order=['a:Home:/home', '#pay']))
assert v['ok'] and v['focus_pinned'] is False
print('7. unpinned focus chain never blocks ✓')

# --- 8. removed_block=False accepts losses ---
amnesty = dict(base, removed_block=False, focus_order=None)
v = compare_structural(amnesty, dict(SNAP, elements=[SNAP['elements'][0]]))
assert v['ok'] and v['removed'] == ['a:Home:/home']
print('8. removed_block=False accepts losses ✓')

# --- 9. baseline expiry blocks ---
old = dict(base, review_date='2020-01-01')
v = compare_structural(old, SNAP, today='2026-11-02')
assert not v['ok'] and v['baseline_expired'] is True
print('9. expired baseline blocks ✓')

# --- 10. shape guards ---
assert 'error' in compare_structural({'format': 'other/1'}, SNAP)
assert 'error' in compare_structural(base, {'foo': 1})
assert 'error' in init_structural({'elements': 'nope'})
assert 'error' in init_structural('not a dict')
print('10. shape guards return errors ✓')

# --- 11. CLI: --init-snapshot from file + --snapshot exit codes ---
import tempfile  # noqa: E402
from a11y_toolkit.a11ybudget import main as budget_main  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    s1, s2, bpath = (os.path.join(tmp, n) for n in ('s1.json', 's2.json', 'b.json'))
    for path, snap in ((s1, SNAP), (s2, snap2)):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(snap, f)
    assert budget_main(['--init-snapshot', s1]) == 0
    import io, contextlib  # noqa: E402
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert budget_main(['--init-snapshot', s1]) == 0
    baseline = json.loads(buf.getvalue())
    with open(bpath, 'w', encoding='utf-8') as f:
        json.dump(baseline, f)
    with contextlib.redirect_stdout(io.StringIO()):
        assert budget_main(['--budget', bpath, '--snapshot', s1]) == 0   # same → ok
        assert budget_main(['--budget', bpath, '--snapshot', s2]) == 2   # added → blocked
print('11. CLI --init-snapshot / --snapshot exit 0 / 2 ✓')

print('OK test_budget_structural: 11 checks')
