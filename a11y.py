#!/usr/bin/env python3
"""a11ytoolkit — one command for the whole toolkit.

  a11ytoolkit pair "#text" "#background" [--lang es|en]
  a11ytoolkit image path.jpg --text "#ffffff" [--region x,y,w,h] [--sample 4]
  a11ytoolkit audit --url https://client.web | --file page.html
  a11ytoolkit declaration --entidad "Name" --url https://… --estado parcial [options]
  a11ytoolkit snapshot https://mysite --out before.json      # needs Playwright
  a11ytoolkit diff before.json after.json
  a11ytoolkit audit --url https://web --pages 5            # light same-domain crawl
  a11ytoolkit sarif --url https://web -o a11y.sarif        # GitHub code scanning
  a11ytoolkit badge --score 92 --lang en --out badge.svg   # honest SVG badge
  a11ytoolkit budget --budget budget.json --audit today.json # only NEW findings block
  a11ytoolkit fix --file page.html --lang es --title "T" -o fixed.html  # safe autofix
  a11ytoolkit reflow https://web                          # 320px reflow (1.4.10)
  a11ytoolkit kbd https://web                             # keyboard traps? (2.1.2)
  a11ytoolkit scroll https://medium/section               # infinite-scroll audit
"""

import sys

import a11yaudit
import a11ybadge
import a11yfix
import a11ydom
import a11yscroll
import a11ybudget
import a11ycrit
import a11ydiff
import a11ysarif
import contrast
import declaracion

SUBCOMANDOS = {
    'pair': (contrast, 'pair'),
    'image': (contrast, 'image'),
    'audit': (a11yaudit, None),
    'declaration': (declaracion, None),
    'snapshot': (a11ydiff, 'snapshot'),
    'diff': (a11ydiff, 'diff'),
    'criterion': (a11ycrit, None),
    'sarif': (a11ysarif, None),
    'fix': (a11yfix, None),
    'kbd': (a11ydom, 'kbd_main'),
    'scroll': (a11yscroll, None),
    'reflow': (a11ydom, 'reflow_main'),
    'badge': (a11ybadge, None),
    'budget': (a11ybudget, None),
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        print('Subcomandos disponibles:', ', '.join(sorted(SUBCOMANDOS)))
        return 0
    if argv[0] not in SUBCOMANDOS:
        print(__doc__)
        print(f'Subcomando desconocido: {argv[0]}. Disponibles:', ', '.join(sorted(SUBCOMANDOS)))
        return 2
    modulo, sub = SUBCOMANDOS[argv[0]]
    if sub and sub.endswith('_main'):
        return getattr(modulo, sub)(argv[1:])   # función propia (reflow_main, kbd_main)
    args = ([sub] + argv[1:]) if sub else argv[1:]
    return modulo.main(args)


if __name__ == '__main__':
    sys.exit(main())
