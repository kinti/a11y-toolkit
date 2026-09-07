#!/usr/bin/env python3
"""Insignia SVG honesta — score de accesibilidad con fecha y alcance, sin promesas.

La lección del sector (FTC × accessiBe, 1M$, 2025): el sello que promete
"conforme" acaba en multa. Esta insignia solo afirma lo que el toolkit puede
demostrar: una puntuación sobre lo automatizable, la fecha y el alcance
(screening). Es SVG accesible (role="img" + <title>), sin dependencias.

Colores por score: ≥90 verde · 75-89 lima · 50-74 naranja · <50 rojo.

CLI:
  a11ybadge.py --score 92 [--fecha 2026-09-07] [--alcance screening] [--lang en] [--out badge.svg]
"""

import argparse
import datetime
import json
import sys

_TEXTOS = {
    'es': {
        'nombre': 'a11y-toolkit', 'alcance': 'cribado automático',
        'titulo': 'Accesibilidad: {score}/100 — {fecha} — {alcance} (≈1/3 de WCAG); no es conformidad.',
    },
    'en': {
        'nombre': 'a11y-toolkit', 'alcance': 'automated screening',
        'titulo': 'Accessibility: {score}/100 — {fecha} — {alcance} (≈1/3 of WCAG); not conformance.',
    },
}

_COLORES = [(90, '#2da44e'), (75, '#8bdb5e'), (50, '#d29922'), (0, '#cf222e')]


def _color(score):
    for umbral, c in _COLORES:
        if score >= umbral:
            return c
    return _COLORES[-1][1]


def badge(score, fecha=None, alcance=None, lang='en'):
    """Devuelve el SVG (str) de la insignia. score 0-100."""
    score = max(0, min(100, int(round(score))))
    t = _TEXTOS.get(lang, _TEXTOS['en'])
    fecha = fecha or datetime.date.today().isoformat()
    alcance = alcance or t['alcance']
    titulo = t['titulo'].format(score=score, fecha=fecha, alcance=alcance)
    color = _color(score)
    izq = len(t['nombre']) * 6.5 + 14
    der = len(f'{score}/100 · {fecha}') * 6.5 + 14
    ancho = izq + der
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{ancho:.0f}" height="20" role="img" aria-label="{titulo}">
  <title>{titulo}</title>
  <linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
  <clipPath id="r"><rect width="{ancho:.0f}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{izq:.0f}" height="20" fill="#1f2328"/>
    <rect x="{izq:.0f}" width="{der:.0f}" height="20" fill="{color}"/>
    <rect width="{ancho:.0f}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{izq / 2:.0f}" y="14" fill="#010409" fill-opacity=".3">{t['nombre']}</text>
    <text x="{izq / 2:.0f}" y="13">{t['nombre']}</text>
    <text x="{izq + der / 2:.0f}" y="14" fill="#010409" fill-opacity=".3">{score}/100 · {fecha}</text>
    <text x="{izq + der / 2:.0f}" y="13">{score}/100 · {fecha}</text>
  </g>
</svg>'''


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--score', type=float, required=True)
    ap.add_argument('--fecha', default=None)
    ap.add_argument('--alcance', default=None)
    ap.add_argument('--lang', default='en', choices=['es', 'en'])
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    svg = badge(a.score, fecha=a.fecha, alcance=a.alcance, lang=a.lang)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(svg)
        print(json.dumps({'insignia': a.out, 'score': int(a.score)}))
    else:
        print(svg)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
