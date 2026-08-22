#!/usr/bin/env python3
"""Generador de Declaración de Accesibilidad (RD 1112/2018 · Ley 11/2023 · EAA).

Produce el documento HTML con la estructura del artículo 10 del RD 1112/2018
(sector público) o la información de accesibilidad de servicio al estilo
Ley 11/2023 (privado/EAA). El HTML generado es accesible de nacimiento:
lang, jerarquía de encabezados, listas semánticas y fechas en <time>.

Uso:
  declaracion.py --entidad "Concello de Ejemplo" --url "https://ejemplo.gal" \
      --estado parcial --no-accesible "El mapa interactivo no tiene alternativa textual" \
      --feedback "accesibilidad@ejemplo.gal" [--marco rd1112|eaa] [--output decl.html]
"""

import argparse
import datetime
import html
import json
import sys

ESTADOS = {
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
}

HOY = datetime.date.today().isoformat()


def generar(entidad, url, estado, contenido_no_accesible=None, metodo=None,
            fecha_evaluacion=None, fecha_revision=None, feedback=None,
            reclamacion=None, marco='rd1112', disponibilidad_alternativa=None):
    """Devuelve dict con 'html' y resumen. marco: 'rd1112' | 'eaa'."""
    if estado not in ESTADOS:
        return {'error': "estado debe ser: 'plena', 'parcial' o 'no_conforme'"}
    contenido_no_accesible = contenido_no_accesible or []
    if estado == 'plena' and contenido_no_accesible:
        return {'error': 'con estado plena no procede enumerar contenido no accesible'}

    e = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    titulo_estado, texto_estado = ESTADOS[estado]
    fecha_evaluacion = fecha_evaluacion or HOY
    fecha_revision = fecha_revision or HOY
    metodo = metodo or ('Revisión manual experta conforme a WCAG 2.2 nivel AA y EN 301 549, '
                        'complementada con verificación automática (axe-core) y prueba con '
                        'teclado y lector de pantalla.')
    feedback = feedback or 'el formulario de contacto del sitio'

    if marco == 'rd1112':
        titulo_doc = 'Declaración de Accesibilidad'
        intro = (f'Declaración de accesibilidad de {e(entidad)} relativa a {e(url)}, '
                 'conforme al Real Decreto 1112/2018, de 7 de septiembre, sobre accesibilidad '
                 'de los sitios webs y aplicaciones para dispositivos móviles del sector público.')
        via_reclamacion = (reclamacion or
                           'Si la respuesta no es satisfactoria, puede presentarse una reclamación '
                           'ante la Unidad de Supervisión de Accesibilidad (División de Inspección '
                           'de Servicios y Atención a las Personas con Discapacidad) conforme al '
                           'artículo 13 del RD 1112/2018.')
    else:
        titulo_doc = 'Información de accesibilidad del servicio'
        intro = (f'Información de accesibilidad del servicio prestado por {e(entidad)} a través '
                 'de {e(url)}, en cumplimiento de la Ley 11/2023, de 8 de mayo, por la que se '
                 'transpone la Directiva (UE) 2019/882 (Acta Europea de Accesibilidad), '
                 'aplicable desde el 28 de junio de 2025.')
        via_reclamacion = (reclamacion or
                           'Se puede comunicar cualquier incidencia de accesibilidad a través del '
                           'punto de contacto indicado. En última instancia, el servicio está '
                           'sujeto a supervisión en los términos de la Ley 11/2023.')

    no_acc = ''
    if contenido_no_accesible:
        items = '\n'.join(f'      <li>{e(x)}</li>' for x in contenido_no_accesible)
        no_acc = f'''
  <h2>Contenido no accesible</h2>
  <p>El contenido listado a continuación no es accesible por alguno de los motivos siguientes:</p>
  <ul>
{items}
  </ul>'''
    elif estado != 'plena':
        no_acc = '''
  <h2>Contenido no accesible</h2>
  <p>No consta contenido no accesible en la última evaluación realizada.</p>'''

    disp = ''
    if disponibilidad_alternativa:
        disp = f'''
  <h2>Disponibilidad alternativa</h2>
  <p>{e(disponibilidad_alternativa)}</p>'''

    doc = f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo_doc} · {e(entidad)}</title>
<meta name="robots" content="noindex">
</head>
<body>
<main>
<h1>{titulo_doc} · {e(entidad)}</h1>
<p>{intro}</p>

  <h2>Estado</h2>
  <p>{texto_estado}</p>
{no_acc}

  <h2>Preparación de esta declaración</h2>
  <ul>
    <li>Fecha de la última evaluación: <time datetime="{e(fecha_evaluacion)}">{e(fecha_evaluacion)}</time></li>
    <li>Declaración elaborada el <time datetime="{e(HOY)}">{e(HOY)}</time></li>
    <li>Método de evaluación: {e(metodo)}</li>
    <li>Última revisión de la declaración: <time datetime="{e(fecha_revision)}">{e(fecha_revision)}</time></li>
  </ul>

  <h2>Observaciones y datos de contacto</h2>
  <p>
    Cualquier comunicación sobre la accesibilidad de este sitio puede dirigirse a
    {e(feedback)}.
  </p>
  <p>{via_reclamacion}</p>
{disp}
</main>
</body>
</html>
'''
    return {
        'html': doc,
        'resumen': {
            'entidad': entidad, 'url': url, 'marco': marco,
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
    p.add_argument('--estado', required=True, choices=list(ESTADOS))
    p.add_argument('--no-accesible', action='append', default=[],
                   help='Contenido no accesible (repetible)')
    p.add_argument('--metodo')
    p.add_argument('--fecha-evaluacion')
    p.add_argument('--fecha-revision')
    p.add_argument('--feedback')
    p.add_argument('--reclamacion')
    p.add_argument('--disponibilidad-alternativa')
    p.add_argument('--marco', default='rd1112', choices=['rd1112', 'eaa'])
    p.add_argument('--output', help='Fichero HTML de salida (por defecto stdout)')
    a = p.parse_args(argv)
    res = generar(a.entidad, a.url, a.estado, a.no_accesible, a.metodo,
                  a.fecha_evaluacion, a.fecha_revision, a.feedback,
                  a.reclamacion, a.marco, a.disponibilidad_alternativa)
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
