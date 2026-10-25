#!/usr/bin/env python3
"""Ingesta WCAG 2.2 — el estándar completo (A/AA/AAA) desde la fuente w3c/wcag.

La biblia del toolkit es WCAG 2.2 con TODOS sus niveles: este script extrae
cada criterio de éxito del repo canónico (guidelines/index.html da el orden
y la numeración; guidelines/sc/<ver>/<slug>.html el nombre y nivel), lo
contrasta con nuestro catálogo (a11ycrit._C) y graba el snapshot. El 4.1.1
Parsing se numera y se EXCLUYE (retirado en 2.2 — el pin normativo del repo
ya lo excluye).

Uso (re-verificar tras cualquier cambio del catálogo o de upstream):
  git clone --depth 1 https://github.com/w3c/wcag.git /tmp/wcag
  python3 scripts/wcag22_ingest.py --repo /tmp/wcag            # verificar
  python3 scripts/wcag22_ingest.py --repo /tmp/wcag --update   # snapshot
"""

import argparse
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, AQUI)

from a11y_toolkit.a11ycrit import _C  # noqa: E402

SNAPSHOT = os.path.join(AQUI, 'docs', 'wcag22-criteria-source.json')
RETIRADO = '4.1.1'   # Parsing: retirado en WCAG 2.2


# las 13 guías en orden documental del estándar (el fuente no lleva ids:
# se generan al construir — el orden de los <h3> es la numeración)
_GUIAS = {'Text Alternatives': '1.1', 'Time-based Media': '1.2', 'Adaptable': '1.3',
          'Distinguishable': '1.4', 'Keyboard Accessible': '2.1', 'Enough Time': '2.2',
          'Seizures and Physical Reactions': '2.3', 'Navigable': '2.4',
          'Input Modalities': '2.5', 'Readable': '3.1', 'Predictable': '3.2',
          'Input Assistance': '3.3', 'Compatible': '4.1'}


def extraer(repo):
    base = os.path.join(repo, 'guidelines')
    orden = open(os.path.join(base, 'index.html'), encoding='utf-8').read()
    tokens = re.findall(r'<h3>([^<]+)</h3>|data-include="sc/(\d\d)/([^"]+)\.html"', orden)
    out, conteo, guia = [], {}, None
    for nombre_h3, ver, slug in tokens:
        if nombre_h3:
            if nombre_h3.strip() in _GUIAS:
                guia = _GUIAS[nombre_h3.strip()]
            continue
        if guia is None:
            continue
        html = open(os.path.join(base, 'sc', ver, slug + '.html'), encoding='utf-8').read()
        nombre = re.search(r'<h4[^>]*>([^<]+)</h4>', html).group(1).strip()
        m_niv = re.search(r'conformance-level">\s*([A-Z]+)', html)
        nivel = m_niv.group(1) if m_niv else 'A'   # parsing (retirado) ya no trae nivel
        conteo[guia] = conteo.get(guia, 0) + 1
        num = f'{guia}.{conteo[guia]}'
        out.append({'num': num, 'name': nombre, 'level': nivel,
                    'slug': slug, 'since': f'2.{ver[1]}'})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', default='/tmp/wcag')
    ap.add_argument('--update', action='store_true')
    a = ap.parse_args()

    fuente = [sc for sc in extraer(a.repo) if sc['num'] != RETIRADO]
    print(f'fuente: {len(fuente)} criterios (sin el {RETIRADO} retirado) '
          f'· A={sum(1 for s in fuente if s["level"] == "A")} '
          f'AA={sum(1 for s in fuente if s["level"] == "AA")} '
          f'AAA={sum(1 for s in fuente if s["level"] == "AAA")}')

    # 1. los A/AA del catálogo deben coincidir EXACTAMENTE con la fuente
    fuente_aa = {s['num']: s['level'] for s in fuente if s['level'] != 'AAA'}
    cat_AA = {c: v[0] for c, v in _C.items() if v[0] in ('A', 'AA')}
    mal = {c: (cat_AA.get(c), fuente_aa.get(c))
           for c in set(fuente_aa) | set(cat_AA)
           if fuente_aa.get(c) != cat_AA.get(c)}
    assert not mal, f'catálogo ≠ fuente en A/AA: {mal}'
    print(f'✓ A/AA del catálogo verificados contra la fuente ({len(cat_AA)})')

    # 2. los AAA del catálogo deben ser exactamente los AAA de la fuente
    fuente_aaa = {s['num'] for s in fuente if s['level'] == 'AAA'}
    cat_aaa = {c for c, v in _C.items() if v[0] == 'AAA'}
    faltan = sorted(fuente_aaa - cat_aaa)
    sobran = sorted(cat_aaa - fuente_aaa)
    if faltan or sobran:
        print(f'✗ AAA: faltan en el catálogo {faltan} · sobran {sobran}')
        return 1
    print(f'✓ AAA completos en el catálogo ({len(cat_aaa)})')

    if a.update or not os.path.exists(SNAPSHOT):
        with open(SNAPSHOT, 'w', encoding='utf-8') as f:
            json.dump({'source': 'w3c/wcag guidelines (canónico, 2.x vivo)',
                       'removed': RETIRADO, 'criteria': fuente}, f, ensure_ascii=False, indent=1)
        print(f'snapshot: {SNAPSHOT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
