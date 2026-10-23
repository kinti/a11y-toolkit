#!/usr/bin/env python3
"""W3C Nu Html Checker integration — the W3C's own parser as a toolkit mode.

validar_url / validar_html call the public Nu validator
(https://validator.w3.org/nu/) REST API and map its messages to toolkit
findings. PRIVACY: validar_html POSTs the document content to the W3C
service; validar_url only shares the URL (same as a11y_audit_url).
Self-hosting (docker ghcr.io/validator/validator) is supported via
base_url for sensitive content.

CLI:
  a11yvalidate.py --url https://example.com
  a11yvalidate.py --file page.html
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request

from .a11yaudit import compute_score

BASE = 'https://validator.w3.org/nu/'
UA = 'a11y-toolkit/3.16 (WCAG audit; github.com/kinti/a11y-toolkit)'

# known Nu messages → WCAG criteria (the honest subset; the rest are
# plain HTML validity findings, reported under their own label)
_MAPPING = (
    ('must have an "alt" attribute', '1.1.1'),
    ('"lang" attribute', '3.1.1'),
    ('Bad value' and 'role', None),  # placeholder, refined below
    ('duplicate id', None),
)


def _criterion_for(message):
    m = message.lower()
    if 'alt' in m and 'img' in m:
        return '1.1.1'
    if 'lang' in m and ('html' in m or 'language' in m):
        return '3.1.1'
    if 'role' in m and ('bad value' in m or 'must not' in m):
        return '4.1.2'
    return None


def _call(data=None, url=None, timeout=60, base_url=None):
    target = (base_url or BASE).rstrip('/') + '/'
    if url:
        target += '?' + urllib.parse.urlencode({'doc': url, 'out': 'json'})
        req = urllib.request.Request(target, headers={'User-Agent': UA})
    else:
        target += '?out=json'
        req = urllib.request.Request(target, data=data.encode('utf-8'),
                                     headers={'User-Agent': UA,
                                              'Content-Type': 'text/html; charset=utf-8'},
                                     method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _process(resp, origin, lang='en'):
    findings = []
    for m in resp.get('messages', []):
        kind = m.get('type', 'info')
        if kind == 'info':
            continue
        crit = _criterion_for(m.get('message', ''))
        findings.append({
            'severity': 'medium' if kind == 'error' else 'low',
            'criterion': crit or 'HTML validity (W3C Nu)',
            'signal': 'html_invalid',
            'issue': (m.get('message', '') or '')[:220],
            'remediation': 'Fix the HTML error reported by the W3C validator'
                           if lang == 'en' else 'Corrige el error HTML reportado por el validador W3C',
            'line': m.get('lastLine'),
        })
    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])
    return {
        'url': origin,
        'mode': 'w3c-nu',
        'score': compute_score(findings),
        'summary': {s_: sum(1 for h in findings if h['severity'] == s_)
                    for s_ in ('high', 'medium', 'low')},
        'findings': findings,
        'notice': ('Report from the W3C Nu validator (validator.w3.org/nu). Complements the '
                  'toolkit audits with the W3C parser view: doctype, encoding, structural '
                  'validity. HTML validity is not WCAG by itself; mapped criteria where they '
                  'overlap are labeled.'),
    }


def validate_url(url, timeout=60, lang='en', base_url=None):
    resp = _call(url=url, timeout=timeout, base_url=base_url)
    return _process(resp, url, lang)


def validate_html(html_text, timeout=60, lang='en', base_url=None):
    resp = _call(data=html_text, timeout=timeout, base_url=base_url)
    return _process(resp, '(html posted)', lang)


def main(argv):
    ap = argparse.ArgumentParser(description='W3C Nu validator integration')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--url')
    g.add_argument('--file')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--self-hosted', help='base URL of a self-hosted vnu instance')
    a = ap.parse_args(argv)
    try:
        if a.url:
            res = validate_url(a.url, lang=a.lang, base_url=a.self_hosted)
        else:
            with open(a.file, encoding='utf-8', errors='replace') as f:
                res = validate_html(f.read(), lang=a.lang, base_url=a.self_hosted)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({'error': f'validator call failed: {e}'}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
