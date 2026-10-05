#!/usr/bin/env python3
"""Blindfold journey testing — the agent IS the non-visual user.

The idea no other accessibility tool has: instead of checking rules, the AI
coding agent attempts a REAL task ("sign up", "find the price and add to
cart") perceiving only what a screen reader exposes — the linearized
accessibility tree — and acting only by accessible name and keyboard. Every
point of friction it meets is logged against a WCAG criterion. This module
turns that friction log into a deterministic, scored, evidence-ready verdict.

Division of labor:
  - the PROMPT (blindfold-task) drives the perceive→act→log loop in the agent;
  - this module judges it: fixed scoring rules, bilingual remediations,
    criterion validation against the 55 A/AA set, pack-ready output.

Honesty: a pass means ONE task was completable non-visually by an AI agent on
one URL. It is usability evidence, never conformance — a human screen-reader
user is not an AI agent (different strategies, habits, patience).

CLI:
  a11yjourney.py friction.json [-o verdict.json] [--lang en]
"""

import argparse
import json
import sys

# Friction catalogue: the recurring ways a task breaks non-visually, each with
# its criterion and bilingual remediation. The agent logs `pattern` keys from
# here (or raw criterion+issue for anything rarer). Parity-tested like every
# other catalog in this toolkit.
_J = {
    'es': {
        'journey_unnamed_control': ('4.1.2', 'high',
             'Un control necesario para la tarea se anuncia sin nombre ("botón" a secas).',
             'Da al control un nombre accesible: texto visible, aria-label o aria-labelledby.'),
        'journey_focus_lost': ('2.4.3', 'high',
             'Tras una acción, el foco desapareció o saltó a un lugar inesperado.',
             'Mueve el foco programáticamente al destino lógico tras insertar o reemplazar contenido.'),
        'journey_error_silent': ('3.3.1', 'high',
             'El envío falló y el error no se anuncia ni recibe el foco.',
             'Asocia el mensaje de error al campo (aria-describedby) y mueve el foco al primer error.'),
        'journey_status_silent': ('4.1.3', 'medium',
             'El resultado de la acción (éxito o carga) no se anuncia por una región viva.',
             'Anuncia el cambio de estado con role="status" o aria-live="polite".'),
        'journey_no_instruction': ('3.3.2', 'medium',
             'La tarea exigía un dato sin indicar su formato o su obligatoriedad.',
             'Etiqueta el campo con instrucciones y marca lo requerido antes del error.'),
        'journey_reach_fail': ('2.1.1', 'high',
             'Un control necesario no es alcanzable ni operable con teclado.',
             'Hazlo enfocable y operable con teclado; nunca solo con puntero.'),
        'journey_dialog_trap': ('2.1.2', 'high',
             'Un diálogo atrapa el teclado y Escape no lo cierra.',
             'Cierra el diálogo con Escape y devuelve el foco al disparador.'),
        'journey_generic_link': ('2.4.4', 'low',
             'El destino de un enlace clave no se entiende por su texto.',
             'Texto de enlace descriptivo en contexto («leer más» no dice nada solo).'),
        'journey_hidden_in_tree': ('1.3.1', 'medium',
             'Información esencial de la tarea no está en el árbol de accesibilidad.',
             'Expresa la relación con semántica real (lista, encabezado, tabla), no con layout.'),
        'journey_timeout_confusion': ('2.2.1', 'medium',
             'La tarea se perdió por un límite de tiempo sin opción de extenderlo.',
             'Permite ajustar, extender o desactivar el límite de tiempo.'),
        'journey_heading_nav_broken': ('2.4.6', 'high',
             'Los encabezados faltan o rompen la jerarquía: navegar por encabezados — la estrategia principal de un lector de pantalla — no encuentra la sección que la tarea necesita.',
             'Usa marcado real de encabezados en orden lógico (h1→h2…); nunca simules encabezados con negritas.'),
        'journey_landmark_missing': ('2.4.1', 'medium',
             'La página no expone landmarks (main/nav): la navegación por regiones no salta el boilerplate.',
             'Envuelve el contenido en main/navigation reales; el skip-link es un extra, no el arreglo.'),
        'journey_mode_confusion': ('4.1.2', 'high',
             'Un widget personalizado se traga las teclas u oculta su rol y estado: el cambio entre modo navegación y modo foco rompe la interacción.',
             'Usa elementos nativos (select, button) o el patrón ARIA completo: rol, estado y soporte de teclado.'),
        'journey_duplicate_targets': ('4.1.2', 'medium',
             'Varios controles comparten el mismo nombre accesible: «el botón de comprar» es ambiguo por nombre solo.',
             'Diferencia los nombres accesibles con contexto (aria-label, texto visible).'),
        'journey_dynamic_stale': ('4.1.3', 'medium',
             'El árbol cambió tras la acción (contenido reemplazado) sin anuncio: el mapa del agente quedó obsoleto.',
             'Anuncia las actualizaciones de regiones dinámicas (role=status/aria-live) y mantiene el foco estable.'),
    },
    'en': {
        'journey_unnamed_control': ('4.1.2', 'high',
             'A control needed for the task is announced without a name ("button", bare).',
             'Give the control an accessible name: visible text, aria-label or aria-labelledby.'),
        'journey_focus_lost': ('2.4.3', 'high',
             'After an action, focus disappeared or jumped somewhere unexpected.',
             'Move focus programmatically to the logical destination after inserting or replacing content.'),
        'journey_error_silent': ('3.3.1', 'high',
             'Submission failed and the error is neither announced nor focused.',
             'Associate the error message with the field (aria-describedby) and move focus to the first error.'),
        'journey_status_silent': ('4.1.3', 'medium',
             'The action result (success or loading) is not announced via a live region.',
             'Announce the status change with role="status" or aria-live="polite".'),
        'journey_no_instruction': ('3.3.2', 'medium',
             'The task required input whose format or requiredness was never stated.',
             'Label the field with instructions and mark requiredness before the error does.'),
        'journey_reach_fail': ('2.1.1', 'high',
             'A control needed for the task is not reachable or operable by keyboard.',
             'Make it focusable and keyboard-operable; pointer-only is never enough.'),
        'journey_dialog_trap': ('2.1.2', 'high',
             'A dialog traps the keyboard and Escape does not close it.',
             'Close the dialog on Escape and return focus to the trigger.'),
        'journey_generic_link': ('2.4.4', 'low',
             'The destination of a key link is not understandable from its text.',
             'Descriptive link text in context ("read more" says nothing alone).'),
        'journey_hidden_in_tree': ('1.3.1', 'medium',
             'Information essential to the task is missing from the accessibility tree.',
             'Express the relationship with real semantics (list, heading, table), not layout.'),
        'journey_timeout_confusion': ('2.2.1', 'medium',
             'The task was lost to a time limit with no way to extend it.',
             'Allow adjusting, extending or turning off the time limit.'),
        'journey_heading_nav_broken': ('2.4.6', 'high',
             'Headings are missing or break the hierarchy: navigating by headings — a screen-reader user\u2019s primary strategy — cannot find the section the task needs.',
             'Use real heading markup in logical order (h1→h2…); never fake headings with bold text.'),
        'journey_landmark_missing': ('2.4.1', 'medium',
             'The page exposes no landmarks (main/nav): landmark navigation cannot skip the boilerplate.',
             'Wrap content in real main/navigation landmarks; the skip link is a bonus, not the fix.'),
        'journey_mode_confusion': ('4.1.2', 'high',
             'A custom widget swallows keystrokes or hides its role and state: browse-mode vs focus-mode switching breaks the interaction.',
             'Use native elements (select, button) or the full ARIA pattern: role, state, keyboard support.'),
        'journey_duplicate_targets': ('4.1.2', 'medium',
             'Several controls share one accessible name: “the Buy button” is ambiguous by name alone.',
             'Differentiate accessible names with context (aria-label, visible text).'),
        'journey_dynamic_stale': ('4.1.3', 'medium',
             'The tree changed after the action (content replaced) with no announcement — the agent\u2019s map went stale.',
             'Announce dynamic region updates (role=status/aria-live) and keep focus stable.'),
    },
}

_RULES = {'start': 100, 'high': 25, 'medium': 12, 'low': 5, 'pass_threshold': 85}


def _crit_set():
    from a11y_toolkit.a11ycrit import _C
    return {k for k, v in _C.items() if v[0] in ('A', 'AA')}


def _validar_friction(item, crits):
    """Expand a friction item (pattern key or raw criterion) → dict, or None+error."""
    if 'pattern' in item:
        pat = item['pattern']
        if pat not in _J['en']:
            return None, f"patrón desconocido: {pat} — disponibles: {sorted(_J['en'])}"
        crit, sev, issue, rem = _J['en'][pat]
        return {'signal': pat, 'criterion': crit, 'severity': sev,
                'issue': issue, 'remediation': rem}, None
    crit = str(item.get('criterion', '')).strip()
    if crit not in crits:
        return None, f"criterio fuera del conjunto A/AA 2.2: {crit!r}"
    sev = item.get('severity', 'medium')
    if sev not in ('high', 'medium', 'low'):
        return None, f"severidad inválida: {sev!r} (high|medium|low)"
    issue = str(item.get('issue', '')).strip()
    if not issue:
        return None, 'fricción sin issue (describe la estructura, nunca cites contenido)'
    return {'signal': item.get('signal', 'journey_custom'), 'criterion': crit,
            'severity': sev, 'issue': issue,
            'remediation': str(item.get('remediation', '')).strip()}, None


def verdictar(task, steps, outcome, url='', lang='en'):
    """Friction log → deterministic journey verdict (pack-ready report shape)."""
    lang = 'es' if lang == 'es' else 'en'
    if not isinstance(task, dict) or not str(task.get('goal', '')).strip():
        return {'error': 'task.goal es obligatorio (qué tarea intentó el agente)'}
    if not isinstance(steps, list):
        return {'error': 'steps debe ser una lista de pasos'}
    if not isinstance(outcome, dict):
        return {'error': 'outcome debe ser un objeto'}

    crits = _crit_set()
    findings, errores = [], []
    for i, paso in enumerate(steps):
        if not isinstance(paso, dict):
            errores.append(f'step[{i}] no es un objeto')
            continue
        f = paso.get('friction')
        if not f:
            continue
        items = f if isinstance(f, list) else [f]
        for item in items:
            if not isinstance(item, dict):
                errores.append(f'step[{i}].friction no es un objeto')
                continue
            conv, err = _validar_friction(item, crits)
            if err:
                errores.append(f'step[{i}]: {err}')
                continue
            conv['step'] = i
            conv.setdefault('perceived', str(paso.get('perceived', ''))[:120] or None)
            findings.append(conv)

    if errores:
        return {'error': 'log de fricción inválido', 'detalles': errores}

    high = sum(1 for x in findings if x['severity'] == 'high')
    medium = sum(1 for x in findings if x['severity'] == 'medium')
    low = sum(1 for x in findings if x['severity'] == 'low')

    score = _RULES['start'] - high * _RULES['high'] - medium * _RULES['medium'] - low * _RULES['low']
    score = max(0, score)
    completed = bool(outcome.get('completed'))
    gave_up = bool(outcome.get('gave_up'))
    workaround = bool(outcome.get('workaround_used'))
    if workaround:
        score = max(0, score - 15)

    if gave_up:
        verdict = 'blocked'
    elif not completed:
        verdict = 'fail'
    elif (not workaround and high == 0 and score >= _RULES['pass_threshold']):
        verdict = 'pass'
    else:
        verdict = 'partial'

    nota = ('Task-based usability evidence: ONE task attempted by an AI agent '
            'perceiving only the accessibility tree, on this URL. A pass means '
            'the task was completable non-visually by the agent — it is not a '
            'conformance claim and not a substitute for a human screen-reader '
            'user. The friction list is the handoff to the human half.'
            if lang == 'en' else
            'Evidencia de usabilidad por tareas: UNA tarea intentada por un '
            'agente de IA percibiendo solo el árbol de accesibilidad, en esta '
            'URL. Un pase significa que el agente completó la tarea sin vista; '
            'no es una declaración de conformidad ni sustituye a una persona '
            'usuaria de lector de pantalla. La lista de fricción es el puente '
            'hacia la mitad humana.')

    return {
        'mode': 'journey',
        'url': url,
        'task': {'goal': str(task['goal'])[:200], 'kind': str(task.get('kind', 'custom'))},
        'steps_count': len(steps),
        'outcome': {'completed': completed, 'gave_up': gave_up, 'workaround_used': workaround,
                    'notes': str(outcome.get('notes', ''))[:300] or None},
        'verdict': verdict,
        'score': score,
        'findings': findings,
        'summary': {'high': high, 'medium': medium, 'low': low},
        'rules': dict(_RULES, workaround_penalty=15,
                      note='deterministic: start 100, minus friction, minus 15 if only reachable via workaround'),
        'score_note': nota,
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('log', help='JSON friction log: {task, steps, outcome, url?, lang?}')
    ap.add_argument('-o', '--out', help='escribe el veredicto en fichero')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    a = ap.parse_args(argv)
    with open(a.log, encoding='utf-8') as f:
        d = json.load(f)
    res = verdictar(d.get('task', {}), d.get('steps', []), d.get('outcome', {}),
                    url=d.get('url', ''), lang=a.lang or d.get('lang', 'en'))
    out = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print(json.dumps({'verdict': res.get('verdict'), 'score': res.get('score'),
                          'out': a.out}))
    else:
        print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
