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

from .a11yaudit import calcular_score

BASE = 'https://validator.w3.org/nu/'
UA = 'a11y-toolkit/3.16 (WCAG audit; github.com/kinti/a11y-toolkit)'

# known Nu messages → WCAG criteria (the honest subset; the rest are
# plain HTML validity findings, reported under their own label)
_MAPEO = (
    ('must have an "alt" attribute', '1.1.1'),
    ('"lang" attribute', '3.1.1'),
    ('Bad value' and 'role', None),  # placeholder, refined below
    ('duplicate id', None),
)


def _criterio_de(mensaje):
    m = mensaje.lower()
    if 'alt' in m and 'img' in m:
        return '1.1.1'
    if 'lang' in m and ('html' in m or 'language' in m):
        return '3.1.1'
    if 'role' in m and ('bad value' in m or 'must not' in m):
        return '4.1.2'
    return None


def _llamar(data=None, url=None, timeout=60, base_url=None):
    destino = (base_url or BASE).rstrip('/') + '/'
    if url:
        destino += '?' + urllib.parse.urlencode({'doc': url, 'out': 'json'})
        req = urllib.request.Request(destino, headers={'User-Agent': UA})
    else:
        destino += '?out=json'
        req = urllib.request.Request(destino, data=data.encode('utf-8'),
                                     headers={'User-Agent': UA,
                                              'Content-Type': 'text/html; charset=utf-8'},
                                     method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _procesar(resp, origen, lang='en'):
    hallazgos = []
    for m in resp.get('messages', []):
        tipo = m.get('type', 'info')
        if tipo == 'info':
            continue
        crit = _criterio_de(m.get('message', ''))
        hallazgos.append({
            'severidad': 'media' if tipo == 'error' else 'baja',
            'criterio': crit or 'HTML validity (W3C Nu)',
            'senal': 'html_invalid',
            'hallazgo': (m.get('message', '') or '')[:220],
            'remediacion': 'Fix the HTML error reported by the W3C validator'
                           if lang == 'en' else 'Corrige el error HTML reportado por el validador W3C',
            'linea': m.get('lastLine'),
        })
    orden = {'alta': 0, 'media': 1, 'baja': 2}
    hallazgos.sort(key=lambda h: orden[h['severidad']])
    return {
        'url': origen,
        'modo': 'w3c-nu',
        'score': calcular_score(hallazgos),
        'resumen': {s_: sum(1 for h in hallazgos if h['severidad'] == s_)
                    for s_ in ('alta', 'media', 'baja')},
        'hallazgos': hallazgos,
        'aviso': ('Report from the W3C Nu validator (validator.w3.org/nu). Complements the '
                  'toolkit audits with the W3C parser view: doctype, encoding, structural '
                  'validity. HTML validity is not WCAG by itself; mapped criteria where they '
                  'overlap are labeled.'),
    }


def validar_url(url, timeout=60, lang='en', base_url=None):
    resp = _llamar(url=url, timeout=timeout, base_url=base_url)
    return _procesar(resp, url, lang)


def validar_html(html_text, timeout=60, lang='en', base_url=None):
    resp = _llamar(data=html_text, timeout=timeout, base_url=base_url)
    return _procesar(resp, '(html posted)', lang)


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
            res = validar_url(a.url, lang=a.lang, base_url=a.self_hosted)
        else:
            with open(a.file, encoding='utf-8', errors='replace') as f:
                res = validar_html(f.read(), lang=a.lang, base_url=a.self_hosted)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({'error': f'validator call failed: {e}'}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
