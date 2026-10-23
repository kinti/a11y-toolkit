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

    # 3. _meta completo y plural evaluable
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
                res = eval(regla, {'__builtins__': {}}, {'n': n})  # noqa: S307
                if not isinstance(res, bool):
                    fallos.append(f'{lang}: plural no devuelve bool con n={n}')
                    break
            except Exception as e:
                fallos.append(f'{lang}: plural no evaluable ({e})')
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

print(f'test_locales.py OK — {len(locales) + 1} locales validados (claves, placeholders, plural, completitud)')
