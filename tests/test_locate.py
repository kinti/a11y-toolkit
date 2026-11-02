#!/usr/bin/env python3
"""a11y_locate: name → deterministic route, honest refusal on ambiguity.

The contract: same routes as the auditor (annotate-compatible), confidence
only where earned, ambiguity NEVER silently resolved, no invented matches,
bilingual notes, hostile HTML never crashes."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a11y_toolkit.a11ylocate import locate  # noqa: E402
from a11y_toolkit import server  # noqa: E402

results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(('ok  ' if cond else 'FAIL') + ' ' + name)


HTML = """<html><head><title>T</title></head><body>
<h1>Bienvenidos</h1>
<nav><a href="/x">Ver mas</a></nav>
<div>
  <button id="b1">Enviar</button>
  <button class="sec">Enviar</button>
  <img src="a.png" alt="Logo" id="logo">
  <input type="email" aria-label="Correo electronico">
  <select aria-label="Pais"><option>1</option></select>
  <iframe src="f.html" title="Mapa"></iframe>
  <span role="heading" aria-level="2">Detalles</span>
  <div aria-hidden="true"><button>invisible</button></div>
</div>
</body></html>"""

# ── exact unique match → high + annotate-compatible route ──────────────────
r = locate(HTML, 'Bienvenidos')
check('h1 exact found', r['found'] and not r['ambiguous'])
check('h1 confidence high', r['confidence'] == 'high')
check('h1 route is deterministic', r['selector'] ==
      'html:nth-of-type(1)>body:nth-of-type(1)>h1:nth-of-type(1)')
check('match carries tag/role', r['matches'][0]['tag'] == 'h1'
      and r['matches'][0]['role'] == 'h1')

r = locate(HTML, 'Ver mas')
check('link exact route', r['found'] and r['selector'] and 'a:nth-of-type(1)' in r['selector'])
check('match carries id when present', locate(HTML, 'Logo')['matches'][0]['id'] == 'logo')

# ── ambiguity: two identical buttons → refuse, never pick ──────────────────
r = locate(HTML, 'Enviar')
check('duplicate names → ambiguous', r['found'] and r['ambiguous'])
check('ambiguous has NO selector', r['selector'] is None)
check('ambiguous lists all candidates', r['count'] == 2 and len(r['matches']) == 2)
r2 = locate(HTML, 'Enviar', multiple=True)
check('multiple=true lists all', r2['count'] == 2 and r2['selector'] is None
      and len(r2['matches']) == 2)

# ── no match → honest, bilingual, no invention ─────────────────────────────
r = locate(HTML, 'Inexistente')
check('no match found=False', r['found'] is False and r['matches'] == [])
check('no match note resolves (en)', 'No named element' in r['note'])
r = locate(HTML, 'Inexistente', lang='es')
check('no match note resolves (es)', 'Ningún elemento' in r['note'])
check('empty html honest', locate('', 'X')['found'] is False)
check('empty query honest', locate(HTML, '   ')['found'] is False
      and locate(HTML, '   ')['note'])

# ── partial matches: medium, single → selector, many → ambiguous ───────────
r = locate(HTML, 'log')
check('partial single → medium', r['found'] and r['confidence'] == 'medium'
      and r['selector'] is not None)
r = locate(HTML, 'en')
check('partial many → ambiguous', r['ambiguous'] and r['selector'] is None)

# ── normalization: case + whitespace collapse ───────────────────────────────
check('case/whitespace normalized', locate(HTML, '  BIENVENIDOS  ')['found'])

# ── role filters ────────────────────────────────────────────────────────────
check('role button filter', locate(HTML, 'Enviar', role='button')['count'] == 2)
r = locate(HTML, 'Ver mas', role='link')
check('role link filter', r['found'] and r['count'] == 1)
check('role excludes other roles', locate(HTML, 'Ver mas', role='button')['found'] is False)
r = locate(HTML, 'Correo electronico', role='textbox')
check('email input is textbox (input:kind normalized)', r['found']
      and r['matches'][0]['role'] == 'input:email')
check('select is combobox', locate(HTML, 'Pais', role='combobox')['found'])
check('image alias', locate(HTML, 'Logo', role='image')['found'])
check('h1 via heading alias', locate(HTML, 'Bienvenidos', role='heading')['found'])
check('unknown role honest', locate(HTML, 'Enviar', role='marquee')['found'] is False)

# ── surfaces: images, iframes, role=heading, hidden excluded ────────────────
check('iframe by title', locate(HTML, 'Mapa')['found'])
r = locate(HTML, 'Detalles')
check('role=heading + aria-level indexed', r['found']
      and r['matches'][0]['role'] == 'h2')
check('aria-hidden button NOT indexed', locate(HTML, 'invisible')['found'] is False)

# ── labelledby resolved even when declared AFTER the element ────────────────
LB = ('<html><body><button aria-labelledby="lbl">fallback</button>'
      '<p id="lbl">Confirmar pedido</p></body></html>')
r = locate(LB, 'Confirmar pedido')
check('aria-labelledby resolved post-parse', r['found'])
check('accname order: labelledby beats content', r['found']
      and 'Confirmar pedido' in r['matches'][0]['name'])
ARIA = '<html><body><button aria-label="Guardar todo">Guardar</button></body></html>'
check('accname order: aria-label beats content',
      locate(ARIA, 'Guardar todo')['found'])

# ── hostile HTML never crashes ───────────────────────────────────────────────
for hostile in ('<button><button>A', '<html', '<a href=', '<<<>>>',
                '<button aria-label="', '\x00<button>\xff', '<img alt=>'):
    try:
        locate(hostile, 'A')
        ok = True
    except Exception as e:  # noqa: BLE001
        ok = False
        print('   crash:', repr(hostile), e)
    if not ok:
        break
check('hostile HTML never crashes', ok)

# ── MCP surface: schema, dispatch, annotations ───────────────────────────────
names = [t['name'] for t in server.TOOLS]
check('tool registered as a11y_locate (#36)', names.count('a11y_locate') == 1
      and len(server.TOOLS) == 36)
resp = server.invoke('a11y_locate', {'html': HTML, 'query': 'Bienvenidos'})
payload = json.loads(resp['content'][0]['text'])
check('MCP invoke returns located route', payload['found']
      and 'h1:nth-of-type(1)' in (payload['selector'] or ''))
resp_es = server.invoke('a11y_locate', {'html': HTML, 'query': 'zzz', 'lang': 'es'})
check('MCP lang=es note', 'Ningún elemento' in json.loads(
    resp_es['content'][0]['text'])['note'])

# ── catalogs: es/en key parity for the locate namespace ─────────────────────
en = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'a11y_toolkit', 'locales', 'en.json'),
    encoding='utf-8'))['locate']
es = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'a11y_toolkit', 'locales', 'es.json'),
    encoding='utf-8'))['locate']
check('locate es/en key parity', set(en) == set(es) and len(en) == 6)
check('placeholders identical es/en', all(
    en[k].count('{') == es[k].count('{') for k in en))

fails = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(fails)}/{len(results)} checks")
sys.exit(1 if fails else 0)
