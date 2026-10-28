#!/usr/bin/env python3
"""a11y_route — the router: tell the agent WHICH tools solve a task.

32 specialized tools are the positioning; this makes the choice O(1). The
agent (or the human) states a goal in plain language — "gate my PR",
"arregla el contraste del hero" — and gets the ordered tool sequence with
the why of each step. Deterministic by design: a keyword index over the
routes table, NOT an LLM guessing. If nothing matches, the honest fallback
says where everyone starts: the express audit.

The routes table is the product: keep it in sync with the toolkit (the
test suite pins that every referenced tool and prompt exists).

CLI:
  a11yroute.py --goal "gate my PR" [--lang en]
"""

import argparse
import json
import re
import sys

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


def route(goal, lang='en'):
    """Goal en lenguaje natural → secuencia de tools con el porqué."""
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
    ap.add_argument('--goal', required=True, help='the task in plain language')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    a = ap.parse_args(argv)
    print(json.dumps(route(a.goal, lang=a.lang), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
