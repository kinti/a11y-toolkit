#!/usr/bin/env python3
"""Accessibility Statement generator (bilingual es/en).

- framework 'rd1112': art. 10 of RD 1112/2018 (ES) or Directive (EU)
  2016/2102 / EN 301 549 style statement (EN) — public sector.
- framework 'eaa': Ley 11/2023 (ES) or the service accessibility information
  under Directive (EU) 2019/882 — European Accessibility Act (EN).

The generated HTML is accessible by construction (correct lang, heading
hierarchy, semantic lists, dates in <time>).

Usage:
  declaracion.py --entity "Name" --url "https://…" --status partial \
      --inaccessible "…" --feedback "a@b.gal" [--framework rd1112|eaa] \
      [--lang es|en] [--output decl.html]
"""

import argparse
import datetime
import html
import json
import sys
from . import a11yi18n

def TODAY() -> str:
    # computed per call: freezing it at import time produced statements dated
    # with the process START time (long-running processes)
    return datetime.date.today().isoformat()

STATES = a11yi18n.pair('statement_states')  # locales/<lang>.json — community-editable

TXT = a11yi18n.pair('statement_txt')  # locales/<lang>.json — community-editable


# estados canónicos ingleses; los valores españoles pre-5.11 se aceptan como alias
STATUS_ALIASES = {'plena': 'full', 'parcial': 'partial', 'no_conforme': 'not_conformant'}


def generate(entity, url, status, inaccessible_content=None, method=None,
            evaluation_date=None, review_date=None, feedback=None,
            complaints=None, framework='rd1112', alternative_format=None,
            lang='en'):
    """Devuelve dict con 'html' y resumen. framework: 'rd1112'|'eaa' · lang: 'es'|'en'."""
    t = TXT.get(lang, TXT['es'])
    status = STATUS_ALIASES.get(status, status)
    if status not in STATES['es']:
        return {'error': t['error_status']}
    inaccessible_content = inaccessible_content or []
    if status == 'full' and inaccessible_content:
        return {'error': t['error_inconsistent']}

    e = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    status_title, status_text = STATES.get(lang, STATES['es'])[status]
    evaluation_date = evaluation_date or TODAY()
    review_date = review_date or TODAY()
    method = method or t['method_default']
    feedback = feedback or t['feedback_default']

    if inaccessible_content:
        items = '\n'.join(f'      <li>{e(x)}</li>' for x in inaccessible_content)
        no_acc = f'''
  <h2>{t['h_inaccessible']}</h2>
  <p>{t['inaccessible_intro']}</p>
  <ul>
{items}
  </ul>'''
    else:
        no_acc = f'''
  <h2>{t['h_inaccessible']}</h2>
  <p>{t['inaccessible_empty']}</p>'''

    disalt = ''
    if alternative_format:
        disalt = f'''
  <h2>{t['h_alt_access']}</h2>
  <p>{e(alternative_format)}</p>'''

    doc_title = t['title'][framework]
    doc = f'''<!doctype html>
<html lang="{html.escape(str(lang), quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{doc_title} · {e(entity)}</title>
<meta name="robots" content="noindex">
</head>
<body>
<main>
<h1>{doc_title} · {e(entity)}</h1>
  <p>{t['intro'][framework].format(e=e(entity), u=e(url))}</p>
  <p>{t['standard_note']}</p>

  <h2>{t['h_status']} · {status_title}</h2>
  <p>{status_text}</p>
{no_acc}

  <h2>{t['h_preparation']}</h2>
  <ul>
    <li>{t['l_evaluation']}: <time datetime="{e(evaluation_date)}">{e(evaluation_date)}</time></li>
    <li>{t['l_declared']} <time datetime="{e(TODAY())}">{e(TODAY())}</time></li>
    <li>{t['l_method']}: {e(method)}</li>
    <li>{t['l_review']}: <time datetime="{e(review_date)}">{e(review_date)}</time></li>
  </ul>

  <h2>{t['h_contact']}</h2>
  <p>{t['contact'].format(f=e(feedback))}</p>
  <p>{e(complaints) if complaints else t['complaints'][framework]}</p>
{disalt}
</main>
</body>
</html>
'''
    return {
        'html': doc,
        'summary': {
            'entity': entity, 'url': url, 'framework': framework, 'lang': lang,
            'status': status_title,
            'inaccessible_items': len(inaccessible_content),
            'dates': {'evaluation': evaluation_date, 'declaration': TODAY(),
                       'review': review_date},
        },
    }


def main(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entity', required=True)
    p.add_argument('--url', required=True)
    p.add_argument('--status', required=True,
                   choices=['full', 'partial', 'not_conformant', 'plena', 'parcial', 'no_conforme'])
    p.add_argument('--inaccessible', action='append', default=[])
    p.add_argument('--method')
    p.add_argument('--evaluation-date')
    p.add_argument('--review-date')
    p.add_argument('--feedback')
    p.add_argument('--complaints')
    p.add_argument('--alternative-format')
    p.add_argument('--framework', default='rd1112', choices=['rd1112', 'eaa'])
    p.add_argument('--lang', default='en', choices=['en', 'es'])
    p.add_argument('--output')
    a = p.parse_args(argv)
    res = generate(a.entity, a.url, a.status, a.inaccessible, a.method,
                  a.evaluation_date, a.review_date, a.feedback,
                  a.complaints, a.framework, a.alternative_format, a.lang)
    if 'error' in res:
        print(res['error'], file=sys.stderr)
        return 1
    if a.output:
        with open(a.output, 'w', encoding='utf-8') as f:
            f.write(res['html'])
        print(json.dumps(res['summary'], ensure_ascii=False, indent=1))
    else:
        print(res['html'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
