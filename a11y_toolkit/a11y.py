#!/usr/bin/env python3
"""a11ytoolkit — one command for the whole toolkit.

  a11ytoolkit pair "#text" "#background" [--lang es|en]
  a11ytoolkit image path.jpg --text "#ffffff" [--region x,y,w,h] [--sample 4]
  a11ytoolkit audit --url https://client.web | --file page.html
  a11ytoolkit declaration --entity "Name" --url https://… --status partial [options]
  a11ytoolkit engines https://web                        # same page in 3 engines: behavioral divergences
  a11ytoolkit trace https://web -o t.json && a11ytoolkit trace diff t1.json t2.json   # journey gate
  a11ytoolkit patterns https://web                       # APG keyboard contracts: dialog, tablist, disclosure
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
  a11ytoolkit openacr pack.json --product "App" -o openacr.yaml  # OpenACR YAML (GSA) draft
  a11ytoolkit earl --from-audit audit.json -o earl.json       # ACT Rules / EARL export
  a11ytoolkit init [path]                                  # agent hook: AGENTS.md + MCP config
  a11ytoolkit wcag3 --from-audit audit.json                # WCAG 3 draft preview (no score)
  a11ytoolkit route --goal "gate my PR"                     # which tools for the task
  a11ytoolkit route --file page.html                        # diagnosis: read the page, order the exams
  a11ytoolkit dom https://web                               # rendered audit (needs Playwright)
  a11ytoolkit hover https://mysite                          # tooltip dismissibility (1.4.13)
  a11ytoolkit criteria --list --level AA --new-in 2.2       # criterion's alias: the Quick Ref
  a11ytoolkit wizard --url https://client.web --lang es     # guided: standard, audit, scope, annex
  a11ytoolkit mutants --seed 7 --n 12                       # the engine's sealed self-exam
  a11ytoolkit corpus build && a11ytoolkit corpus verify     # versioned audit corpus (dataset + baselines)
  a11ytoolkit fingerprints page1.html page2.html --dir p/  # twin-page detection (one audit per template)
  a11ytoolkit audit --url https://web --standard en301549   # EN 301 549 clause on every finding
  a11ytoolkit scope audit.json -o scope.json --standard en301549  # applicability: machine proposes, human confirms
  a11ytoolkit annotate page.html --report r.json -o copy.html  # per-element marks on a copy
  a11ytoolkit locate --file page.html --query "Submit"     # element by accessible name → route
  a11ytoolkit patches --file page.html -o patches.json     # sealed fix record (verify with --verify)
  a11ytoolkit guard --file page.html                       # write-time gate: NEW high/medium refuse the save
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
from . import a11ycorpus
from . import contrast
from . import a11ystatement
from . import a11yjourney
from . import a11yvtt
from . import a11ypdf
from . import a11yvpat
from . import a11yopenacr
from . import a11yact
from . import a11yinit
from . import a11ywcag3
from . import a11yroute
from . import a11ymutants
from . import a11yfingerprints
from . import a11yscope
from . import a11yannotate
from . import a11ylocate
from . import a11ypatches
from . import a11ygate
from . import a11yengines
from . import a11ytrace
from . import a11ypatterns
from . import a11ywiz

SUBCOMMANDS = {
    'pair': (contrast, 'pair'),
    'image': (contrast, 'image'),
    'audit': (a11yaudit, None),
    'declaration': (a11ystatement, None),
    'snapshot': (a11ydiff, 'snapshot'),
    'diff': (a11ydiff, 'diff'),
    'criterion': (a11ycrit, None),
    'criteria': (a11ycrit, None),
    'sarif': (a11ysarif, None),
    'corpus': (a11ycorpus, None),
    'fix': (a11yfix, None),
    'kbd': (a11ydom, 'kbd_main'),
    'hover': (a11ydom, 'hover_main'),
    'dom': (a11ydom, None),
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
    'openacr': (a11yopenacr, None),
    'earl': (a11yact, None),
    'init': (a11yinit, 'init_main'),
    'wcag3': (a11ywcag3, None),
    'route': (a11yroute, None),
    'mutants': (a11ymutants, None),
    'fingerprints': (a11yfingerprints, None),
    'scope': (a11yscope, None),
    'annotate': (a11yannotate, None),
    'locate': (a11ylocate, None),
    'patches': (a11ypatches, None),
    'guard': (a11ygate, None),
    'engines': (a11yengines, None),
    'trace': (a11ytrace, None),
    'patterns': (a11ypatterns, None),
    'wizard': (a11ywiz, None),
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        print('Available subcommands:', ', '.join(sorted(SUBCOMMANDS)))
        return 0
    if argv[0] not in SUBCOMMANDS:
        print(__doc__)
        print(f'Unknown subcommand: {argv[0]}. Available:', ', '.join(sorted(SUBCOMMANDS)))
        return 2
    modulo, sub = SUBCOMMANDS[argv[0]]
    if sub and sub.endswith('_main'):
        return getattr(modulo, sub)(argv[1:])   # función propia (reflow_main, kbd_main)
    args = ([sub] + argv[1:]) if sub else argv[1:]
    return modulo.main(args)


if __name__ == '__main__':
    sys.exit(main())
