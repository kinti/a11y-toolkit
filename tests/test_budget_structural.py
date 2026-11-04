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

# --- 12. (2026-11) --snapshot contra un presupuesto NO estructural → error
#         limpio exit 1 (antes: KeyError 'ok' con traceback) ---
from a11y_toolkit.a11ybudget import _CLI_MSG  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    classic = {'url': 'https://web', 'signals': ['img_no_alt'],
               'blocking': ['high'], 'max_new': 0}
    cpath, spath = os.path.join(tmp, 'c.json'), os.path.join(tmp, 's.json')
    with open(cpath, 'w', encoding='utf-8') as f:
        json.dump(classic, f)
    with open(spath, 'w', encoding='utf-8') as f:
        json.dump(SNAP, f)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = budget_main(['--budget', cpath, '--snapshot', spath])
    assert code == 1, code                       # error de uso, no KeyError
    assert 'not a structural budget' in buf.getvalue()
    # y un snapshot malformado con presupuesto estructural: mismo trato
    bpath = os.path.join(tmp, 'b.json')
    with open(bpath, 'w', encoding='utf-8') as f:
        json.dump(init_structural(SNAP), f)
    with open(spath, 'w', encoding='utf-8') as f:
        json.dump({'foo': 1}, f)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = budget_main(['--budget', bpath, '--snapshot', spath])
    assert code == 1 and 'not a snapshot' in buf.getvalue()
print('12. --snapshot con input equivocado → error limpio exit 1 ✓')

# --- 13. (2026-11) --init con stdin vacío no-tty: mensaje accionable, exit 1 ---
assert set(_CLI_MSG) == {'es', 'en'} and set(_CLI_MSG['en']) == set(_CLI_MSG['es'])
_old_stdin, sys.stdin = sys.stdin, io.StringIO('')   # isatty() → False
try:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = budget_main(['--init'])
finally:
    sys.stdin = _old_stdin
assert code == 1, code
assert 'stdin' in buf.getvalue() and 'a11ytoolkit audit' in buf.getvalue()
print('13. --init stdin vacío → qué esperar + exit 1, sin traceback ✓')

# ── regresiones CLI/robutez de datos cruzadas (2026-11) ──────────────────────
# Mismo patrón de bug (input hostil → traceback o exit 0 mentiroso) en los
# módulos hermanos; herméticas todas (monkeypatch / datos sintéticos).

# --- 14. a11yscroll: carga fallida → exit 1, no 0 (un gate CI no puede
#         seguir tras un error de carga) ---
from a11y_toolkit import a11yscroll  # noqa: E402

_orig_scroll = a11yscroll.audit_scroll
a11yscroll.audit_scroll = lambda *a, **k: {'error': 'could not load: boom'}
try:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = a11yscroll.main(['https://dead.example'])
finally:
    a11yscroll.audit_scroll = _orig_scroll
assert code == 1 and 'error' in buf.getvalue(), (code, buf.getvalue())
print('14. a11yscroll carga fallida → exit 1 ✓')

# (a11ywcagem checks: moved with the module to a11y-toolkit-pro — 4-nov)

# --- 16. corpus: README sellado en el manifiesto + JSONL hostil no tumba el
#          evaluate (invalid_lines declarado en el resultado) ---
from a11y_toolkit import a11ycorpus  # noqa: E402

with tempfile.TemporaryDirectory() as cdir:
    m = a11ycorpus.build(version='2026.11.0', seeds=(7,), n_per_seed=3,
                         out=cdir, date='2026-11-04')
    assert 'README.md' in m['files'], 'el contrato de sumisión debe ir sellado'
    ok, detail = a11ycorpus.verify(cdir)
    assert ok, detail
    # determinismo con el README sellado: misma ubicación-independencia
    cdir2 = tempfile.mkdtemp()
    m2 = a11ycorpus.build(version='2026.11.0', seeds=(7,), n_per_seed=3,
                          out=cdir2, date='2026-11-04')
    assert m2['sha256'] == m['sha256'], 'el sello no puede depender de la ruta'
    import shutil as _sh  # noqa: E402
    _sh.rmtree(cdir2)
    # README manipulado con manifiesto QUE LO SELLÓ → verify False (hash)
    with open(os.path.join(cdir, 'README.md'), 'a', encoding='utf-8') as f:
        f.write('\ntampered')
    ok, detail = a11ycorpus.verify(cdir)
    assert not ok and 'README.md' in detail, detail
    # manifiesto LEGADO (sin fila README) + README en disco → fallo declarado
    import hashlib as _h  # noqa: E402
    a11ycorpus.build(version='2026.11.0', seeds=(7,), n_per_seed=3,
                     out=cdir, date='2026-11-04')   # restaura el corpus
    mpath = os.path.join(cdir, 'MANIFEST.json')
    man = json.load(open(mpath, encoding='utf-8'))
    man['files'].pop('README.md')
    man['sha256'] = _h.sha256(a11ycorpus._canon(
        {k: v for k, v in man.items() if k != 'sha256'}).encode('utf-8')).hexdigest()
    with open(mpath, 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=1, sort_keys=True)
    ok, detail = a11ycorpus.verify(cdir)
    assert not ok and 'NOT sealed' in detail, detail
    # JSONL mixto válido/corrupto → evaluate responde con invalid_lines
    a11ycorpus.build(version='2026.11.0', seeds=(7,), n_per_seed=3,
                     out=cdir, date='2026-11-04')   # manifiesto sano otra vez
    sub = os.path.join(cdir, 'sub.jsonl')
    with open(sub, 'w', encoding='utf-8') as f:
        f.write('{"case_id": "m7-0", "criteria_found": ["1.1.1"]}\n'
                '{"case_id": "m7-1", criteria_broken\n'
                '{"case_id": "m7-2", "criteria_found": ["1.1.1"]}\n')
    entries, invalid = a11ycorpus._read_submission(sub)
    assert len(entries) == 2 and invalid and invalid['count'] == 1
    assert invalid['example'].startswith('line 2:')
    res = a11ycorpus.evaluate(entries, cdir, submission_name='sub.jsonl')
    assert res['mutants'] == 3 and 'invalid_lines' not in res  # API directo: limpio
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = a11ycorpus.main(['evaluate', '--submission', sub, cdir])
    out = json.loads(buf.getvalue())
    assert code == 0 and out['invalid_lines']['count'] == 1, out
print('16. corpus: README sellado + JSONL hostil declarado, sin crash ✓')

print('OK test_budget_structural: 16 checks')
