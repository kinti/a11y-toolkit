#!/usr/bin/env python3
"""Tests for scripts/verify_pack.py — the STANDALONE evidence-pack verifier.

The verifier's defining constraint is independence: it must verify a pack
WITHOUT the engine (stdlib only, no `a11y_toolkit` import), so a third party
can copy the single script and verify packs anywhere. These tests pin that.
"""

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'scripts', 'verify_pack.py')
SAMPLE = os.path.join(ROOT, 'docs', 'evidence-pack.sample.json')

FAILS = []


def check(name, cond, detail=''):
    print(('  OK ' if cond else '  FAIL ') + name + (f' — {detail}' if detail and not cond else ''))
    if not cond:
        FAILS.append(name)


def run(pack_path, *flags, independence=False):
    """Run the verifier on pack_path. independence=True: temp cwd + no PYTHONPATH,
    so any import of the engine would crash (proves standalone-ness)."""
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    cwd = tempfile.mkdtemp() if independence else ROOT
    return subprocess.run([sys.executable, SCRIPT, pack_path, *flags],
                          capture_output=True, text=True, env=env, cwd=cwd)


def tampered(mutate):
    """Copy of the sample pack with `mutate(pack)` applied → path."""
    pack = json.load(open(SAMPLE, encoding='utf-8'))
    mutate(pack)
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(pack, f, ensure_ascii=False)
    return path


def section(title):
    print(f'\n== {title}')


def main():
    section('1. The sample pack verifies (exit 0)')
    r = run(SAMPLE)
    check('exit 0 on the published sample', r.returncode == 0, r.stderr + r.stdout)
    check('says VERIFIED (not NOT VERIFIED)', '\nVERIFIED' in r.stdout)

    section('2. Independence: no engine import, no repo around it')
    src = open(SCRIPT, encoding='utf-8').read()
    import re
    check('source never imports the engine',
          not re.search(r'^\s*(from|import)\s+a11y_toolkit', src, re.M), src)
    r = run(SAMPLE, independence=True)
    check('runs from a temp cwd without PYTHONPATH', r.returncode == 0,
          r.stderr + r.stdout)

    section('3. Tamper detection (every mutation → exit 1)')
    cases = [
        ('artifact body byte swapped', lambda p: p['artifacts'][0]['body']
         .__setitem__('url', 'https://evil.example')),
        ('criterion status flipped (seal now stale)', lambda p:
         p['criteria'][0].__setitem__('status', 'agent-verified')),
        ('pack sha256 itself edited', lambda p: p.__setitem__(
            'sha256', '0' * 64)),
        ('recompute-seal attack: body changed, seal honestly recomputed, '
         'artifact hash left stale', lambda p: (
             p['artifacts'][0]['body'].__setitem__('url', 'https://evil.example'),
             p.__setitem__('sha256', None))),
        ('generated removed (seal excludes it, but it must be present)',
         lambda p: p.pop('generated')),
        ('format downgraded to pack/1 (historical, not verifiable here)',
         lambda p: p.__setitem__('format', 'a11y-evidence-pack/1')),
        ('criteria count 54 (contract says exactly 55)',
         lambda p: p['criteria'].pop()),
    ]
    import hashlib
    _canon = lambda o: json.dumps(o, ensure_ascii=False, sort_keys=True,
                                  separators=(',', ':'))
    for name, mutate in cases:
        def m(pack, mutate=mutate):
            mutate(pack)
            if pack.get('sha256') is None:  # recompute-seal attack helper
                pack['sha256'] = hashlib.sha256(
                    _canon({k: v for k, v in pack.items()
                            if k not in ('sha256', 'generated')}).encode('utf-8')
                ).hexdigest()
        r = run(tampered(m))
        check(f'detects: {name}', r.returncode == 1, r.stdout + r.stderr)

    section('3b. Legacy seal rule (packs emitted before v5.13.0)')
    # seal recomputed over the pack minus sha256 ONLY (clock sealed in)
    def to_legacy(pack):
        import hashlib as h
        pack['sha256'] = h.sha256(_canon({k: v for k, v in pack.items()
                                          if k != 'sha256'}).encode('utf-8')).hexdigest()
    r = run(tampered(to_legacy))
    check('legacy-sealed pack verifies (exit 0)', r.returncode == 0,
          r.stdout + r.stderr)
    check('labels it as legacy', 'legacy' in r.stdout.lower())
    def to_legacy_tampered(pack):
        to_legacy(pack)
        pack['criteria'][0]['status'] = 'agent-verified'  # post-seal tamper
    r = run(tampered(to_legacy_tampered))
    check('tampered legacy pack fails', r.returncode == 1, r.stdout)

    section('4. Diagnosis names WHERE the chain broke')
    r = run(tampered(lambda p: p['artifacts'][0]['body']
                     .__setitem__('url', 'https://evil.example')))
    check('names the artifact', 'artifact' in r.stdout.lower())
    r = run(tampered(lambda p: p['criteria'][0]
                     .__setitem__('status', 'agent-verified')))
    check('names the pack seal', 'seal' in r.stdout.lower()
          or 'sha256' in r.stdout.lower())

    section('5. Machine-readable mode (--json)')
    r = run(SAMPLE, '--json')
    try:
        out = json.loads(r.stdout)
        check('--json emits {verified: true}', out.get('verified') is True)
    except json.JSONDecodeError:
        check('--json emits valid JSON', False, r.stdout[:200])

    section('6. Hostile input (never crashes with a traceback)')
    fd, path = tempfile.mkstemp(suffix='.json')
    os.write(fd, b'{"format": "a11y-evidence-pack/2", "sha256": "x"')
    os.close(fd)
    r = run(path)
    check('truncated JSON → exit 1, no traceback', r.returncode == 1
          and 'Traceback' not in r.stderr, r.stderr[:200])
    r = run(tampered(lambda p: p.__setitem__('artifacts', 'not-a-list')))
    check('artifacts not a list → exit 1, no traceback', r.returncode == 1
          and 'Traceback' not in r.stderr, r.stderr[:200])
    r = run(tampered(lambda p: p['artifacts'][0].__setitem__('sha256', 123)))
    check('artifact sha256 is an int → exit 1, no traceback', r.returncode == 1
          and 'Traceback' not in r.stderr, r.stderr[:200])
    fd, path = tempfile.mkstemp(suffix='.json')
    os.write(fd, ('{"format": "a11y-evidence-pack/2", "sha256": "x", '
                  '"generated": "t", "tool": "t", "criteria": [], "artifacts": '
                  '[{"type": "t", "sha256": "x", "body": {"a": "\\ud800"}}], '
                  '"summary": {}}').encode())
    os.close(fd)
    r = run(path)
    check('lone surrogate in body → exit 1, no traceback', r.returncode == 1
          and 'Traceback' not in r.stderr, r.stderr[:200])
    r = run(tampered(lambda p: (p.__setitem__('summary', '5 fails, trust me'),
                                p['artifacts'][0].pop('body'))))
    check('summary is a string + seal recomputed → still flags summary',
          r.returncode == 1 and 'summary' in r.stdout, r.stdout[:300])

    print(f'\n{"ALL OK" if not FAILS else "FAILURES: " + ", ".join(FAILS)}')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
