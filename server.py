#!/usr/bin/env python3
"""a11y-toolkit MCP v3 · stdio MCP server (JSON-RPC, zero dependencies).

The accessibility layer for AI coding agents: audit → fix → document → watch.

Tools:
  - a11y_audit_url(url | html, lang?, timeout?)   express static WCAG audit
  - a11y_audit_dom(url, lang?, timeout?)          rendered audit (Playwright):
                                                  real contrast, target size 2.5.8,
                                                  focus indicator
  - a11y_contrast_pair(fg, bg, lang?)             ratio + AA/AAA verdicts + fix
  - a11y_contrast_image(path, text_color, ...)    text over image, pixel sampling
  - a11y_suggest_color(fg, bg, target?)           nearest passing color
  - a11y_generate_declaration(...)                legal statement RD 1112/2018 / EAA
  - a11y_snapshot(url)                            interactive elements + tab order
  - a11y_diff(a, b)                               regression diff between snapshots
  - a11y_diff_urls(url_a, url_b)                  staging vs production in one call
  - a11y_aria_live_snippet(lang?)                 injectable live-region monitor

Prompts: audit-page, fix-contrast, pre-deploy-check, declaration-eaa.

Register in an MCP client (no clone needed):

  { "mcpServers": { "a11y-toolkit": {
      "command": "uvx", "args": ["--from", "a11y-toolkit", "a11y-toolkit-mcp"] } } }
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

from contrast import pair as pair_fn, image_contrast, sugerir, parse_color  # noqa: E402
from declaracion import generar as declaracion_fn  # noqa: E402
from a11yaudit import audit_url as audit_url_fn, audit_html as audit_html_fn  # noqa: E402
from a11ydom import audit_dom_url  # noqa: E402
from a11ydiff import snapshot as snapshot_fn, diff as diff_fn  # noqa: E402
from a11ycrit import criterio as criterio_fn  # noqa: E402
from a11ybadge import badge as badge_fn  # noqa: E402
from a11yaudit import audit_site as audit_site_fn  # noqa: E402

try:
    from arialive_js import ARIALIVE_JS  # installed as a module (pip)
except ImportError:
    ARIALIVE_JS = None  # repo checkout: read the file

VERSION = '3.3.0'

INSTRUCTIONS = (
    'Accessibility toolkit (WCAG 2.2), multilanguage es/en. '
    'Loop: AUDIT (a11y_audit_url for a fast static pass with a 0-100 score; '
    'a11y_audit_dom for a rendered audit with real computed contrast, 2.5.8 target '
    'size and focus indicator — needs local Playwright) → FIX (a11y_contrast_pair, '
    'a11y_contrast_image, a11y_suggest_color) → DOCUMENT (a11y_generate_declaration: '
    'RD 1112/2018 or European Accessibility Act wording) → WATCH (a11y_snapshot — '
    'includes the computed accessibility tree — + a11y_diff across deploys). '
    'a11y_criterion explains what any criterion means. Every tool returns es/en '
    'findings with concrete remediation. '
    'Automation covers about one third of WCAG: pair audits with the manual checklist '
    'in the audit-page prompt (keyboard, screen reader, zoom).'
)

TOOLS = [
    {
        'name': 'a11y_audit_url',
        'description': ('Express WCAG 2.2 audit of a URL or an HTML string: 20+ automated '
                        'signals with a weighted 0-100 score — images without alt (1.1.1), '
                        'controls without accessible names (4.1.2), form fields without labels '
                        '(3.3.2), missing autocomplete on user-data fields (1.3.5), click '
                        'handlers on non-interactive elements (2.1.1), unknown ARIA roles and '
                        'broken aria-labelledby (4.1.2), duplicated unnamed landmarks, timed '
                        'meta refresh (2.2.1), missing skip mechanism (2.4.1), lang/title '
                        '(3.1.1, 2.4.2), heading structure (1.3.1), blocked zoom (1.4.4), '
                        'captions (1.2.2), autoplay audio (1.4.2), generic/duplicated link text '
                        '(2.4.4), target=_blank without warning (3.2.5), positive tabindex '
                        '(2.4.3), aria-hidden on focusable elements, tables without th, '
                        'duplicate ids, duplicate accesskeys. Each finding includes concrete '
                        'remediation. Filter, not verdict: automation covers ~1/3 of WCAG; '
                        'query a11y_criterion for what a criterion means.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string', 'description': 'URL to fetch and audit'},
            'html': {'type': 'string', 'description': 'raw HTML to audit directly (overrides url)'},
            'pages': {'type': 'integer', 'description': 'light same-domain crawl: audit up to N pages, aggregated by score and recurring signals (default 1, max 20)'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'output language (es default)'},
            'timeout': {'type': 'number', 'description': 'fetch timeout seconds (30 default)'},
        }},
    },
    {
        'name': 'a11y_audit_dom',
        'description': ('Deep RENDERED WCAG audit via local Playwright/Chromium: real computed '
                        'text contrast against effective backgrounds with alpha compositing '
                        '(1.4.3), minimum target size 24×24 (2.5.8, new in WCAG 2.2), visible '
                        'focus indicator heuristic (2.4.7), plus rendered versions of the '
                        'static checks (alt, accessible names, labels, headings, lang/title, '
                        'tabindex, aria-hidden, captions, tables). Findings include remediation. '
                        'Requires playwright: pip install playwright && playwright install '
                        'chromium.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
            'timeout': {'type': 'number', 'description': 'page load timeout seconds (45 default)'},
        }, 'required': ['url']},
    },
    {
        'name': 'a11y_contrast_pair',
        'description': ('Exact WCAG contrast ratio for a color pair: per-criterion verdicts '
                        '1.4.3 (AA), 1.4.6 (AAA), 1.4.11 (non-text). Accepts #hex, rgb(), '
                        'hsl(), CSS color names; rgba/hsl with alpha is composited over the '
                        'background. If AA fails, suggests the nearest passing color.'),
        'inputSchema': {'type': 'object', 'properties': {
            'fg': {'type': 'string'}, 'bg': {'type': 'string'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'output language (es default)'},
        }, 'required': ['fg', 'bg']},
    },
    {
        'name': 'a11y_contrast_image',
        'description': ('TEXT OVER IMAGE contrast: pixel-level sampling of the real background '
                        'behind the text box → worst/median/p95 ratio, % of area passing AA, '
                        'and automatic hostile-zone detection on a 3×3 grid (zona_peor). What '
                        'pair-only checkers cannot do. region="x,y,w,h" recommended.'),
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string'}, 'text_color': {'type': 'string'},
            'region': {'type': 'string'},
            'sample': {'type': 'integer'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['path', 'text_color']},
    },
    {
        'name': 'a11y_suggest_color',
        'description': ('Nearest opaque color (RGB distance) to fg that reaches the target '
                        'ratio against bg (4.5 default). Returns the color, its ratio and '
                        'whether it lightens or darkens.'),
        'inputSchema': {'type': 'object', 'properties': {
            'fg': {'type': 'string'}, 'bg': {'type': 'string'},
            'target': {'type': 'number'},
        }, 'required': ['fg', 'bg']},
    },
    {
        'name': 'a11y_generate_declaration',
        'description': ('Generates an Accessibility Statement in HTML: art. 10 RD 1112/2018 '
                        '(Spanish public sector, marco="rd1112") or European Accessibility Act '
                        'wording (Directive (EU) 2019/882 / Ley 11/2023, marco="eaa"; EN output '
                        'uses Directive (EU) 2016/2102 / EAA wording). The generated document '
                        'is itself accessible. Saves to output_path when given.'),
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
            'output_path': {'type': 'string', 'description': 'save the HTML here (optional)'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['entidad', 'url', 'estado']},
    },
    {
        'name': 'a11y_snapshot',
        'description': ('Accessibility snapshot of a URL: interactive elements (tag, role, '
                        'accessible name, href) in DOM order, the REAL tab focus order, and '
                        'when Playwright ≥1.49 is available the computed ACCESSIBILITY TREE '
                        '(aria snapshot — what a screen reader announces). Save it before a '
                        'deploy and compare after with a11y_diff. Requires local Playwright.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string'},
        }, 'required': ['url']},
    },
    {
        'name': 'a11y_diff',
        'description': ('Regression diff between two accessibility snapshots (before/after a '
                        'deploy): added/removed/renamed interactives and focus-order changes. '
                        'ok=false means a regression to review. Accepts inline JSON (starting '
                        'with "{") or file paths.'),
        'inputSchema': {'type': 'object', 'properties': {
            'a': {'type': 'string', 'description': 'BEFORE snapshot (inline JSON or path)'},
            'b': {'type': 'string', 'description': 'AFTER snapshot (inline JSON or path)'},
        }, 'required': ['a', 'b']},
    },
    {
        'name': 'a11y_diff_urls',
        'description': ('Snapshot two URLs and diff them in a single call (e.g. staging vs '
                        'production). Requires local Playwright.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url_a': {'type': 'string'}, 'url_b': {'type': 'string'},
        }, 'required': ['url_a', 'url_b']},
    },
    {
        'name': 'a11y_aria_live_snippet',
        'description': ('Returns injectable JavaScript for an aria-live announcement monitor '
                        '(bookmarklet or page.evaluate): logs every dynamic-region '
                        'announcement with time, politeness, role and text — what a screen '
                        'reader would say, visible on screen.'),
        'inputSchema': {'type': 'object', 'properties': {
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'monitor panel language (es default)'},
        }},
    },
    {
        'name': 'a11y_badge',
        'description': ('Returns an HONEST accessibility badge as accessible SVG: score, '
                        'date and scope (automated screening ≈ 1/3 of WCAG), color-coded '
                        'by score. Deliberately does NOT say "conformant" — the honest '
                        'seal. Embed it in audited sites or statements.'),
        'inputSchema': {'type': 'object', 'properties': {
            'score': {'type': 'number', 'description': '0-100 (from an audit result)'},
            'fecha': {'type': 'string', 'description': 'ISO date (today by default)'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['score']},
    },
    {
        'name': 'a11y_criterion',
        'description': ('Explains a WCAG 2.2 success criterion in plain language (es/en): '
                        'what it requires, typical failures, and how to verify it with this '
                        'toolkit (which tool automates which part). Codes like "1.4.3", '
                        '"2.5.8", "4.1.2". Use it whenever you need to explain WHY a finding '
                        'matters or what the criterion actually says.'),
        'inputSchema': {'type': 'object', 'properties': {
            'code': {'type': 'string', 'description': 'criterion number, e.g. 1.4.3'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['code']},
    },
]

_PROMPTS = [
    {
        'name': 'audit-page',
        'description': 'Full accessibility audit workflow for a URL: automated tools + what to verify manually (keyboard, screen reader, zoom).',
        'arguments': [
            {'name': 'url', 'description': 'page to audit', 'required': True},
            {'name': 'language', 'description': 'es or en (default: match the user)', 'required': False},
        ],
    },
    {
        'name': 'fix-contrast',
        'description': 'Guided contrast fix: verify the pair (or the text-over-image region), get the nearest passing color, apply it to the code.',
        'arguments': [
            {'name': 'fg', 'description': 'foreground/text color', 'required': True},
            {'name': 'bg', 'description': 'background color', 'required': True},
            {'name': 'context', 'description': 'file(s) or component where the colors live', 'required': False},
        ],
    },
    {
        'name': 'pre-deploy-check',
        'description': 'Pre-deploy regression check: express audit of the URL plus snapshot diff against a baseline snapshot.',
        'arguments': [
            {'name': 'url', 'description': 'staging URL to check', 'required': True},
            {'name': 'baseline', 'description': 'path or URL of the before snapshot', 'required': False},
        ],
    },
    {
        'name': 'declaration-eaa',
        'description': 'Generate a European Accessibility Act / RD 1112/2018 accessibility statement, collecting any missing legal fields from the user.',
        'arguments': [
            {'name': 'entidad', 'description': 'organization name', 'required': True},
            {'name': 'url', 'description': 'website URL', 'required': True},
            {'name': 'estado', 'description': 'plena | parcial | no_conforme', 'required': False},
        ],
    },
    {
        'name': 'conformance-wcagem',
        'description': 'Guided WCAG-EM conformance ladder for a site: express screening → agent-verified guided evaluation on a representative sample → conformance report inputs.',
        'arguments': [
            {'name': 'url', 'description': 'site root to evaluate', 'required': True},
            {'name': 'tier', 'description': 'express | guided | conformance (default: express)', 'required': False},
            {'name': 'language', 'description': 'es or en', 'required': False},
        ],
    },
]


def _prompt(nombre, args):
    L = (args.get('language') or 'en').lower()
    if L not in ('es', 'en'):
        L = 'en'
    t = {
        'audit-page': {
            'en': f"Run a full accessibility audit of {args.get('url','the URL')} and report in the user's language:\n"
                  "1. Call a11y_audit_url (static express pass). If Playwright is available, also call a11y_audit_dom for real computed contrast, 2.5.8 target size and focus indicator.\n"
                  "2. Group findings by severity; for each, cite the WCAG criterion, the evidence, and the remediation the tool returned.\n"
                  "3. State clearly what automation CANNOT check, and verify what you can: keyboard operability (Tab/Shift+Tab/Enter/Esc, focus visible), heading landmarks, form flow, 200% zoom reflow.\n"
                  "4. End with a prioritized fix list (high/medium/low) and the honest scope note: automation ≈ 1/3 of WCAG; recommend screen-reader testing for the rest.",
            'es': f"Ejecuta una auditoría de accesibilidad completa de {args.get('url','la URL')} e informa en el idioma de la persona usuaria:\n"
                  "1. Llama a a11y_audit_url (pase estático exprés). Si hay Playwright, llama también a a11y_audit_dom para contraste real computado, tamaño de objetivo 2.5.8 e indicador de foco.\n"
                  "2. Agrupa por severidad; para cada hallazgo cita el criterio WCAG, la evidencia y la remediación devuelta por la herramienta.\n"
                  "3. Deja claro lo que la automatización NO puede revisar y verifica lo que puedas: operabilidad por teclado (Tab/Shift+Tab/Enter/Esc, foco visible), landmarks, flujo de formularios, reflujo al 200%.\n"
                  "4. Cierra con una lista priorizada de arreglo (alta/media/baja) y la nota honesta: automatización ≈ 1/3 de WCAG; recomienda prueba con lector de pantalla para el resto.",
        },
        'fix-contrast': {
            'en': f"Fix the contrast of {args.get('fg','fg')} on {args.get('bg','bg')}"
                  + (f" in {args.get('context','')}" if args.get('context') else '') + ":\n"
                  "1. Call a11y_contrast_pair to get the exact ratio and per-criterion verdicts.\n"
                  "2. If AA fails, take sugerencia_aa (or call a11y_suggest_color with the needed level: 4.5 normal text, 3.0 large text, 3.0 UI components).\n"
                  "3. Locate the color in the code" + (f" ({args.get('context','')})" if args.get('context') else '')
                  + ", replace it with the suggested value, and re-verify with a11y_contrast_pair.\n"
                  "4. If the text sits over an image or gradient, use a11y_contrast_image with a screenshot region instead — pixel sampling is the only honest check there.",
            'es': f"Corrige el contraste de {args.get('fg','fg')} sobre {args.get('bg','bg')}"
                  + (f" en {args.get('context','')}" if args.get('context') else '') + ":\n"
                  "1. Llama a a11y_contrast_pair para el ratio exacto y los veredictos por criterio.\n"
                  "2. Si no pasa AA, toma sugerencia_aa (o llama a a11y_suggest_color con el nivel necesario: 4.5 texto normal, 3.0 texto grande, 3.0 componentes UI).\n"
                  "3. Localiza el color en el código" + (f" ({args.get('context','')})" if args.get('context') else '')
                  + ", sustitúyelo por el valor sugerido y reverifica con a11y_contrast_pair.\n"
                  "4. Si el texto va sobre imagen o degradado, usa a11y_contrast_image con la región de una captura — el muestreo píxel a píxel es la única verificación honesta ahí.",
        },
        'pre-deploy-check': {
            'en': f"Pre-deploy accessibility regression check for {args.get('url','the URL')}:\n"
                  "1. Call a11y_audit_url on the staging URL (and a11y_audit_dom if Playwright is available).\n"
                  + (f"2. Compare against baseline {args.get('baseline','')} with a11y_diff (if the baseline is a URL, snapshot it first with a11y_snapshot).\n"
                     if args.get('baseline') else
                     "2. If a baseline snapshot exists, diff it with a11y_diff; if not, create one with a11y_snapshot for the next deploy.\n")
                  + "3. Report: new findings (blockers), resolved findings (good news), interactive elements added/removed/renamed, focus-order changes.\n"
                  "4. Verdict: GO (no new high findings and no focus regressions) / NO-GO (otherwise) with the evidence.",
            'es': f"Comprobación de regresión de accesibilidad antes de desplegar {args.get('url','la URL')}:\n"
                  "1. Llama a a11y_audit_url sobre la URL de staging (y a11y_audit_dom si hay Playwright).\n"
                  + (f"2. Compara con la referencia {args.get('baseline','')} mediante a11y_diff (si la referencia es una URL, captúrala antes con a11y_snapshot).\n"
                     if args.get('baseline') else
                     "2. Si existe un snapshot de referencia, compara con a11y_diff; si no, créalo con a11y_snapshot para el próximo despliegue.\n")
                  + "3. Informa: hallazgos nuevos (bloqueantes), hallazgos resueltos (buenas noticias), interactivos añadidos/eliminados/renombrados, cambios de orden de foco.\n"
                  "4. Veredicto: GO (sin hallazgos altos nuevos ni regresiones de foco) / NO-GO (en caso contrario) con la evidencia.",
        },
        'conformance-wcagem': {
            'en': f"Run the WCAG-EM conformance ladder for {args.get('url','the site')} (tier: {args.get('tier','express')}):\n"
                  "1. EXPRESS (always): a11y_audit_url on the root and the 4-5 key pages (use pages parameter / crawl). Report scores and findings by severity.\n"
                  "2. GUIDED: pick a WCAG-EM sample — structured pages (home, contact, login, a content page, a form flow) plus a random pick from the crawl. On each sample page, run a11y_audit_dom if Playwright is available, then verify the manual checklist yourself (keyboard walk, focus visibility, zoom 200%, error announcement on one form). Mark each item verified-by-agent vs automated-only.\n"
                  "3. CONFORMANCE: only with a human in the loop — compile the evidence (sample, pages, results, dates) into WCAG-EM report structure, state the scope honestly (sample-based evaluation, not a certification), and feed contenido_no_accesible into a11y_generate_declaration.\n"
                  "Escalate one tier at a time; never present tier 1 or 2 as conformance.",
            'es': f"Ejecuta la escalera de conformidad WCAG-EM para {args.get('url','el sitio')} (nivel: {args.get('tier','express')})\u003a\n"
                  "1. EXPRESS (siempre): a11y_audit_url en la raíz y las 4-5 páginas clave (parámetro pages). Informa puntuaciones y hallazgos por severidad.\n"
                  "2. GUIDED: elige una muestra WCAG-EM — páginas estructurales (inicio, contacto, login, una de contenido, un flujo de formulario) más una aleatoria del rastreo. En cada una, a11y_audit_dom si hay Playwright, y verifica tú el checklist manual (recorrido de teclado, foco visible, zoom 200%, anuncio de errores en un formulario). Marca cada punto como verificado-por-agente o solo-automático.\n"
                  "3. CONFORMANCE: solo con humana en el bucle — recopila la evidencia (muestra, páginas, resultados, fechas) en la estructura del informe WCAG-EM, declara el alcance con honestidad (evaluación por muestreo, no certificación) y alimenta contenido_no_accesible en a11y_generate_declaration.\n"
                  "Escala un nivel cada vez; nunca presentes el nivel 1 o 2 como conformidad.",
        },
        'declaration-eaa': {
            'en': f"Generate an accessibility statement for {args.get('entidad','the entity')} ({args.get('url','URL')}):\n"
                  "1. Establish the compliance state with a11y_audit_url (parcial is the honest default when findings exist).\n"
                  f"2. Current estado argument: {args.get('estado','(missing)')}. If missing, infer from the audit and confirm with the user.\n"
                  "3. Collect what is missing: feedback contact, claim procedure (reclamación), evaluation method and dates. Ask the user only for what you cannot infer.\n"
                  "4. List contenido_no_accesible from the audit findings with reasons and alternatives.\n"
                  "5. Call a11y_generate_declaration (marco='eaa' for private sector / EAA; 'rd1112' for Spanish public sector), lang matching the site, and save with output_path.\n"
                  "6. Remind: the statement must be linked from every page (typically the footer) and reviewed after significant changes.",
            'es': f"Genera la declaración de accesibilidad de {args.get('entidad','la entidad')} ({args.get('url','URL')}):\n"
                  "1. Establece el estado de conformidad con a11y_audit_url (parcial es lo honesto por defecto si hay hallazgos).\n"
                  f"2. Argumento estado actual: {args.get('estado','(falta)')}. Si falta, infiérelo de la auditoría y confírmalo con la persona usuaria.\n"
                  "3. Recoge lo que falte: contacto de feedback, procedimiento de reclamación, método y fechas de evaluación. Pregunta solo lo que no puedas inferir.\n"
                  "4. Enumera contenido_no_accesible a partir de los hallazgos, con razón y alternativa.\n"
                  "5. Llama a a11y_generate_declaration (marco='eaa' para sector privado / EAA; 'rd1112' para sector público español), lang del sitio, y guarda con output_path.\n"
                  "6. Recuerda: la declaración debe enlazarse desde todas las páginas (típico en el pie) y revisarse tras cambios significativos.",
        },
    }
    txt = t[nombre][L]
    return {'description': next(p['description'] for p in _PROMPTS if p['name'] == nombre),
            'messages': [{'role': 'user', 'content': {'type': 'text', 'text': txt}}]}


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
            return _texto({'error': 'invalid color'})
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
            if args.get('html'):
                return _texto(audit_html_fn(args['html'], args.get('url') or '(html)',
                                            lang=args.get('lang', 'es')))
            if args.get('pages', 1) > 1:
                return _texto(audit_site_fn(args['url'], max_pages=args['pages'],
                                            timeout=args.get('timeout', 30),
                                            lang=args.get('lang', 'es')))
            return _texto(audit_url_fn(args['url'], timeout=args.get('timeout', 30),
                                       lang=args.get('lang', 'es')))
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_audit_dom':
        try:
            return _texto(audit_dom_url(args['url'], timeout=args.get('timeout', 45),
                                        lang=args.get('lang', 'es')))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium (or use a11y_audit_url for the zero-dependency static audit)'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_snapshot':
        try:
            return _texto(snapshot_fn(args['url']))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_diff':
        def _carga(v):
            v = v.strip()
            if v.startswith('{'):
                return json.loads(v)
            with open(v, encoding='utf-8') as f:
                return json.load(f)
        try:
            return _texto(diff_fn(_carga(args['a']), _carga(args['b'])))
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_diff_urls':
        try:
            return _texto(diff_fn(snapshot_fn(args['url_a']), snapshot_fn(args['url_b'])))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_criterion':
        return _texto(criterio_fn(args['code'], lang=args.get('lang', 'es')))
    if nombre == 'a11y_badge':
        svg = badge_fn(args['score'], fecha=args.get('fecha'),
                       lang=args.get('lang', 'en'))
        return {'content': [{'type': 'text', 'text': svg}]}
    if nombre == 'a11y_aria_live_snippet':
        if ARIALIVE_JS is not None:
            js = ARIALIVE_JS
        else:
            with open(os.path.join(AQUI, 'arialive.js'), encoding='utf-8') as f:
                js = f.read()
        if args.get('lang') == 'en':
            js = "window.ALM_LANG='en';\n" + js
        return {'content': [{'type': 'text', 'text': js}]}
    raise ValueError(f'unknown tool: {nombre}')


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
                    'capabilities': {'tools': {}, 'prompts': {}},
                    'serverInfo': {'name': 'a11y-toolkit', 'version': VERSION},
                    'instructions': INSTRUCTIONS,
                }}
            elif metodo == 'ping':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {}}
            elif metodo == 'tools/list':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {'tools': TOOLS}}
            elif metodo == 'tools/call':
                p = msg.get('params', {})
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': llamar(p.get('name'), p.get('arguments') or {})}
            elif metodo == 'prompts/list':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {'prompts': _PROMPTS}}
            elif metodo == 'prompts/call':
                p = msg.get('params', {})
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': _prompt(p.get('name'), p.get('arguments') or {})}
            else:
                resp = {'jsonrpc': '2.0', 'id': mid,
                        'error': {'code': -32601, 'message': f'unknown method: {metodo}'}}
        except Exception as e:  # noqa: BLE001
            resp = {'jsonrpc': '2.0', 'id': mid, 'result': {
                'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
