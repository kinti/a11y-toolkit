#!/usr/bin/env python3
"""Per-element annotation kernel — pinned.

The load-bearing rules:
  1. Determinism: same html + same report → same routes, same marks, same ids.
  2. Byte preservation: the annotated copy equals the original EXCEPT the
     injected ` data-a11y-id="mN"` attributes (offset surgery, nothing else).
  3. Honest fallback: findings without locatable paths land in `unplaced`
     — never a wrong mark. Hostile html never crashes.
  4. The route algorithm is SHARED with the auditor (VOID_TAGS /
     path_segment from a11yaudit): locator and auditor cannot drift apart.
  5. Duplicate ids cannot break identity (routes use nth-of-type always).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a11y_toolkit.a11yaudit import audit_html                       # noqa: E402
from a11y_toolkit.a11yannotate import annotate                      # noqa: E402

failures = []


def check(name, cond, detail=''):
    print(('  OK ' if cond else '  FAIL ') + name + ('' if cond else f' — {detail}'))
    if not cond:
        failures.append(name)


DOC = ('<html>\n<body>\n  <img src="a.png">\n  <p>texto con "comillas" y <b>negrita</b></p>\n'
       '  <img src="b.png">\n  <input placeholder="solo">\n  <iframe src="x"></iframe>\n</body>\n</html>')

print('== 1. marcas en su sitio exacto')
r = audit_html(DOC)
res = annotate(DOC, r)
m = {x['path'].split('>')[-1] + '#' + x['id']: x for x in res['marks']}
img1 = next(x for x in res['marks'] if x['path'].endswith('img:nth-of-type(1)'))
check('img 1 marcada', 'data-a11y-id="%s"' % img1['id'] in res['annotated_html'].split('\n')[2])
img2 = next(x for x in res['marks'] if x['path'].endswith('img:nth-of-type(2)'))
line_img2 = [ln for ln in res['annotated_html'].split('\n') if 'b.png' in ln][0]
check('img 2 marcada en SU línea', f'data-a11y-id="{img2["id"]}"' in line_img2)
html_mark = [x for x in res['marks'] if x['path'] == 'html:nth-of-type(1)']
check('lang_missing marca <html>', bool(html_mark)
      and res['annotated_html'].startswith('<html data-a11y-id='))
check('las marcas llevan criterio y severidad',
      all(x.get('criterion') and x.get('severity') and x.get('signal') for x in res['marks']))

print('== 2. preservación de bytes')
stripped = re.sub(r' data-a11y-id="m\d+"', '', res['annotated_html'])
check('original + solo los attrs inyectados', stripped == DOC)
check('comillas y <b> intactos', '"comillas" y <b>negrita</b>' in res['annotated_html'])

print('== 3. determinismo')
r2 = audit_html(DOC)
res2 = annotate(DOC, r2)
check('misma entrada → misma salida (ids incluidos)', res == res2)

print('== 4. fallback honesto')
check('hallazgos sin paths → unplaced (nunca marca)',
      all(x['signal'] in {u['signal'] for u in res['unplaced']}
          for x in r['findings'] if not x.get('paths')))
res_wrong = annotate('<html><body><p>otro documento</p></body></html>', r)
check('informe de OTRO html → source_mismatch y sin marcas de contenido',
      res_wrong['source_mismatch'] is True
      and not [x for x in res_wrong['marks'] if 'img' in x['path']])
check('el informe sella su fuente (source_sha256)',
      bool(r.get('source_sha256')))
res_ok = annotate(DOC, r)
check('mismo html → sin mismatch', res_ok['source_mismatch'] is False)

print('== 5. hostil: jamás caer')
hostiles = [
    '<img src=a.png',                                  # truncado
    '<html><body><div><img src=a></div></span></body>',  # anidado roto
    '<!-- <img src=fake> --> real',                     # falso img en comentario
    '<html>' + '<div><img src=x.png></div>' * 300,      # volumen
    '',
    'no soy html',
]
for i, h in enumerate(hostiles):
    try:
        rh = audit_html(h)
        annotate(h, rh)
        check(f'hostil {i + 1} sin caída', True)
    except Exception as e:  # noqa: BLE001
        check(f'hostil {i + 1} sin caída', False, repr(e))
com = '<html><body><!-- <img src="x"> --><img src="y"></body></html>'
rc = audit_html(com)
resc = annotate(com, rc)
check('la marca cae en el img real, no en el del comentario',
      '<img data-a11y-id="m1" src="y">' in resc['annotated_html']
      and '<!-- <img src="x"> -->' in resc['annotated_html'])

print('== 6. ids duplicados no rompen identidad')
dup = '<html><body><img id="x" src="a.png"><img id="x" src="b.png"></body></html>'
rd = audit_html(dup)
resd = annotate(dup, rd)
check('dos imgs con id duplicado: dos marcas distintas',
      len([x for x in resd['marks'] if ':nth-of-type(' in x['path']]) >= 2)

print('== 7. informe JSON redondo (los paths viajan)')
rr = json.loads(json.dumps(r))
check('paths sobreviven al json round-trip',
      any(h.get('paths') for h in rr['findings']))

print('== 8. CLI real')
with tempfile.TemporaryDirectory() as td:
    hp, rp, op = [os.path.join(td, n) for n in ('p.html', 'r.json', 'copy.html')]
    open(hp, 'w', encoding='utf-8').write(DOC)
    json.dump(r, open(rp, 'w', encoding='utf-8'))
    pr = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11yannotate', hp,
                         '--report', rp, '-o', op], capture_output=True, text=True)
    check('CLI exit 0', pr.returncode == 0, pr.stderr[-200:])
    if pr.returncode == 0:
        out = json.loads(pr.stdout)
        copy = open(op, encoding='utf-8').read()
        check('CLI: marks>0 y copia con attrs', out['marks'] > 0
              and 'data-a11y-id' in copy)

if failures:
    print(f'ANNOTATE: {len(failures)} fallos — {failures}')
    sys.exit(1)
print('ANNOTATE OK ✓ (marcas exactas, bytes preservados, determinista, '
      'fallback honesto, hostil domado, CLI real)')
