#!/usr/bin/env python3
"""a11y — un solo comando para todo el toolkit.

  a11y pair "#texto" "#fondo" [--lang es|en]
  a11y image ruta.jpg --text "#ffffff" [--region x,y,w,h] [--sample 4]
  a11y audit --url https://cliente.web | --file pagina.html
  a11y declaration --entidad "Nome" --url https://… --estado parcial [opciones]
  a11y snapshot https://miweb --out antes.json      # requiere Playwright
  a11y diff antes.json despues.json
"""

import sys

import a11yaudit
import a11ydiff
import contrast
import declaracion

SUBCOMANDOS = {
    'pair': (contrast, 'pair'),
    'image': (contrast, 'image'),
    'audit': (a11yaudit, None),
    'declaration': (declaracion, None),
    'snapshot': (a11ydiff, 'snapshot'),
    'diff': (a11ydiff, 'diff'),
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
