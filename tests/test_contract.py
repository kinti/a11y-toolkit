#!/usr/bin/env python3
"""Contract tests: every tool's schema, dispatch and real function signature
must agree — mechanically.

Kills two real bug classes from the 2026-10 reviews at the root:
  - dispatch passes a kwarg the function does not accept (a11y_forms
    browser= crash): rule KWARG-IN-SIGNATURE
  - schema declares a parameter the dispatch silently drops (auth_state
    in six rendered tools): rule SCHEMA-REFERENCED

The dispatch source is parsed (not introspected) because that is where the
bugs lived: between the schema dict, the `if nombre ==` block and the
imported function. If this test is green, the three agree."""

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a11y_toolkit import server  # noqa: E402

SRC = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)),
                          ), 'a11y_toolkit', 'server.py'), encoding='utf-8').read()

# parámetros de schema que el dispatch gestiona por otra vía documentada
WHITELIST_SCHEMA_NO_REF = {
    # a11y_diff acepta snapshots inline o paths de fichero: los args se usan
    # dentro del bloque pero vía json.loads(open(...)) sobre a['a']/a['b']
    'a11y_diff': {'a', 'b'},
}


def _bloque_dispatch(nombre):
    """El bloque `if nombre == 'X': ...` hasta el siguiente if/elif de nivel."""
    # límites EXACTOS: siguiente bloque `if nombre ==`/`elif` a 4 espacios,
    # o `def` a columna 0 — nada más corto corta el bloque por accidente
    m = re.search(rf"\n    if nombre == '{nombre}':\n(.*?)(?=\n    (?:if nombre ==|elif )|\ndef |\Z)",
                  SRC, re.S)
    return m.group(1) if m else None


def _args_referidos(bloque):
    return set(re.findall(r"args(?:\.get\(\s*|\[)\s*['\"](\w+)['\"]", bloque))


def _kwargs_por_llamada(bloque):
    """{(fn, kwarg): arg_key} — cada kwarg se atribuye a su PROPIA llamada
    (el call-start más cercano a su izquierda): evita culpar a audit_html_fn
    de los kwargs de audit_site_fn, o a diff_fn de los de snapshot_fn."""
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'(\w+)\(', bloque)]
    out = {}
    for m in re.finditer(r"(\w+)\s*=\s*args(?:\.get\(\s*|\[)\s*['\"](\w+)['\"]", bloque):
        fn = next((name for pos, name in reversed(starts) if pos < m.start()), None)
        out[(fn, m.group(1))] = m.group(2)
    return out


errores = []
for t in server.TOOLS:
    name = t['name']
    props = set(t['inputSchema'].get('properties', {}))
    bloque = _bloque_dispatch(name)
    if bloque is None:
        errores.append(f'{name}: sin bloque de dispatch')
        continue
    refs = _args_referidos(bloque)
    # 1. todo parámetro del schema debe aparecer en el dispatch
    sin_usar = props - refs - WHITELIST_SCHEMA_NO_REF.get(name, set())
    if sin_usar:
        errores.append(f'{name}: schema declara {sorted(sin_usar)} pero el dispatch no lo usa '
                       '(la clase auth_state: aceptado y tirado en silencio)')
    # 2. todo kwarg de la llamada debe existir en la firma real
    for (fn_name, kwarg), argkey in _kwargs_por_llamada(bloque).items():
        if argkey not in props:
            errores.append(f'{name}: dispatch usa {argkey!r} que el schema no declara')
        fn = getattr(server, fn_name, None) if fn_name else None
        if fn is not None and callable(fn) and not fn_name.startswith('_'):
            try:
                sig = inspect.signature(fn)
                if not any(p.kind is inspect.Parameter.VAR_KEYWORD
                           for p in sig.parameters.values()):
                    if kwarg not in sig.parameters:
                        errores.append(f'{name}: {fn_name} recibe {kwarg}=args[{argkey!r}] '
                                       'que su firma no acepta (la clase browser=)')
            except (ValueError, TypeError):
                pass

# 3. forma del inputSchema: claves huérfanas FUERA de properties son
# invisibles para clientes y tests (la clase browser-huérfano, 2026-10)
_CLAVES_VALIDAS = {'type', 'properties', 'required'}
for t in server.TOOLS:
    extra = set(t['inputSchema']) - _CLAVES_VALIDAS
    if extra:
        errores.append(f"{t['name']}: inputSchema con claves huérfanas {sorted(extra)} "
                       '(fuera de properties: ningún cliente las verá)')

if errores:
    print('CONTRATO ROTO —')
    for e in errores:
        print(' ·', e)
    sys.exit(1)
print(f'CONTRATO OK ✓ ({len(server.TOOLS)} tools: schema ↔ dispatch ↔ firma reales)')
