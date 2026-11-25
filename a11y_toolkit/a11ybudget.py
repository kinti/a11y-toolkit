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

Generate the baseline:  a11ytoolkit budget --init --audit today.json
Compare with:           a11ytoolkit budget --budget budget.json --audit audit.json
Exit code: 0 ok / 1 incomplete or invalid / 2 blocked.

New baselines compare by page, signal and element path or measured count.
Existing signal-only baselines retain their original comparison.

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
from collections import Counter

from .a11yaudit import audit_conditions, audit_conditions_match, completed_report_pages, normalize_signal
import sys

# mensajes CLI bilingües (patrón _labels): el stdin de --init espera el JSON
# del informe de auditoría — un input vacío/corrupto debe decir QUÉ espera,
# no tronar con un traceback
_CLI_MSG = {
    'es': {'stdin_json': ('stdin no contiene un JSON de informe válido — '
                          'esperado: la salida de `a11ytoolkit audit` '
                          '(p. ej. {"url": …, "score": …, "findings": […]}) '
                          'por tubería, o usa --audit fichero.json')},
    'en': {'stdin_json': ('stdin is not a valid audit-report JSON — expected: '
                          'the output of `a11ytoolkit audit` (e.g. {"url": …, '
                          '"score": …, "findings": […]}), or pass '
                          '--audit report.json instead')},
}


BUDGET_FORMAT = 'a11y-budget/2'


def _active_findings(page):
    for finding in page['findings']:
        if not isinstance(finding, dict):
            raise ValueError('invalid finding')
        if finding.get('status') != 'rejected' and finding.get('disprover_status') != 'rejected':
            yield finding


def _page_index(pages):
    result = {}
    for page in pages:
        url = page.get('url')
        if not isinstance(url, str) or not url or url in result:
            raise ValueError('every audited page must have a unique URL')
        findings = {}
        for finding in _active_findings(page):
            signal = normalize_signal(finding['signal'])
            paths = [path for path in (finding.get('paths') or []) if isinstance(path, str)]
            count = finding.get('count')
            if type(count) is not int or count < 1:
                count = max(len(paths), len(finding.get('examples') or []), 1)
            findings[signal] = {'severity': finding['severity'], 'count': max(count, len(paths)),
                                'paths': sorted(paths)}
        result[url] = {'mode': page.get('mode', 'static'), 'conditions': audit_conditions(page),
                       'findings': findings}
    return result


def init(audit):
    """Build a page- and instance-scoped baseline from a complete audit."""
    pages, error = completed_report_pages(audit)
    if error:
        return error
    try:
        index = _page_index(pages)
    except (ValueError, KeyError, TypeError) as err:
        return {'error': f'invalid budget input: {err}'}
    return {
        'format': BUDGET_FORMAT,
        'url': audit.get('url', ''),
        'signals': sorted({signal for page in index.values() for signal in page['findings']}),
        'pages': index,
        'blocking': ['high', 'medium'],
        'max_new': 0,
        'review_date': (datetime.date.today() + datetime.timedelta(days=90)).isoformat(),
    }


def _instance_delta(before, after):
    before_count = before['count'] if before else 0
    after_count = after['count'] if after else 0
    before_paths = (before or {}).get('paths', [])
    after_paths = (after or {}).get('paths', [])
    old, new = Counter(before_paths), Counter(after_paths)
    before_missing = max(0, before_count - len(before_paths))
    after_missing = max(0, after_count - len(after_paths))
    added_paths = sum((new - old).values())
    removed_paths = sum((old - new).values())
    if not before_missing and not after_missing:
        return added_paths, removed_paths, 'paths'
    # A path observed on one side could be among the hidden paths on the other.
    # Any excess over those hidden slots is still a demonstrated change.
    added_by_count = max(0, after_count - before_count)
    removed_by_count = max(0, before_count - after_count)
    added = max(added_by_count, added_paths - before_missing)
    removed = max(removed_by_count, removed_paths - after_missing)
    basis = 'partial-paths' if (added, removed) != (added_by_count, removed_by_count) else 'count'
    return added, removed, basis


def _compare_instances(budget, pages, blocking):
    base = budget['pages']
    missing = sorted(set(base) - set(pages))
    if missing:
        return {'error': 'baseline pages were not audited', 'pages_missing': missing}
    changes = []
    for url, page in sorted(pages.items()):
        prior = base.get(url)
        if prior and prior['mode'] != page['mode']:
            return {'error': 'the audit mode changed for a baseline page', 'url': url}
        if prior and not audit_conditions_match(page['mode'], prior.get('conditions', {}),
                                                page['conditions']):
            return {'error': 'the capture conditions changed or were not recorded in the baseline',
                    'url': url}
        old = prior['findings'] if prior else {}
        current = page['findings']
        for signal in sorted(set(old) | set(current)):
            before, after = old.get(signal), current.get(signal)
            added, removed, basis = _instance_delta(before, after)
            added_blocking = 0
            if after and after['severity'] in blocking:
                added_blocking = added if before and before['severity'] in blocking else after['count']
            if added or removed or added_blocking:
                changes.append({'url': url, 'signal': signal, 'new': added,
                                'resolved': removed, 'new_blocking': added_blocking,
                                'basis': basis})
    return {
        'new': sorted({change['signal'] for change in changes if change['new']}),
        'resolved': sorted({change['signal'] for change in changes if change['resolved']}),
        'new_blocking': sorted({change['signal'] for change in changes if change['new_blocking']}),
        'new_blocking_count': sum(change['new_blocking'] for change in changes),
        'changes': changes,
    }


def _compare_signals(budget, pages, blocking):
    """Keep the original comparison for existing signal-only baselines."""
    base = {normalize_signal(s) for s in budget.get('signals', [])}
    current = {}
    for pg in pages:
        for h in _active_findings(pg):
            current.setdefault(normalize_signal(h.get('signal', '')), []).append(h['severity'])
    new = sorted(s for s in current if s not in base)
    resolved = sorted(base - set(current))
    new_blocking = [s for s in new
                          if any(sev in blocking for sev in current[s])]
    return {'new': new, 'resolved': resolved, 'new_blocking': new_blocking,
            'new_blocking_count': len(new_blocking)}


def compare(budget, audit, today=None):
    """Compare a complete run against the active baseline."""
    pages, error = completed_report_pages(audit)
    if error:
        return error
    if not isinstance(budget, dict) or budget.get('format') not in (None, BUDGET_FORMAT):
        return {'error': 'not a compatible findings budget'}
    try:
        blocking = set(budget.get('blocking', ['high', 'medium']))
        max_new = int(budget.get('max_new', 0))
        signals = {normalize_signal(h['signal']) for pg in pages for h in _active_findings(pg)}
        if budget.get('format') == BUDGET_FORMAT:
            verdict = _compare_instances(budget, _page_index(pages), blocking)
        else:
            if any(p.get('mode') == 'rendered' for p in pages):
                return {'error': 'a rendered audit needs a baseline with recorded capture conditions'}
            verdict = _compare_signals(budget, pages, blocking)
    except (ValueError, KeyError, TypeError) as err:
        return {'error': f'invalid budget input: {err}'}
    if 'error' in verdict:
        return verdict
    ok = verdict['new_blocking_count'] <= max_new
    expired = False
    date = budget.get('review_date')
    if date:
        expired = (today or datetime.date.today().isoformat()) > date
    return {
        'ok': ok and not expired,
        'url': audit.get('url', budget.get('url', '')),
        **verdict,
        'summary': {
            'baseline': len(set(budget.get('signals', []))),
            'current': len(signals),
            'new': len(verdict['new']),
            'resolved': len(verdict['resolved']),
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
        if a.audit:
            with open(a.audit, encoding='utf-8') as f:
                inform = json.load(f)
        elif not sys.stdin.isatty():
            try:
                inform = json.loads(sys.stdin.read())
            except json.JSONDecodeError:
                # stdin vacío/corrupto (no-tty): decir qué se espera, no un
                # traceback — el JSON del informe, con la forma de arriba
                print(json.dumps({'error': _CLI_MSG['en']['stdin_json']},
                                 ensure_ascii=False))
                return 1
        if not inform:
            print('need the report via stdin or --audit file')
            return 1
        baseline = init(inform)
        print(json.dumps(baseline, ensure_ascii=False, indent=1))
        return 1 if 'error' in baseline else 0
    if a.snapshot:
        with open(a.budget, encoding='utf-8') as f:
            budget = json.load(f)
        with open(a.snapshot, encoding='utf-8') as f:
            snap = json.load(f)
        verdict = compare_structural(budget, snap)
        if 'error' in verdict:
            # presupuesto no-estructural / snapshot malformado: error de USO
            # limpio (exit 1), no un KeyError 'ok' con traceback
            print(json.dumps(verdict, ensure_ascii=False, indent=1))
            return 1
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
    if 'error' in verdict:
        # informe fallido/malformado: error de EJECUCIÓN (exit 1), jamás un
        # verde — el gate presupuestario no puede declarar resuelto lo que no
        # llegó a mirar
        print(json.dumps(verdict, ensure_ascii=False, indent=1))
        return 1
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    return 0 if verdict['ok'] else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
