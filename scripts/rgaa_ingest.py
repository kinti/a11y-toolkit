#!/usr/bin/env python3
"""Ingesta RGAA 4.1 — el estándar legal francés desde su JSON oficial.

El gobierno francés publica el RGAA como dato abierto
(github.com/DISIC/accessibilite.numerique.gouv.fr → RGAA/4.1/criteres.json):
106 criterios en 13 temas, cada uno con tests operativos numerados y
references con el puente a WCAG (106/106 mapeados — verificado).

Este script verifica la estructura, aplana el markdown interno (los títulos
y tests enlazan al glosario con [texto](#ancla)) y escribe el paquete de
datos que consume a11yrgaa.py (patrón locales: JSON dentro del paquete).

Uso:
  python3 scripts/rgaa_ingest.py --file /tmp/criteres.json            # verificar
  python3 scripts/rgaa_ingest.py --file /tmp/criteres.json --update   # escribir
  python3 scripts/rgaa_ingest.py --download                           # fetch del oficial
"""

import argparse
import json
import os
import re
import sys
import urllib.request

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_URL = ('https://raw.githubusercontent.com/DISIC/'
              'accessibilite.numerique.gouv.fr/main/RGAA/4.1/criteres.json')
OUT_JSON = os.path.join(AQUI, 'a11y_toolkit', 'rgaa.json')

_LINK = re.compile(r'\[([^\]]+)\]\(#[^)]*\)')


def _flat(x):
    """Aplana el markdown interno del RGAA: [texto](#ancla) → texto, y las
    listas estructuradas ({\"ul\": [...]}) → líneas con viñeta. El resultado
    es texto plano listo para cualquier superficie."""
    if isinstance(x, dict):
        parts = []
        for key, items in x.items():
            bullet = '-' if key == 'ul' else '*'
            parts.extend(bullet + ' ' + _flat(i) for i in items)
        return '\n'.join(parts)
    return _LINK.sub(r'\1', str(x))


def _clean_criterium(crit):  # noqa: N802  (punto de entrada legible)
    c = crit['criterium']
    return {
        'number': str(c['number']),
        'title': _flat(c['title']),
        'tests': {n: [_flat(x) for x in items] for n, items in c.get('tests', {}).items()},
        'notes': [_flat(x) for x in c.get('technicalNote', [])],
        'wcag': [w for ref in c.get('references', []) for w in ref.get('wcag', [])],
    }


def ingest(data):
    topics = data.get('topics')
    if not isinstance(topics, list) or len(topics) != 13:
        raise ValueError(f'RGAA: expected 13 topics, got {len(topics) if topics else 0}')
    out = {'version': data.get('rgaa_version', '4.1'),
           'wcag_base': str(data.get('wcag', {}).get('version', '2.1')),
           'source': SOURCE_URL,
           'topics': [], 'criteria': []}
    total = 0
    for t in topics:
        out['topics'].append({'number': t['number'], 'name': t['topic']})
        for item in t['criteria']:
            c = _clean_criterium(item)
            num = f"{t['number']}.{c['number']}"
            out['criteria'].append({**c, 'num': num, 'topic': t['number']})
            total += 1
    if total != 106:
        raise ValueError(f'RGAA: expected 106 criteria, got {total}')
    # verificación del puente: TODO criterio con mapeo a WCAG
    sin_wcag = [c['num'] for c in out['criteria'] if not c['wcag']]
    if sin_wcag:
        raise ValueError(f'RGAA: criteria without WCAG mapping: {sin_wcag[:5]}')
    return out, total


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--file', help='local criteres.json to ingest')
    g.add_argument('--download', action='store_true', help='fetch from the official repo')
    ap.add_argument('--update', action='store_true', help='write a11y_toolkit/rgaa.json')
    a = ap.parse_args(argv)
    if a.download:
        print('descargando', SOURCE_URL)
        with urllib.request.urlopen(SOURCE_URL, timeout=30) as r:  # noqa: S310
            raw = r.read().decode('utf-8')
    else:
        raw = open(a.file, encoding='utf-8').read()
    out, total = ingest(json.loads(raw))
    ok = {'criteria': total, 'topics': len(out['topics']),
          'with_tests': sum(1 for c in out['criteria'] if c['tests'])}
    if a.update:
        with open(OUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        ok['written'] = OUT_JSON
    print(json.dumps(ok, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
