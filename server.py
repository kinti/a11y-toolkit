#!/usr/bin/env python3
"""a11y-toolkit MCP v2 · mini-servidor MCP (stdio, JSON-RPC, cero dependencias).

Herramientas expuestas:
  - a11y_contrast_pair(fg, bg)                  → ratio + veredictos + sugerencia
  - a11y_contrast_image(path, text_color, region?, sample?) → muestreo fondo real
  - a11y_suggest_color(fg, bg, target?)         → color más cercano que cumple
  - a11y_generate_declaration(...)              → declaración RD 1112/2018 / Ley 11/2023 (HTML)
  - a11y_aria_live_snippet()                    → código del monitor de anuncios inyectable

Registro en un cliente MCP:

  { "mcpServers": { "a11y-toolkit": {
      "command": "python3",
      "args": ["/Users/mm/Dev/A11Y-MCP/server.py"] } } }
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from contrast import pair as pair_fn, image_contrast, sugerir, parse_color  # noqa: E402
from declaracion import generar as declaracion_fn  # noqa: E402
from a11yaudit import audit_url as audit_url_fn  # noqa: E402

TOOLS = [
    {
        'name': 'a11y_contrast_pair',
        'description': ('Contraste WCAG 2.2 de un par de colores: ratio exacto y veredictos '
                        'por criterio 1.4.3 (AA), 1.4.6 (AAA) y 1.4.11 (no textual). Si no pasa '
                        'AA, sugiere el color más cercano que sí pasa.'),
        'inputSchema': {'type': 'object', 'properties': {
            'fg': {'type': 'string'}, 'bg': {'type': 'string'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'Idioma de la salida (es por defecto)'},
        }, 'required': ['fg', 'bg']},
    },
    {
        'name': 'a11y_contrast_image',
        'description': ('Contraste de TEXTO SOBRE IMAGEN: muestrea píxel a píxel el fondo real '
                        'de la región y devuelve ratio peor/mediana/p95 y % de área que pasa AA. '
                        'region="x,y,ancho,alto" delimita la caja del texto (recomendado).'),
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string'}, 'text_color': {'type': 'string'},
            'region': {'type': 'string'},
            'sample': {'type': 'integer'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['path', 'text_color']},
    },
    {
        'name': 'a11y_suggest_color',
        'description': 'Color más cercano a fg que alcanza el ratio objetivo contra bg (4.5 por defecto).',
        'inputSchema': {'type': 'object', 'properties': {
            'fg': {'type': 'string'}, 'bg': {'type': 'string'},
            'target': {'type': 'number'},
        }, 'required': ['fg', 'bg']},
    },
    {
        'name': 'a11y_generate_declaration',
        'description': ('Genera una Declaración de Accesibilidad en HTML conforme al artículo 10 '
                        'del RD 1112/2018 (sector público) o la información de accesibilidad estilo '
                        'Ley 11/2023/EAA (marco="eaa"). Campos legales incluidos; el HTML es accesible.'),
        'inputSchema': {'type': 'object', 'properties': {
            'entidad': {'type': 'string'}, 'url': {'type': 'string'},
            'estado': {'type': 'string', 'enum': ['plena', 'parcial', 'no_conforme']},
            'contenido_no_accesible': {'type': 'array', 'items': {'type': 'string'}},
            'metodo': {'type': 'string'},
            'fecha_evaluacion': {'type': 'string'},
            'fecha_revision': {'type': 'string'},
            'feedback': {'type': 'string'},
            'reclamacion': {'type': 'string'},
            'marco': {'type': 'string', 'enum': ['rd1112', 'eaa']},
            'disponibilidad_alternativa': {'type': 'string'},
            'output_path': {'type': 'string', 'description': 'Guarda el HTML en esta ruta (opcional)'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'Idioma de la declaración (es por defecto; en = Directive (EU) 2016/2102 / EAA wording)'},
        }, 'required': ['entidad', 'url', 'estado']},
    },
    {
        'name': 'a11y_audit_url',
        'description': ('Express accessibility audit of a URL: fetches the page and checks '
                        'automatic WCAG 2.2 signals — images without alt (1.1.1), controls '
                        'without accessible names (4.1.2), form fields without labels (3.3.2), '
                        'missing lang/title (3.1.1, 2.4.2), heading level skips (1.3.1), blocked '
                        'zoom (1.4.4), positive tabindex (2.4.3), untitled iframes. Returns '
                        'findings by severity. Filter, not verdict: automation covers ~1/3 of WCAG.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['url']},
    },
    {
        'name': 'a11y_aria_live_snippet',
        'description': ('Devuelve el código JavaScript del monitor de anuncios aria-live para '
                        'inyectar en una página (bookmarklet o page.evaluate): registra cada '
                        'anuncio de regiones dinámicas con hora, cortesía, rol y texto.'),
        'inputSchema': {'type': 'object', 'properties': {
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'Idioma del panel del monitor (es por defecto)'},
        }},
    },
]


def _texto(obj):
    r = {'content': [{'type': 'text', 'text': json.dumps(obj, ensure_ascii=False, indent=1)}]}
    if isinstance(obj, dict) and 'error' in obj:
        r['isError'] = True
    return r


def llamar(nombre, args):
    if nombre == 'a11y_contrast_pair':
        return _texto(pair_fn(args['fg'], args['bg'], lang=args.get('lang', 'es')))
    if nombre == 'a11y_contrast_image':
        return _texto(image_contrast(args['path'], args['text_color'],
                                     region=args.get('region'), sample=args.get('sample', 4), lang=args.get('lang', 'es')))
    if nombre == 'a11y_suggest_color':
        fg, bg = parse_color(args['fg']), parse_color(args['bg'])
        if not fg or not bg:
            return _texto({'error': 'color no válido'})
        return _texto(sugerir(fg, bg, float(args.get('target', 4.5)), args.get('lang', 'es')) or {'resultado': None})
    if nombre == 'a11y_generate_declaration':
        res = declaracion_fn(
            args['entidad'], args['url'], args['estado'],
            contenido_no_accesible=args.get('contenido_no_accesible'),
            metodo=args.get('metodo'), fecha_evaluacion=args.get('fecha_evaluacion'),
            fecha_revision=args.get('fecha_revision'), feedback=args.get('feedback'),
            reclamacion=args.get('reclamacion'), marco=args.get('marco', 'rd1112'),
            disponibilidad_alternativa=args.get('disponibilidad_alternativa'),
            lang=args.get('lang', 'es'))
        if 'error' in res:
            return {'content': [{'type': 'text', 'text': res['error']}], 'isError': True}
        salida = args.get('output_path')
        if salida:
            with open(salida, 'w', encoding='utf-8') as f:
                f.write(res['html'])
            return _texto({'guardado_en': salida, 'resumen': res['resumen']})
        return {'content': [{'type': 'text', 'text': res['html']}]}
    if nombre == 'a11y_audit_url':
        try:
            return _texto(audit_url_fn(args['url']))
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_aria_live_snippet':
        with open(os.path.join(AQUI, 'arialive.js'), encoding='utf-8') as f:
            js = f.read()
        if args.get('lang') == 'en':
            js = "window.ALM_LANG='en';\n" + js
        return {'content': [{'type': 'text', 'text': js}]}
    raise ValueError(f'herramienta desconocida: {nombre}')


def main():
    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        try:
            msg = json.loads(linea)
        except json.JSONDecodeError:
            continue
        metodo = msg.get('method', '')
        mid = msg.get('id')
        if mid is None:
            continue
        try:
            if metodo == 'initialize':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {
                    'protocolVersion': msg.get('params', {}).get('protocolVersion', '2024-11-05'),
                    'capabilities': {'tools': {}},
                    'serverInfo': {'name': 'a11y-toolkit', 'version': '2.2.0'},
                }}
            elif metodo == 'ping':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {}}
            elif metodo == 'tools/list':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {'tools': TOOLS}}
            elif metodo == 'tools/call':
                p = msg.get('params', {})
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': llamar(p.get('name'), p.get('arguments') or {})}
            else:
                resp = {'jsonrpc': '2.0', 'id': mid,
                        'error': {'code': -32601, 'message': f'método desconocido: {metodo}'}}
        except Exception as e:  # noqa: BLE001
            resp = {'jsonrpc': '2.0', 'id': mid, 'result': {
                'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
