#!/usr/bin/env python3
"""Regenera la sección de tools del README desde server.TOOLS — de verdad.

El README siempre lo prometió ("generated from the server itself"); ahora lo
es: este script produce la sección `## The tools (N)` completa (entradas ####
por tool, con categorías) y la inyecta entre marcadores. Correr tras AÑADIR o
CAMBIAR una tool: python3 scripts/gen_readme.py [--check]

  --check: no escribe; falla (exit 1) si el README está desincronizado —
           apto para CI.
"""

import argparse
import os
import re
import sys

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AQUI)

from a11y_toolkit import server  # noqa: E402

README = os.path.join(AQUI, 'README.md')
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
]


def _entrada(t):
    """Entrada markdown de una tool, generada de su schema real."""
    a = t['annotations']
    sub = []
    if a.get('readOnlyHint') and not a.get('idempotentHint'):
        sub.append('read-only')
    elif not a.get('readOnlyHint') and not a.get('idempotentHint'):
        sub.append('mutates state')
    props = t['inputSchema'].get('properties', {})
    req = set(t['inputSchema'].get('required', []))
    args = []
    for p, d in props.items():
        nom = f'`{p}`' + (' *(required)*' if p in req else '')
        if d.get('enum'):
            args.append(f'- {nom} — one of {d["enum"]}: {d["description"]}.')
        else:
            args.append(f'- {nom}: {d["description"]}.')
    return (f'#### `{t["name"]}`\n\n<sub>{ " · ".join(sub) if sub else "read-only" }</sub>\n\n'
            f'{t["description"]}\n\n\n**Arguments**\n\n' + '\n\n'.join(args))


def seccion():
    por_cat = {n: c for c, nombres in CATEGORIAS for n in nombres}
    sin_cat = [t['name'] for t in server.TOOLS if t['name'] not in por_cat]
    assert not sin_cat, f'tools sin categoría en scripts/gen_readme.py: {sin_cat}'
    duplicadas = [n for c, ns in CATEGORIAS for n in ns if ns.count(n) > 1]
    assert not duplicadas, f'tools duplicadas en categorías: {duplicadas}'
    partes = [f'## The tools ({len(server.TOOLS)})', '',
              'Every tool, complete — description, arguments, and behavior '
              'annotations, generated from the server itself by '
              '`scripts/gen_readme.py` (`server.TOOLS` is the source of truth). '
              'All tools accept `lang` (`en`|`es`) unless noted; output is JSON '
              'unless noted.', '']
    for titulo, nombres in CATEGORIAS:
        partes.append(f'### {titulo}')
        partes.append('')
        for n in nombres:
            t = next(x for x in server.TOOLS if x['name'] == n)
            partes.append(_entrada(t))
            partes.append('')
    return '\n'.join(partes).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    texto = open(README, encoding='utf-8').read()
    if INI not in texto or FIN not in texto:
        # primera ejecución: inyectar marcadores alrededor de la sección actual
        m = re.search(r'(## The tools \(\d+\)\n.*?)(\n##?#? The 6 prompts)', texto, re.S)
        assert m, 'no se encontró la sección de tools para acotar'
        texto = texto[:m.start(1)] + INI + '\n' + m.group(1) + FIN + '\n' + texto[m.start(2):]
    actual = texto.split(INI)[1].split(FIN)[0].strip()
    nueva = seccion().strip()
    if a.check:
        if actual != nueva:
            print('README DESINCRONIZADO con server.TOOLS — correr scripts/gen_readme.py')
            return 1
        print(f'README sincronizado ✓ ({len(server.TOOLS)} tools)')
        return 0
    texto = texto.split(INI)[0] + INI + '\n' + nueva + '\n' + FIN + texto.split(FIN)[1]
    with open(README, 'w', encoding='utf-8') as f:
        f.write(texto)
    print(f'README regenerado: {len(server.TOOLS)} tools desde server.TOOLS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
