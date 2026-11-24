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
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
sys.path.insert(0, AQUI)

import browser  # noqa: E402  (bench/browser.py: pool loan + axe-core lookup)
from a11y_toolkit.a11yaudit import audit_url  # noqa: E402
from a11y_toolkit.a11ydom import audit_dom_url  # noqa: E402

_ENGINES = ('toolkit_static', 'toolkit_rendered', 'axe')

# mapa señal-toolkit → criterio, para comparar por criterio WCAG
CRIT_TOOLKIT = {'1.1.1', '1.2.2', '1.3.1', '1.3.5', '1.4.2', '1.4.3', '1.4.4',
                '2.1.1', '2.2.1', '2.4.1', '2.4.2', '2.4.3', '2.4.4', '2.4.7',
                '2.5.8', '3.1.1', '3.2.5', '3.3.2', '4.1.2'}

# reglas axe (violaciones) → criterio WCAG aproximado
AXE_A_CRIT = {
    'image-alt': '1.1.1', 'input-image-alt': '1.1.1', 'area-alt': '1.1.1',
    'button-name': '4.1.2', 'link-name': '4.1.2',
    'label': '3.3.2', 'label-title-only': '3.3.2',
    'html-has-lang': '3.1.1', 'html-lang-valid': '3.1.1', 'valid-lang': '3.1.1',
    'document-title': '2.4.2',
    'heading-order': '1.3.1', 'empty-heading': '1.3.1', 'page-has-heading-one': '1.3.1',
    'th-has-data-cells': '1.3.1', 'table-fake-caption': '1.3.1', 'td-has-header': '1.3.1',
    'td-headers-attr': '1.3.1', 'th-has-data-cells': '1.3.1',
    'color-contrast': '1.4.3', 'color-contrast-enhanced': '1.4.3',
    'meta-viewport': '1.4.4', 'meta-viewport-large': '1.4.4',
    'aria-allowed-attr': '4.1.2', 'aria-allowed-role': '4.1.2', 'aria-command-name': '4.1.2',
    'aria-dialog-name': '4.1.2', 'aria-meter-name': '4.1.2', 'aria-progressbar-name': '4.1.2',
    'aria-required-attr': '4.1.2', 'aria-required-children': '4.1.2',
    'aria-required-parent': '4.1.2', 'aria-roles': '4.1.2', 'aria-toggle-field-name': '4.1.2',
    'aria-tooltip-name': '4.1.2', 'aria-valid-attr': '4.1.2', 'aria-valid-attr-value': '4.1.2',
    'role-img-alt': '4.1.2', 'scrollable-region-focusable': '2.1.1',
    'meta-refresh': '2.2.1', 'blink': '2.2.2', 'marquee': '2.2.2',
    'bypass': '2.4.1', 'frame-title': '4.1.2', 'region': '2.4.1',
    'tabindex': '2.4.3', 'duplicate-id-aria': '4.1.2', 'duplicate-id-active': '2.4.3',
    'identical-links-same-purpose': '2.4.4', 'link-in-text-block': '2.4.4',
    'focus-order-semantics': '2.4.3', 'frame-focusable-content': '2.4.7',
    'target-size': '2.5.8', 'autocomplete-valid': '1.3.5', 'autocomplete-appropriate': '1.3.5',
    'video-caption': '1.2.2', 'audio-caption': '1.2.2',
    'list': '1.3.1', 'listitem': '1.3.1', 'definition-list': '1.3.1',
    'select-name': '3.3.2', 'nested-interactive': '4.1.2', 'hidden-content': None,
}


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
        crit = AXE_A_CRIT.get(v['id'])
        if crit:
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
        if axe_status is None or axe_status >= 400:
            raise RuntimeError(
                f'axe cargó una respuesta HTTP {axe_status}: no es la página pedida')
        # y los dos motores tienen que haber auditado la MISMA página final:
        # se comprueba antes de ejecutar axe, que no corre sobre otra página
        axe_url = page.url.split('#')[0]
        toolkit_url = str(informe_dom.get('url') or url).split('#')[0]
        if axe_url != toolkit_url:
            raise RuntimeError(
                f'axe terminó en {axe_url} y el toolkit en {toolkit_url}: no es la misma página')
        axe_bruto = axe_en_pagina(page)
    finally:
        close_page()

    tk_est = {h['criterion'].split(' ')[0] for h in informe_estatico.get('findings', [])}
    tk_dom = {h['criterion'].split(' ')[0] for h in informe_dom.get('findings', [])}
    tk = tk_est | tk_dom
    ax = set(axe_a_criterios(axe_bruto))

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
            'solo_axe': {c: axe_a_criterios(axe_bruto)[c] for c in sorted(ax - tk)},
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
        if not isinstance(status, int) or isinstance(status, bool) or status >= 400:
            out.append(f'{url}: axe audited HTTP {status}, not the requested page')
        final = ((r.get('toolkit') or {}).get('url_final'), axe.get('url_final'))
        if not final[0] or not final[1] or final[0] != final[1]:
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
