#!/usr/bin/env python3
"""SARIF 2.1.0 export — findings as GitHub code-scanning annotations.

Mechanism: findings travel in the OASIS interchange standard, not a bespoke
format. Upload with the official action:

  - uses: github/codeql-action/upload-sarif@v3
    with: { sarif_file: a11y.sarif }

Findings appear as repository alerts; in PRs, only new ones surface.

CLI:
  a11ysarif.py --url https://example.com -o a11y.sarif [--lang es]
  a11ysarif.py --from-audit audit.json -o a11y.sarif
"""

import argparse
import json

from .a11yaudit import normalize_signal  # noqa: E402  (compat 5.10)
import sys

from .a11yaudit import audit_url, audit_site, audit_html

LEVEL = {'high': 'error', 'medium': 'warning', 'low': 'note'}

# Criterio → Understanding URL oficial de WCAG 2.2
_UNDERSTANDING = {
    '1.1.1': 'non-text-content',
    '1.2.2': 'captions-prerecorded',
    '1.3.1': 'info-and-relationships',
    '1.3.5': 'identify-input-purpose',
    '1.4.2': 'audio-control',
    '1.4.3': 'contrast-minimum',
    '1.4.4': 'resize-text',
    '2.1.1': 'keyboard',
    '2.2.1': 'timing-adjustable',
    '2.4.1': 'bypass-blocks',
    '2.4.2': 'page-titled',
    '2.4.3': 'focus-order',
    '2.4.4': 'link-purpose-in-context',
    '2.4.7': 'focus-visible',
    '2.5.8': 'target-size-minimum',
    '3.1.1': 'language-of-page',
    '3.2.5': 'change-on-request',
    '3.3.2': 'labels-or-instructions',
    '4.1.2': 'name-role-value',
}
_BASE = 'https://www.w3.org/WAI/WCAG22/Understanding/'


def _help_uri(criterion_text):
    code = criterion_text.split(' ')[0]
    slug = _UNDERSTANDING.get(code)
    return _BASE + slug if slug else 'https://www.w3.org/TR/WCAG22/'


def from_report(report, driver_version='3.2.0'):
    """Informe(s) del auditor → dict SARIF 2.1.0.

    Acepta un informe individual (audit_html/audit_url) o uno 'site'
    (con la lista 'reports')."""
    pages = report.get('reports') if 'reports' in report else [report]
    rules = {}
    results = []
    for pg in pages:
        url = pg.get('url', '(html)')
        for h in pg.get('findings', []):
            code = h['criterion'].split(' ')[0]
            rule_id = f'WCAG-{code}-{normalize_signal(h.get("signal", ""))}'
            if rule_id not in rules:
                rules[rule_id] = {
                    'id': rule_id,
                    'shortDescription': {'text': h['criterion']},
                    'helpUri': _help_uri(h['criterion']),
                }
            message = h['issue']
            if h.get('remediation'):
                message += ' — Fix: ' + h['remediation']
            results.append({
                'ruleId': rule_id,
                'level': LEVEL.get(h['severity'], 'note'),
                'message': {'text': message},
                'locations': [{
                    'physicalLocation': {
                        'artifactLocation': {'uri': url},
                    },
                }],
            })
    return {
        '$schema': 'https://json.schemastore.org/sarif-2.1.0.json',
        'version': '2.1.0',
        'runs': [{
            'tool': {'driver': {
                'name': 'a11y-toolkit',
                'version': driver_version,
                'informationUri': 'https://github.com/kinti/a11y-toolkit',
                'rules': sorted(rules.values(), key=lambda r: r['id']),
            }},
            'results': results,
        }],
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--url')
    g.add_argument('--file', help='HTML local')
    g.add_argument('--from-audit', help='informe JSON ya generado')
    ap.add_argument('-o', '--out', default='a11y.sarif')
    ap.add_argument('--pages', type=int, default=1)
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    a = ap.parse_args(argv)
    if a.from_audit:
        with open(a.from_audit, encoding='utf-8') as f:
            report = json.load(f)
    elif a.url:
        report = (audit_site(a.url, max_pages=a.pages, lang=a.lang)
                   if a.pages > 1 else audit_url(a.url, lang=a.lang))
    else:
        with open(a.file, encoding='utf-8', errors='replace') as f:
            report = audit_html(f.read(), a.file, lang=a.lang)
    if 'error' in report:
        print(json.dumps(report))
        return 1
    sarif = from_report(report)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(sarif, f, ensure_ascii=False, indent=1)
    summary = report.get('summary', {'high': 0, 'medium': 0, 'low': 0})
    print(json.dumps({'sarif': a.out,
                      'results': len(sarif['runs'][0]['results']),
                      'score': report.get('score'),
                      'summary': summary}))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
