#!/usr/bin/env python3
"""Generador de Declaración de Accesibilidad (multilenguaje es/en).

- marco 'rd1112': art. 10 del RD 1112/2018 (ES) o declaración estilo Directiva
  (UE) 2016/2102 / EN 301 549 (EN) — sector público.
- marco 'eaa': Ley 11/2023 (ES) o información de accesibilidad del servicio
  conforme a la Directiva (UE) 2019/882 — European Accessibility Act (EN).

El HTML generado es accesible de nacimiento (lang correcto, jerarquía de
encabezados, listas semánticas, fechas en <time>).

Uso:
  declaracion.py --entidad "Nome" --url "https://…" --estado parcial \
      --no-accesible "…" --feedback "a@b.gal" [--marco rd1112|eaa] \
      [--lang es|en] [--output decl.html]
"""

import argparse
import datetime
import html
import json
import sys

HOY = datetime.date.today().isoformat()

ESTADOS = {
    'es': {
        'plena': ('Plenamente conforme',
                  'El sitio web es <strong>plenamente conforme</strong> con el estándar '
                  '<abbr lang="en" title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 '
                  'nivel AA, incluido en la norma <abbr lang="en">EN&nbsp;301&nbsp;549</abbr>.'),
        'parcial': ('Parcialmente conforme',
                    'El sitio web es <strong>parcialmente conforme</strong> con el estándar '
                    '<abbr lang="en" title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 '
                    'nivel AA, incluido en la norma <abbr lang="en">EN&nbsp;301&nbsp;549</abbr>, '
                    'por los contenidos no accesibles que se enumeran a continuación.'),
        'no_conforme': ('No conforme',
                        'El sitio web <strong>no es conforme</strong> con el estándar '
                        '<abbr lang="en" title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 '
                        'nivel AA, incluido en la norma <abbr lang="en">EN&nbsp;301&nbsp;549</abbr>. '
                        'Los contenidos no accesibles se enumeran a continuación.'),
    },
    'en': {
        'plena': ('Fully compliant',
                  'The website is <strong>fully compliant</strong> with '
                  '<abbr title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 level AA, '
                  'as included in standard <abbr>EN&nbsp;301&nbsp;549</abbr>.'),
        'parcial': ('Partially compliant',
                    'The website is <strong>partially compliant</strong> with '
                    '<abbr title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 level AA, '
                    'as included in standard <abbr>EN&nbsp;301&nbsp;549</abbr>, due to the '
                    'non-accessible content listed below.'),
        'no_conforme': ('Not compliant',
                        'The website <strong>is not compliant</strong> with '
                        '<abbr title="Web Content Accessibility Guidelines">WCAG</abbr> 2.2 level AA, '
                        'as included in standard <abbr>EN&nbsp;301&nbsp;549</abbr>. The '
                        'non-accessible content is listed below.'),
    },
}

TXT = {
    'es': {
        'titulo': {'rd1112': 'Declaración de Accesibilidad',
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
        'h_estado': 'Estado', 'h_noacc': 'Contenido no accesible',
        'h_prep': 'Preparación de esta declaración',
        'h_contacto': 'Observaciones y datos de contacto',
        'h_disalt': 'Disponibilidad alternativa',
        'noacc_intro': 'El contenido listado a continuación no es accesible por alguno de los motivos siguientes:',
        'noacc_vacio': 'No consta contenido no accesible en la última evaluación realizada.',
        'l_eval': 'Fecha de la última evaluación', 'l_declar': 'Declaración elaborada el',
        'l_metodo': 'Método de evaluación', 'l_revision': 'Última revisión de la declaración',
        'contacto': ('Cualquier comunicación sobre la accesibilidad de este sitio puede '
                     'dirigirse a {f}.'),
        'reclamacion': {
            'rd1112': ('Si la respuesta no es satisfactoria, puede presentarse una reclamación '
                       'ante la Unidad de Supervisión de Accesibilidad (División de Inspección '
                       'de Servicios y Atención a las Personas con Discapacidad) conforme al '
                       'artículo 13 del RD 1112/2018.'),
            'eaa': ('Se puede comunicar cualquier incidencia de accesibilidad a través del punto '
                    'de contacto indicado. En última instancia, el servicio está sujeto a '
                    'supervisión en los términos de la Ley 11/2023.'),
        },
        'metodo_defecto': ('Revisión manual experta conforme a WCAG 2.2 nivel AA y EN 301 549, '
                           'complementada con verificación automática (axe-core) y prueba con '
                           'teclado y lector de pantalla.'),
        'feedback_defecto': 'el formulario de contacto del sitio',
        'error_estado': "estado debe ser: 'plena', 'parcial' o 'no_conforme'",
        'error_incoherente': 'con estado plena no procede enumerar contenido no accesible',
    },
    'en': {
        'titulo': {'rd1112': 'Accessibility Declaration',
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
        'h_estado': 'Status', 'h_noacc': 'Non-accessible content',
        'h_prep': 'Preparation of this declaration',
        'h_contacto': 'Feedback and contact information',
        'h_disalt': 'Alternative access',
        'noacc_intro': 'The content listed below is not accessible for one of the following reasons:',
        'noacc_vacio': 'No non-accessible content is recorded in the latest assessment.',
        'l_eval': 'Date of latest assessment', 'l_declar': 'Declaration drawn up on',
        'l_metodo': 'Assessment method', 'l_revision': 'Last revision of the declaration',
        'contacto': 'Any communication about the accessibility of this website can be sent to {f}.',
        'reclamacion': {
            'rd1112': ('If the response is not satisfactory, an enforcement complaint may be '
                       'lodged with the accessibility supervisory body of the relevant Member '
                       'State (in Spain, the Accessibility Supervision Unit under Article 13 of '
                       'Royal Decree 1112/2018).'),
            'eaa': ('Any accessibility issue may be reported through the contact point '
                    'indicated. The service is ultimately subject to supervision under the '
                    'terms of Directive (EU) 2019/882.'),
        },
        'metodo_defecto': ('Expert manual review against WCAG 2.2 level AA and EN 301 549, '
                           'complemented by automated checking (axe-core) and keyboard and '
                           'screen reader testing.'),
        'feedback_defecto': 'the site contact form',
        'error_estado': "estado must be: 'plena', 'parcial' or 'no_conforme'",
        'error_incoherente': 'with fully-compliant status, non-accessible content cannot be listed',
    },
}


def generar(entidad, url, estado, contenido_no_accesible=None, metodo=None,
            fecha_evaluacion=None, fecha_revision=None, feedback=None,
            reclamacion=None, marco='rd1112', disponibilidad_alternativa=None,
            lang='es'):
    """Devuelve dict con 'html' y resumen. marco: 'rd1112'|'eaa' · lang: 'es'|'en'."""
    t = TXT.get(lang, TXT['es'])
    if estado not in ESTADOS['es']:
        return {'error': t['error_estado']}
    contenido_no_accesible = contenido_no_accesible or []
    if estado == 'plena' and contenido_no_accesible:
        return {'error': t['error_incoherente']}

    e = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    titulo_estado, texto_estado = ESTADOS.get(lang, ESTADOS['es'])[estado]
    fecha_evaluacion = fecha_evaluacion or HOY
    fecha_revision = fecha_revision or HOY
    metodo = metodo or t['metodo_defecto']
    feedback = feedback or t['feedback_defecto']

    if contenido_no_accesible:
        items = '\n'.join(f'      <li>{e(x)}</li>' for x in contenido_no_accesible)
        no_acc = f'''
  <h2>{t['h_noacc']}</h2>
  <p>{t['noacc_intro']}</p>
  <ul>
{items}
  </ul>'''
    else:
        no_acc = f'''
  <h2>{t['h_noacc']}</h2>
  <p>{t['noacc_vacio']}</p>'''

    disalt = ''
    if disponibilidad_alternativa:
        disalt = f'''
  <h2>{t['h_disalt']}</h2>
  <p>{e(disponibilidad_alternativa)}</p>'''

    titulo_doc = t['titulo'][marco]
    doc = f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo_doc} · {e(entidad)}</title>
<meta name="robots" content="noindex">
</head>
<body>
<main>
<h1>{titulo_doc} · {e(entidad)}</h1>
<p>{t['intro'][marco].format(e=e(entidad), u=e(url))}</p>

  <h2>{t['h_estado']} · {titulo_estado}</h2>
  <p>{texto_estado}</p>
{no_acc}

  <h2>{t['h_prep']}</h2>
  <ul>
    <li>{t['l_eval']}: <time datetime="{e(fecha_evaluacion)}">{e(fecha_evaluacion)}</time></li>
    <li>{t['l_declar']} <time datetime="{e(HOY)}">{e(HOY)}</time></li>
    <li>{t['l_metodo']}: {e(metodo)}</li>
    <li>{t['l_revision']}: <time datetime="{e(fecha_revision)}">{e(fecha_revision)}</time></li>
  </ul>

  <h2>{t['h_contacto']}</h2>
  <p>{t['contacto'].format(f=e(feedback))}</p>
  <p>{e(reclamacion) if reclamacion else t['reclamacion'][marco]}</p>
{disalt}
</main>
</body>
</html>
'''
    return {
        'html': doc,
        'resumen': {
            'entidad': entidad, 'url': url, 'marco': marco, 'lang': lang,
            'estado': titulo_estado,
            'items_no_accesibles': len(contenido_no_accesible),
            'fechas': {'evaluacion': fecha_evaluacion, 'declaracion': HOY,
                       'revision': fecha_revision},
        },
    }


def main(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entidad', required=True)
    p.add_argument('--url', required=True)
    p.add_argument('--estado', required=True, choices=['plena', 'parcial', 'no_conforme'])
    p.add_argument('--no-accesible', action='append', default=[])
    p.add_argument('--metodo')
    p.add_argument('--fecha-evaluacion')
    p.add_argument('--fecha-revision')
    p.add_argument('--feedback')
    p.add_argument('--reclamacion')
    p.add_argument('--disponibilidad-alternativa')
    p.add_argument('--marco', default='rd1112', choices=['rd1112', 'eaa'])
    p.add_argument('--lang', default='es', choices=['es', 'en'])
    p.add_argument('--output')
    a = p.parse_args(argv)
    res = generar(a.entidad, a.url, a.estado, a.no_accesible, a.metodo,
                  a.fecha_evaluacion, a.fecha_revision, a.feedback,
                  a.reclamacion, a.marco, a.disponibilidad_alternativa, a.lang)
    if 'error' in res:
        print(res['error'], file=sys.stderr)
        return 1
    if a.output:
        with open(a.output, 'w', encoding='utf-8') as f:
            f.write(res['html'])
        print(json.dumps(res['resumen'], ensure_ascii=False, indent=1))
    else:
        print(res['html'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
