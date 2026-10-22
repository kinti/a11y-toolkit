#!/usr/bin/env python3
"""ACT Rules mapping + EARL export — interoperability with the W3C ecosystem.

- ACT_MAP: toolkit signal → published ACT rule(s) (act-rules.github.io), only
  where a rule directly corresponds. Partial by design and documented: signals
  without a published counterpart stay toolkit-specific (honest boundary,
  never invented rules).
- earl(informe): EARL 1.0 JSON-LD assertions (earl:failed / earl:cantTell) for
  findings whose signal has an ACT mapping. Automated findings only; the
  absence of findings is NEVER asserted as pass (the pack's not-flagged rule).

CLI:
  a11yact.py --url https://example.com -o earl.json     # audits first
  a11yact.py --from-audit audit.json -o earl.json       # from a report
  a11yact.py --list                                     # print the map
"""

import argparse
import json

from .a11yaudit import normalize_signal  # noqa: E402  (compat 5.10)
import sys
from datetime import datetime, timezone

# señal del toolkit → [(id ACT, nombre de la regla)] — curado, solo reglas
# publicadas en act-rules.github.io/rules/<id>/ que corresponden directamente.
ACT_MAP = {
    'img_no_alt': [('23a2a8', 'Image has non-empty accessible name')],
    'input_img_alt': [('59796f', 'Image button has non-empty accessible name')],
    'ctrl_name': [('97a4e1', 'Button has non-empty accessible name'),
                  ('c487ae', 'Link has non-empty accessible name')],
    'field_label': [('e086e5', 'Form field has non-empty accessible name')],
    'placeholder_only': [('e086e5', 'Form field has non-empty accessible name')],
    'label_in_name': [('2ee8b8', 'Visible label is part of accessible name')],
    'empty_heading': [('ffd0e9', 'Heading has non-empty accessible name')],
    'iframe_title': [('cae760', 'iframe element has non-empty accessible name')],
    'aria_hidden_focusable': [('6cfa84', 'Element with aria-hidden has no focusable content')],
    'aria_value_invalid': [('6a7281', 'ARIA state or property has valid value')],
    'role_unknown': [('674b10', 'Role attribute has valid value')],
    'lang_missing': [('b5c3f8', 'HTML page has lang attribute')],
    'lang_invalid': [('bf051a', 'HTML page lang attribute has valid language tag')],
    'element_lang_invalid': [('de46e4', 'Element with lang attribute has valid language tag')],
    'title_missing': [('2779a5', 'HTML page has non-empty title')],
    'meta_refresh': [('bc659a', 'Meta element has no refresh delay')],
    'zoom_max': [('b4f0c3', 'Meta viewport does not prevent zoom')],
    'zoom_no': [('b4f0c3', 'Meta viewport does not prevent zoom')],
    'no_bypass': [('3e12e1', 'Block of repeated content is collapsible')],
    'dup_ids': [('3ea0c8', 'id attribute value is unique')],
    'autocomplete': [('73f2c2', 'autocomplete attribute has valid value')],
    'contrast_fail': [('afw4f7', 'Text has minimum contrast')],
}

# Notas de honestidad por señal (solapes aproximados declarados)
ACT_NOTES = {
    'ctrl_name': 'toolkit signal covers a/button/summary; the two ACT rules map by element role',
    'placeholder_only': 'placeholder is not an accessible name under the ACT rule',
    'dup_ids': 'ACT rule references WCAG 2.0/2.1 4.1.1 (removed in WCAG 2.2); kept as a parsing-quality signal',
    'contrast_fail': ('ACT rule assumes solid backgrounds; the toolkit measurement '
                      'composes effective backgrounds with alpha — approximate overlap'),
    'autocomplete': ('ACT rule validates the attribute value; the toolkit flags missing '
                     'autocomplete on user-data fields (1.3.5 intent)'),
    'no_bypass': 'toolkit signal is a bypass-mechanism heuristic (skip link/main); the ACT rule verifies the technique',
}

_EARL_CTX = {
    'earl': 'http://www.w3.org/ns/earl#',
    'dct': 'http://purl.org/dc/terms/',
    'url': 'dct:source',
    'title': 'dct:title',
    'date': 'dct:date',
}

_NOT_DEAD = {'rejected', 'not-rechecked'}


def act_ids(signal):
    """ACT rule ids para una señal (lista; vacía si no hay correspondencia publicada)."""
    return [rid for rid, _n in ACT_MAP.get(signal, [])]


def earl(report, url=None):
    """Informe de auditoría → EARL 1.0 JSON-LD (solo hallazgos con mapeo ACT)."""
    assertions = []
    for h in report.get('findings', []):
        if h.get('status') in _NOT_DEAD or h.get('disprover_status') in _NOT_DEAD:
            continue
        rules = ACT_MAP.get(normalize_signal(h.get('signal', '')))
        if not rules:
            continue
        outcome = 'earl:failed' if h.get('severity') in ('high', 'medium') else 'earl:cantTell'
        for rid, name in rules:
            assertions.append({
                '@type': 'earl:Assertion',
                'earl:subject': {'@type': 'earl:TestSubject',
                                 'url': url or report.get('url', '')},
                'earl:test': {'@type': 'earl:TestCase',
                              'url': f'https://act-rules.github.io/rules/{rid}/',
                              'title': name},
                'earl:result': {'@type': 'earl:TestResult',
                                'outcome': outcome,
                                'date': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                                'description': (h.get('issue') or '')[:300]},
                'earl:mode': 'earl:automatic',
                'earl:assertedBy': {'@type': 'earl:Software', 'title': 'a11y-toolkit'},
            })
    return {
        '@context': _EARL_CTX,
        '@graph': assertions,
        'meta': {
            'tool': 'a11y-toolkit',
            'url': url or report.get('url', ''),
            'note': ('Only failed/cantTell findings are asserted; absence is never '
                     'asserted as pass. ACT coverage is partial by design — see ACT_MAP '
                     'and ACT_NOTES in a11yact.py.'),
            'coverage': {'mapped_signals': len(ACT_MAP),
                         'assertions': len(assertions)},
        },
    }


def main(argv):
    ap = argparse.ArgumentParser(description='ACT Rules mapping + EARL export')
    ap.add_argument('--url', help='URL to audit first (static pass)')
    ap.add_argument('--from-audit', help='existing audit report JSON')
    ap.add_argument('--list', action='store_true', help='print the signal → ACT rule map')
    ap.add_argument('-o', '--out', help='write EARL JSON here (default: stdout)')
    a = ap.parse_args(argv)
    if a.list:
        print(json.dumps({'act_map': ACT_MAP, 'act_notes': ACT_NOTES},
                         ensure_ascii=False, indent=1))
        return 0
    if a.from_audit:
        report = json.load(open(a.from_audit, encoding='utf-8'))
    elif a.url:
        from .a11yaudit import audit_url
        report = audit_url(a.url)
    else:
        ap.print_help()
        return 2
    res = earl(report, url=a.url)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        print(json.dumps({'earl': a.out, 'assertions': res['meta']['coverage']['assertions']}))
    else:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
