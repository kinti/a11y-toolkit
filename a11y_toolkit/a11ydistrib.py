#!/usr/bin/env python3
"""a11y_distrib — distributional aggregation (the HEGM translation).

Cross-industry translation: VK AI's HEGM (Hierarchical Exponential-Gaussian
Mixtures, ICDM 2026, arXiv 2608.23356) models the FULL distribution instead
of the mean because watch-time data is zero-inflated and long-tailed — the
mean lies in silence. Per-page accessibility numbers have exactly that
shape: most sampled pages are clean, a few are catastrophic. This module is
the statistics layer of WCAG-EM aggregation:

  - prevalence with a Wilson score interval (closed form, small-n honest)
  - per-page effort modeled as a zero-inflated mixture — a declared point
    mass at exactly zero (pages with nothing pending) plus an exponential
    tail and a gaussian body over the positives, fitted by pure-Python EM
    with a DECLARED init: deterministic, reproducible
  - HEGM's own failure catalog imported as fit VALIDATIONS: a dead
    component, a collapsed variance, a single distinct value — a fit that
    trips any of them never publishes a fitted interval; the rejection and
    the fallback are declared in the output, never hidden. A bad fit is
    data, not an embarrassment to bury.
  - totals and site projections via a seeded percentile bootstrap (B and
    seed declared in the output)
  - effort minutes are a RANGE per criterion everywhere in the pack, so the
    inference runs on both bands and publishes the OUTER ENVELOPE — a point
    estimate that hid the range would be the exact lie this module exists
    to avoid.

Statistics, never conformance: everything here is inference over the
SAMPLE. No output of this module is a conformance claim; the human still
owns the verdict (zero-claims rule, same as the pack).
"""

import math
import random

# z two-sided 95% (declared constant — no tables, no scipy)
_Z975 = 1.959963984540054

# init y validaciones DECLARADAS (el catálogo de modos de fallo de HEGM,
# traducido a reglas que este módulo se aplica a sí mismo)
_INIT_SIGMA_FLOOR = 1.0     # minutos: un único valor distinto no arranca colapsado
_MIN_ABOVE_ZERO = 4          # menos de 4 positivos: 4 parámetros no se sostienen
_MIN_WEIGHT = 0.02          # peso < 2% = componente muerto
_MIN_SIGMA_RATIO = 0.01     # σ < 1% del rango observado = varianza colapsada
_MAX_ITER = 200
_TOL = 1e-9
_B_DEFAULT = 2000

_NOTE = {
    'es': ('Estadística sobre la muestra, nunca conformidad: los intervalos '
           'describen lo que la muestra permite afirmar, no lo que el sitio '
           'es. Los minutos son un rango por criterio: la inferencia corre '
           'sobre ambas bandas y publica el envolvente exterior (declarado). '
           'Un ajuste que no pasa las validaciones se declara y cae al '
           'bootstrap; jamás se publica un intervalo de un ajuste roto.'),
    'en': ('Statistics over the sample, never conformance: the intervals '
           'describe what the sample supports, not what the site is. Minutes '
           'are a range per criterion: the inference runs on both bands and '
           'publishes the outer envelope (declared). A fit that fails its '
           'validations is declared and falls back to the bootstrap; an '
           'interval from a broken fit is never published.'),
}


def wilson_interval(k, n, z=_Z975):
    """Wilson score interval for k successes of n (closed form, deterministic;
    honest at small n where the naive p±z rule goes below 0 or above 1).
    k outside [0, n] is a caller lie and fails LOUD, never clamped silent."""
    if n <= 0:
        return None
    if k < 0 or k > n:
        raise ValueError('k=%s outside [0, n=%s]: a proportion cannot' % (k, n))
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def _dens_exp(lam, x):
    return lam * math.exp(-lam * x) if lam > 0 else 0.0


def _dens_gauss(mu, sigma, x):
    if sigma <= 0:
        return 0.0
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))


def fit_mixture(values):
    """Mezcla cero-inflada (δ0 en el cero exacto + Exp + Gauss sobre los
    positivos) por EM determinista. NUNCA lanza: un ajuste que no se sostiene
    se devuelve con sus validaciones en rojo — es un resultado."""
    n = len(values)
    zeros = sum(1 for v in values if v == 0)
    pos = [v for v in values if v > 0]
    out = {'model': 'zero-inflated exponential+gaussian EM',
           'init': 'declared (pi_zero = zeros/n, w = 0.5, lam = 1/mean, '
                   'sigma floored at 1.0 min)',
           'sample': n, 'zeros': zeros, 'positives': len(pos),
           'pi_zero': round(zeros / n, 4) if n else 1.0,
           'max_iter': _MAX_ITER, 'tol': _TOL,
           'validations': {}, 'ok': False, 'rejections': []}
    if not pos:
        out['rejections'].append('no positive values: the zero mass is the '
                                 'whole sample (nothing to fit, honestly)')
    elif len(set(pos)) < 2:
        out['rejections'].append('single distinct positive value: variance '
                                 'collapses by construction')
    elif len(pos) < _MIN_ABOVE_ZERO:
        out['rejections'].append('fewer than %d positive values: four free '
                                 'parameters do not stand on less' % _MIN_ABOVE_ZERO)
    if out['rejections']:
        out['validations'] = {'dead_component': None, 'variance_collapse': None,
                              'single_distinct_value': len(set(pos)) < 2 if pos else None}
        return out

    mean = sum(pos) / len(pos)
    var = sum((v - mean) ** 2 for v in pos) / len(pos)
    w = 0.5
    lam = 1.0 / mean
    mu = mean
    sigma = max(math.sqrt(var), _INIT_SIGMA_FLOOR)
    iterations = 0
    stable = False
    zero_density = False
    prev_ll = None
    for _ in range(_MAX_ITER):
        iterations += 1
        # E-step sobre los positivos (los ceros exactos son masa puntual)
        r_e, ll = [], 0.0
        for x in pos:
            de = w * _dens_exp(lam, x)
            dg = (1 - w) * _dens_gauss(mu, sigma, x)
            tot = de + dg
            if tot <= 0:
                # underflow: densidad CERO bajo ambos componentes — otro modo
                # de fallo del catálogo HEGM, se declara (nunca -1e300 mudo)
                zero_density = True
                tot = 1e-300
            r_e.append(de / tot)
            ll += math.log(tot)
        if prev_ll is not None and abs(ll - prev_ll) < _TOL:
            stable = True
            break
        prev_ll = ll
        # M-step
        se, sg = sum(r_e), len(pos) - sum(r_e)
        w = se / len(pos)
        if se > 0:
            lam = se / sum(r * x for r, x in zip(r_e, pos))
        if sg > 0:
            mu = sum((1 - r) * x for r, x in zip(r_e, pos)) / sg
            sigma = math.sqrt(max(
                1e-12,
                sum((1 - r) * (x - mu) ** 2 for r, x in zip(r_e, pos)) / sg))
    rng_pos = max(pos) - min(pos)
    dead = w < _MIN_WEIGHT or w > 1 - _MIN_WEIGHT
    collapse = sigma < _MIN_SIGMA_RATIO * rng_pos
    out.update({'w_exp': round(w, 4), 'w_gauss': round(1 - w, 4),
                'lambda': round(lam, 6), 'mu': round(mu, 4),
                'sigma': round(sigma, 4),
                'iterations': iterations, 'converge': stable,
                'validations': {'dead_component': dead,
                                'variance_collapse': collapse,
                                'single_distinct_value': False}})
    if dead:
        out['rejections'].append('dead component: mixture weight %.4f outside '
                                 '[%.2f, %.2f]' % (w, _MIN_WEIGHT, 1 - _MIN_WEIGHT))
    if collapse:
        out['rejections'].append('collapsed variance: sigma %.4f < 1%% of the '
                                 'observed range %.4f' % (sigma, rng_pos))
    if zero_density:
        out['rejections'].append('density underflow: a positive point has zero '
                                 'likelihood under both components')
    if not stable:
        out['rejections'].append('EM did not converge in %d iterations' % _MAX_ITER)
    out['ok'] = not out['rejections']
    return out


def bootstrap_mean_ci(values, b=_B_DEFAULT, seed=7,
                      lo_pct=2.5, hi_pct=97.5):
    """Percentile bootstrap de la MEDIA (semilla y B declarados → el mismo
    intervalo siempre). Vacío → None; constante → [c, c] (honesto)."""
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    stats = sorted(sum(rng.choices(values, k=n)) / n for _ in range(b))
    i_lo = min(b - 1, max(0, int(b * lo_pct / 100)))
    i_hi = min(b - 1, max(0, int(b * hi_pct / 100)))
    return [round(stats[i_lo], 2), round(stats[i_hi], 2)]


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _median(xs):
    if not xs:
        return 0.0
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def effort_inference(per_page_minutes_lo, per_page_minutes_hi, seed=7,
                     projected_pages=None, lang='en'):
    """Bandas de minutos por página (la lo y la hi del rango por criterio,
    sumadas por página) → bloque de inferencia completo para el reporte
    WCAG-EM. Envolvente exterior de ambas bandas; jamás un punto oculto."""
    if not per_page_minutes_lo:
        raise ValueError('empty sample: nothing to infer over')
    lo_band = [float(v) for v in per_page_minutes_lo]
    hi_band = [float(v) for v in per_page_minutes_hi]
    if len(lo_band) != len(hi_band):
        raise ValueError('lo/hi bands must have one value per sampled page')
    if projected_pages is not None and int(projected_pages) < 1:
        raise ValueError('projected_pages must be a positive integer')
    n = len(lo_band)
    mid = [(a + b) / 2 for a, b in zip(lo_band, hi_band)]
    block = {
        'format': 'a11y-effort-inference/1',
        'sample_pages': n,
        'zero_pages': sum(1 for v in mid if v == 0),
        'observed_total_minutes': [round(sum(lo_band), 1), round(sum(hi_band), 1)],
        'per_page_minutes': {
            'mean': [round(_mean(lo_band), 2), round(_mean(hi_band), 2)],
            'median': [round(_median(lo_band), 2), round(_median(hi_band), 2)],
        },
        'seed': seed, 'bootstrap_b': _B_DEFAULT,
        'ci95_method': 'percentile bootstrap over pages, outer envelope of '
                       'the lo/hi minute bands',
    }
    for name, band in (('lo', lo_band), ('hi', hi_band)):
        block['fit_%s' % name] = fit_mixture(band)
        block['ci95_mean_%s' % name] = bootstrap_mean_ci(band, seed=seed)
    bounds_lo = [block['ci95_mean_lo'][0], block['ci95_mean_hi'][0]]
    bounds_hi = [block['ci95_mean_lo'][1], block['ci95_mean_hi'][1]]
    block['ci95_mean_envelope'] = [round(min(bounds_lo), 2), round(max(bounds_hi), 2)]
    if projected_pages:
        npages = int(projected_pages)
        block['projection'] = {
            'pages': npages,
            'declared_by': 'plan.estimated_pages (evaluator figure, not a '
                           'measurement)',
            'expected_total_minutes': [round(npages * _mean(lo_band), 1),
                                       round(npages * _mean(hi_band), 1)],
            'ci95_minutes': [round(npages * min(bounds_lo), 1),
                             round(npages * max(bounds_hi), 1)],
        }
    block['mixture_used'] = bool(block['fit_lo']['ok'] and block['fit_hi']['ok'])
    block['note'] = _NOTE['es' if lang == 'es' else 'en']
    return block
