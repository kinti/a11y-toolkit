#!/usr/bin/env python3
"""PR-flow regression measurement: does a change introduce NEW a11y findings?

The question the external DAFO left open: which tool helps a team catch more
real accessibility regressions before shipping, with less review work? This
harness is the measuring side. Given two snapshots of the same page (before /
after), it runs every available detector on both and reports, PER TOOL, the
findings that appeared and the ones that disappeared:

    python3 bench/pr-flow.py before.html after.html [--rendered] [--axe]

- Toolkit static always runs (stdlib only).
- --rendered adds the Playwright pass (audit_dom_url) if Playwright exists.
- --axe adds axe-core on both snapshots when a local vendored axe.min.js
  exists (bench/axe.min.js); it degrades with a notice otherwise, never
  silently.

Output: JSON with per-tool {new:[], fixed:[], same:n} and a summary. The
verdict that matters is NEW per tool: a regression gate blocks on new
findings, not on old debt. Exit code 0 always (this measures; the budget
gate elsewhere decides).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from a11y_toolkit.a11yaudit import audit_html  # noqa: E402


def _keys(report):
    out = set()
    for h in report.get('findings', []):
        out.add((h.get('criterion', '').split(' ')[0], h.get('signal'),
                 str(h.get('examples') or h.get('issue') or '')[:60]))
    return out


def _run_static(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return audit_html(f.read(), lang='en')


def _run_rendered(path):
    try:
        from a11y_toolkit.a11ydom import audit_dom_url
        r = audit_dom_url('file://' + str(Path(path).resolve()), lang='en')
        return None if 'error' in r else r
    except ImportError:
        return None


def _run_axe(path):
    axe_js = ROOT / 'bench' / 'axe.min.js'
    if not axe_js.exists():
        return {'skipped': 'bench/axe.min.js not vendored'}
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        page = nav.new_page()
        page.goto('file://' + str(Path(path).resolve()), wait_until='load')
        page.wait_for_timeout(400)
        page.evaluate(axe_js.read_text(encoding='utf-8'))
        bruto = page.evaluate(
            "async () => { const r = await axe.run(document, "
            "{resultTypes: ['violations']}); "
            "return r.violations.map(v => ({id: v.id, n: v.nodes.length})); }")
        nav.close()
    return {'violations': bruto}


def _axe_keys(report):
    if 'violations' not in report:
        return None
    return {(v['id'], v['n']) for v in report['violations']}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('before')
    ap.add_argument('after')
    ap.add_argument('--rendered', action='store_true')
    ap.add_argument('--axe', action='store_true')
    a = ap.parse_args(argv)

    tools = {}
    b, af = _run_static(a.before), _run_static(a.after)
    kb, ka = _keys(b), _keys(af)
    tools['toolkit_static'] = {
        'new': sorted(ka - kb), 'fixed': sorted(kb - ka),
        'same': len(ka & kb),
        'score_before': b.get('score'), 'score_after': af.get('score')}

    if a.rendered:
        b2, a2 = _run_rendered(a.before), _run_rendered(a.after)
        if b2 is None or a2 is None:
            tools['toolkit_rendered'] = {'skipped': 'playwright unavailable'}
        else:
            kb2, ka2 = _keys(b2), _keys(a2)
            tools['toolkit_rendered'] = {
                'new': sorted(ka2 - kb2), 'fixed': sorted(kb2 - ka2),
                'same': len(ka2 & kb2),
                'score_before': b2.get('score'), 'score_after': a2.get('score')}

    if a.axe:
        kb3, ka3 = _axe_keys(_run_axe(a.before)), _axe_keys(_run_axe(a.after))
        if kb3 is None or ka3 is None:
            tools['axe'] = {'skipped': 'axe not vendored at bench/axe.min.js'}
        else:
            tools['axe'] = {'new': sorted(ka3 - kb3), 'fixed': sorted(kb3 - ka3),
                            'same': len(ka3 & kb3)}

    resumen = {t: len(v.get('new', [])) for t, v in tools.items()
               if 'skipped' not in v}
    print(json.dumps({'before': a.before, 'after': a.after, 'tools': tools,
                      'new_per_tool': resumen}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
