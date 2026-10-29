#!/usr/bin/env python3
"""a11y_mutants — el examen sellado del motor (mutation testing WCAG).

Lo que este test clava (nació con el módulo):
  1. DETERMINISMO: misma semilla → mismo examen (html idéntico).
  2. SEMILLA NUEVA → examen distinto: nadie memoriza el banco.
  3. PLACEBOS a cero hallazgos: la página limpia está limpia de verdad
     (y un falso positivo del motor queda expuesto como tal).
  4. COBERTURA: n suficiente recorre los 18 operadores.
  5. KILL RATE 100%: el motor caza TODO lo que el banco inyecta — una
     regresión de detección en cualquiera de las señales tiñe la suite.
  6. INTEGRIDAD: cada operador apunta a una señal del mapa señal→criterio
     (el banco se deriva del motor, no vive paralelo a él).
  7. BORDE: n=0 no divide por cero; la página no crashea al motor.
  8. CLI: el subcomando `mutants` ejecuta de verdad (vía subprocess).
"""

import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
sys.path.insert(0, ROOT)

from a11y_toolkit import a11ymutants  # noqa: E402
from a11y_toolkit.a11yaudit import audit_html  # noqa: E402
from a11y_toolkit.a11ycrit import _SIGNAL_CRIT  # noqa: E402

# 1. determinismo
a = a11ymutants.generate(42, 6)
b = a11ymutants.generate(42, 6)
assert [m['html'] for m in a['mutants']] == [m['html'] for m in b['mutants']], \
    'misma semilla, examen distinto: el banco no es determinista'
assert [m['sealed'] for m in a['mutants']] == [m['sealed'] for m in b['mutants']]
print('1. determinismo: misma semilla → mismo examen ✓')

# 2. semilla nueva → página distinta (el examen no se memoriza)
c = a11ymutants.generate(43, 6)
assert [m['html'] for m in a['mutants']] != [m['html'] for m in c['mutants']], \
    'semillas distintas producen la misma página'
print('2. variación por semilla ✓')

# 3. placebos a cero hallazgos (la plantilla limpia es limpia DE VERDAD)
revisados = 0
for seed in (1, 2, 3):
    for p in a11ymutants.generate(seed, 6)['control_pages']:
        rep = audit_html(p['html'], lang='en')
        assert not rep.get('findings'), \
            f'placebo sucio ({p["id"]}): {[(h["signal"], h["issue"][:60]) for h in rep["findings"]]}'
        revisados += 1
print(f'3. placebos: {revisados} páginas limpias, cero hallazgos ✓')

# 4. cobertura de operadores
e = a11ymutants.generate(7, 60)
vistos = {m['sealed']['operator'] for m in e['mutants']}
assert vistos == {op['op'] for op in a11ymutants.OPERATORS}, \
    f'60 mutantes no cubren todos los operadores: faltan {sorted({op["op"] for op in a11ymutants.OPERATORS} - vistos)}'
print(f'4. cobertura: 60 mutantes recorren los {len(a11ymutants.OPERATORS)} operadores ✓')

# 5. kill rate 100% en varias semillas (regresión de detección = suite roja)
for seed in (7, 42, 99):
    rep = a11ymutants.run_exam(seed, 18)
    assert rep['kill_rate'] == 1.0, \
        f'seed {seed}: mutantes sin cazar: {rep["missed_detail"]}'
    assert rep['false_positives'] == [], \
        f'seed {seed}: falsos positivos en placebos: {rep["false_positives"]}'
print('5. kill rate 100% (seeds 7/42/99) + cero falsos positivos ✓')

# 6. integridad: el banco se deriva del mapa señal→criterio del motor
for op in a11ymutants.OPERATORS:
    assert op['signal'] in _SIGNAL_CRIT, \
        f'{op["op"]} apunta a la señal {op["signal"]}, ausente del mapa señal→criterio'
    assert op['criterion'] == _SIGNAL_CRIT[op['signal']], \
        f'{op["op"]}: criterio {op["criterion"]} ≠ mapa ({_SIGNAL_CRIT[op["signal"]]})'
print(f'6. integridad: {len(a11ymutants.OPERATORS)} operadores derivados del mapa señal→criterio ✓')

# 7. borde: n=0 no divide por cero
rep0 = a11ymutants.run_exam(5, 0)
assert rep0['kill_rate'] is None and rep0['mutants'] == 0 and rep0['control_pages'] >= 1
assert isinstance(audit_html(a11ymutants.generate(5, 3)['mutants'][0]['html']), dict)
print('7. borde n=0 sin división por cero ✓')

# 8. CLI por subprocess (la vía pública real)
r = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y', 'mutants',
                    '--seed', '3', '--n', '9'], cwd=ROOT, capture_output=True,
                   text=True, timeout=180)
assert r.returncode == 0, r.stderr[-400:]
out = json.loads(r.stdout)
assert out['kill_rate'] == 1.0 and out['mode'] == 'mutant-exam'
print('8. CLI `a11ytoolkit mutants` ejecuta y puntúa de verdad ✓')

# 9. el examen acepta evaluadores EXTERNOS: firma (html) o (html, lang=)
# — medir a otros (axe, un juez-LLM) es el punto del módulo (revisión externa)
rep_ext = a11ymutants.run_exam(7, 6, engine=lambda html: audit_html(html))
assert rep_ext['kill_rate'] == 1.0, rep_ext['missed_detail']
rep_lang = a11ymutants.run_exam(7, 6, engine=lambda html, lang='en': audit_html(html, lang=lang))
assert rep_lang['kill_rate'] == 1.0
# nota bilingüe
assert a11ymutants.run_exam(7, 2, lang='es')['note'] != a11ymutants.run_exam(7, 2)['note']
print('9. evaluador externo (con o sin lang=) y nota es/en ✓')

print(f'MUTANTES OK ✓ (18 operadores de {len({op["criterion"] for op in a11ymutants.OPERATORS})} '
      'criterios, examen sellado, placebos, kill rate clavado a 1.0)')
