#!/usr/bin/env python3
"""PR-flow regression measurement: does a change introduce NEW a11y findings?

Give two snapshots of the same page (before / after). Every available
detector runs on both and the harness reports, PER TOOL, the findings that
appeared and the ones that disappeared, instance by instance (one entry per
element):

    python3 bench/pr-flow.py before.html after.html [--rendered] [--axe]

- Toolkit static always runs (stdlib only).
- --rendered adds the Playwright pass (audit_dom_url) if Playwright exists.
- --axe adds axe-core on both snapshots when a local axe.min.js exists
  (bench/axe.min.js, or the user cache the monthly benchmark fills); it
  degrades with a notice otherwise, never silently.

How instances are told apart:
- Toolkit: a finding aggregates N elements and carries only the first ones
  (5 routes and 5 examples in the static pass, up to 6 examples in the
  rendered one). Up to that number every instance is compared by element:
  the element route when the finding carries paths, else its example text.
  Past it, the elements the report does not carry can neither be compared nor
  located, and the harness says so instead of reporting a clean zero:
  `insufficient_evidence` lists the signal with the count delta read from the
  message (engine messages start with the number of affected elements). A
  move between two hidden elements keeps the count and cannot be seen at
  all, which is why a signal at or past the cap is always listed there.
  Routes are positional (tag:nth-of-type):
  inserting an element before shifts the routes of its later siblings, which
  then read as moved instances (one fixed + one new).
- axe: per failing node (rule + target), so a failure moving from element A
  to element B is one new + one fixed, never "nothing".

Output: JSON with per tool {new:[], fixed:[], same:n, insufficient_evidence:[]
and a summary. The verdict that matters is NEW per tool: a regression gate
blocks on new findings, not on old debt.

Exit code: 0 when every requested pass measured, new findings or not (this
measures; the budget gate elsewhere decides). 1 when a pass failed to run: a
failed measurement is never reported as zero findings.
"""
import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'bench'))

import browser  # noqa: E402  (bench/browser.py: pool loan + axe-core lookup)
from a11y_toolkit.a11yaudit import audit_html  # noqa: E402

# from this many carried elements on, a finding may be cut by the report's cap
_CARRIED = 5
# engine messages open with the number of affected elements ("7 images ...")
_LEADING_COUNT = re.compile(r'^\s*(\d+)\b')


class PassFailed(Exception):
    """A detector could not run. Never the same as "it found nothing"."""


def _run_static(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            report = audit_html(f.read(), lang='en')
    except OSError as e:
        raise PassFailed(f'cannot read {path}: {e}') from e
    if 'error' in report:
        raise PassFailed(f'engine error: {report["error"]}')
    return report


def _need_playwright():
    if importlib.util.find_spec('playwright') is None:
        raise LookupError('playwright unavailable')


def _run_rendered(path):
    _need_playwright()
    from a11y_toolkit.a11ydom import audit_dom_url
    report = audit_dom_url(Path(path).resolve().as_uri(), lang='en')
    if 'error' in report:
        raise PassFailed(f'engine error: {report["error"]}')
    return report


def _run_axe(path):
    _need_playwright()                   # LookupError → the caller skips
    axe_js = browser.load_axe()          # FileNotFoundError → the caller skips
    page, close_page = browser.borrow_page()
    try:
        page.goto(Path(path).resolve().as_uri(), wait_until='load')
        page.wait_for_timeout(400)
        return browser.axe_run(page, axe_js)
    finally:
        close_page()


def _findings(report):
    """{(criterion, signal): finding} for a toolkit report."""
    out = {}
    for f in report.get('findings', []):
        if isinstance(f, dict):
            out[(str(f.get('criterion', '')).split(' ')[0], str(f.get('signal') or ''))] = f
    return out


def _elements(finding):
    """What identifies each instance of a finding: routes when it carries
    them, else example texts. Empty for a page-level finding."""
    if finding is None:
        return []
    paths = [p for p in (finding.get('paths') or []) if isinstance(p, str)]
    if paths:
        return paths
    return [e for e in (finding.get('examples') or []) if isinstance(e, str)]


def _count(finding):
    """Affected elements read from the message, or None when it does not say."""
    if finding is None:
        return 0
    m = _LEADING_COUNT.match(str(finding.get('issue') or ''))
    return int(m.group(1)) if m else None


def _instances(finding):
    """Counter of the instances a finding carries. An absent finding is an
    empty counter. A finding that carries no element (page-level: a missing
    title, a missing lang attribute) is ONE instance of its own: it used to
    vanish from the diff, so a page losing its title reported zero new."""
    if finding is None:
        return Counter()
    carried = _elements(finding)
    return Counter(carried) if carried else Counter([None])


def compare(before, after):
    """Per-element diff of two toolkit reports."""
    fb, fa = _findings(before), _findings(after)
    new, fixed, same, insufficient = [], [], 0, []
    for key in sorted(set(fb) | set(fa)):
        b, a = fb.get(key), fa.get(key)
        eb, ea = _elements(b), _elements(a)
        if max(len(eb), len(ea)) < _CARRIED:
            # every instance is carried on both sides: compare by element
            # (a page-level finding is one instance)
            cb, ca = _instances(b), _instances(a)
            new += [[key[0], key[1], el] for el in sorted((ca - cb).elements(), key=str)]
            fixed += [[key[0], key[1], el] for el in sorted((cb - ca).elements(), key=str)]
            same += sum((cb & ca).values())
            continue
        # at or past the carried cap: the report may hide elements. What it
        # carries is still located; the rest only shows as a count delta
        nb, na = _count(b), _count(a)
        entry = {'criterion': key[0], 'signal': key[1],
                 'carried_before': len(eb), 'carried_after': len(ea),
                 'count_before': nb, 'count_after': na}
        if b is None or a is None:
            target, carried, total = (new, ea, na) if b is None else (fixed, eb, nb)
            target += [[key[0], key[1], el] for el in sorted(carried)]
            hidden = (total - len(carried)) if total is not None else None
            entry['new' if b is None else 'fixed'] = max(0, hidden or 0)
            entry['fixed' if b is None else 'new'] = 0
            entry['delta_known'] = hidden is not None
            entry['changed'] = True
        elif nb is not None and na is not None:
            entry['new'], entry['fixed'] = max(0, na - nb), max(0, nb - na)
            entry['delta_known'] = True
            entry['changed'] = na != nb or eb != ea
        else:
            entry['new'] = entry['fixed'] = None
            entry['delta_known'] = False
            entry['changed'] = eb != ea or b.get('issue') != a.get('issue')
        # always listed: with elements past the cap the report cannot back
        # an element-level verdict for this signal, changed or not
        insufficient.append(entry)
    return {'new': new, 'fixed': fixed, 'same': same,
            'insufficient_evidence': insufficient}


def compare_axe(before, after):
    """Per-node diff of two axe runs (rule + target of every failing node)."""
    def nodes(run):
        return Counter((v['id'], target) for v in run['violations'] for target in v['targets'])
    nb, na = nodes(before), nodes(after)
    return {'new': [['axe', r, t] for r, t in sorted((na - nb).elements())],
            'fixed': [['axe', r, t] for r, t in sorted((nb - na).elements())],
            'same': sum((nb & na).values()),
            'insufficient_evidence': []}


def summarize(tools):
    measured = {t: v for t, v in tools.items() if 'skipped' not in v and 'error' not in v}
    hidden = {t: v['insufficient_evidence'] for t, v in measured.items()}
    return {
        'new_per_tool': {t: len(v['new']) + sum(e['new'] or 0 for e in hidden[t])
                         for t, v in measured.items()},
        'new_unlocated_per_tool': {t: sum(e['new'] or 0 for e in hidden[t]) for t in measured},
        'fixed_per_tool': {t: len(v['fixed']) + sum(e['fixed'] or 0 for e in hidden[t])
                           for t, v in measured.items()},
        # a tool is inconclusive for a signal when the report carries its
        # elements only up to its cap: the hidden ones were not compared
        'inconclusive': {t: [e['signal'] for e in hidden[t]]
                         for t in measured if hidden[t]},
        'failed': sorted(t for t, v in tools.items() if 'error' in v),
        'skipped': sorted(t for t, v in tools.items() if 'skipped' in v),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('before')
    ap.add_argument('after')
    ap.add_argument('--rendered', action='store_true')
    ap.add_argument('--axe', action='store_true')
    a = ap.parse_args(argv)
    tools = {}

    def measure(name, run_pair):
        try:
            b, af = run_pair()
            tools[name] = dict(compare(b, af), score_before=b.get('score'),
                               score_after=af.get('score'))
        except LookupError as e:
            tools[name] = {'skipped': str(e)}
        except Exception as e:  # noqa: BLE001 (a failed pass still prints JSON)
            tools[name] = {'error': f'{type(e).__name__}: {e}'}

    measure('toolkit_static', lambda: (_run_static(a.before), _run_static(a.after)))
    if a.rendered:
        measure('toolkit_rendered', lambda: (_run_rendered(a.before), _run_rendered(a.after)))
    if a.axe:
        try:
            tools['axe'] = compare_axe(_run_axe(a.before), _run_axe(a.after))
        except FileNotFoundError as e:
            tools['axe'] = {'skipped': f'axe-core not found ({e})'}
        except LookupError as e:
            tools['axe'] = {'skipped': str(e)}
        except Exception as e:  # noqa: BLE001
            tools['axe'] = {'error': f'{type(e).__name__}: {e}'}
    summary = summarize(tools)
    print(json.dumps({'before': a.before, 'after': a.after, 'tools': tools,
                      'summary': summary,
                      'new_per_tool': summary['new_per_tool']},
                     ensure_ascii=False, indent=1))
    return 1 if summary['failed'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
