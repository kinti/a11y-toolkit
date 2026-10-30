#!/usr/bin/env python3
"""Tests del modo WCAG-EM 2.0 (a11ywcgem): plan válido → agregado honesto
de packs por muestra, con sello raíz sobre los sellos de los packs."""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a11y_toolkit import a11ywcagem  # noqa: E402
from a11y_toolkit.a11yevidence import build_pack  # noqa: E402

FAILS = []


def check(name, cond, detail=''):
    print(('  OK ' if cond else '  FAIL ') + name + (f' — {detail}' if detail and not cond else ''))
    if not cond:
        FAILS.append(name)


def _report(con_criterio=None):
    """Informe estático mínimo; con_criterio añade un finding X.Y.Z high."""
    findings = [] if not con_criterio else [
        {'severity': 'high', 'criterion': f'{con_criterio} Something', 'signal': 'img_no_alt',
         'issue': 'x', 'remediation': 'y', 'examples': []}]
    return {'url': 'https://example.com', 'score': 90, 'mode': 'static',
            'findings': findings, 'summary': {'high': 1 if con_criterio else 0, 'medium': 0, 'low': 0}}


def _pack(marca):
    return build_pack([_report('1.1.1' if marca == 'falla' else None)])


PLAN = {
    'product': {'name': 'Acme Site', 'url': 'https://acme.example',
                'scope': 'whole product incl. checkout'},
    'conformance_target': 'WCAG 2.2 AA',
    'support_baseline': ['NVDA + Chrome', 'VoiceOver + Safari'],
    'sample': [
        {'id': 'home', 'url': 'https://acme.example/', 'type': 'structured',
         'why': 'common view'},
        {'id': 'checkout', 'url': 'https://acme.example/checkout', 'type': 'process',
         'why': 'complete process'},
    ],
}


def main():
    print('== 1. Validación del plan (hostil incluido)')
    ok, err = a11ywcagem.validate_plan(PLAN)
    check('plan válido pasa', ok, err)
    for name, plan in [
        ('sin product', {k: v for k, v in PLAN.items() if k != 'product'}),
        ('sin sample', {k: v for k, v in PLAN.items() if k != 'sample'}),
        ('sample vacía', {**PLAN, 'sample': []}),
        ('muestra sin id', {**PLAN, 'sample': [{'url': 'x', 'type': 'structured'}]}),
        ('muestra con type inventado', {**PLAN, 'sample': [{'id': 'x', 'url': 'y', 'type': 'whatever'}]}),
    ]:
        ok, err = a11ywcagem.validate_plan(plan)
        check(f'rechaza: {name}', not ok, err)

    print('== 2. Agregado por criterio (el peor estado gana, honesto)')
    p_falla, p_limpia = _pack('falla'), _pack('limpia')
    informe = a11ywcagem.aggregate(PLAN, [p_falla, p_limpia])
    estados = {c['criterion'].split(' ')[0]: c['status'] for c in informe['criteria']}
    check('1.1.1 falla en una muestra → fail en el agregado',
          estados.get('1.1.1') == 'automated-fail')
    check('55 criterios en la matriz', len(informe['criteria']) == 55)
    check('no afirma conformidad: sin campo pass/conformant',
          not any(k in json.dumps(informe).lower() for k in ('"conformant"', '"passed"')))
    check('traza WCAG-EM: pasos del estándar referenciados',
          'wcag_em' in informe and informe['wcag_em'].get('steps'))

    print('== 3. Sello raíz sobre los sellos de los packs')
    check('root sha256 sobre los pack-sha', len(informe['sha256']) == 64
          and p_falla['sha256'] in informe['packs'][0].get('sha256', ''))
    roto = json.loads(json.dumps(informe))
    roto['criteria'][0]['status'] = 'agent-verified'
    check('mutar el informe rompe su sello', a11ywcagem.verify_report(roto)[0] is False)
    check('informe intacto verifica', a11ywcagem.verify_report(informe)[0] is True)

    print('== 4. CLI end-to-end (plan + packs → informe.json)')
    with tempfile.TemporaryDirectory() as d:
        pp, pk1, pk2, out = [os.path.join(d, n) for n in ('plan.json', 'p1.json', 'p2.json', 'inf.json')]
        json.dump(PLAN, open(pp, 'w'))
        json.dump(p_falla, open(pk1, 'w'))
        json.dump(p_limpia, open(pk2, 'w'))
        r = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y', 'wcagem',
                            '--plan', pp, '--packs', pk1, pk2, '-o', out],
                           capture_output=True, text=True, timeout=120)
        inf = json.load(open(out)) if os.path.exists(out) else {}
        check('exit 0 y informe escrito', r.returncode == 0 and inf, r.stderr[-200:])
        check('el CLI imprime el sello raíz', informe['sha256'][:12] in r.stdout
              or inf.get('sha256', '').startswith(informe['sha256'][:8]))

    print(f"\n{'ALL OK' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
