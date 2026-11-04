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

Recommended task kinds (free-form by design; these make baselines comparable):
sign-up, checkout, password-reset, search, onboarding, settings, data-export.
The friction catalogue lives in locales/<lang>.json (journey_* keys) —
community-editable, parity-tested.
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
            _msg = ('patrón desconocido: {p} — disponibles: {d}'
                    if lang == 'es' else
                    'unknown pattern: {p} — available: {d}')
            return None, _msg.format(p=pat, d=sorted(cat))
        crit, sev, issue, rem = cat[pat]
        return {'signal': pat, 'criterion': crit, 'severity': sev,
                'issue': issue, 'remediation': rem}, None
    crit = str(item.get('criterion', '')).strip()
    if crit not in crits:
        _msg = ('criterio fuera del conjunto A/AA 2.2: {c!r}'
                if lang == 'es' else 'criterion outside the A/AA 2.2 set: {c!r}')
        return None, _msg.format(c=crit)
    sev = item.get('severity', 'medium')
    if sev not in ('high', 'medium', 'low'):
        _msg = ('severidad inválida: {s!r} (high|medium|low)'
                if lang == 'es' else 'invalid severity: {s!r} (high|medium|low)')
        return None, _msg.format(s=sev)
    issue = str(item.get('issue', '')).strip()
    if not issue:
        return None, ('fricción sin issue (describe la estructura, nunca cites contenido)'
                      if lang == 'es' else
                      'friction without issue (describe the structure, never quote content)')
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


JOURNEY_FORMAT = 'a11y-journey/1'


def seal_record(task, steps, outcome, url='', lang='en', trace=None):
    """Verdict → the sealed journey record (format `a11y-journey/1`).

    The open artifact the market keeps describing ("replayable traces" in
    every journey-monitoring pitch) and nobody owns: the walk AND the
    judgment in one envelope — the agent's steps as walked, the outcome,
    the deterministic verdict, and an optional a11ytrace capture — sealed
    with a SHA-256 over the canonical payload. Honesty twice over: the sha
    makes the record tamper-evident, and the scoring is deterministic, so
    `record_verify` can RE-DERIVE the verdict from the stored steps and
    demand it matches. A record is evidence, never conformance."""
    import hashlib
    lang = 'es' if lang == 'es' else 'en'
    v = verdict(task, steps, outcome, url=url, lang=lang)
    if 'error' in v:
        return v
    from .server import VERSION   # lazy: server imports this module
    record = {
        'format': JOURNEY_FORMAT,
        'engine_version': VERSION,
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'lang': lang,
        'task': v['task'],
        'url': v['url'],
        'steps': steps,
        'outcome': v['outcome'],
        'verdict': {'verdict': v['verdict'], 'score': v['score'],
                    'summary': v['summary'], 'findings': v['findings']},
        'trace': trace,
        'rules': v['rules'],
        'score_note': v['score_note'],
    }
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False,
                         default=str).encode('utf-8')
    record['sha256'] = hashlib.sha256(payload).hexdigest()
    return record


def _canonical_findings(findings):
    """Language-independent projection of a findings list: the sealed verdict
    must re-derive identically regardless of the VERIFIER's lang — issue and
    remediation are localized catalog text, signal/criterion/severity/step
    are the stable contract."""
    return [(f.get('signal'), f.get('criterion'), f.get('severity'),
             f.get('step')) for f in (findings or [])]


def record_verify(record, lang='en'):
    """Re-derive the verdict from the stored steps and demand it matches.

    Returns {'status': 'verified'|'tampered'|'invalid', ...}: `tampered`
    means the sha no longer covers the payload OR the deterministic scoring
    of the stored steps no longer produces the stored verdict — either way
    the record cannot be trusted. `invalid` means it is not a record.

    The record's sealed `lang` wins over the param (a record sealed in es
    verifies from an en session without false 'tampered'); legacy records
    without lang fall back to the param."""
    import hashlib
    lang = 'es' if lang == 'es' else 'en'
    if not isinstance(record, dict) or record.get('format') != JOURNEY_FORMAT \
            or not record.get('sha256'):
        _JR = a11yi18n.pair('journeyrec')
        return {'status': 'invalid',
                'note': _JR.get(lang, _JR['en']).get('bad_format')}
    eff_lang = record.get('lang') if record.get('lang') in ('es', 'en') else lang
    body = {k: v for k, v in record.items() if k != 'sha256'}
    payload = json.dumps(body, sort_keys=True, ensure_ascii=False,
                         default=str).encode('utf-8')
    sha_ok = hashlib.sha256(payload).hexdigest() == record['sha256']
    re_v = verdict(record.get('task', {}), record.get('steps', []),
                   record.get('outcome', {}), url=record.get('url', ''),
                   lang=eff_lang)
    derived_ok = ('error' not in re_v and isinstance(record.get('verdict'), dict)
                  and re_v['verdict'] == record['verdict'].get('verdict')
                  and re_v['score'] == record['verdict'].get('score')
                  and _canonical_findings(re_v.get('findings'))
                  == _canonical_findings(record['verdict'].get('findings')))
    if sha_ok and derived_ok:
        return {'status': 'verified', 'sha256': record['sha256'],
                'verdict': record['verdict'].get('verdict'),
                'score': record['verdict'].get('score')}
    return {'status': 'tampered',
            'sha_intact': sha_ok, 'verdict_reproducible': derived_ok,
            'recomputed': None if 'error' in re_v
            else {'verdict': re_v['verdict'], 'score': re_v['score'],
                  'findings': re_v['findings']}}


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
