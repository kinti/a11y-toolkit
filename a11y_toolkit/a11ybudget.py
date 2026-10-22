#!/usr/bin/env python3
"""Accessibility error budget — Google SRE's lesson applied to WCAG.

The classic paralysis: the audit finds 40 issues, nobody can fix them this
week, so nobody turns the control on. The budget breaks the deadlock: today's
baseline is ACCEPTED and only what is NEW blocks. Every fix lowers the
baseline; every regression screams.

Budget file (budget.json):

  {
    "url": "https://mysite",
    "signals": ["img_no_alt", "field_label"],       // accepted baseline
    "blocking": ["high", "medium"],              // severities that block
    "max_new": 0,                               // how many new ones tolerated
    "review_date": "2026-12-07"                 // baseline expiry (optional)
  }

Generate the baseline:  a11ytoolkit audit --url https://mysite | a11ytoolkit budget --init
Compare with:           a11ytoolkit budget --budget budget.json --audit audit.json
Exit code: 0 ok / 2 blocked.

Only stable keys ('signal') and severities are compared, never prose.
"""

import argparse
import datetime
import json

from .a11yaudit import normalize_signal  # noqa: E402  (compat 5.10)
import sys


def init(audit):
    """Informe (o site) → fichero de presupuesto inicial."""
    pages = audit.get('reports') if 'reports' in audit else [audit]
    signals = sorted({normalize_signal(h.get('signal', '')) for pg in pages for h in pg.get('findings', [])})
    return {
        'url': audit.get('url', ''),
        'signals': signals,
        'blocking': ['high', 'medium'],
        'max_new': 0,
        'review_date': (datetime.date.today() + datetime.timedelta(days=90)).isoformat(),
    }


def comparar(budget, audit, today=None):
    """Presupuesto vs informe actual → veredicto ok/bloqueado con el detalle."""
    pages = audit.get('reports') if 'reports' in audit else [audit]
    base = {normalize_signal(s) for s in budget.get('signals', [])}
    blocking = set(budget.get('blocking', ['high', 'medium']))
    actuales = {}
    for pg in pages:
        for h in pg.get('findings', []):
            actuales.setdefault(normalize_signal(h.get('signal', '')), []).append(h['severity'])
    new = sorted(s for s in actuales if s not in base)
    resueltos = sorted(base - set(actuales))
    new_blocking = [s for s in new
                          if any(sev in blocking for sev in actuales[s])]
    max_new = int(budget.get('max_new', 0))
    ok = len(new_blocking) <= max_new
    expired = False
    date = budget.get('review_date')
    if date:
        expired = (today or datetime.date.today().isoformat()) > date
    return {
        'ok': ok and not expired,
        'url': audit.get('url', budget.get('url', '')),
        'new': new,
        'new_blocking': new_blocking,
        'resolved': resueltos,
        'summary': {
            'baseline': len(base),
            'current': len(actuales),
            'new': len(new),
            'resolved': len(resueltos),
        },
        'baseline_expired': expired,
        'note': ('ok=false: there are new blocking findings (or the baseline expired). '
                 'ok=true: nothing new vs the accepted baseline — fix baseline items '
                 'and re-run --init to lower it.'),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--init', action='store_true',
                    help='genera el presupuesto desde un informe (stdin o --audit)')
    ap.add_argument('--budget', default='budget.json', help='fichero de presupuesto')
    ap.add_argument('--audit', help='informe JSON del auditor')
    ap.add_argument('--url', help='auditar esta URL al vuelo')
    a = ap.parse_args(argv)
    if a.init:
        inform = None
        if not sys.stdin.isatty():
            inform = json.loads(sys.stdin.read())
        elif a.audit:
            with open(a.audit, encoding='utf-8') as f:
                inform = json.load(f)
        if not inform:
            print('necesito el informe por stdin o --audit fichero')
            return 1
        print(json.dumps(init(inform), ensure_ascii=False, indent=1))
        return 0
    if not (a.audit or a.url):
        print('necesito --audit informe.json o --url https://…')
        return 1
    with open(a.budget, encoding='utf-8') as f:
        budget = json.load(f)
    if a.audit:
        with open(a.audit, encoding='utf-8') as f:
            report = json.load(f)
    else:
        from .a11yaudit import audit_url
        report = audit_url(a.url)
    veredicto = comparar(budget, report)
    print(json.dumps(veredicto, ensure_ascii=False, indent=1))
    return 0 if veredicto['ok'] else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
