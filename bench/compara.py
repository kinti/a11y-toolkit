#!/usr/bin/env python3
"""Bench a11y-toolkit vs axe-core sobre páginas REALES.

Ejecuta en la MISMA página de Chromium, con el MISMO Playwright:
  1. a11y_audit (estático sobre el HTML servido)
  2. a11y_audit_dom (renderizado, nuestro colector)
  3. axe-core 4.10 (el estándar de facto) — inyectado y ejecutado igual

Salida: comparación por página — qué caza cada uno, solapamiento y divergencias.
Este script es la prueba de que las afirmaciones del toolkit están contrastadas.

CLI:  python3 bench/compara.py https://www.gov.uk [otra-url ...]
      python3 bench/compara.py --check bench/results.json [--expect 4] [url ...]
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import urlsplit

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
sys.path.insert(0, AQUI)

import browser  # noqa: E402  (bench/browser.py: pool loan + axe-core lookup)
from a11y_toolkit.a11yaudit import audit_url, page_identity  # noqa: E402
from a11y_toolkit.a11ydom import audit_dom_url  # noqa: E402

_ENGINES = ('toolkit_static', 'toolkit_rendered', 'axe')

_WCAG_TAG = re.compile(r'wcag([1-4])([0-9])([0-9]{1,2})')


def _page_url(url):
    if not url:
        return None
    parts = urlsplit(url)
    return parts._replace(path=parts.path or '/', fragment='').geturl()


def axe_en_pagina(page, axe_js=None):
    bruto = browser.axe_run(page, axe_js or browser.load_axe(download=True))
    # el formato de results/ guarda las claves de cada regla en español
    # (nodos, impacto): se traduce aquí, en la costura con el módulo compartido
    bruto['violations'] = [{'id': v['id'], 'nodos': v['nodes'], 'impacto': v['impact'],
                            'tags': v['tags'], 'targets': v['targets']}
                           for v in bruto['violations']]
    return bruto


from a11y_toolkit.a11ycrit import _C as _CRITERION_LEVELS  # noqa: E402

# Lo que el toolkit audita: WCAG 2.2 A y AA (la tabla del propio motor). axe
# etiqueta además criterios AAA y obsoletos (1.4.6, 2.4.9, 4.1.1): entraban en
# `solo_axe` como si fueran huecos nuestros (revisión 2026-11-25)
_AA = frozenset(code for code, (level, _) in _CRITERION_LEVELS.items() if level in ('A', 'AA'))


def _axe_criteria(violation):
    criteria = set()
    for tag in violation.get('tags', []):
        match = _WCAG_TAG.fullmatch(tag)
        if match:
            criteria.add('.'.join(match.groups()))
    return criteria


def axe_a_criterios(bruto):
    """Criterios WCAG 2.2 A/AA que axe encontró → [(regla, nodos, impacto)]."""
    out = {}
    for v in bruto['violations']:
        for crit in sorted(_axe_criteria(v) & _AA):
            out.setdefault(crit, []).append((v['id'], v['nodos'], v['impacto']))
    return out


def axe_out_of_scope(bruto):
    """Criterios que axe etiquetó y el bench deja fuera (AAA, obsoletos): se
    listan en la fila en vez de desaparecer en silencio."""
    out = set()
    for v in bruto['violations']:
        out |= _axe_criteria(v) - _AA
    return sorted(out, key=lambda code: tuple(int(part) for part in code.split('.')))


def compara(url, lang='en'):
    informe_estatico = audit_url(url, lang=lang)
    if 'error' in informe_estatico:
        raise RuntimeError(f"estático falló: {informe_estatico['error']}")
    informe_dom = audit_dom_url(url, lang=lang)
    if 'error' in informe_dom:
        # un error del motor NO es "cero hallazgos": una run fallida que
        # parece limpia es el peor falso verde que existe (hallado en la
        # revisión externa de nov-2026)
        raise RuntimeError(f"renderizado falló: {informe_dom['error']}")
    static_url = _page_url(informe_estatico.get('url'))
    toolkit_url = _page_url(informe_dom.get('url'))
    target_page = page_identity(toolkit_url)
    if not isinstance(target_page, tuple) or page_identity(static_url) != target_page:
        raise RuntimeError(
            f'estático terminó en {static_url} y renderizado en {toolkit_url}: no es la misma página')
    # axe corre en el MISMO navegador que el pase renderizado (una página
    # prestada de su pool): abrir aquí una sesión de Playwright propia
    # reventaba con la configuración por defecto, porque el pool deja vivo su
    # driver en este hilo («Sync API inside the asyncio loop»)
    page, close_page = browser.borrow_page()
    try:
        resp = page.goto(url, wait_until='load', timeout=60000)
        page.wait_for_timeout(600)
        axe_status = resp.status if resp is not None else None
        # un 404 cargado en el navegador NO es un error de navegación: la
        # página de error se audita igual de bien y la fila salía como buena,
        # comparando el toolkit sobre la página real contra axe sobre un error
        if axe_status is None or not 200 <= axe_status < 400:
            raise RuntimeError(
                f'axe cargó una respuesta HTTP {axe_status}: no es la página pedida')
        # y los dos motores tienen que haber auditado la MISMA página final:
        # se comprueba antes de ejecutar axe, que no corre sobre otra página
        axe_url = _page_url(page.url)
        if page_identity(axe_url) != target_page:
            raise RuntimeError(
                f'axe terminó en {axe_url} y el toolkit en {toolkit_url}: no es la misma página')
        axe_bruto = axe_en_pagina(page)
    finally:
        close_page()

    toolkit_findings = {}
    for report in (informe_estatico, informe_dom):
        for finding in report.get('findings', []):
            code = finding['criterion'].split(' ', 1)[0]
            toolkit_findings.setdefault(code, []).append(finding)
    tk = set(toolkit_findings)
    axe_criteria = axe_a_criterios(axe_bruto)
    ax = set(axe_criteria)

    return {
        'url': url,
        # la fila solo es evidencia si los TRES motores produjeron resultados
        # (--check lo exige; el gate viejo miraba solo al toolkit y daba verde
        # con axe sin correr)
        'engines': dict.fromkeys(_ENGINES, 'ok'),
        'toolkit': {'score_estatico': informe_estatico.get('score'),
                    'score_dom': informe_dom.get('score'),
                    'criterios': sorted(tk),
                    'findings_dom': len(informe_dom.get('findings', [])),
                    'url_final_static': static_url,
                    'url_final': toolkit_url},
        'axe': {'violaciones': [(v['id'], v['nodos'], v['impacto']) for v in axe_bruto['violations']],
                'criterios': sorted(ax),
                'out_of_scope': axe_out_of_scope(axe_bruto),
                'rules_inapplicable': axe_bruto.get('inapplicable_count'),
                'http_status': axe_status,
                'url_final': axe_url},
        'coinciden': sorted(tk & ax),
        'solo_axe': sorted(ax - tk),      # candidatos a hueco/falso negativo nuestro
        'solo_toolkit': sorted(tk - ax),  # candidatos a falso positivo o señal extra
        'divergencias_detalle': {
            'solo_axe': {c: axe_criteria[c] for c in sorted(ax - tk)},
            'solo_toolkit': {c: toolkit_findings[c] for c in sorted(tk - ax)},
        },
    }


def problems(results, expected=None, min_signals=4, expected_urls=()):
    """List measurement failures and missing, substituted or repeated pages."""
    if not isinstance(results, list):
        return ['results must be a JSON array']
    out = []
    if expected is not None and len(results) != expected:
        out.append(f'expected {expected} results, got {len(results)}')
    requested = {}
    destinations = {}
    signals = 0
    for index, r in enumerate(results, 1):
        if not isinstance(r, dict):
            out.append(f'row {index}: result must be a JSON object')
            continue
        url = r.get('url')
        page = page_identity(url)
        if not isinstance(page, tuple):
            out.append(f'row {index}: missing or invalid requested URL')
            continue
        if page in requested:
            out.append(f'{url}: duplicate requested page')
            continue
        requested[page] = url
        if r.get('failed') or 'error' in r:
            out.append(f'{url}: run failed: {str(r.get("error"))[:80]}')
            continue
        ran = r.get('engines') or {}
        axe = r.get('axe') or {}
        toolkit = r.get('toolkit') or {}
        if not all(isinstance(part, dict) for part in (ran, axe, toolkit)):
            out.append(f'{url}: engine results must be JSON objects')
            continue
        for engine in _ENGINES:
            if ran.get(engine) != 'ok':
                out.append(f'{url}: no results from {engine}')
        inapplicable = axe.get('rules_inapplicable')
        if type(inapplicable) is not int or inapplicable < 1:
            out.append(f'{url}: axe executed no rules')
        status = axe.get('http_status')
        if type(status) is not int or not 200 <= status < 400:
            out.append(f'{url}: axe audited HTTP {status}, not the requested page')
        final = tuple(page_identity(url) for url in (
            toolkit.get('url_final_static'), toolkit.get('url_final'), axe.get('url_final')))
        if not all(isinstance(value, tuple) for value in final) or len(set(final)) != 1:
            out.append(f'{url}: toolkit and axe did not audit the same final page')
        elif final[0] in destinations:
            out.append(f'{url}: reached the same final page as {destinations[final[0]]}')
        else:
            destinations[final[0]] = url
        criteria = toolkit.get('criterios', [])
        if not isinstance(criteria, list) or any(not isinstance(code, str) for code in criteria):
            out.append(f'{url}: toolkit criteria must be an array of strings')
        else:
            signals += len(set(criteria))
    if expected_urls:
        targets = {page_identity(url): url for url in expected_urls}
        if any(not isinstance(page, tuple) for page in targets):
            out.append('expected pages must use valid HTTP(S) URLs')
        if len(targets) != len(expected_urls):
            out.append('expected pages must be distinct')
        out.extend(f'missing requested page: {url}'
                   for url in sorted(targets[page] for page in targets.keys() - requested.keys()))
        out.extend(f'unexpected requested page: {url}'
                   for url in sorted(requested[page] for page in requested.keys() - targets.keys()))
    if signals < min_signals:
        out.append(f'toolkit found almost nothing ({signals} criteria) '
                   'collector regression?')
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('urls', nargs='*',
                    help='pages to compare, or the required pages with --check')
    ap.add_argument('--check', metavar='RESULTS.json',
                    help='validate a results file instead of running (the CI gate)')
    ap.add_argument('--expect', type=int,
                    help='with --check: how many rows the file must hold')
    a = ap.parse_args(argv)
    if a.check:
        try:
            with open(a.check, encoding='utf-8') as f:
                results = json.load(f)
            found = problems(results, expected=a.expect, expected_urls=a.urls)
        except (OSError, ValueError) as e:
            print(f'BENCH INVALID: {e}', file=sys.stderr)
            return 1
        for line in found:
            print(f'BENCH INVALID: {line}', file=sys.stderr)
        if not found:
            print(f'BENCH OK: {len(results)} pages, three passes each')
        return 1 if found else 0
    urls = a.urls or ['https://www.gov.uk', 'https://en.wikipedia.org/wiki/Main_Page',
                      'https://example.com']
    results, failed = [], []
    for u in urls:
        print(f'— {u} …', file=sys.stderr)
        try:
            results.append(compara(u))
        except Exception as e:  # noqa: BLE001
            # la fila viaja en el JSON (--check la rechaza) y el código de
            # salida dice la verdad: run fallida
            results.append({'url': u, 'failed': True, 'error': str(e)})
            failed.append(u)
    print(json.dumps(results, ensure_ascii=False, indent=1))
    if failed:
        print(f'BENCH FALLIDO en {len(failed)}/{len(urls)}: {failed}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
