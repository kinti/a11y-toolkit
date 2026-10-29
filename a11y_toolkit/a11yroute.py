#!/usr/bin/env python3
"""a11y_route — the router: tell the agent WHICH tools solve a task.

Two brains, one tool:
  - GOAL routing: the agent states a goal in plain language — "gate my PR",
    "arregla el contraste del hero" — and gets the ordered tool sequence
    with the why of each step. Deterministic keyword index, not an LLM.
  - SEQUENTIAL DIAGNOSIS (pass url= or html=): the router takes the page's
    cheap vitals (the static pass) and lets the EVIDENCE order the next
    exams — forms present → form error testing; menus → keyboard; video →
    caption content. Severity only breaks ties: a page without forms does
    not need the form exam no matter how severe 3.3.1 is on paper.
    Diagnosis ORDERS the exams, never trims them — the full catalog stays
    one route(goal) away.

The tables are the product: keep them in sync with the toolkit (the
test suite pins that every referenced tool exists).

CLI:
  a11yroute.py --goal "gate my PR" [--lang en]
  a11yroute.py --file page.html          # diagnosis mode
  a11yroute.py --url https://…           # diagnosis mode
"""

import argparse
import json
import re
import sys

from .a11yaudit import audit_html, _fetch

# Índice de rutas: patrones es/en → pasos ordenados. Una ruta gana por
# puntuación de coincidencias (subcadena sobre el goal en minúsculas);
# el empate lo decide el orden de la tabla. 'start' es el fallback honesto.
ROUTES = [
    {'id': 'ci',
     'patterns': ['pr', 'pull request', 'ci', 'pipeline', 'github actions',
                  'gate', 'commit', 'merge', 'cambios', 'before merging'],
     'tools': [
         ('a11y_audit_url', 'pase exprés de lo tocado: el gate mínimo',
          'express pass over what changed: the minimum gate'),
         ('cli:budget', 'solo hallazgos NUEVOS bloquean (regresión, no deuda vieja)',
          'only NEW findings block (regression, not old debt)'),
     ],
     'cli': 'a11ytoolkit audit --changed  # exit 2 on high/medium in changed files',
     'prompts': []},
    {'id': 'deploy',
     'patterns': ['deploy', 'despliegue', 'regression', 'regresión',
                  'before shipping', 'pre-deploy', 'antes de publicar'],
     'tools': [
         ('a11y_snapshot', 'foto de interactivos + árbol antes de desplegar',
          'interactive elements + tree snapshot before deploying'),
         ('a11y_diff', 'tras el deploy: hallazgos nuevos bloquean, resueltos celebran',
          'after deploy: new findings block, resolved ones are good news'),
         ('cli:budget', 'el veredicto GO/NO-GO con evidencia',
          'the GO/NO-GO verdict with evidence'),
     ],
     'cli': 'a11ytoolkit snapshot https://… --out before.json',
     'prompts': ['pre-deploy-check']},
    {'id': 'contrast',
     'patterns': ['contrast', 'contraste', 'color', 'colour', 'legibility',
                  'legible', '4.5', 'ratio', 'texto sobre imagen'],
     'tools': [
         ('a11y_contrast_pair', 'el par exacto: ratio y veredicto por criterio',
          'the exact pair: ratio and per-criterion verdicts'),
         ('a11y_contrast_dom', 'si el texto vive en una página: muestreo de la región real',
          'if the text lives on a page: real-region sampling'),
         ('a11y_contrast_image', 'sobre imagen o degradado: píxeles, no suposiciones',
          'over image or gradient: pixels, not guesses'),
         ('a11y_suggest_color', 'el color más cercano que pasa',
          'the nearest passing color'),
     ],
     'cli': 'a11ytoolkit pair "#1f2328" "#fbfaf7"',
     'prompts': ['fix-contrast']},
    {'id': 'rendered',
     'patterns': ['rendered', 'js', 'react', 'vue', 'angular', 'svelte',
                  'spa', 'computado', 'real contrast'],
     'tools': [
         ('a11y_audit_dom', 'auditoría renderizada: contraste computado, 2.5.8, foco',
          'rendered audit: computed contrast, 2.5.8, focus indicator'),
         ('a11y_criterion', 'qué significa cada criterio que salga',
          'what each flagged criterion means'),
     ],
     'cli': None, 'prompts': []},
    {'id': 'forms',
     'patterns': ['form', 'formulario', 'error', 'validación', 'validacion',
                  '3.3', 'checkout', 'signup field'],
     'tools': [
         ('a11y_forms', 'rellena inválido, envía y juzga el aviso de errores (3.3.1/3.3.3)',
          'fills invalid data, submits, judges error announcement (3.3.1/3.3.3)'),
         ('a11y_audit_url', 'labels, autocomplete y nombres en el pase estático',
          'labels, autocomplete and names in the static pass'),
     ],
     'cli': 'a11ytoolkit forms https://…/contact',
     'prompts': []},
    {'id': 'keyboard',
     'patterns': ['keyboard', 'teclado', 'trap', 'trampa', 'focus', 'foco',
                  'tab', 'esc', 'modal'],
     'tools': [
         ('a11y_keyboard', 'detecta trampas de teclado con Tab real',
          'detects keyboard traps with real Tab walking'),
         ('a11y_audit_dom', 'foco visible y no oscurecido, renderizado',
          'visible, unobscured focus, rendered'),
     ],
     'cli': 'a11ytoolkit kbd https://…',
     'prompts': []},
    {'id': 'statement',
     'patterns': ['statement', 'declaración', 'declaracion', 'eaa', 'ley',
                  'legal', 'rd 1112', 'acta', '11/2023', 'compliance doc'],
     'tools': [
         ('a11y_audit_url', 'los hallazgos alimentan la lista de contenido no accesible',
          'findings feed the non-accessible content list'),
         ('a11y_generate_declaration', 'la declaración EAA/RD 1112 como borrador honesto',
          'the EAA/RD 1112 statement as an honest draft'),
     ],
     'cli': 'a11ytoolkit declaration --entity "Acme" --url https://… --status partial --framework eaa',
     'prompts': ['declaration-eaa']},
    {'id': 'evidence',
     'patterns': ['evidence', 'evidencia', 'pack', 'prove', 'demostrar',
                  'conformity', 'buyer', 'auditor firmado', 'verify report'],
     'tools': [
         ('a11y_audit_url', 'la materia prima: hallazgos con señal y remedio',
          'the raw material: findings with signal and remediation'),
         ('a11y_evidence', 'el pack verificable: matriz 55, esfuerzo humano, sha256',
          'the verifiable pack: 55-matrix, human effort, sha256'),
         ('a11y_disprove', 're-verifica antes de actuar: lo que no reproduce, fuera',
          're-verify before acting: what does not reproduce is out'),
     ],
     'cli': 'a11ytoolkit evidence audit.json -o pack.json',
     'prompts': []},
    {'id': 'vpat',
     'patterns': ['vpat', 'acr', 'procurement', 'licitación', 'licitacion',
                  'tender', 'rfp', 'us market'],
     'tools': [
         ('a11y_evidence', 'primero el pack: el VPAT se deriva de evidencia',
          'the pack first: the VPAT derives from evidence'),
         ('a11y_generate_vpat', 'borrador VPAT 2.5: la máquina rellena, la persona firma',
          'VPAT 2.5 draft: the machine fills, the human signs'),
         ('a11y_generate_openacr', 'OpenACR YAML (GSA): el ACR máquina que parsea el procurement',
          'OpenACR YAML (GSA): the machine-readable ACR procurement parses'),
     ],
     'cli': 'a11ytoolkit vpat pack.json --product "Acme" -o vpat.html',
     'prompts': []},
    {'id': 'media',
     'patterns': ['video', 'caption', 'subtítulo', 'subtitulo', 'subtitulo',
                  'vtt', 'audio description', 'audiodescripción', 'podcast'],
     'tools': [
         ('a11y_vtt_check', 'el CONTENIDO de los subtítulos: cps, solapes, cobertura',
          'caption CONTENT: cps, overlaps, coverage'),
         ('a11y_audit_url', 'presencia de track y autoplay en el pase estático',
          'track presence and autoplay in the static pass'),
     ],
     'cli': None, 'prompts': []},
    {'id': 'pdf',
     'patterns': ['pdf', 'documento', 'document', 'docx', 'word', 'informe pdf'],
     'tools': [
         ('a11y_audit_pdf', 'cribado estructural + formularios: lo que nadie automatiza',
          'structural screening + forms: what nobody automates'),
         ('a11y_docx_screen', 'si es Word: alt, encabezados, idioma, tablas',
          'if it is Word: alt, headings, language, tables'),
     ],
     'cli': None, 'prompts': []},
    {'id': 'blindfold',
     'patterns': ['task', 'tarea', 'journey', 'blindfold', 'usuario ciego',
                  'screen reader flow', 'comprar', 'signup flow', 'can a user'],
     'tools': [
         ('blindfold-task', 'el prompt: el agente ES el usuario de lector, paso a paso',
          'the prompt: the agent IS the screen-reader user, step by step'),
         ('a11y_journey_verdict', 'el veredicto determinista del recorrido',
          'the deterministic journey verdict'),
     ],
     'cli': None, 'prompts': ['blindfold-task']},
    {'id': 'wcag3',
     'patterns': ['wcag 3', 'wcag3', 'silver', 'futuro', 'future', 'draft wcag'],
     'tools': [
         ('a11y_wcag3_preview', 'tus hallazgos 2.2 bajo los outcomes del borrador (sin score)',
          'your 2.2 findings under the draft outcomes (no score)'),
     ],
     'cli': 'a11ytoolkit wcag3 --from-audit audit.json',
     'prompts': []},
    {'id': 'scroll',
     'patterns': ['infinite scroll', 'scroll infinito', 'feed', 'lazy load',
                  'paginación', 'pagination'],
     'tools': [('a11y_scroll', 'el foco sobrevive a cada tanda, lo nuevo se anuncia',
                'focus survives each batch, the new content is announced')],
     'cli': 'a11ytoolkit scroll https://…/feed', 'prompts': []},
    {'id': 'motion',
     'patterns': ['animation', 'animación', 'animacion', 'motion', 'parallax',
                  'reduced motion', 'vestibular'],
     'tools': [('a11y_reduced_motion', '¿respeta prefers-reduced-motion? Nadie lo automatizaba',
                'does it honor prefers-reduced-motion? Nobody automated it')],
     'cli': None, 'prompts': []},
    {'id': 'names',
     'patterns': ['accessible name', 'nombre accesible', 'aria', 'role',
                  'widget', '4.1.2', 'control sin nombre'],
     'tools': [
         ('a11y_audit_url', 'detección estática: botones sin nombre, roles rotos',
          'static detection: unnamed buttons, broken roles'),
         ('a11y_snapshot', 'los nombres REALES que anuncia el navegador',
          'the REAL names the browser announces'),
         ('a11y_criterion', 'qué exige exactamente 4.1.2 (con reglas ACT)',
          'what 4.1.2 exactly requires (with ACT rules)'),
     ],
     'cli': None, 'prompts': []},
    {'id': 'criterion',
     'patterns': ['what is', 'qué es', 'que es', 'significa', 'criterio',
                  'criterion', 'explain', 'regla', 'rule', '1.4.3', '2.4.7'],
     'tools': [('a11y_criterion', 'el criterio explicado, con fuente Understanding y ACT',
                'the criterion explained, with Understanding source and ACT')],
     'cli': None, 'prompts': []},
    # fallback honesto: por dónde empieza todo el mundo
    {'id': 'start',
     'patterns': [],
     'tools': [
         ('a11y_audit_url', 'el pase exprés: score, hallazgos con remedio',
          'the express pass: score, findings with remediation'),
         ('a11y_criterion', 'para entender cualquier criterio que salga',
          'to understand any criterion that comes up'),
         ('a11y_evidence', 'cuando quieras pasarlo a evidencia firmable',
          'when you want it as signable evidence'),
     ],
     'cli': 'a11ytoolkit audit --url https://…',
     'prompts': ['audit-page']},
]

_NOTE = {
    'es': ('Índice determinista de goals→tools: no adivina. Si nada encajó, '
           'la ruta "start" es por donde empieza todo el mundo.'),
    'en': ('Deterministic goal→tools index: it does not guess. When nothing '
           'matched, the "start" route is where everyone begins.'),
}

# ── diagnóstico secuencial: la EVIDENCIA manda, la severidad solo desempata ──
# Traducción cruzada del diagnóstico diferencial (medicina): primero la
# constante vital barata —el pase estático— y sus síntomas deciden qué
# examen reduce más la incertidumbre. No es una prioridad fija de criterios:
# una página sin formularios no necesita el examen de formularios por muy
# grave que sea 3.3.1 sobre el papel. detect() devuelve None (síntoma
# ausente) o la evidencia en una línea.
_DIAG = [
    {'id': 'forms', 'severity': 'high', 'tool': 'a11y_forms',
     # ojo: sin \b dentro de las llaves del f-string (barra invertida DENTRO
     # de llaves es SyntaxError antes de 3.12; el guardián de test_solido lo
     # vigila) — la detección con \b vive en el re.search de fuera
     'detect': lambda h: (f'{len(re.findall(r"<(?:input|select|textarea)", h))} form fields'
                          if re.search(r'<(?:input|select|textarea)\b', h) else None),
     'why': ('formularios presentes: rellenar inválido, enviar y juzgar el aviso de errores',
             'forms present: fill invalid data, submit, judge the error announcement')},
    {'id': 'menus', 'severity': 'high', 'tool': 'a11y_keyboard',
     'detect': lambda h: ('menus or disclosure widgets'
                          if re.search(r'<(?:nav|details)\b|aria-expanded', h) else None),
     'why': ('menús o desplegables: la zona clásica de trampas de teclado',
             'menus or disclosure widgets: the classic keyboard-trap zone')},
    {'id': 'video', 'severity': 'medium', 'tool': 'a11y_vtt_check',
     'detect': lambda h: (f'{h.count("<video")} <video>' if '<video' in h else None),
     'why': ('vídeo presente: que existan subtítulos no basta — juzgar su CONTENIDO',
             'video present: captions existing is not enough — judge their CONTENT')},
    {'id': 'animation', 'severity': 'medium', 'tool': 'a11y_reduced_motion',
     'detect': lambda h: ('animated content'
                          if re.search(r'animation|transition|<marquee', h) else None),
     'why': ('contenido animado: ¿respeta prefers-reduced-motion?',
             'animated content: does it honor prefers-reduced-motion?')},
    {'id': 'svg', 'severity': 'low', 'tool': 'a11y_forced_colors',
     'detect': lambda h: (f'{h.count("<svg")} inline <svg>' if h.count('<svg') >= 2 else None),
     'why': ('iconografía SVG en volumen: los fills fijos caen en forced-colors',
             'SVG iconography at volume: hardcoded fills fall in forced-colors')},
]

_RANK = {'high': 0, 'medium': 1, 'low': 2}

_GUARANTEE = {
    'es': ('El diagnóstico ORDENA los exámenes, nunca los recorta: el catálogo '
           'completo sigue a un route(goal) de distancia.'),
    'en': ('Diagnosis ORDERS the exams, never trims them: the full catalog '
           'stays one route(goal) away.'),
}


def diagnose(html_text, url='(html)', lang='en', goal=None):
    """Pase barato → síntomas → exámenes ordenados por rendimiento esperado."""
    t = 'es' if lang == 'es' else 'en'
    idx = 0 if t == 'es' else 1
    rep = audit_html(html_text, url=url, lang=t)
    if 'error' in rep:
        return {'mode': 'diagnose', 'lang': t, 'error': rep['error']}
    vitals = {'tool': 'a11y_audit_url', 'score': rep.get('score'),
              'summary': rep.get('summary'),
              'signals': [f"{h['severity']}: {h['signal']}"
                          for h in rep.get('findings', [])]}
    symptoms, hit = [], []
    for d in _DIAG:
        ev = d['detect'](html_text)
        if ev:
            symptoms.append({'symptom': d['id'], 'evidence': ev})
            hit.append(d)
    # sort estable: severidad como desempate, orden de tabla dentro de cada nivel
    hit.sort(key=lambda d: _RANK[d['severity']])
    steps = [{'step': 1, 'tool': 'a11y_audit_url',
              'why': ('constante vital ya medida: este pase barato decidió lo demás',
                      'vitals already taken: this cheap pass decided the rest')[idx]}]
    evidences = {d['id']: d['detect'](html_text) for d in _DIAG}
    for i, d in enumerate(hit, 2):
        steps.append({'step': i, 'tool': d['tool'], 'why': d['why'][idx],
                      'symptom': d['id'], 'evidence': evidences[d['id']]})
    steps.append({'step': len(steps) + 1, 'tool': 'a11y_audit_dom',
                  'why': ('profundizar lo que el estático no ve: contraste computado, 2.5.8, foco',
                          'deepen what static cannot see: computed contrast, 2.5.8, focus')[idx]})
    return {'mode': 'diagnose', 'goal': goal, 'url': url, 'lang': t,
            'vitals': vitals, 'symptoms': symptoms, 'steps': steps,
            'guarantee': _GUARANTEE[t]}


def route(goal, lang='en', url=None, html=None):
    """Goal en lenguaje natural → secuencia de tools con el porqué.
    Con url= o html= → diagnóstico secuencial (la página decide el orden)."""
    if html or url:
        if html:
            return diagnose(html, url=url or '(html)', lang=lang, goal=goal)
        try:
            html_text = _fetch(url, timeout=20)
        except ValueError as e:
            return {'mode': 'diagnose', 'lang': lang, 'error': str(e)}
        except Exception as e:  # noqa: BLE001
            return {'mode': 'diagnose', 'lang': lang, 'error': f'fetch failed: {e}'}
        if isinstance(html_text, dict):
            return {'mode': 'diagnose', 'lang': lang,
                    'error': html_text.get('error', 'fetch failed')}
        return diagnose(html_text, url=url, lang=lang, goal=goal)
    t = 'es' if lang == 'es' else 'en'
    g = (goal or '').lower()
    scored = []
    for r in ROUTES:
        # palabra completa: 'ci' no puede colarse dentro de 'licitación'
        # o 'ciego' — la subcadena arruinaba el enrutado en español
        score = sum(1 for p in r['patterns']
                    if re.search(rf'\b{re.escape(p)}\b', g))
        if score:
            scored.append((score, r))
    if not scored:
        best = next(r for r in ROUTES if r['id'] == 'start')
        alt = []
    else:
        scored.sort(key=lambda x: -x[0])
        best = scored[0][1]
        alt = [r['id'] for _, r in scored[1:4]]
    idx = 0 if t == 'es' else 1
    steps_out = []
    for i, one_step in enumerate(best['tools'], 1):
        steps_out.append({'step': i, 'tool': one_step[0], 'why': one_step[idx]})
    return {
        'mode': 'route', 'goal': goal, 'lang': t,
        'route': best['id'],
        'alternates': alt,
        'steps': steps_out,
        'prompts': [p for p in best['prompts']],
        'cli': best.get('cli'),
        'note': _NOTE[t],
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--goal', default='', help='the task in plain language')
    ap.add_argument('--url', help='diagnosis mode: read the page, order the exams')
    ap.add_argument('--file', help='diagnosis mode: local HTML file')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    a = ap.parse_args(argv)
    html = None
    if a.file:
        with open(a.file, encoding='utf-8') as f:
            html = f.read()
    print(json.dumps(route(a.goal, lang=a.lang, url=a.url, html=html),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
