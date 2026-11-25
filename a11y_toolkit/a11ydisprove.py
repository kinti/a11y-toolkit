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

import sys

from .a11yaudit import audit_url, normalize_signal, page_identity


def _recheck(url, expected_url, findings, timeout, lang, color_scheme=None):
    """Compare findings only after a successful visit to the same page."""
    if color_scheme is None:
        fresh = audit_url(url, timeout=timeout, lang=lang)
    else:
        from .a11ydom import audit_dom_url
        fresh = audit_dom_url(url, timeout=timeout, lang=lang, color_scheme=color_scheme)
    if 'error' in fresh:
        return findings, fresh['error']
    if page_identity(fresh.get('url')) != page_identity(expected_url):
        return findings, ('La reauditoría terminó en una URL distinta de la del informe original.'
                          if lang == 'es' else
                          'The re-audit ended at a different URL from the original report.')

    signals = {h['signal'] for h in fresh['findings']}
    rejected = ('La señal {signal!r} ya no aparece en la nueva auditoría de la página.'
                if lang == 'es' else
                'Signal {signal!r} no longer fires in the new audit of the page.')
    verified = []
    for finding in findings:
        checked = dict(finding)
        checked.pop('disprover_status', None)
        checked.pop('reject_reason', None)
        if normalize_signal(checked.get('signal', '')) in signals:
            checked['status'] = 'confirmed'
        else:
            checked['status'] = 'rejected'
            checked['reject_reason'] = rejected.format(signal=checked.get('signal', '?'))
        verified.append(checked)
    return verified, None


def disprove(url, report=None, timeout=30, lang='en'):
    """Audit a URL and disprove findings, or verify an existing report.

    Returns a report with each finding marked confirmed/rejected."""
    if report is None:
        report = audit_url(url, timeout=timeout, lang=lang)
    if report.get('error'):
        return report
    mode_name = report.get('mode', 'static')
    expected_url = report.get('url') or url
    findings = report.get('findings', [])

    if mode_name == 'site':
        # site reports nest findings INSIDE each page: re-checking them against
        # ONE url marked everything 'rejected' and scored 100 on unreviewed
        # evidence. Honest path: not-rechecked per page, with the pointer to
        # re-verify each page properly.
        if not findings:
            findings = [dict(h, page=page.get('url', '')) for page in report.get('reports', [])
                        for h in page.get('findings', [])]
        res = dict(report)
        res['findings'] = [dict(h, disprover_status='not-rechecked') for h in findings]
        res['disprover'] = {'executed': False,
                            'reason': ('site mode: each finding belongs to a page; '
                                       're-verify with a11ydisprove --url <page> '
                                       '--file <that page report>')}
        return res

    if mode_name == 'static':
        verified, err = _recheck(url, expected_url, findings, timeout, lang)
    elif mode_name == 'rendered':
        # condición necesaria: el esquema de color bajo el que se auditó. Sin
        # él no se reverifica (rechazar un contrast_fail de dark mode tras
        # mirar la página en claro es exactamente el falso «arreglado» que
        # este patrón existe para impedir)
        scheme = report.get('color_scheme') or report.get('scheme')
        if scheme not in ('light', 'dark'):
            res = dict(report)
            res['findings'] = [dict(h, disprover_status='not-rechecked') for h in findings]
            res['disprover'] = {
                'executed': False,
                'reason': ('the rendered report does not record its color_scheme '
                           '— re-verifying under a different condition could reject '
                           'real findings (a dark-only contrast fail looks fixed '
                           'under light); re-audit with a11y_audit_dom and disprove '
                           'THAT report')}
            return res
        verified, err = _recheck(url, expected_url, findings, timeout, lang, color_scheme=scheme)
    else:
        # no re-verifier for this mode: report not-rechecked, never a proxy
        # audit (a keyboard finding must not vanish just because the wrong
        # method ran). `rejected` is reserved for an equivalent check that
        # actually disproves the original finding.
        res = dict(report)
        res['findings'] = [dict(h, disprover_status='not-rechecked') for h in findings]
        res['disprover'] = {'executed': False,
                            'reason': f"no re-verifier for mode {mode_name!r}"}
        return res

    if err:
        return dict(report, error=err, disprover={'executed': False, 'reason': err})

    result = dict(report)
    result['findings'] = verified
    result['disprover'] = {
        'executed': True,
        'confirmed': sum(1 for h in verified if h.get('status') == 'confirmed'),
        'rejected': sum(1 for h in verified if h.get('status') == 'rejected'),
        'note': ('Each finding was re-checked against the live page. '
                 'Rejected findings include the reason they did not reproduce. '
                 'Confirmed findings survived a fresh verification pass.'),
    }

    # recalcular score sobre los confirmed
    from .a11yaudit import compute_score
    solo_confirmed = [h for h in verified if h.get('status') == 'confirmed']
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
