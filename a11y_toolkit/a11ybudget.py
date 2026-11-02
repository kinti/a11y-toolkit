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

Structural budget (the same SRE doctrine applied to the RENDERED structure —
what a11y snapshot captures):

  Baseline today:   a11ytoolkit snapshot https://web --out s.json
                    a11ytoolkit budget --init-snapshot s.json > structural.json
  Compare:          a11ytoolkit budget --budget structural.json --snapshot s2.json
  Exit code: 0 ok / 2 blocked.

The baseline ACCEPTS the interactives and focus order that exist today; only
what is NEW blocks (added elements count against max_new; a lost element
contradicts the approved baseline and blocks; a reordered focus chain blocks).
Renames surface as removed+added (elements without ids are matched by
tag+name+href). Noise doctrine from fingerprints: give controls stable ids
and the budget stops counting cosmetic churn as structure.
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


def compare(budget, audit, today=None):
    """Presupuesto vs informe actual → veredicto ok/bloqueado con el detalle."""
    pages = audit.get('reports') if 'reports' in audit else [audit]
    base = {normalize_signal(s) for s in budget.get('signals', [])}
    blocking = set(budget.get('blocking', ['high', 'medium']))
    current = {}
    for pg in pages:
        for h in pg.get('findings', []):
            current.setdefault(normalize_signal(h.get('signal', '')), []).append(h['severity'])
    new = sorted(s for s in current if s not in base)
    resolved = sorted(base - set(current))
    new_blocking = [s for s in new
                          if any(sev in blocking for sev in current[s])]
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
        'resolved': resolved,
        'summary': {
            'baseline': len(base),
            'current': len(current),
            'new': len(new),
            'resolved': len(resolved),
        },
        'baseline_expired': expired,
        'note': ('ok=false: there are new blocking findings (or the baseline expired). '
                 'ok=true: nothing new vs the accepted baseline — fix baseline items '
                 'and re-run --init to lower it.'),
    }


STRUCTURAL_FORMAT = 'a11y-budget-structural/1'


def init_structural(snapshot, days=90):
    """Snapshot (a11y snapshot) → structural budget: the structure of TODAY is
    accepted. Keys are the snapshot's stable signatures (tag+name+href, or
    #id when the control has one)."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('elements'), list):
        return {'error': 'not a snapshot (use a11ytoolkit snapshot / a11y_snapshot)'}
    return {
        'format': STRUCTURAL_FORMAT,
        'url': snapshot.get('url', ''),
        'elements': sorted({e['key'] for e in snapshot['elements']
                            if isinstance(e, dict) and e.get('key')}),
        'focus_order': list(snapshot.get('focus_order', [])),
        'max_new': 0,
        'removed_block': True,
        'review_date': (datetime.date.today() + datetime.timedelta(days=days)).isoformat(),
        'generated': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def compare_structural(budget, snapshot, today=None):
    """Structural budget vs today's snapshot → verdict. Only what is NEW
    blocks: added elements (up to max_new), lost baseline elements (they
    contradict the approved baseline), reordered focus chain, expired baseline."""
    if not isinstance(budget, dict) or budget.get('format') != STRUCTURAL_FORMAT:
        return {'error': f'not a structural budget (format {STRUCTURAL_FORMAT})'}
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('elements'), list):
        return {'error': 'not a snapshot (use a11ytoolkit snapshot / a11y_snapshot)'}

    base = set(budget.get('elements', []))
    current = {e['key'] for e in snapshot['elements'] if isinstance(e, dict) and e.get('key')}
    added = sorted(current - base)
    removed = sorted(base - current)
    removed_block = bool(budget.get('removed_block', True))
    max_new = int(budget.get('max_new', 0))

    # focus chain: the RELATIVE order of the surviving common keys is the
    # invariant (same doctrine as the diff) — an appended new element is
    # governed by `added`/max_new, a reorder of the existing chain blocks
    focus_pinned = 'focus_order' in budget and budget['focus_order'] is not None
    focus_changed = False
    if focus_pinned:
        base_order = budget['focus_order']
        cur_order = snapshot.get('focus_order', [])
        base_set, cur_set = set(base_order), set(cur_order)
        focus_changed = [k for k in cur_order if k in base_set] != \
                        [k for k in base_order if k in cur_set]

    ok = (len(added) <= max_new
          and (not removed_block or not removed)
          and not focus_changed)
    expired = False
    date = budget.get('review_date')
    if date:
        expired = (today or datetime.date.today().isoformat()) > date

    return {
        'ok': ok and not expired,
        'url': snapshot.get('url', budget.get('url', '')),
        'added': added,
        'removed': removed,
        'focus_order_changed': focus_changed,
        'focus_pinned': focus_pinned,
        'summary': {
            'baseline': len(base),
            'current': len(current),
            'added': len(added),
            'removed': len(removed),
        },
        'baseline_expired': expired,
        'note': ('ok=false: structure changed against the accepted baseline '
                 '(new interactives beyond max_new, a baseline element '
                 'disappeared, or the focus chain reordered — or the baseline '
                 'expired). ok=true: the rendered structure is the approved one; '
                 'to accept a deliberate change, re-run --init-snapshot.'),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--init', action='store_true',
                    help='genera el presupuesto desde un informe (stdin o --audit)')
    ap.add_argument('--init-snapshot', dest='init_snapshot',
                    help='structural budget: baseline from a snapshot JSON (stdin if omitted)')
    ap.add_argument('--budget', default='budget.json', help='fichero de presupuesto')
    ap.add_argument('--audit', help='informe JSON del auditor')
    ap.add_argument('--snapshot', help='structural compare: today\'s snapshot JSON')
    ap.add_argument('--url', help='auditar esta URL al vuelo')
    a = ap.parse_args(argv)
    if a.init_snapshot:
        if a.init_snapshot == '-':
            snap = json.loads(sys.stdin.read())
        else:
            with open(a.init_snapshot, encoding='utf-8') as f:
                snap = json.load(f)
        b = init_structural(snap)
        if 'error' in b:
            print(json.dumps(b, ensure_ascii=False))
            return 1
        print(json.dumps(b, ensure_ascii=False, indent=1))
        return 0
    if a.init:
        inform = None
        if not sys.stdin.isatty():
            inform = json.loads(sys.stdin.read())
        elif a.audit:
            with open(a.audit, encoding='utf-8') as f:
                inform = json.load(f)
        if not inform:
            print('need the report via stdin or --audit file')
            return 1
        print(json.dumps(init(inform), ensure_ascii=False, indent=1))
        return 0
    if a.snapshot:
        with open(a.budget, encoding='utf-8') as f:
            budget = json.load(f)
        with open(a.snapshot, encoding='utf-8') as f:
            snap = json.load(f)
        verdict = compare_structural(budget, snap)
        print(json.dumps(verdict, ensure_ascii=False, indent=1))
        return 0 if verdict['ok'] else 2
    if not (a.audit or a.url):
        print('need --audit report.json or --url https://…')
        return 1
    with open(a.budget, encoding='utf-8') as f:
        budget = json.load(f)
    if a.audit:
        with open(a.audit, encoding='utf-8') as f:
            report = json.load(f)
    else:
        from .a11yaudit import audit_url
        report = audit_url(a.url)
    verdict = compare(budget, report)
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    return 0 if verdict['ok'] else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
