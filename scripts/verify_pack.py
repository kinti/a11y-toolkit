#!/usr/bin/env python3
"""Independent verifier for a11y-evidence-pack/2 — no engine required.

Copy this single file anywhere with Python 3.9+ and verify a pack:

    python3 verify_pack.py evidence-pack.json      # human output, exit 0/1
    python3 verify_pack.py evidence-pack.json --json
    cat evidence-pack.json | python3 verify_pack.py -

It recomputes the whole hash chain from the pack ALONE (report bodies are
embedded): every artifacts[].sha256 and the pack seal (pack.sha256, computed
over the pack without the sha256 and generated fields — re-emitting the same
evidence later must yield the same seal). The canonicalization below must
stay byte-for-byte identical to the builder's (a11y_toolkit/a11yevidence.py);
it is deliberately re-implemented here instead of imported, because a verifier
that needs the producing tool is not an independent verifier.

Honest boundary: only report:* artifacts embed their body, so only those
hashes are recomputable from the pack itself. snapshot:a11y / sr_transcript
artifacts carry a recorded sha256 but no body — they are reported as
"recorded" (integrity-annotated), not verified here. Tampering with anything
that IS embedded always breaks the seal anyway.

Exit codes: 0 verified · 1 any failure (with the field that broke the chain).
"""

import argparse
import hashlib
import json
import sys

FORMAT = 'a11y-evidence-pack/2'
STATES = ('automated-fail', 'automated-review', 'not-flagged', 'manual-only',
          'agent-verified', 'not-run')
REQUIRED = ('format', 'sha256', 'generated', 'tool', 'summary', 'criteria',
            'artifacts')


def _canon(obj):
    # MUST match a11yevidence._canon byte-for-byte (see docstring)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'))


def _sha256(obj):
    return hashlib.sha256(_canon(obj).encode('utf-8')).hexdigest()


def verify(pack):
    """Pack (dict) → (ok, checks). checks: [{check, ok, detail}] — every
    failure names WHERE the chain broke."""
    checks = []

    def fail(name, detail):
        checks.append({'check': name, 'ok': False, 'detail': detail})

    def ok(name, detail=''):
        checks.append({'check': name, 'ok': True, 'detail': detail})

    if not isinstance(pack, dict):
        fail('load', 'pack is not a JSON object')
        return False, checks
    if pack.get('format') != FORMAT:
        fail('format', f'expected {FORMAT}, got {pack.get("format")!r}'
             + (' (pack/1 is historical; builders MUST emit pack/2)'
                if isinstance(pack.get('format'), str) and 'pack/1' in pack.get('format', '')
                else ''))
        return False, checks
    missing = [k for k in REQUIRED if k not in pack]
    if missing:
        fail('structure', f'missing required field(s): {", ".join(missing)}')
        return False, checks

    criteria = pack['criteria']
    if not isinstance(criteria, list) or len(criteria) != 55:
        fail('structure', f'criteria must be exactly 55 entries (the WCAG 2.2 '
             f'A/AA matrix), got {len(criteria) if isinstance(criteria, list) else type(criteria).__name__}')
    else:
        bad = [c.get('criterion', '?') for c in criteria
               if not isinstance(c, dict) or c.get('status') not in STATES]
        if bad:
            fail('structure', f'criterion rows with unknown status: {bad[:3]}')
        else:
            ok('criteria matrix', '55 entries, known statuses')

    summary = pack.get('summary')
    if isinstance(summary, dict) and isinstance(criteria, list):
        actual = {}
        for c in criteria:
            if isinstance(c, dict) and c.get('status') in STATES:
                actual[c['status']] = actual.get(c['status'], 0) + 1
        drift = {k: (summary.get(k), v) for k, v in actual.items()
                 if summary.get(k) != v}
        if drift:
            fail('summary', f'summary counts disagree with the matrix '
                 f'(field: summary vs actual): {drift}')
        else:
            ok('summary counts match the criteria matrix')
    else:
        fail('structure', 'summary must be an object of status counts')

    verified_bodies = recorded = 0
    if not isinstance(pack['artifacts'], list):
        fail('artifacts', 'artifacts must be a list')
    else:
        for i, a in enumerate(pack['artifacts']):
            if not isinstance(a, dict) or 'sha256' not in a:
                fail(f'artifact #{i + 1} ({a.get("type", "?") if isinstance(a, dict) else "?"})',
                     'missing sha256')
                continue
            if 'body' in a:
                got = _sha256(a['body'])
                if got != a['sha256']:
                    fail(f'artifact #{i + 1} ({a.get("type", "?")})',
                         f'body hash mismatch: pack says {str(a["sha256"])[:16]}…, '
                         f'recomputed {got[:16]}… — the body was tampered with')
                else:
                    verified_bodies += 1
            else:
                recorded += 1
        if verified_bodies or recorded:
            note = f'{verified_bodies} recomputed from embedded bodies'
            note += f', {recorded} recorded without body (not recomputable from the pack)' if recorded else ''
            ok('artifact hashes', note)
        elif not any(not c['ok'] for c in checks if c['check'].startswith('artifact')):
            fail('artifacts', 'no artifacts to verify — an evidence pack '
                 'must carry at least one artifact')

    sealed = _sha256({k: v for k, v in pack.items()
                      if k not in ('sha256', 'generated')})
    if sealed != pack['sha256']:
        # legacy rule (packs emitted before v5.13.0): the clock WAS sealed in.
        # Both rules are deterministic; the label says which one the pack used.
        legacy = _sha256({k: v for k, v in pack.items() if k != 'sha256'})
        if legacy == pack['sha256']:
            ok('pack seal', 'legacy rule (pre-v5.13: generated sealed in) — recomputed')
        else:
            fail('pack seal', f'pack.sha256 mismatch under BOTH seal rules '
                 f'(current: minus sha256/generated → {sealed[:16]}…; legacy: '
                 f'minus sha256 → {legacy[:16]}…) — any field was changed '
                 f'after sealing (or the seal was edited)')
    else:
        ok('pack seal', 'recomputed over the pack minus sha256/generated')

    return all(c['ok'] for c in checks), checks


def main(argv):
    ap = argparse.ArgumentParser(
        description='Independently verify an a11y-evidence-pack/2 (no engine needed)')
    ap.add_argument('pack', help="pack JSON path, or '-' for stdin")
    ap.add_argument('--json', action='store_true', help='machine-readable output')
    a = ap.parse_args(argv)

    try:
        pack = json.load(sys.stdin if a.pack == '-' else open(a.pack, encoding='utf-8'))
    except Exception as e:
        if a.json:
            print(json.dumps({'verified': False, 'error': f'load: {e}'}))
        else:
            print(f'FAIL load — cannot read pack: {e}')
        return 1

    try:
        ok, checks = verify(pack)
    except Exception as e:  # hostile input must never traceback
        if a.json:
            print(json.dumps({'verified': False,
                              'error': f'verify crashed on hostile input: {type(e).__name__}: {e}'}))
        else:
            print(f'FAIL verify — cannot process this pack '
                  f'({type(e).__name__}: {e})')
        return 1
    if a.json:
        print(json.dumps({'verified': ok, 'checks': checks}, ensure_ascii=False))
    else:
        for c in checks:
            line = ('OK   ' if c['ok'] else 'FAIL ') + c['check']
            if c['detail']:
                line += f' — {c["detail"]}'
            print(line)
        print(('VERIFIED — the sealed hash chain holds'
               if ok else 'NOT VERIFIED — the chain above is where it broke'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
