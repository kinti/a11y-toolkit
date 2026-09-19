#!/usr/bin/env python3
"""Disprover pattern — re-verify findings against the live page and reject those
that don't reproduce.

The Cloudflare security-audit-skill lesson: every finding deserves a fresh
verifier that tries to DISPROVE it, not confirm it. This module does that for
accessibility findings:

  1. Take an audit report
  2. For each finding, re-check the signal against the live page
  3. Findings that reproduce → estado: confirmed
  4. Findings that don't → estado: rejected + razon_rechazo

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

from a11yaudit import audit_url, audit_html


def _recheck_static(url, hallazgos, timeout=30, lang='en'):
    """Re-run the static audit and check which findings still fire."""
    informe_fresco = audit_url(url, timeout=timeout, lang=lang)
    if 'error' in informe_fresco:
        return hallazgos, informe_fresco['error']
    senales_frescas = {h['senal'] for h in informe_fresco.get('hallazgos', [])}
    verificadas = []
    for h in hallazgos:
        if h.get('senal') in senales_frescas:
            h['estado'] = 'confirmed'
        else:
            h['estado'] = 'rejected'
            h['razon_rechazo'] = (
                f"signal '{h.get('senal', '?')}' no longer fires on re-audit — "
                "the page may have changed, or the finding was a false positive")
        verificadas.append(h)
    return verificadas, None


def _recheck_rendered(url, hallazgos, timeout=45, lang='en'):
    """Re-run the rendered audit and check which findings still fire."""
    try:
        from a11ydom import audit_dom_url
    except ImportError:
        return hallazgos, "Playwright not installed"
    informe_fresco = audit_dom_url(url, timeout=timeout, lang=lang)
    if 'error' in informe_fresco:
        return hallazgos, informe_fresco['error']
    senales_frescas = {h['senal'] for h in informe_fresco.get('hallazgos', [])}
    verificadas = []
    for h in hallazgos:
        if h.get('senal') in senales_frescas:
            h['estado'] = 'confirmed'
        else:
            h['estado'] = 'rejected'
            h['razon_rechazo'] = (
                f"signal '{h.get('senal', '?')}' no longer fires in the rendered "
                "re-audit — the element may have changed, been fixed, or the "
                "first finding was a false positive")
        verificadas.append(h)
    return verificadas, None


def disprove(url, informe=None, timeout=30, lang='en'):
    """Audit a URL and disprove findings, or verify an existing report.

    Returns a report with each finding marked confirmed/rejected."""
    if informe is None:
        informe = audit_url(url, timeout=timeout, lang=lang)
        if 'error' in informe:
            return informe

    modo = informe.get('modo', 'static')
    hallazgos = informe.get('hallazgos', [])

    if modo in ('static', 'site'):
        verificadas, err = _recheck_static(url, hallazgos, timeout=timeout, lang=lang)
    elif modo == 'rendered':
        verificadas, err = _recheck_rendered(url, hallazgos, timeout=timeout, lang=lang)
    else:
        # for other modes, re-run the static audit as a proxy
        verificadas, err = _recheck_static(url, hallazgos, timeout=timeout, lang=lang)

    if err:
        return {'error': f'disprove re-audit failed: {err}'}

    resultado = dict(informe)
    resultado['hallazgos'] = verificadas
    resultado['disprover'] = {
        'ejecutado': True,
        'confirmados': sum(1 for h in verificadas if h.get('estado') == 'confirmed'),
        'rechazados': sum(1 for h in verificadas if h.get('estado') == 'rejected'),
        'nota': ('Each finding was re-checked against the live page. '
                 'Rejected findings include the reason they did not reproduce. '
                 'Confirmed findings survived a fresh verification pass.'),
    }

    # recalcular score sobre los confirmed
    from a11yaudit import calcular_score
    solo_confirmed = [h for h in verificadas if h.get('estado') == 'confirmed']
    resultado['score_original'] = informe.get('score')
    resultado['score'] = calcular_score(solo_confirmed)
    resultado['resumen'] = {
        'alta': sum(1 for h in solo_confirmed if h['severidad'] == 'alta'),
        'media': sum(1 for h in solo_confirmed if h['severidad'] == 'media'),
        'baja': sum(1 for h in solo_confirmed if h['severidad'] == 'baja'),
    }
    return resultado


def main(argv):
    ap = argparse.ArgumentParser(description='Disprover: re-verify findings against the live page')
    ap.add_argument('--url', required=True, help='URL to audit and disprove')
    ap.add_argument('--file', help='existing report JSON (optional; if absent, audits first)')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--timeout', type=int, default=30)
    ap.add_argument('-o', '--out', help='save result JSON here')
    a = ap.parse_args(argv)
    informe = None
    if a.file:
        with open(a.file, encoding='utf-8') as f:
            informe = json.load(f)
    res = disprove(a.url, informe=informe, timeout=a.timeout, lang=a.lang)
    if 'error' in res:
        print(json.dumps(res))
        return 1
    salida = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(salida)
        print(json.dumps({'fichero': a.out, **res['disprover']}))
    else:
        print(salida)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
