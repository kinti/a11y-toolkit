#!/usr/bin/env python3
"""a11y_route — el router que hace O(1) elegir entre 33 tools.

Lo que este test clava (nació con la tool):
  1. INTEGRIDAD: cada tool referenciada por las rutas EXISTE en server.TOOLS
     (o es un prompt declarado); un route que apunte al vacío es un link roto.
  2. DETERMINISMO: mismo goal → misma salida (es un índice, no un LLM).
  3. BILINGÜE: mismo goal responde en es y en en con whys del idioma.
  4. FALLBACK honesto: goal sin coincidencias → ruta 'start', nunca vacío.
  5. HOSTIL: goal vacío/basura no crashea.
  6. INVOKE MCP: el contrato del server entrega la forma completa.
"""

import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
sys.path.insert(0, ROOT)

from a11y_toolkit.a11yroute import route, ROUTES  # noqa: E402
from a11y_toolkit import server  # noqa: E402
from a11y_toolkit.a11y import SUBCOMMANDS  # noqa: E402

# 1. integridad: tools MCP, prompts o subcomandos CLI (prefijo cli:)
_tools = {t['name'] for t in server.TOOLS}
_prompts = {p['name'] for p in server._PROMPTS}
for r in ROUTES:
    for tool, _es, _en in r['tools']:
        if tool.startswith('cli:'):
            assert tool[4:] in SUBCOMMANDS, f'{r["id"]} referencia CLI {tool} inexistente'
        else:
            assert tool in _tools or tool in _prompts, f'{r["id"]} referencia {tool} que no existe'
    for p in r['prompts']:
        assert p in _prompts, f'{r["id"]} referencia el prompt {p} que no existe'
assert next(r for r in ROUTES if r['id'] == 'start')['patterns'] == [], 'start debe ser el fallback sin patrones'
print(f'1. integridad: {len(ROUTES)} rutas, todas las tools/prompts referenciados existen ✓')

# 2. determinismo
a = route('gate my PR before merging', 'en')
b = route('gate my PR before merging', 'en')
assert a == b, 'el router no es determinista'
print('2. determinismo ✓')

# 3. bilingüe: mismo goal, whys del idioma pedido
es = route('arregla el contraste del hero', 'es')
en = route('fix the contrast of my hero', 'en')
assert es['route'] == en['route'] == 'contrast'
assert es['steps'][0]['why'] != en['steps'][0]['why']
assert en['steps'][0]['tool'] == 'a11y_contrast_pair' and es['steps'][0]['tool'] == 'a11y_contrast_pair'
print('3. bilingüe es/en ✓')

# 4. fallback honesto
fb = route('zzzqqq www', 'en')
assert fb['route'] == 'start' and fb['steps'] and fb['note']
assert fb['steps'][0]['tool'] == 'a11y_audit_url', 'el fallback empieza por el pase exprés'
print('4. fallback honesto → start ✓')

# 5. hostil: vacío, solo espacios, unicode raro
for goal in ('', '   ', '🦄🦄', 'a' * 500):
    r = route(goal, 'es')
    assert isinstance(r, dict) and r['steps'], f'crasheó o vació con: {goal!r}'
print('5. hostil cubierto ✓')

# 6. invoke MCP end-to-end
d = json.loads(server.invoke('a11y_route', {'goal': 'quiero una declaración EAA', 'lang': 'es'})['content'][0]['text'])
assert d['route'] == 'statement' and d['steps'][0]['tool'] == 'a11y_audit_url'
assert d['prompts'] == ['declaration-eaa']
# los GOALS delREADME también rutear
for goal, esperada in (('what does 2.4.7 mean', 'criterion'),
                       ('revisar este pdf', 'pdf'),
                       ('travel de un usuario ciego', 'blindfold'),
                       ('regresión antes del deploy', 'deploy'),
                       ('wcag 3', 'wcag3'),
                       ('validación de mi formulario', 'forms')):
    assert route(goal, 'en' if goal[0].isascii() else 'es')['route'] == esperada, goal
print('6. invoke MCP + goals canónicos ✓')

# 7. CLI real
out = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11yroute', '--goal', 'gate my PR'],
                     capture_output=True, text=True, cwd=ROOT, timeout=30)
d2 = json.loads(out.stdout)
assert d2['route'] == 'ci' and d2['cli']
print('7. CLI ✓')

print('ROUTE OK ✓ (17 rutas, índice determinista, es/en, fallback honesto)')
