#!/usr/bin/env python3
"""a11ytoolkit — one command for the whole toolkit.

  a11ytoolkit pair "#text" "#background" [--lang es|en]
  a11ytoolkit image path.jpg --text "#ffffff" [--region x,y,w,h] [--sample 4]
  a11ytoolkit audit --url https://client.web | --file page.html
  a11ytoolkit declaration --entity "Name" --url https://… --status partial [options]
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
  a11ytoolkit evidence audit.json -o pack.json           # verifiable evidence pack
  a11ytoolkit forms https://web/contact                 # form errors (3.3.1/3.3.3)
  a11ytoolkit validate --url https://web                # W3C Nu parser view
  a11ytoolkit disprove --url https://web                # re-verify findings
  a11ytoolkit ledger record --url https://web --audit r.json  # track coverage
  a11ytoolkit contrast-dom https://web --selector ".hero h1"   # auto-region pixel sampling
  a11ytoolkit vpat pack.json --product "App" -o vpat.html    # VPAT 2.5 (WCAG) draft
  a11ytoolkit earl --from-audit audit.json -o earl.json       # ACT Rules / EARL export
  a11ytoolkit init [path]                                  # agent hook: AGENTS.md + MCP config
"""

import sys

from . import a11yaudit
from . import a11ybadge
from . import a11yfix
from . import a11ydom
from . import a11yevidence
from . import a11yvalidate
from . import a11ydisprove
from . import a11yledger
from . import a11yscroll
from . import a11ybudget
from . import a11ycrit
from . import a11ydiff
from . import a11ysarif
from . import contrast
from . import a11ystatement
from . import a11yjourney
from . import a11yvtt
from . import a11ypdf
from . import a11yvpat
from . import a11yact
from . import a11yinit

SUBCOMANDOS = {
    'pair': (contrast, 'pair'),
    'image': (contrast, 'image'),
    'audit': (a11yaudit, None),
    'declaration': (a11ystatement, None),
    'snapshot': (a11ydiff, 'snapshot'),
    'diff': (a11ydiff, 'diff'),
    'criterion': (a11ycrit, None),
    'sarif': (a11ysarif, None),
    'fix': (a11yfix, None),
    'kbd': (a11ydom, 'kbd_main'),
    'scroll': (a11yscroll, None),
    'forms': (a11ydom, 'forms_main'),
    'validate': (a11yvalidate, None),
    'disprove': (a11ydisprove, None),
    'ledger': (a11yledger, None),
    'evidence': (a11yevidence, None),
    'reflow': (a11ydom, 'reflow_main'),
    'badge': (a11ybadge, None),
    'budget': (a11ybudget, None),
    'journey': (a11yjourney, None),
    'journey-budget': (a11yjourney, '_budget_main'),
    'vtt': (a11yvtt, None),
    'pdf': (a11ypdf, None),
    'contrast-dom': (a11ydom, 'contrast_dom_main'),
    'vpat': (a11yvpat, None),
    'earl': (a11yact, None),
    'init': (a11yinit, 'init_main'),
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
