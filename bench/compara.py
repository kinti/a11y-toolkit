#!/usr/bin/env python3
"""Bench a11y-toolkit vs axe-core sobre páginas REALES.

Ejecuta en la MISMA página de Chromium, con el MISMO Playwright:
  1. a11y_audit (estático sobre el HTML servido)
  2. a11y_audit_dom (renderizado, nuestro colector)
  3. axe-core 4.10 (el estándar de facto) — inyectado y ejecutado igual

Salida: comparación por página — qué caza cada uno, solapamiento y divergencias.
Este script es la prueba de que las afirmaciones del toolkit están contrastadas.

CLI:  python3 bench/compara.py https://www.gov.uk [otra-url ...]
      python3 bench/compara.py --check bench/results.json [--expect 4]
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
from a11y_toolkit.a11yaudit import audit_url  # noqa: E402
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


def axe_a_criterios(bruto):
    out = {}
    for v in bruto['violations']:
        criteria = set()
        for tag in v.get('tags', []):
            match = _WCAG_TAG.fullmatch(tag)
            if match:
                criteria.add('.'.join(match.groups()))
        for crit in sorted(criteria):
            out.setdefault(crit, []).append((v['id'], v['nodos'], v['impacto']))
    return out


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
    if not static_url or static_url != toolkit_url:
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
        if axe_url != toolkit_url:
            raise RuntimeError(
                f'axe terminó en {axe_url} y el toolkit en {toolkit_url}: no es la misma página')
        axe_bruto = axe_en_pagina(page)
    finally:
        close_page()

    tk_est = {h['criterion'].split(' ')[0] for h in informe_estatico.get('findings', [])}
    tk_dom = {h['criterion'].split(' ')[0] for h in informe_dom.get('findings', [])}
    tk = tk_est | tk_dom
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
                'rules_inapplicable': axe_bruto.get('inapplicable_count'),
                'http_status': axe_status,
                'url_final': axe_url},
        'coinciden': sorted(tk & ax),
        'solo_axe': sorted(ax - tk),      # candidatos a hueco/falso negativo nuestro
        'solo_toolkit': sorted(tk - ax),  # candidatos a falso positivo o señal extra
        'divergencias_detalle': {
            'solo_axe': {c: axe_criteria[c] for c in sorted(ax - tk)},
            'solo_toolkit': {c: [h for h in (informe_estatico.get('findings', []) +
                                             informe_dom.get('findings', []))
                                 if h['criterion'].startswith(c)]
                             for c in sorted(tk - ax)},
        },
    }


def problems(results, expected=None, min_signals=4):
    """What invalidates a benchmark run. A row is only evidence when the THREE
    engines produced results ON THE SAME PAGE: the old gate only checked that
    the toolkit found something, so it went green with axe not running at all,
    and later with axe auditing a 404 the browser had loaded without complaint."""
    out = []
    if expected is not None and len(results) != expected:
        out.append(f'expected {expected} results, got {len(results)}')
    signals = 0
    for r in results:
        url = r.get('url', '?')
        if r.get('failed') or 'error' in r:
            out.append(f'{url}: run failed: {str(r.get("error"))[:80]}')
            continue
        ran = r.get('engines') or {}
        for engine in _ENGINES:
            if ran.get(engine) != 'ok':
                out.append(f'{url}: no results from {engine}')
        axe = r.get('axe') or {}
        if not axe.get('rules_inapplicable'):
            out.append(f'{url}: axe executed no rules')
        status = axe.get('http_status')
        if type(status) is not int or not 200 <= status < 400:
            out.append(f'{url}: axe audited HTTP {status}, not the requested page')
        toolkit = r.get('toolkit') or {}
        final = (toolkit.get('url_final_static'), toolkit.get('url_final'), axe.get('url_final'))
        if not all(final) or len(set(final)) != 1:
            out.append(f'{url}: toolkit and axe did not audit the same final page')
        signals += len(r.get('toolkit', {}).get('criterios', []))
    if signals < min_signals:
        out.append(f'toolkit found almost nothing ({signals} criteria) '
                   'collector regression?')
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('urls', nargs='*', help='pages to compare the engines on')
    ap.add_argument('--check', metavar='RESULTS.json',
                    help='validate a results file instead of running (the CI gate)')
    ap.add_argument('--expect', type=int,
                    help='with --check: how many rows the file must hold')
    a = ap.parse_args(argv)
    if a.check:
        with open(a.check, encoding='utf-8') as f:
            results = json.load(f)
        found = problems(results, expected=a.expect)
        for line in found:
            print(f'BENCH INVALID: {line}', file=sys.stderr)
        if not found:
            print(f'BENCH OK: {len(results)} pages, three engines each')
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
