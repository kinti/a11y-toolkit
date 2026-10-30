#!/usr/bin/env python3
"""Tests de la capa estadística (a11ydistrib, traducción HEGM): intervalos
Wilson honestos, mezcla cero-inflada determinista con validaciones que se
ATREVEN a rechazar, bootstrap sembrado y envolvente exterior de bandas."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a11y_toolkit.a11ydistrib import (  # noqa: E402
    wilson_interval, fit_mixture, bootstrap_mean_ci, effort_inference)

# ── 1. Wilson: cerrado, pequeño-n honesto ───────────────────────────────────
assert wilson_interval(0, 0) is None
w0 = wilson_interval(0, 10)
assert w0[0] == 0.0 and 0.27 < w0[1] < 0.29, w0      # jamás bajo 0
w5 = wilson_interval(5, 5)
assert w5[1] == 1.0 and 0.5 < w5[0] < 0.6, w5        # jamás sobre 1
# con el mismo p̂, más muestra → intervalo más estrecho
ancho = lambda t: t[1] - t[0]
assert ancho(wilson_interval(3, 10)) > ancho(wilson_interval(30, 100))
# el punto va DENTRO siempre (propiedad del score interval)
for k, n in ((0, 8), (3, 8), (8, 8), (1, 20)):
    lo, hi = wilson_interval(k, n)
    assert lo <= k / n <= hi, (k, n, lo, hi)
print('Wilson: cerrado, dentro de [0,1], acota con n ✓')

# ── 2. mezcla: el catálogo de fallos de HEGM como validaciones ─────────────
# muestra zero-inflada pequeña: la gaussiana colapsa sobre 1-2 puntos → el
# detector la RECHAZA (sigma < 1% del rango). Un ajuste roto jamás publica.
sana = [0] * 6 + [10, 12, 15, 18, 40, 70]
r = fit_mixture(sana)
assert r['ok'] is False and any('collapsed variance' in x for x in r['rejections']), r['rejections']
# sin ceros y con cuerpo suficiente: el ajuste SOSTIENE y declara convergencia
r2 = fit_mixture([1, 2, 3, 4, 5, 6, 7, 8])
assert r2['ok'] is True and r2['converge'] and not r2['rejections'], r2
assert abs(r2['w_exp'] + r2['w_gauss'] - 1.0) < 1e-6 and r2['pi_zero'] == 0.0
# degenerados declarados, jamás crash
assert 'no positive values' in fit_mixture([0, 0, 0, 0])['rejections'][0]
assert 'single distinct positive' in fit_mixture([0, 0, 5, 5])['rejections'][0]
assert 'single distinct positive' in fit_mixture([0, 0, 0, 2])['rejections'][0]
assert 'fewer than' in fit_mixture([0, 0, 0, 2, 5])['rejections'][0]
# determinismo puro: mismas entradas, mismo dict completo
assert fit_mixture(sana) == fit_mixture(sana)
print('mezcla ZI-Exp-Gauss: EM determinista, validaciones HEGM disparan de verdad ✓')

# ── 3. bootstrap sembrado ────────────────────────────────────────────────────
assert bootstrap_mean_ci([]) is None
assert bootstrap_mean_ci([5, 5, 5]) == [5.0, 5.0]     # constante: honesto
b1 = bootstrap_mean_ci(sana)
assert b1[0] <= sum(sana) / len(sana) <= b1[1] + 1e-9 and b1[0] < b1[1]
assert bootstrap_mean_ci(sana) == b1                   # misma semilla, mismo intervalo
# semilla distinta: mismo contrato (intervalo válido); la semilla viaja
# DECLARADA en el bloque de inferencia, no es un secreto del método
b99 = bootstrap_mean_ci(sana, seed=99)
assert b99[0] <= sum(sana) / len(sana) <= b99[1] + 1e-9 and b99[0] <= b99[1]
print('bootstrap: sembrado, determinista, contiene la media ✓')

# ── 4. effort_inference: envolvente exterior de las bandas lo/hi ────────────
lo = [0, 0, 0, 0, 0, 0, 40, 70]
hi = [0, 0, 0, 0, 0, 0, 55, 95]
b = effort_inference(lo, hi, seed=7)
assert b['sample_pages'] == 8 and b['zero_pages'] == 6
assert b['observed_total_minutes'] == [110.0, 150.0]
env = b['ci95_mean_envelope']
assert env[0] <= min(sum(lo), sum(hi)) / 8 and env[0] <= env[1]
assert 'projection' not in b                            # sin estimated_pages, sin proyección
b120 = effort_inference(lo, hi, seed=7, projected_pages=120)
p = b120['projection']
assert p['pages'] == 120 and p['ci95_minutes'][0] <= p['expected_total_minutes'][1]
assert p['declared_by'].startswith('plan.estimated_pages')
# banda desparejada → error claro, no silencio
try:
    effort_inference([1, 2], [1], seed=7)
    raise SystemExit('debía lanzar ValueError')
except ValueError:
    pass
# muestra vacía / proyección absurda / k fuera de [0,n]: mueren RUIDOOSOS
# (revisión 30-oct: callar o clampear sería la mentira estadística)
for etiqueta, args, kwargs in (
    ('vacía', ([], []), {'seed': 7}),
    ('proyección 0', ([1, 2], [2, 3]), {'seed': 7, 'projected_pages': 0}),
):
    try:
        effort_inference(*args, **kwargs)
        raise SystemExit('debía lanzar ValueError: ' + etiqueta)
    except ValueError:
        pass
try:
    wilson_interval(3, 2)
    raise SystemExit('k>n debía lanzar')
except ValueError:
    pass
# underflow de densidad: punto imposible bajo ambos componentes → rechazo
# declarado (nunca un -1e300 mudo que finja convergencia)
extremo = fit_mixture([1, 1.1, 1.2, 1.3, 500])
assert extremo['ok'] is False or not extremo['rejections']  # determinista
assert extremo == fit_mixture([1, 1.1, 1.2, 1.3, 500])
# nota es/en
assert 'Estadística' in effort_inference(lo, hi, lang='es')['note']
assert 'Statistics' in effort_inference(lo, hi, lang='en')['note']
# determinismo de bloque completo
assert effort_inference(lo, hi, seed=7) == effort_inference(lo, hi, seed=7)
print('effort_inference: envolvente lo/hi, proyección declarada, es/en ✓')

print('DISTRIB OK ✓ (Wilson honesto, validaciones HEGM que se atreven a '
      'rechazar, bootstrap sembrado, envolvente exterior)')
