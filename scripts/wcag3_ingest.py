#!/usr/bin/env python3
"""Ingesta WCAG 3 — verifica el registro de outcomes contra la FUENTE (w3c/wcag3).

El preview (a11ywcag3._OUTCOMES) nació del TR renderizado; este script lo
contrasta con el repo canónico del borrador, donde cada outcome vive como
guidelines/groups/<área>/<outcome>.md (con sus requisitos como hijos en el
frontmatter). Sin números TR (se generan al construir) — la verificación es
por NOMBRE normalizado.

Uso (re-baseline por publicación de draft):
  git clone --depth 1 https://github.com/w3c/wcag3.git /tmp/wcag3
  python3 scripts/wcag3_ingest.py --repo /tmp/wcag3          # verificar
  python3 scripts/wc3_ingest.py --repo /tmp/wcag3 --update   # refrescar snapshot
"""

import argparse
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AQUI)

from a11y_toolkit.a11ywcag3 import _OUTCOMES  # noqa: E402

SNAPSHOT = os.path.join(AQUI, 'docs', 'wcag3-outcomes-source.json')


def _slug_a_titulo(slug):
    return ' '.join(p.capitalize() if p not in ('and', 'of', 'or') else p
                    for p in slug.split('-'))


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def extraer(repo):
    """{área: [outcome_slug…]} del repo canónico."""
    grupos = os.path.join(repo, 'guidelines', 'groups')
    orden = json.load(open(os.path.join(repo, 'guidelines', 'groups.json'),
                           encoding='utf-8'))
    out = {}
    for area in orden:
        for f in sorted(os.listdir(os.path.join(grupos, area))):
            if f.endswith('.md'):
                out.setdefault(area, []).append(f[:-3])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', default='/tmp/wcag3', help='clon de w3c/wcag3')
    ap.add_argument('--update', action='store_true',
                    help='reescribir el snapshot con la fuente actual')
    a = ap.parse_args()

    fuente = extraer(a.repo)
    titulos_fuente = sorted(_slug_a_titulo(s) for slugs in fuente.values() for s in slugs)
    print(f'fuente: {len(titulos_fuente)} outcomes en {len(fuente)} áreas '
          f'({", ".join(sorted(fuente))})')

    nuestros = sorted(_OUTCOMES.values())
    f_norm, n_norm = {_norm(t) for t in titulos_fuente}, {_norm(t) for t in nuestros}
    solo_fuente = [t for t in titulos_fuente if _norm(t) not in n_norm]
    solo_nosotros = [t for t in nuestros if _norm(t) not in f_norm]
    if solo_fuente or solo_nosotros:
        print('✗ DERIVA respecto a la fuente:')
        for t in solo_fuente:
            print(f'  solo en la fuente: {t}')
        for t in solo_nosotros:
            print(f'  solo en nuestro registro: {t}')
        print('  → re-baseline pendiente (actualizar _OUTCOMES/_CRIT_OUTCOME '
              'y tests/test_wcag3.py)')
        return 1
    print(f'✓ registro de outcomes VERIFICADO contra la fuente ({len(nuestros)} nombres)')

    if a.update or not os.path.exists(SNAPSHOT):
        with open(SNAPSHOT, 'w', encoding='utf-8') as f:
            json.dump({'source': 'w3c/wcag3 guidelines/groups (canónico)',
                       'outcomes': fuente}, f, ensure_ascii=False, indent=1)
        print(f'snapshot: {SNAPSHOT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
