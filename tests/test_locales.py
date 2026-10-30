#!/usr/bin/env python3
"""Locale packs — validación mecánica de contribuciones.

Un idioma nuevo (locales/xx.json) se revisa SOLO con este test:
  1. mismas CLAVES que en.json (anidado, namespace a namespace)
  2. mismos PLACEHOLDERS ({n}, {ej}…) en cada mensaje
  3. _meta completa: native, dir válida, plural evaluable para n=0..5
  4. sin valores vacíos (traducción a medias → mejor borrar el locale)
El fallback a inglés cubre claves ausentes en runtime, pero el pin exige
completitud para MERGE: nada a medias entra por un PR.
"""

import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
sys.path.insert(0, ROOT)

from a11y_toolkit import a11yi18n  # noqa: E402

DIR = os.path.join(ROOT, 'a11y_toolkit', 'locales')
EN = json.load(open(os.path.join(DIR, 'en.json'), encoding='utf-8'))
ARGS = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')


def _claves(anidado, prefijo=''):
    """Rutas de claves de un dict anidado: {'a': {'b': 1}} → {'a.b'}."""
    salida = set()
    for k, v in anidado.items():
        ruta = f'{prefijo}{k}'
        if isinstance(v, dict):
            salida |= _claves(v, ruta + '.')
        else:
            salida.add(ruta)
    return salida


def _valores(anidado, prefijo=''):
    for k, v in anidado.items():
        ruta = f'{prefijo}{k}'
        if isinstance(v, dict):
            yield from _valores(v, ruta + '.')
        else:
            yield ruta, v


fallos = []
locales = [f for f in sorted(os.listdir(DIR))
           if f.endswith('.json') and not f.startswith('_') and f != 'en.json']

for nombre in locales + ['en.json']:
    lang = nombre[:-5]
    data = json.load(open(os.path.join(DIR, nombre), encoding='utf-8'))

    # 1. mismas claves que en (excepto _meta)
    faltan = _claves({k: v for k, v in EN.items() if k != '_meta'}) - \
             _claves({k: v for k, v in data.items() if k != '_meta'})
    sobran = _claves({k: v for k, v in data.items() if k != '_meta'}) - \
             _claves({k: v for k, v in EN.items() if k != '_meta'})
    if faltan:
        fallos.append(f'{lang}: faltan claves ({len(faltan)}): {sorted(faltan)[:4]}')
    if sobran:
        fallos.append(f'{lang}: claves desconocidas: {sorted(sobran)[:4]}')

    # 2. mismos placeholders por mensaje
    if not faltan and not sobran:
        en_plano = dict(_valores({k: v for k, v in EN.items() if k != '_meta'}))
        for ruta, valor in _valores({k: v for k, v in data.items() if k != '_meta'}):
            esperados = set(ARGS.findall(str(en_plano[ruta])))
            reales = set(ARGS.findall(str(valor)))
            if esperados != reales:
                fallos.append(f'{lang}:{ruta} placeholders {sorted(reales)} ≠ en {sorted(esperados)}')

    # 3. _meta completo y plural evaluable (por la vía SEGURA: sin eval —
    # un locale pack es dato, y el dato jamás se convierte en código)
    meta = data.get('_meta', {})
    for campo in ('native', 'plural', 'dir'):
        if not meta.get(campo):
            fallos.append(f'{lang}: _meta.{campo} ausente')
    if meta.get('dir') not in ('ltr', 'rtl'):
        fallos.append(f'{lang}: _meta.dir debe ser ltr/rtl')
    regla = meta.get('plural', '')
    if regla:
        for n in range(6):
            try:
                a11yi18n.eval_plural_rule(regla, n)
            except ValueError as e:
                fallos.append(f'{lang}: plural fuera de la gramática CLDR ({e})')
                break

    # 4. sin vacíos (solo locales reales, no el template)
    if lang != 'en':
        vacios = [ruta for ruta, v in _valores(data) if ruta.split('.', 1)[-1] != '_meta' and str(v).strip() == '']
        if vacios:
            fallos.append(f'{lang}: {len(vacios)} valores vacíos: {vacios[:3]}')

assert not fallos, '\n'.join(fallos)

# el loader ve todos los locales del directorio
assert set(a11yi18n.available()) >= {'en', 'es'}
assert a11yi18n.plural_category('en', 1) == 'one' and a11yi18n.plural_category('en', 2) == 'other'

# el evaluador plural es una lista blanca AST, NO eval: payloads hostiles en
# un _meta.plural (o en un use_overlay de un tercero) se RECHAZAN, jamás se
# ejecutan — pin del hardening de supply-chain (Socket: "Package uses eval")
for hostil in ('__import__("os").system("x")', 'open("/etc/passwd")',
               'n.__class__', 'exec("1")', '().__class__', 'lambda: 1',
               'n if n else 1', '[1, 2][0]', '5', 'n & 1', 'x'):
    try:
        a11yi18n.eval_plural_rule(hostil, 1)
        raise SystemExit('payload debía RECHAZARSE: ' + hostil)
    except ValueError:
        pass
# la gramática legítima completa sigue funcionando
assert a11yi18n.eval_plural_rule('n != 1', 2)
assert a11yi18n.eval_plural_rule('n % 10 == 1 and n % 100 != 11', 21)
assert not a11yi18n.eval_plural_rule('n % 10 == 1 and n % 100 != 11', 11)
assert a11yi18n.eval_plural_rule('n == 0 or n != 2', 0)
assert a11yi18n.eval_plural_rule('1 < n < 5', 3)
# cero eval() en TODO el paquete: el pin que impide que vuelva
import subprocess as _sp
_quedan = _sp.run(['grep', '-rn', 'eval(', os.path.join(ROOT, 'a11y_toolkit'),
                   '--include=*.py'], capture_output=True, text=True).stdout.splitlines()
_fuera = [l for l in _quedan if 'eval_plural' not in l]
assert not _fuera, 'eval() fuera de la lista blanca: %r' % _fuera[:3]
print('pin anti-eval: payloads hostiles rechazados, gramática CLDR intacta, sin eval() en el paquete ✓')

print(f'test_locales.py OK — {len(locales) + 1} locales validados (claves, placeholders, plural, completitud)')
