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

TODAY = datetime.date.today().isoformat()

STATES = {
    'es': {
        'full': ('Plenamente conforme',
                  'El sitio web es <strong>plenamente conforme</strong> con el estándar '
                  '<abbr lang="en" title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 '
                  'nivel AA, incluido en la norma <abbr lang="en">EN&nbsp;301&nbsp;549</abbr>.'),
        'partial': ('Parcialmente conforme',
                    'El sitio web es <strong>parcialmente conforme</strong> con el estándar '
                    '<abbr lang="en" title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 '
                    'nivel AA, incluido en la norma <abbr lang="en">EN&nbsp;301&nbsp;549</abbr>, '
                    'por los contenidos no accesibles que se enumeran a continuación.'),
        'not_conformant': ('No conforme',
                        'El sitio web <strong>no es conforme</strong> con el estándar '
                        '<abbr lang="en" title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 '
                        'nivel AA, incluido en la norma <abbr lang="en">EN&nbsp;301&nbsp;549</abbr>. '
                        'Los contenidos no accesibles se enumeran a continuación.'),
    },
    'en': {
        'full': ('Fully compliant',
                  'The website is <strong>fully compliant</strong> with '
                  '<abbr title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 level AA, '
                  'as included in standard <abbr>EN&nbsp;301&nbsp;549</abbr>.'),
        'partial': ('Partially compliant',
                    'The website is <strong>partially compliant</strong> with '
                    '<abbr title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 level AA, '
                    'as included in standard <abbr>EN&nbsp;301&nbsp;549</abbr>, due to the '
                    'non-accessible content listed below.'),
        'not_conformant': ('Not compliant',
                        'The website <strong>is not compliant</strong> with '
                        '<abbr title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 level AA, '
                        'as included in standard <abbr>EN&nbsp;301&nbsp;549</abbr>. The '
                        'non-accessible content is listed below.'),
    },
}

TXT = {
    'es': {
        'title': {'rd1112': 'Declaración de Accesibilidad',
                   'eaa': 'Información de accesibilidad del servicio'},
        'intro': {
            'rd1112': ('Declaración de accesibilidad de {e} relativa a {u}, conforme al Real '
                       'Decreto 1112/2018, de 7 de septiembre, sobre accesibilidad de los sitios '
                       'webs y aplicaciones para dispositivos móviles del sector público.'),
            'eaa': ('Información de accesibilidad del servicio prestado por {e} a través de {u}, '
                    'en cumplimiento de la Ley 11/2023, de 8 de mayo, por la que se transpone la '
                    'Directiva (UE) 2019/882 (Acta Europea de Accesibilidad), aplicable desde el '
                    '28 de junio de 2025.'),
        },
        'h_status': 'Estado', 'h_inaccessible': 'Contenido no accesible',
        'h_preparation': 'Preparación de esta declaración',
        'h_contact': 'Observaciones y datos de contacto',
        'h_alt_access': 'Disponibilidad alternativa',
        'inaccessible_intro': 'El contenido listado a continuación no es accesible por alguno de los motivos siguientes:',
        'inaccessible_empty': 'No consta contenido no accesible en la última evaluación realizada.',
        'l_evaluation': 'Fecha de la última evaluación', 'l_declared': 'Declaración elaborada el',
        'l_method': 'Método de evaluación', 'l_review': 'Última revisión de la declaración',
        'contact': ('Cualquier comunicación sobre la accesibilidad de este sitio puede '
                     'dirigirse a {f}.'),
        'complaints': {
            'rd1112': ('Si la respuesta no es satisfactoria, puede presentarse una reclamación '
                       'ante la Unidad de Supervisión de Accesibilidad (División de Inspección '
                       'de Servicios y Atención a las Personas con Discapacidad) conforme al '
                       'artículo 13 del RD 1112/2018.'),
            'eaa': ('Se puede comunicar cualquier incidencia de accesibilidad a través del punto '
                    'de contacto indicado. En última instancia, el servicio está sujeto a '
                    'supervisión en los términos de la Ley 11/2023.'),
        },
        'method_default': ('Pendiente de completar: declara aquí el método de evaluación real '
                           '(revisión manual, herramientas y pruebas realizadas), con fechas y '
                           'responsable. Esta declaración es un BORRADOR NO VALIDADO mientras '
                           'este campo no se complete.'),
        'feedback_default': 'el formulario de contacto del sitio',
        'error_status': "estado debe ser: 'plena', 'parcial' o 'no_conforme'",
        'error_inconsistent': 'con estado plena no procede enumerar contenido no accesible',
    },
    'en': {
        'title': {'rd1112': 'Accessibility Declaration',
                   'eaa': 'Service accessibility information'},
        'intro': {
            'rd1112': ('Accessibility declaration of {e} regarding {u}, in accordance with '
                       'Directive (EU) 2016/2102 on the accessibility of the websites and mobile '
                       'applications of public sector bodies and standard EN 301 549 '
                       '(transposed in Spain by Royal Decree 1112/2018).'),
            'eaa': ('Accessibility information for the service provided by {e} through {u}, in '
                    'compliance with Directive (EU) 2019/882 (European Accessibility Act), '
                    'applicable since 28 June 2025.'),
        },
        'h_status': 'Status', 'h_inaccessible': 'Non-accessible content',
        'h_preparation': 'Preparation of this declaration',
        'h_contact': 'Feedback and contact information',
        'h_alt_access': 'Alternative access',
        'inaccessible_intro': 'The content listed below is not accessible for one of the following reasons:',
        'inaccessible_empty': 'No non-accessible content is recorded in the latest assessment.',
        'l_evaluation': 'Date of latest assessment', 'l_declared': 'Declaration drawn up on',
        'l_method': 'Assessment method', 'l_review': 'Last revision of the declaration',
        'contact': 'Any communication about the accessibility of this website can be sent to {f}.',
        'complaints': {
            'rd1112': ('If the response is not satisfactory, an enforcement complaint may be '
                       'lodged with the accessibility supervisory body of the relevant Member '
                       'State (in Spain, the Accessibility Supervision Unit under Article 13 of '
                       'Royal Decree 1112/2018).'),
            'eaa': ('Any accessibility issue may be reported through the contact point '
                    'indicated. The service is ultimately subject to supervision under the '
                    'terms of Directive (EU) 2019/882.'),
        },
        'method_default': ('To be completed: state the actual assessment method '
                           '(manual review, tools used and testing performed), with dates and '
                           'a responsible party. This declaration remains an UNVALIDATED DRAFT '
                           'until this field is filled.'),
        'feedback_default': 'the site contact form',
        'error_status': "estado must be: 'plena', 'parcial' or 'no_conforme'",
        'error_inconsistent': 'with fully-compliant status, non-accessible content cannot be listed',
    },
}


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
    evaluation_date = evaluation_date or TODAY
    review_date = review_date or TODAY
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

  <h2>{t['h_status']} · {status_title}</h2>
  <p>{status_text}</p>
{no_acc}

  <h2>{t['h_preparation']}</h2>
  <ul>
    <li>{t['l_evaluation']}: <time datetime="{e(evaluation_date)}">{e(evaluation_date)}</time></li>
    <li>{t['l_declared']} <time datetime="{e(TODAY)}">{e(TODAY)}</time></li>
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
            'dates': {'evaluation': evaluation_date, 'declaration': TODAY,
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
