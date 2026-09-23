#!/usr/bin/env python3
"""Accessibility error budget — Google SRE's lesson applied to WCAG.

The classic paralysis: the audit finds 40 issues, nobody can fix them this
week, so nobody turns the control on. The budget breaks the deadlock: today's
baseline is ACCEPTED and only what is NEW blocks. Every fix lowers the
baseline; every regression screams.

Budget file (budget.json):

  {
    "url": "https://mysite",
    "signals": ["imgs_alt", "field_label"],       // accepted baseline
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
import sys


def init(auditoria):
    """Informe (o site) → fichero de presupuesto inicial."""
    paginas = auditoria.get('reports') if 'reports' in auditoria else [auditoria]
    senales = sorted({h['signal'] for pg in paginas for h in pg.get('findings', [])})
    return {
        'url': auditoria.get('url', ''),
        'signals': senales,
        'blocking': ['high', 'medium'],
        'max_new': 0,
        'review_date': (datetime.date.today() + datetime.timedelta(days=90)).isoformat(),
    }


def comparar(presupuesto, auditoria, hoy=None):
    """Presupuesto vs informe actual → veredicto ok/bloqueado con el detalle."""
    paginas = auditoria.get('reports') if 'reports' in auditoria else [auditoria]
    base = set(presupuesto.get('signals', []))
    bloqueantes = set(presupuesto.get('blocking', ['high', 'medium']))
    actuales = {}
    for pg in paginas:
        for h in pg.get('findings', []):
            actuales.setdefault(h['signal'], []).append(h['severity'])
    nuevos = sorted(s for s in actuales if s not in base)
    resueltos = sorted(base - set(actuales))
    nuevos_bloqueantes = [s for s in nuevos
                          if any(sev in bloqueantes for sev in actuales[s])]
    max_nuevos = int(presupuesto.get('max_new', 0))
    ok = len(nuevos_bloqueantes) <= max_nuevos
    caducada = False
    fecha = presupuesto.get('review_date')
    if fecha:
        caducada = (hoy or datetime.date.today().isoformat()) > fecha
    return {
        'ok': ok and not caducada,
        'url': auditoria.get('url', presupuesto.get('url', '')),
        'new': nuevos,
        'new_blocking': nuevos_bloqueantes,
        'resolved': resueltos,
        'summary': {
            'baseline': len(base),
            'current': len(actuales),
            'new': len(nuevos),
            'resolved': len(resueltos),
        },
        'baseline_expired': caducada,
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
        presupuesto = json.load(f)
    if a.audit:
        with open(a.audit, encoding='utf-8') as f:
            informe = json.load(f)
    else:
        from .a11yaudit import audit_url
        informe = audit_url(a.url)
    veredicto = comparar(presupuesto, informe)
    print(json.dumps(veredicto, ensure_ascii=False, indent=1))
    return 0 if veredicto['ok'] else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
