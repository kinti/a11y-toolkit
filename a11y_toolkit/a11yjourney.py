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
from datetime import datetime, timezone
from . import a11yi18n

# Friction catalogue: the recurring ways a task breaks non-visually, each with
# its criterion and bilingual remediation. The agent logs `pattern` keys from
# here (or raw criterion+issue for anything rarer). Parity-tested like every
# other catalog in this toolkit.
_J = a11yi18n.pair('journey')  # locales/<lang>.json — community-editable

_RULES = {'start': 100, 'high': 25, 'medium': 12, 'low': 5, 'pass_threshold': 85}


def _crit_set():
    from a11y_toolkit.a11ycrit import _C
    return {k for k, v in _C.items() if v[0] in ('A', 'AA')}


def _validate_friction(item, crits, lang='en'):
    """Expand a friction item (pattern key or raw criterion) → dict, or None+error."""
    cat = _J['es' if lang == 'es' else 'en']
    if 'pattern' in item:
        pat = item['pattern']
        if pat not in cat:
            return None, f"patrón desconocido: {pat} — disponibles: {sorted(cat)}"
        crit, sev, issue, rem = cat[pat]
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


def verdict(task, steps, outcome, url='', lang='en'):
    """Friction log → deterministic journey verdict (pack-ready report shape)."""
    lang = 'es' if lang == 'es' else 'en'
    if not isinstance(task, dict) or not str(task.get('goal', '')).strip():
        return {'error': 'task.goal is required (what task the agent attempted)'}
    if not isinstance(steps, list):
        return {'error': 'steps must be a list of steps'}
    if not isinstance(outcome, dict):
        return {'error': 'outcome must be an object'}

    crits = _crit_set()
    findings, errors = [], []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f'step[{i}] no es un objeto')
            continue
        f = step.get('friction')
        if not f:
            continue
        items = f if isinstance(f, list) else [f]
        for item in items:
            if not isinstance(item, dict):
                errors.append(f'step[{i}].friction no es un objeto')
                continue
            conv, err = _validate_friction(item, crits, lang=lang)
            if err:
                errors.append(f'step[{i}]: {err}')
                continue
            conv['step'] = i
            conv.setdefault('perceived', str(step.get('perceived', ''))[:120] or None)
            findings.append(conv)

    if errors:
        return {'error': 'log de fricción inválido', 'details': errors}

    high = sum(1 for x in findings if x['severity'] == 'high')
    medium = sum(1 for x in findings if x['severity'] == 'medium')
    low = sum(1 for x in findings if x['severity'] == 'low')

    score = _RULES['start'] - high * _RULES['high'] - medium * _RULES['medium'] - low * _RULES['low']
    score = max(0, score)
    def _bool(v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() == 'true'
        return bool(v)

    completed = _bool(outcome.get('completed'))
    gave_up = _bool(outcome.get('gave_up'))
    workaround = _bool(outcome.get('workaround_used'))
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

    note = ('Task-based usability evidence: ONE task attempted by an AI agent '
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
        'score_note': note,
    }


def budget_init(verdict, url=''):
    """Verdict → baseline del journey (para comparar tras cada deploy).

    La clave de fricción es `criterio:señal` — los IDs de señal son estables
    por diseño (D3), así que el baseline sigue siendo válido entre versiones
    del motor."""
    if not isinstance(verdict, dict) or verdict.get('verdict') is None:
        return {'error': 'not a journey verdict (use a11y_journey_verdict)'}
    return {
        'format': 'a11y-journey-budget/1',
        'task': verdict.get('task', {}),
        'url': verdict.get('url', url),
        'verdict': verdict['verdict'],
        'score': verdict.get('score'),
        'friction': sorted({f"{f['criterion']}:{f['signal']}" for f in verdict.get('findings', [])}),
        'generated': datetime.now(timezone.utc).isoformat(),
    }


def budget_compare(baseline, verdict):
    """Solo la fricción NUEVA bloquea — la regresión de USABILIDAD, no ya de reglas.

    NO-GO si: aparece fricción alta nueva, o la tarea degradó su veredicto
    (pass→partial/fail/blocked). La fricción nueva media/baja avisa, no bloquea."""
    if not isinstance(baseline, dict) or baseline.get('format') != 'a11y-journey-budget/1':
        return {'error': 'baseline inválida (usa budget_init)'}
    if not isinstance(verdict, dict) or verdict.get('verdict') is None:
        return {'error': 'not a journey verdict'}
    if baseline.get('task', {}).get('goal') != verdict.get('task', {}).get('goal'):
        return {'error': "el baseline es de OTRA tarea: %r vs %r" % (
            baseline.get('task', {}).get('goal'), verdict.get('task', {}).get('goal'))}

    base = set(baseline.get('friction', []))
    _rank = {'high': 2, 'medium': 1, 'low': 0}
    current = {}
    for f in verdict.get('findings', []):
        k = f"{f['criterion']}:{f['signal']}"
        prev = current.get(k)
        # colisión clave→severidad MÁS grave (dos custom sobre el mismo
        # criterio no pueden esconder una high tras una medium)
        if prev is None or _rank[f['severity']] > _rank[prev['severity']]:
            current[k] = f
    new_f = sorted(set(current) - base)
    resolved = sorted(base - set(current))
    new_high = [k for k in new_f if current[k]['severity'] == 'high']
    degrades = (baseline.get('verdict') == 'pass'
               and verdict['verdict'] in ('partial', 'fail', 'blocked'))

    go = not new_high and not degrades
    return {
        'verdict': 'GO' if go else 'NO-GO',
        'new_blocking': new_high,
        'new_friction': new_f,
        'resolved': resolved,
        'verdict_before': baseline.get('verdict'),
        'verdict_after': verdict['verdict'],
        'degraded': degrades,
        'score_before': baseline.get('score'),
        'score_after': verdict.get('score'),
        'note': ('task-based regression gate: only NEW high friction (or a '
                 'pass degrading) blocks the deploy' if go else
                 'the task got harder to complete without sight — fix before deploy'),
    }


def _budget_main(argv):
    ap = argparse.ArgumentParser(description='journey budget: only NEW friction blocks')
    ap.add_argument('verdict', help='verdict JSON from a11y_journey_verdict')
    ap.add_argument('--init', action='store_true', help='create the baseline')
    ap.add_argument('--budget', default='journey-budget.json')
    ap.add_argument('-o', '--out', help='write the result here (default: stdout)')
    a = ap.parse_args(argv)
    with open(a.verdict, encoding='utf-8') as f:
        v = json.load(f)
    if a.init:
        b = budget_init(v)
        if 'error' in b:
            print(json.dumps(b, ensure_ascii=False))
            return 1
        out = json.dumps(b, ensure_ascii=False, indent=1)
        target = a.out or a.budget
        with open(target, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print(json.dumps({'budget': target, 'friction': len(b.get('friction', [])),
                          'verdict': b.get('verdict')}))
        return 0
    with open(a.budget, encoding='utf-8') as f:
        b = json.load(f)
    res = budget_compare(b, v)
    out = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
    print(out)
    if 'error' in res:
        return 1  # error de uso ≠ NO-GO de regresión
    return 0 if res.get('verdict') == 'GO' else 2


def main(argv):
    if argv and ('--init' in argv or '--budget' in argv):
        return _budget_main(argv)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('log', help='JSON friction log: {task, steps, outcome, url?, lang?}')
    ap.add_argument('-o', '--out', help='escribe el veredicto en fichero')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    a = ap.parse_args(argv)
    with open(a.log, encoding='utf-8') as f:
        d = json.load(f)
    res = verdict(d.get('task', {}), d.get('steps', []), d.get('outcome', {}),
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
