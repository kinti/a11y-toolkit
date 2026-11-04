#!/usr/bin/env python3
"""a11y_engines — cross-engine behavioral matrix (the same page, several engines).

Cross-industry translation of the cross-browser accessibility lab: teams run
static scans but cannot verify that an accessible task BEHAVES the same in
real engine configurations. This module captures the a11y snapshot
(interactives, real tab order, computed accessibility tree) of ONE URL in
SEVERAL browser engines and diffs every pair. What diverges between engines
is exactly what a single-engine audit can never see: elements that only exist
in one engine's DOM, tab order that forks, names that engines compute
differently.

Honesty (what this is and is not):
  - Elements and focus order come from the DOM (spec-stable across engines):
    divergence there is a REAL behavioral finding and blocks (ok=false).
  - The accessibility tree is engine-computed: divergence is reported as
    `tree_changed` per pair but does NOT block — different engines legitimately
    compute some roles/names differently. It is the pointer for what a screen
    reader on that platform would announce; judge it, don't gate on it.
  - Engines must be installed locally (playwright install firefox webkit);
    an engine that fails to launch is reported in engines_failed, never silently.

CLI (infrastructure, not a tool — D17, same tier as corpus/mutants):
  a11yengines.py https://web                                  # the 3 default engines
  a11yengines.py https://web --engines chromium,firefox       # your matrix
  a11yengines.py https://web --auth-state session.json -o m.json
Exit: 0 no divergences / 2 behavioral divergences / 1 config error
(playwright missing or fewer than 2 engines launched).
"""

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone

from . import a11ydiff

ENGINES = ('chromium', 'firefox', 'webkit', 'chrome', 'msedge')
DEFAULT_ENGINES = ('chromium', 'firefox', 'webkit')


def _capture(url, engine, auth_state=None):
    """One engine's snapshot; raises on engine failure (caller records it)."""
    return a11ydiff.snapshot(url, engine=engine, auth_state=auth_state)


def _pair_entry(name_a, name_b, sa, sb):
    d = a11ydiff.diff(sa, sb)
    # behavioral verdict: DOM-level facts only — the tree is informational
    # across engines (engines compute some roles/names differently by design)
    focus = d['focus']
    ok = not (d['added'] or d['removed'] or d['renamed']
              or focus['removed'] or focus['reordered'])
    return {
        'engines': [name_a, name_b],
        'ok': ok,
        'added': d['added'],
        'removed': d['removed'],
        'renamed': d['renamed'],
        'focus': {'removed': focus['removed'], 'added': focus['added'],
                  'reordered': focus['reordered'],
                  'first_divergence': focus['first_divergence']},
        'tree_changed': bool(d['tree']['changed']),
        'tree_first_differences': (d['tree']['first_differences'] or [])[:3],
    }


def matrix(url, engines=None, auth_state=None, capture=None):
    """One URL → per-engine snapshots → pairwise divergence report."""
    engines = tuple(engines or DEFAULT_ENGINES)
    capture = capture or _capture

    ok, failed, snaps = [], [], {}
    for name in engines:
        if name not in ENGINES:
            failed.append({'engine': name, 'error': f'unknown engine (known: {", ".join(ENGINES)})'})
            continue
        try:
            snaps[name] = capture(url, name, auth_state)
            s = snaps[name]
            ok.append({'engine': name, 'elements': len(s.get('elements', [])),
                       'focus_steps': len(s.get('focus_order', [])),
                       'tree': 'arbol_accesible' in s})
        except ImportError:
            # playwright ausente NO es «un motor muerto»: es un error de
            # instalación que mata TODA la matriz — relanzar para que main
            # aconseje `pip install playwright` (no `playwright install …`,
            # el consejo equivocado cuando falta el paquete pip) y salga 1
            raise
        except Exception as e:  # noqa: BLE001 — one dead engine must not kill the matrix
            msg = str(e).splitlines()[0][:200] if str(e) else e.__class__.__name__
            failed.append({'engine': name, 'error': msg})

    pairs = [_pair_entry(a, b, snaps[a], snaps[b])
             for a, b in itertools.combinations(sorted(snaps), 2)]
    divergences = [p for p in pairs if not p['ok']]

    enough = len(snaps) >= 2
    report = {
        'mode': 'engines',
        'url': url,
        'ts': datetime.now(timezone.utc).isoformat(),
        'engines_ok': ok,
        'engines_failed': failed,
        'pairs': pairs,
        'divergences': divergences,
        'ok': bool(enough and not divergences),
        'insufficient_engines': not enough,
        'limits': ('elements and focus order are DOM facts: divergence blocks. '
                   'The computed accessibility tree is engine-specific: '
                   'tree_changed is informational, not a gate. A pass is '
                   'engine-pair evidence for THIS url at THIS time — not a '
                   'conformance claim.'),
    }
    if not enough:
        report['note'] = ('fewer than 2 engines launched: install them with '
                          '`playwright install firefox webkit` — a matrix of one '
                          'engine cannot see cross-engine behavior')
    return report


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('url')
    ap.add_argument('--engines', default=','.join(DEFAULT_ENGINES),
                    help=f'comma-separated engines (default: {",".join(DEFAULT_ENGINES)})')
    ap.add_argument('--auth-state', help='Playwright storage_state JSON (session)')
    ap.add_argument('-o', '--out', help='write the report here (default: stdout)')
    a = ap.parse_args(argv)

    engines = [e.strip() for e in a.engines.split(',') if e.strip()]
    capture = _capture
    try:
        report = matrix(a.url, engines=engines, auth_state=a.auth_state,
                        capture=capture)
    except ImportError:
        print(json.dumps({'error': 'Playwright not installed: '
                                   'pip install playwright && playwright install chromium'}))
        return 1
    out = json.dumps(report, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        report = dict(report)
        report['pairs'] = [{'engines': p['engines'], 'ok': p['ok']} for p in report['pairs']]
        print(json.dumps({'url': a.url, 'engines_ok': [e['engine'] for e in report['engines_ok']],
                          'pairs': report['pairs'], 'out': a.out}, ensure_ascii=False))
    else:
        print(out)
    if report.get('insufficient_engines'):
        return 1
    return 0 if report.get('ok') else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
