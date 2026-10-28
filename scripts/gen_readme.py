#!/usr/bin/env python3
"""Regenera la tabla compacta de tools del README y docs/tools.md (catálogo
completo) desde server.TOOLS — de verdad.

Dos superficies, una fuente (`server.TOOLS`):
  - README.md: tabla compacta (tool | categoría | qué hace) entre marcadores.
  - docs/tools.md: referencia completa por tool (descripción, argumentos,
    anotaciones de comportamiento, forma de retorno), con categorías.

Correr tras AÑADIR o CAMBIAR una tool: python3 scripts/gen_readme.py [--check]

  --check: no escribe; falla (exit 1) si el README o docs/tools.md están
           desincronizados — apto para CI.
"""

import argparse
import os
import sys

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AQUI)

from a11y_toolkit import server  # noqa: E402

README = os.path.join(AQUI, 'README.md')
TOOLS_DOC = os.path.join(AQUI, 'docs', 'tools.md')
INI = '<!-- TOOLS:BEGIN -->'
FIN = '<!-- TOOLS:END -->'

# categoría por tool (orden de aparición). Una tool nueva sin categoría revienta
# — obligación deliberada de decidir dónde vive antes de shippearla.
CATEGORIAS = [
    ('Audit', ['a11y_audit_url', 'a11y_audit_dom', 'a11y_audit_pdf', 'a11y_docx_screen']),
    ('Blindfold testing', ['a11y_journey_verdict']),
    ('Fix & contrast', ['a11y_autofix', 'a11y_contrast_pair', 'a11y_contrast_image',
                        'a11y_contrast_dom', 'a11y_suggest_color']),
    ('Document', ['a11y_generate_declaration', 'a11y_generate_vpat', 'a11y_badge']),
    ('Watch (regressions)', ['a11y_snapshot', 'a11y_diff', 'a11y_diff_urls',
                             'a11y_aria_live_snippet']),
    ('Knowledge & context', ['a11y_criterion', 'a11y_html_validate']),
    ('Interactions', ['a11y_keyboard', 'a11y_forms', 'a11y_hover', 'a11y_reflow',
                      'a11y_scroll', 'a11y_sr_transcript', 'a11y_reduced_motion',
                      'a11y_forced_colors', 'a11y_vtt_check']),
    ('Coverage & evidence', ['a11y_evidence', 'a11y_disprove', 'a11y_ledger',
                             'a11y_wcag3_preview']),
    ('Routing', ['a11y_route']),
]


def _validar_categorias():
    por_cat = {n for _, names in CATEGORIAS for n in names}
    sin_cat = [t['name'] for t in server.TOOLS if t['name'] not in por_cat]
    assert not sin_cat, f'tools sin categoría en scripts/gen_readme.py: {sin_cat}'
    dup = [n for _, names in CATEGORIAS for n in names if names.count(n) > 1]
    assert not dup, f'tools duplicadas en categorías: {dup}'


def _tool(name):
    return next(x for x in server.TOOLS if x['name'] == name)


def _etiquetas(t):
    """read-only/mutates state · network · not idempotent — las señales que un
    agente necesita para decidir si ejecutar la tool con seguridad."""
    a = t['annotations']
    sub = ['read-only' if a.get('readOnlyHint') else 'mutates state']
    if a.get('openWorldHint'):
        sub.append('network')
    if not a.get('idempotentHint'):
        sub.append('not idempotent')
    return ' · '.join(sub)


def _titulo(name):
    """Título corto por tool (del campo title del servidor, sin el prefijo)."""
    return _tool(name)['title'].replace('a11y-toolkit: ', '')


def tabla():
    """Sección compacta del README: tabla tool | categoría | qué hace."""
    _validar_categorias()
    lineas = [f'## The tools ({len(server.TOOLS)})', '',
              'Full reference — descriptions, arguments, return shapes and '
              'behavior — in [docs/tools.md](docs/tools.md). All tools accept '
              '`lang` (`en`|`es`) unless noted; output is JSON unless noted. '
              'Generated from `server.TOOLS` by `scripts/gen_readme.py`.', '',
              '| Tool | Category | What it does |',
              '|---|---|---|']
    for cat, names in CATEGORIAS:
        for n in names:
            lineas.append(f'| [`{n}`](docs/tools.md#{n}) | {cat} | {_titulo(n)} |')
    return '\n'.join(lineas)


def _entrada(t):
    """Entrada markdown completa de una tool (para docs/tools.md)."""
    props = t['inputSchema'].get('properties', {})
    req = set(t['inputSchema'].get('required', []))
    args = []
    for p, d in props.items():
        nom = f'`{p}`' + (' *(required)*' if p in req else '')
        if d.get('enum'):
            args.append(f'- {nom} — one of {d["enum"]}: {d["description"]}.')
        else:
            args.append(f'- {nom}: {d["description"]}.')
    return (f'#### `{t["name"]}`\n\n<sub>{_etiquetas(t)}</sub>\n\n'
            f'{t["description"]}\n\n\n**Arguments**\n\n' + '\n\n'.join(args))


def seccion():
    """Referencia completa para docs/tools.md."""
    _validar_categorias()
    lineas = ['# Tools reference', '',
              'Every tool, complete — description, arguments, and behavior '
              'annotations, generated from the server itself by '
              '`scripts/gen_readme.py` (`server.TOOLS` is the source of truth). '
              'All tools accept `lang` (`en`|`es`) unless noted; output is JSON '
              'unless noted. Auto-generated — edit `server.TOOLS` and rerun '
              '`scripts/gen_readme.py`, never this file by hand.', '']
    for cat, names in CATEGORIAS:
        lineas.append(f'## {cat}')
        lineas.append('')
        for n in names:
            lineas.append(_entrada(_tool(n)))
            lineas.append('')
    return '\n'.join(lineas).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    tabla_str = tabla().strip()
    seccion_str = seccion().strip()

    readme = open(README, encoding='utf-8').read()
    assert INI in readme and FIN in readme, f'{INI}/{FIN} ausentes en README.md'
    readme_actual = readme.split(INI)[1].split(FIN)[0].strip()
    tools_actual = (open(TOOLS_DOC, encoding='utf-8').read().strip()
                    if os.path.exists(TOOLS_DOC) else '')

    if a.check:
        ok_readme = readme_actual == tabla_str
        ok_doc = tools_actual == seccion_str
        if not (ok_readme and ok_doc):
            print('README/docs/tools.md DESINCRONIZADOS con server.TOOLS — correr scripts/gen_readme.py')
            if not ok_readme:
                print('  README (tabla compacta) desincronizado')
            if not ok_doc:
                print('  docs/tools.md desincronizado')
            return 1
        print(f'README + docs/tools.md sincronizados ✓ ({len(server.TOOLS)} tools)')
        return 0

    readme_nuevo = (readme.split(INI)[0] + INI + '\n' + tabla_str + '\n'
                    + FIN + readme.split(FIN)[1])
    with open(README, 'w', encoding='utf-8') as f:
        f.write(readme_nuevo)
    with open(TOOLS_DOC, 'w', encoding='utf-8') as f:
        f.write(seccion_str + '\n')
    print(f'README (tabla) + docs/tools.md regenerados: {len(server.TOOLS)} tools desde server.TOOLS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
