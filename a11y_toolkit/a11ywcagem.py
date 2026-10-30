#!/usr/bin/env python3
"""WCAG-EM 2.0 evaluation mode — the sampling/aggregation layer.

WCAG-EM (W3C Group Note, 2026-07-23) is HOW a full evaluation is scoped,
sampled and reported. This module does the machine half honestly:

  plan JSON  → what is being evaluated (Step 1), the sample set (Step 3)
  packs[]    → the sealed evidence per sample (Step 4, a11y_evidence output)
  report     → per-criterion rollup ACROSS the sample (Step 5), sealed with
               a root hash over the pack seals

Since a11y-wcagem-report/2 the rollup carries its STATISTICS layer
(a11ydistrib, the HEGM translation): per-criterion failure prevalence with a
Wilson interval (what a random unaudited page may hold), and per-page human
effort as a zero-inflated mixture + seeded bootstrap — intervals over the
sample, never claims about the site.

What it deliberately does NOT do: claim conformance. The report carries
evidence-status per criterion (the worst across the sample wins), the
priced human work that remains, and the standard's step trace. Random
sample selection stays with the evaluator (their methodology, their name);
structured samples and complete processes (journeys) are first-class.

CLI:
  a11ywcagem.py --plan plan.json --packs p1.json p2.json -o report.json
"""

import argparse
import hashlib
import json
import sys

from .a11ydistrib import effort_inference, wilson_interval

# El worst peor gana al agregar samples; never-flagged en TODAS no es pass
# (es "ninguna señal saltó en esta sample"), exactamente como el pack.
_RANK = {'automated-fail': 0, 'not-run': 1, 'automated-review': 2,
          'manual-only': 3, 'not-flagged': 4, 'agent-verified': 5}

_TYPES = ('structured', 'random', 'process', 'common-view')

_STEPS = [
    {'step': '1', 'what': 'Define the evaluation scope',
     'where': 'plan.product (enclosure: all views, states, functionality)'},
    {'step': '1.2', 'what': 'Conformance target', 'where': 'plan.conformance_target'},
    {'step': '1.3', 'what': 'Accessibility support baseline', 'where': 'plan.support_baseline'},
    {'step': '2', 'what': 'Explore the target product', 'where': 'plan.sample[].why'},
    {'step': '3', 'what': 'Select a representative sample set',
     'where': 'plan.sample[] (structured / random / process) + packs per sample'},
    {'step': '4', 'what': 'Evaluate the selected sample set',
     'where': 'the evidence packs (a11y-evidence-pack/2)'},
    {'step': '5', 'what': 'Report the evaluation findings', 'where': 'this report'},
]


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'))


def validate_plan(plan):
    """Plan (dict) → (ok, error). Solo estructura; el muestreo es del auditor."""
    if not isinstance(plan, dict):
        return False, 'el plan debe ser un objeto'
    for field in ('product', 'conformance_target', 'sample'):
        if field not in plan:
            return False, f'falta {field} (WCAG-EM paso 1/3)'
    if not isinstance(plan['product'], dict) or not plan['product'].get('name'):
        return False, 'product.name es obligatorio (¿qué se evalúa?)'
    if not isinstance(plan['conformance_target'], str):
        return False, 'conformance_target debe ser texto (p. ej. "WCAG 2.2 AA")'
    sample = plan['sample']
    if not isinstance(sample, list) or not sample:
        return False, 'sample debe ser una lista no vacía de samples'
    for i, m in enumerate(sample):
        if not isinstance(m, dict):
            return False, f'sample #{i + 1} debe ser objeto'
        for field in ('id', 'type'):
            if not m.get(field):
                return False, f'sample #{i + 1} sin {field}'
        if m['type'] not in _TYPES:
            return False, (f"sample {m['id']}: type debe ser "
                           f"{'/'.join(_TYPES)} (WCAG-EM 3.1-3.3)")
        if not m.get('url') and not m.get('file'):
            return False, f"sample {m['id']}: url o file requeridos"
    if plan.get('estimated_pages') is not None:
        ep = plan['estimated_pages']
        # la proyección es una FIGURA del evaluador, no una medición — pero
        # proyectar sobre menos páginas que la muestra propia es sin sentido
        if not isinstance(ep, int) or isinstance(ep, bool) or ep < len(sample):
            return False, (f'estimated_pages debe ser entero ≥ len(sample) '
                           f'({len(sample)}) para proyectar el esfuerzo')
    return True, ''


def aggregate(plan, packs, lang='en', inference_seed=7):
    """Plan válido + packs sellados → report agregado con sello raíz.

    Regla de agregado por criterio: el PEOR worst de todas las samples
    (un fallo en cualquier página muestreada es un fallo del report).
    agent-verified no borra un fail (misma honestidad que el pack).

    Desde /2: cada criterio lleva su prevalencia en la muestra con intervalo
    Wilson (qué puede contener una página NO muestreada), y el reporte lleva
    el bloque `inference` del esfuerzo (a11ydistrib, traducción HEGM:
    mezcla cero-inflada + bootstrap sembrado sobre las bandas lo/hi de
    minutos). Estadística sobre la muestra, jamás conformidad.
    """
    ok, err = validate_plan(plan)
    if not ok:
        raise ValueError(err)
    if len(packs) != len(plan['sample']):
        raise ValueError(f'{len(plan["sample"])} samples, {len(packs)} packs: deben emparejar')

    codes, names, effort = set(), {}, {'MIN': 0, 'MED': 0, 'MAX': 0}
    worst = {}       # code → peor worst
    fail_counts = {}        # code → cuántas SAMPLES fallaron (no filas)
    for pack in packs:
        seen = set()   # un criterio aparece UNA vez por pack; duplicados de un
        # pack manual no deben inflar prevalencia ni esfuerzo (cuentan 1 sample)
        for c in pack.get('criteria', []):
            code = c['criterion'].split(' ')[0]
            if code in seen:
                continue
            seen.add(code)
            codes.add(code)
            names[code] = c['criterion']
            st = c['status']
            if code not in worst or _RANK[st] < _RANK[worst[code]]:
                worst[code] = st
            if st == 'automated-fail':
                fail_counts[code] = fail_counts.get(code, 0) + 1
            ef = c.get('effort', {}).get('class')
            if ef in effort and st != 'agent-verified':
                effort[ef] += 1

    criteria = []
    for code in sorted(codes, key=lambda x: tuple(int(n) for n in x.split('.'))):
        k = fail_counts.get(code, 0)
        row = {'criterion': names[code], 'status': worst[code],
               'samples_failing': k,
               'total_samples': len(packs)}
        # estadística de la muestra: prevalencia observada + banda Wilson
        row['prevalence'] = round(k / len(packs), 4) if packs else 0.0
        row['prevalence_ci95_wilson'] = wilson_interval(k, len(packs))
        if worst[code] == 'not-flagged':
            row['note'] = ('no signal fired on ANY sampled page — explicitly '
                           'NOT pass; the human still owns this criterion')
        criteria.append(row)

    # esfuerzo por página: ambas bandas del rango de minutos por criterio
    # (el agente-verificado ya está pagado, no cuenta — misma regla arriba);
    # un pack manual puede traer la fila duplicada o el rango invertido: se
    # deduplica por código y el rango se normaliza (min/max es idempotente)
    lo_pages, hi_pages = [], []
    for pack in packs:
        seen, lo, hi = set(), 0, 0
        for c in pack.get('criteria', []):
            if c.get('status') == 'agent-verified':
                continue
            code = c['criterion'].split(' ')[0]
            if code in seen:
                continue
            seen.add(code)
            mins = c.get('effort', {}).get('minutes')
            if isinstance(mins, (list, tuple)) and len(mins) == 2:
                lo += min(mins)
                hi += max(mins)
        lo_pages.append(lo)
        hi_pages.append(hi)

    report = {
        'format': 'a11y-wcagem-report/2',
        'method': 'WCAG-EM 2.0 (W3C Group Note, 2026-07-23)',
        'product': plan['product'],
        'conformance_target': plan['conformance_target'],
        'support_baseline': plan.get('support_baseline', []),
        'sample': plan['sample'],
        'wcag_em': {'steps': _STEPS,
                    'note': ('random selection (3.2) stays with the evaluator: '
                             'this tool aggregates, never chooses')},
        'criteria': criteria,
        'summary': {s: sum(1 for c in criteria if c['status'] == s)
                    for s in _RANK},
        'effort_pending': effort,
        'inference': effort_inference(
            lo_pages, hi_pages, seed=inference_seed,
            projected_pages=plan.get('estimated_pages'), lang=lang),
        'packs': [{'sample': m['id'], 'type': m['type'],
                   'sha256': p['sha256'], 'format': p.get('format')}
                  for m, p in zip(plan['sample'], packs)],
        # sin claim de conformidad: el report ES evidencia para el humano
    }
    report['sha256'] = hashlib.sha256(
        _canon({k: v for k, v in report.items() if k != 'sha256'}).encode('utf-8')
    ).hexdigest()
    return report


def verify_report(report):
    """(ok, detalle): el sello raíz del report (menos sha256)."""
    expected = hashlib.sha256(
        _canon({k: v for k, v in report.items() if k != 'sha256'}).encode('utf-8')
    ).hexdigest()
    return expected == report.get('sha256'), 'root sha256'


def main(argv):
    ap = argparse.ArgumentParser(description='WCAG-EM 2.0 aggregated evaluation report')
    ap.add_argument('--plan', required=True, help='evaluation plan JSON (scope + sample set)')
    ap.add_argument('--packs', nargs='+', required=True,
                    help='evidence pack JSON per sample, in plan.sample order')
    ap.add_argument('--lang', default='en', choices=['en', 'es'],
                    help='inference note language (report data stays English)')
    ap.add_argument('-o', '--out', default='wcagem-report.json')
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan, encoding='utf-8'))
    packs = [json.load(open(p, encoding='utf-8')) for p in a.packs]
    try:
        report = aggregate(plan, packs, lang=a.lang)
    except ValueError as e:
        print(json.dumps({'error': str(e)}))
        return 2
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    inf = report['inference']
    print(json.dumps({'report': a.out, 'sha256': report['sha256'],
                      'criteria': len(report['criteria']),
                      'summary': report['summary'],
                      'effort_ci95_envelope_per_page': inf['ci95_mean_envelope'],
                      'projection': inf.get('projection')},
                     ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
