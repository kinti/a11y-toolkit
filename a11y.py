#!/usr/bin/env python3
"""a11ytoolkit — un solo comando para todo el toolkit.

  a11ytoolkit pair "#texto" "#fondo" [--lang es|en]
  a11ytoolkit image ruta.jpg --text "#ffffff" [--region x,y,w,h] [--sample 4]
  a11ytoolkit audit --url https://cliente.web | --file pagina.html
  a11ytoolkit declaration --entidad "Nome" --url https://… --estado parcial [opciones]
  a11ytoolkit snapshot https://miweb --out antes.json      # requiere Playwright
  a11ytoolkit diff antes.json despues.json
  a11ytoolkit audit --url https://web --pages 5            # crawl ligero mismo dominio
  a11ytoolkit sarif --url https://web -o a11y.sarif        # para GitHub code scanning
  a11ytoolkit badge --score 92 --lang en --out badge.svg   # insignia SVG honesta
  a11ytoolkit budget --budget budget.json --audit hoy.json # solo lo NUEVO bloquea
"""

import sys

import a11yaudit
import a11ybadge
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
    'badge': (a11ybadge, None),
    'budget': (a11ybudget, None),
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help') or argv[0] not in SUBCOMANDOS:
        print(__doc__)
        print('Subcomandos disponibles:', ', '.join(SUBCOMANDOS))
        return 0 if argv and argv[0] in ('-h', '--help') else 1
    modulo, sub = SUBCOMANDOS[argv[0]]
    args = ([sub] + argv[1:]) if sub else argv[1:]
    return modulo.main(args)


if __name__ == '__main__':
    sys.exit(main())
