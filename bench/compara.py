#!/usr/bin/env python3
"""Bench a11y-toolkit vs axe-core sobre páginas REALES.

Ejecuta en la MISMA página de Chromium, con el MISMO Playwright:
  1. a11y_audit (estático sobre el HTML servido)
  2. a11y_audit_dom (renderizado, nuestro colector)
  3. axe-core 4.10 (el estándar de facto) — inyectado y ejecutado igual

Salida: comparación por página — qué caza cada uno, solapamiento y divergencias.
Este script es la prueba de que las afirmaciones del toolkit están contrastadas.

CLI:  python3 bench/compara.py https://www.gov.uk [otra-url ...]
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

from a11yaudit import audit_url
from a11ydom import audit_dom_url

AXE_JS = open('/tmp/axe.min.js', encoding='utf-8').read()

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


def axe_en_pagina(page):
    page.evaluate(AXE_JS)
    bruto = page.evaluate(
        "async () => { const r = await axe.run(document, {resultTypes: ['violations']});"
        " return {violations: r.violations.map(v => ({id: v.id, impacto: v.impact,"
        " nodos: v.nodes.length, tags: v.tags.filter(t => t.startsWith('wcag'))})),"
        " inapplicable_count: r.inapplicable.length}; }")
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
    informe_dom = audit_dom_url(url, lang=lang)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        page = nav.new_page()
        page.goto(url, wait_until='load', timeout=60000)
        page.wait_for_timeout(600)
        axe_bruto = axe_en_pagina(page)
        nav.close()

    tk_est = {h['criterio'].split(' ')[0] for h in informe_estatico.get('hallazgos', [])}
    tk_dom = {h['criterio'].split(' ')[0] for h in informe_dom.get('hallazgos', [])}
    tk = tk_est | tk_dom
    ax = set(axe_a_criterios(axe_bruto))

    return {
        'url': url,
        'toolkit': {'score_estatico': informe_estatico.get('score'),
                    'score_dom': informe_dom.get('score'),
                    'criterios': sorted(tk),
                    'hallazgos_dom': len(informe_dom.get('hallazgos', []))},
        'axe': {'violaciones': [(v['id'], v['nodos'], v['impacto']) for v in axe_bruto['violations']],
                'criterios': sorted(ax)},
        'coinciden': sorted(tk & ax),
        'solo_axe': sorted(ax - tk),      # candidatos a hueco/falso negativo nuestro
        'solo_toolkit': sorted(tk - ax),  # candidatos a falso positivo o señal extra
        'divergencias_detalle': {
            'solo_axe': {c: axe_a_criterios(axe_bruto)[c] for c in sorted(ax - tk)},
            'solo_toolkit': {c: [h for h in (informe_estatico.get('hallazgos', []) +
                                             informe_dom.get('hallazgos', []))
                                 if h['criterio'].startswith(c)]
                             for c in sorted(tk - ax)},
        },
    }


def main(argv):
    urls = argv or ['https://www.gov.uk', 'https://en.wikipedia.org/wiki/Main_Page',
                    'https://example.com']
    resultados = []
    for u in urls:
        print(f'— {u} …', file=sys.stderr)
        try:
            resultados.append(compara(u))
        except Exception as e:  # noqa: BLE001
            resultados.append({'url': u, 'error': str(e)})
    print(json.dumps(resultados, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(sys.argv[1:])
