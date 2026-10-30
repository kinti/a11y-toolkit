#!/usr/bin/env python3
"""Tests for a11yplan — the remediation plan (fix batches, ordered).

Turns a findings list into an executable ROUTE instead of an inventory:
batches by shared cause, declared phase ordering (infrastructure →
design-system decisions → instances; redesign zones last), minutes from
declared assumptions (or pack effort when given), root-sealed, zero
conformance claims. Deterministic: same report, same plan.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a11y_toolkit import a11yplan  # noqa: E402

FAILS = []


def check(name, cond, detail=''):
    print(('  OK ' if cond else '  FAIL ') + name + (f' — {detail}' if detail and not cond else ''))
    if not cond:
        FAILS.append(name)


def _f(signal, sev='medium', url='https://x.test/', **extra):
    f = {'severity': sev, 'signal': signal,
         'criterion': {'heading_order': '1.3.1', 'no_h1': '1.3.1', 'landmark': '1.3.1',
                       'contrast_low': '1.4.3', 'contrast_image_fail': '1.4.3',
                       'img_no_alt': '1.1.1', 'field_label': '3.3.2'}.get(signal, '4.1.2'),
         'issue': 'x', 'remediation': 'y', 'examples': ['a'], 'url': url}
    f.update(extra)
    return f


REPORT = {'url': 'https://x.test/', 'score': 55, 'mode': 'static', 'findings': [
    _f('no_h1', 'high'), _f('heading_order', 'high'), _f('landmark', 'medium'),
    _f('contrast_low', 'high'), _f('contrast_low', 'high', 'https://x.test/p2'),
    _f('contrast_low', 'medium', 'https://x.test/p3'),
    _f('img_no_alt', 'medium'), _f('field_label', 'high'),
] * 1 + [_f('img_no_alt', 'low', 'https://x.test/p2')]}
# 6 distinct signals on one page + spread pages → redesign-zone candidate


def main():
    print('== 1. Shape and honesty')
    plan = a11yplan.build_plan(REPORT)
    check('format a11y-fix-plan/1', plan['format'] == 'a11y-fix-plan/1')
    check('batches exist and are ordered', isinstance(plan['batches'], list) and plan['batches'])
    check('no conformance claim anywhere',
          not any(k in json.dumps(plan).lower() for k in ('conformant', '"passed"')))
    check('assumptions declared (minutes are a heuristic)',
          plan['assumptions'] and 'heuristic' in json.dumps(plan['assumptions']).lower())
    check('human reorder note present',
          'reorder' in json.dumps(plan).lower() or 're-order' in json.dumps(plan).lower())

    print('== 2. Phase ordering (infrastructure → design → instances → redesign)')
    fases = [b['phase'] for b in plan['batches']]
    orden = {'infrastructure': 0, 'design-system': 1, 'instances': 2, 'redesign-zone': 3}
    check('phases in declared order',
          fases == sorted(fases, key=lambda p: orden[p]), str(fases))
    check('infrastructure batch first and carries the structural signals',
          plan['batches'][0]['phase'] == 'infrastructure'
          and {'no_h1', 'heading_order', 'landmark'} <= set(plan['batches'][0]['signals']))
    design = next(b for b in plan['batches'] if b['phase'] == 'design-system')
    check('design batch groups all contrast findings as one decision',
          design['signals'] == ['contrast_low'] and design['finding_count'] == 3)

    print('== 3. Minutes: declared heuristic, cumulative, savings vs itemized')
    check('minutes ranges present per batch',
          all(isinstance(b['minutes'], list) and len(b['minutes']) == 2
              for b in plan['batches']))
    total = plan['total_minutes']
    check('total equals the sum of batches',
          total[0] == sum(b['minutes'][0] for b in plan['batches'])
          and total[1] == sum(b['minutes'][1] for b in plan['batches']))
    check('grouping savings reported (batch vs itemized)',
          isinstance(plan['grouping_savings_minutes'], list))

    print('== 4. Root seal (verify + tamper breaks)')
    check('plan verifies', a11yplan.verify_plan(plan)[0] is True)
    roto = json.loads(json.dumps(plan))
    roto['batches'][0]['finding_count'] += 1
    check('mutation breaks the seal', a11yplan.verify_plan(roto)[0] is False)

    print('== 5. From pack: effort minutes replace the severity heuristic')
    from a11y_toolkit.a11yevidence import build_pack
    pack = build_pack([REPORT])
    plan2 = a11yplan.build_plan(REPORT, pack=pack)
    check('pack minutes differ from severity heuristic and are used',
          plan2['assumptions']['source'] == 'pack effort'
          and plan2['total_minutes'] != plan['total_minutes'])

    print('== 6. Hostile input (never crashes, honest empty)')
    vacio = a11yplan.build_plan({'url': 'x', 'findings': []})
    check('no findings → zero batches + explicit note', vacio['batches'] == []
          and 'no findings' in vacio['note'].lower())
    sucio = a11yplan.build_plan({'findings': ['x', None, {'severity': 'high'},
                                              _f('img_no_alt')]})
    check('malformed findings skipped, valid one planned',
          sum(b['finding_count'] for b in sucio['batches']) == 1)

    print('== 7. CLI end-to-end')
    with tempfile_dir() as d:
        rp, out = os.path.join(d, 'audit.json'), os.path.join(d, 'plan.json')
        json.dump(REPORT, open(rp, 'w'))
        r = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y', 'plan',
                            '--report', rp, '-o', out],
                           capture_output=True, text=True, timeout=120)
        p2 = json.load(open(out)) if os.path.exists(out) else {}
        check('exit 0, plan written, seal printed',
              r.returncode == 0 and p2.get('sha256', '') == plan['sha256'], r.stderr[-150:])

    print(f"\n{'ALL OK' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


def tempfile_dir():
    import tempfile
    return tempfile.TemporaryDirectory()


if __name__ == '__main__':
    sys.exit(main())
