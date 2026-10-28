#!/usr/bin/env python3
"""Genera llms.txt — el índice del repo para agentes (convención llmstxt.org).

El patrón se inventó en a11y.es (/llms.txt); aquí se porta al repo del motor.
Generado desde server.TOOLS + las categorías de gen_readme (fuente única):
añadir una tool y correr este script actualiza el índice. --check falla si
el fichero está desincronizado (apt para CI, ya cableado en el Makefile).

  python3 scripts/gen_llms.py           # regenera llms.txt
  python3 scripts/gen_llms.py --check   # exit 1 si desincronizado
"""

import argparse
import os
import sys

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, 'scripts'))

from a11y_toolkit import server  # noqa: E402
from gen_readme import CATEGORIAS  # noqa: E402  (fuente única de categorías)

DESTINO = os.path.join(AQUI, 'llms.txt')
REPO = 'https://github.com/kinti/a11y-toolkit'


def _titulos():
    """name → título corto (el mismo que ve el cliente en annotations)."""
    return {t['name']: t.get('title', '').replace('a11y-toolkit: ', '')
            for t in server.TOOLS}


def build():
    titulos = _titulos()
    por_cat = {n: c for c, nombres in CATEGORIAS for n in nombres}
    sin_cat = [t['name'] for t in server.TOOLS if t['name'] not in por_cat]
    assert not sin_cat, f'tools sin categoría (van en gen_readme.CATEGORIAS): {sin_cat}'
    L = []
    L.append('# a11y-toolkit')
    L.append('')
    L.append('> The accessibility layer for AI coding agents: a zero-dependency '
             'Python engine (MCP server, 33 tools + 6 prompts, CLI `a11ytoolkit`, '
             'MIT) that audits, fixes, documents and watches WCAG 2.2 — and never '
             'signs conformance: the machine finds, the human signs. Bilingual '
             'es/en output. Runs anywhere MCP runs.')
    L.append('')
    L.append('## What is verifiably true (no marketing)')
    L.append('- 100% consistent with every published W3C ACT rule it implements: '
             '355 official test cases, 20/20 rules, zero inconsistencies, '
             'regenerated per release against the w3c/wcag-act-rules repository '
             f'({REPO}/blob/main/docs/act-report-summary.md).')
    L.append('- The WCAG 2.2 catalog (86 criteria, A/AA/AAA) and the WCAG 3 '
             'outcome registry are ingested from the canonical w3.org sources '
             'and pinned by tests.')
    L.append('- Automation covers about one third of WCAG 2.2. Every report says '
             'so: filter, not verdict. The evidence pack prices the human '
             'remainder per criterion.')
    L.append('- Zero telemetry, zero core dependencies (Playwright/Pillow optional '
             'behind import guards). Python 3.9+.')
    L.append('- The engine behind a11y.es (a separate Spanish-market service; this '
             'repository is the engine).')
    L.append('')
    L.append('## Quickstart')
    L.append('```bash')
    L.append('claude mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp')
    L.append('# or any MCP client: command "uvx", args ["--from","a11y-toolkit","a11y-toolkit-mcp"]')
    L.append('# CLI only: pip install a11y-toolkit && a11ytoolkit audit --url https://example.com')
    L.append('```')
    L.append('')
    L.append(f'## Tools ({len(server.TOOLS)})')
    L.append('')
    L.append('Start with `a11y_route` (the router): state a goal in plain '
             'language and get the ordered tool sequence — an O(1) choice '
             'instead of scanning descriptions.')
    L.append('')
    for titulo, nombres in CATEGORIAS:
        L.append(f'### {titulo}')
        for n in nombres:
            L.append(f'- `{n}` — {titulos[n]}')
        L.append('')
    L.append('## Prompts (6)')
    L.append('')
    for p in server._PROMPTS:
        primera = p['description'].split('. ')[0]
        L.append(f'- `{p["name"]}` — {primera}')
    L.append('')
    L.append('## Documentation')
    L.append(f'- [Full tools reference]({REPO}/blob/main/docs/tools.md): every tool, arguments and annotations')
    L.append(f'- [Install per client]({REPO}/blob/main/docs/clients.md): Claude Code, Cursor, Windsurf and more')
    L.append(f'- [Agent benchmark]({REPO}/blob/main/docs/benchmark-agents.md): blindfold journeys on live sites + the Spanish sample')
    L.append(f'- [Journey example]({REPO}/blob/main/docs/journey-example.md): GOV.UK 100 / IKEA Spain 0, full journals')
    L.append(f'- [axe-core comparison]({REPO}/blob/main/bench/README.md): monthly, real pages, methodology open')
    L.append(f'- [Architecture]({REPO}/blob/main/docs/ARCHITECTURE.md): module map, decisions D1+, traps')
    L.append(f'- [i18n guide]({REPO}/blob/main/docs/i18n.md): add a language in one PR')
    L.append('')
    L.append('## Where it stops (the honest boundary)')
    L.append('- Static audits cannot measure class/var() CSS contrast: the report '
             'says not_measured, a 100 is never "contrast is fine".')
    L.append('- No tool asserts pass from the absence of findings.')
    L.append('- Conformance is signed by a qualified human over verifiable '
             'evidence; nothing here signs it for you.')
    L.append('')
    L.append(f'Version: {server.VERSION}. Generated by `scripts/gen_llms.py` '
             'from `server.TOOLS` — never edit by hand.')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    nueva = build()
    if a.check:
        actual = open(DESTINO, encoding='utf-8').read() if os.path.exists(DESTINO) else ''
        if actual.strip() != nueva.strip():
            print('llms.txt DESINCRONIZADO con server.TOOLS — correr scripts/gen_llms.py')
            return 1
        print(f'llms.txt sincronizado ✓ ({len(server.TOOLS)} tools)')
        return 0
    with open(DESTINO, 'w', encoding='utf-8') as f:
        f.write(nueva)
    print(f'llms.txt generado: {len(server.TOOLS)} tools desde server.TOOLS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
