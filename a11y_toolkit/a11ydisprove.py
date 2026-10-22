#!/usr/bin/env python3
"""Disprover pattern — re-verify findings against the live page and reject those
that don't reproduce.

The Cloudflare security-audit-skill lesson: every finding deserves a fresh
verifier that tries to DISPROVE it, not confirm it. This module does that for
accessibility findings:

  1. Take an audit report
  2. For each finding, re-check the signal against the live page
  3. Findings that reproduce → estado: confirmed
  4. Findings that don't → estado: rejected + reject_reason

This catches:
  - False positives (the element changed, was fixed, or never existed)
  - Race conditions (page was different when first audited)
  - Rendering differences (element is hidden, removed, or in a different context)

CLI:
  a11ydisprove.py --url https://example.com --file report.json
  a11ydisprove.py --url https://example.com  # audit + disprove in one call
"""

import argparse
import json

from .a11yaudit import normalize_signal  # noqa: E402  (compat 5.10)
import sys

from .a11yaudit import audit_url, audit_html


def _recheck_static(url, findings, timeout=30, lang='en'):
    """Re-run the static audit and check which findings still fire."""
    fresh_report = audit_url(url, timeout=timeout, lang=lang)
    if 'error' in fresh_report:
        return findings, fresh_report['error']
    fresh_signals = {h['signal'] for h in fresh_report.get('findings', [])}
    verificadas = []
    for h in findings:
        if normalize_signal(h.get('signal', '')) in fresh_signals:
            h['status'] = 'confirmed'
        else:
            h['status'] = 'rejected'
            h['reject_reason'] = (
                f"signal '{h.get('signal', '?')}' no longer fires on re-audit — "
                "the page may have changed, or the finding was a false positive")
        verificadas.append(h)
    return verificadas, None


def _recheck_rendered(url, findings, timeout=45, lang='en'):
    """Re-run the rendered audit and check which findings still fire."""
    try:
        from .a11ydom import audit_dom_url
    except ImportError:
        return findings, "Playwright not installed"
    fresh_report = audit_dom_url(url, timeout=timeout, lang=lang)
    if 'error' in fresh_report:
        return findings, fresh_report['error']
    fresh_signals = {h['signal'] for h in fresh_report.get('findings', [])}
    verificadas = []
    for h in findings:
        if normalize_signal(h.get('signal', '')) in fresh_signals:
            h['status'] = 'confirmed'
        else:
            h['status'] = 'rejected'
            h['reject_reason'] = (
                f"signal '{h.get('signal', '?')}' no longer fires in the rendered "
                "re-audit — the element may have changed, been fixed, or the "
                "first finding was a false positive")
        verificadas.append(h)
    return verificadas, None


def disprove(url, report=None, timeout=30, lang='en'):
    """Audit a URL and disprove findings, or verify an existing report.

    Returns a report with each finding marked confirmed/rejected."""
    if report is None:
        report = audit_url(url, timeout=timeout, lang=lang)
        if 'error' in report:
            return report

    modo = report.get('mode', 'static')
    findings = report.get('findings', [])

    if modo in ('static', 'site'):
        verificadas, err = _recheck_static(url, findings, timeout=timeout, lang=lang)
    elif modo == 'rendered':
        verificadas, err = _recheck_rendered(url, findings, timeout=timeout, lang=lang)
    else:
        # no re-verifier for this mode: report not-rechecked, never a proxy
        # audit (a keyboard finding must not vanish just because the wrong
        # method ran). `rejected` is reserved for an equivalent check that
        # actually disproves the original finding.
        res = dict(report)
        res['findings'] = [dict(h, disprover_status='not-rechecked') for h in findings]
        res['disprover'] = {'executed': False,
                            'reason': f"no re-verifier for mode {modo!r}"}
        return res

    if err:
        return {'error': f'disprove re-audit failed: {err}'}

    result = dict(report)
    result['findings'] = verificadas
    result['disprover'] = {
        'executed': True,
        'confirmed': sum(1 for h in verificadas if h.get('status') == 'confirmed'),
        'rejected': sum(1 for h in verificadas if h.get('status') == 'rejected'),
        'note': ('Each finding was re-checked against the live page. '
                 'Rejected findings include the reason they did not reproduce. '
                 'Confirmed findings survived a fresh verification pass.'),
    }

    # recalcular score sobre los confirmed
    from .a11yaudit import compute_score
    solo_confirmed = [h for h in verificadas if h.get('status') == 'confirmed']
    result['score_original'] = report.get('score')
    result['score'] = compute_score(solo_confirmed)
    result['summary'] = {
        'high': sum(1 for h in solo_confirmed if h['severity'] == 'high'),
        'medium': sum(1 for h in solo_confirmed if h['severity'] == 'medium'),
        'low': sum(1 for h in solo_confirmed if h['severity'] == 'low'),
    }
    return result


def main(argv):
    ap = argparse.ArgumentParser(description='Disprover: re-verify findings against the live page')
    ap.add_argument('--url', required=True, help='URL to audit and disprove')
    ap.add_argument('--file', help='existing report JSON (optional; if absent, audits first)')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--timeout', type=int, default=30)
    ap.add_argument('-o', '--out', help='save result JSON here')
    a = ap.parse_args(argv)
    report = None
    if a.file:
        with open(a.file, encoding='utf-8') as f:
            report = json.load(f)
    res = disprove(a.url, report=report, timeout=a.timeout, lang=a.lang)
    if 'error' in res:
        print(json.dumps(res))
        return 1
    output = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(output)
        print(json.dumps({'file': a.out, **res['disprover']}))
    else:
        print(output)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
