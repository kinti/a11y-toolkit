#!/usr/bin/env python3
"""Honest SVG badge — accessibility score with date and scope, no promises.

The industry lesson (FTC v. accessiBe, $1M, 2025): a badge that promises
"compliant" ends in a fine. This badge only states what the toolkit can
demonstrate: a score over what is automatable, the date and the scope
(screening). Accessible SVG (role="img" + <title>), zero dependencies.

Score colors: ≥90 green · 75-89 lime · 50-74 orange · <50 red.

CLI:
  a11ybadge.py --score 92 [--date 2026-09-07] [--scope screening] [--lang en] [--out badge.svg]
"""

import argparse
import datetime
import json
import sys
from xml.sax.saxutils import escape as _xesc
from . import a11yi18n

_TEXTS = a11yi18n.pair('badge')  # locales/<lang>.json — community-editable

# paleta por defecto: TODOS los fondos pasan 4.5:1 con el texto blanco del
# badge (verificado con el propio motor) — una herramienta de accesibilidad
# no puede exhibir texto de bajo contraste (revisión externa 2026-11)
_COLORS = [(90, '#1a7f37'), (75, '#4d6b0f'), (50, '#9a6700'), (0, '#cf222e')]


def _esc(value):
    """XML escape INCLUDING double quotes: the title lands in an attribute
    (aria-label), where a raw quote breaks out of the SVG."""
    return _xesc(value, {'"': '&quot;'})


def badge(score, date=None, scope=None, lang='en', brand=None, palette=None, height=None):
    """Honest SVG badge. score 0-100.

    `brand` overrides the left label; `palette` overrides the score colors as
    [(threshold, '#hex'), …] (measure your contrast with a11y_contrast_pair —
    a WCAG tool's own badge must pass 1.4.3); `height` scales the SVG (default 20).
    """
    score = max(0, min(100, int(round(score))))
    t = dict(_TEXTS.get(lang, _TEXTS['en']))
    if brand:
        t['name'] = str(brand)[:24]
    colors = palette or _COLORS

    def _color(s):
        for threshold, c in colors:
            if s >= threshold:
                return c
        return colors[-1][1]

    # truncate FIRST, escape ONCE, per field: truncating escaped text can cut
    # an entity in half (&amp; → &amp), and re-escaping pre-escaped values
    # double-escapes (& → &amp;amp;). Metrics (width) use the raw truncated
    # strings; the SVG gets the escaped ones.
    raw_date = str(date or datetime.date.today().isoformat())[:30]
    raw_scope = str(scope or t['scope'])[:60]
    date_e = _esc(raw_date)
    scope_e = _esc(raw_scope)
    name_e = _esc(t['name'])   # brand incluido: nada crudo entra al SVG
    title = _esc(t['title']).format(score=score, date=date_e, scope=scope_e)
    color = _color(score)
    h = height or 20
    font = 11 if h == 20 else round(h * 0.58)
    y = h / 2 + font * 0.35
    left = len(t['name']) * (font * 0.60) + 14
    right = len(f'{score}/100 · {raw_date}') * (font * 0.60) + 14
    width = left + right
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{h}" role="img" aria-label="{title}">
  <title>{title}</title>
  <linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
  <clipPath id="r"><rect width="{width:.0f}" height="{h}" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{left:.0f}" height="{h}" fill="#1f2328"/>
    <rect x="{left:.0f}" width="{right:.0f}" height="{h}" fill="{color}"/>
    <rect width="{width:.0f}" height="{h}" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="{font}">
    <text x="{left / 2:.0f}" y="{y + 1:.1f}" fill="#010409" fill-opacity=".3">{name_e}</text>
    <text x="{left / 2:.0f}" y="{y:.1f}">{name_e}</text>
    <text x="{left + right / 2:.0f}" y="{y + 1:.1f}" fill="#010409" fill-opacity=".3">{score}/100 · {date_e}</text>
    <text x="{left + right / 2:.0f}" y="{y:.1f}">{score}/100 · {date_e}</text>
  </g>
</svg>'''


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--score', type=float, required=True)
    ap.add_argument('--date', default=None)
    ap.add_argument('--scope', default=None)
    ap.add_argument('--lang', default='en', choices=['es', 'en'])
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    svg = badge(a.score, date=a.date, scope=a.scope, lang=a.lang)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(svg)
        print(json.dumps({'badge': a.out, 'score': int(a.score)}))
    else:
        print(svg)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
