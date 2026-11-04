#!/usr/bin/env python3
"""Standards workbench (lane-A REA picks) — pinned.

The four wizard-pattern proposals, verified:
                pattern) with clauses by principle, confirmed exclusions
                with reasons, evidence list, honest verification note.
  criteria --list --filters: the W3C Quick Ref pattern offline — by
                level, new-in-2.2 (the 9 SC set), signal availability.
  scope multi-target: rows carry a clauses dict per ICT target (ART
                multi-item pattern).
  standard 508: the GSA tree — machine pre-answers web-based from the
                target, human answers the product questions, non-web
                proposes the 2.4.1/2.4.5/3.2.3/3.2.4 exceptions
                (E203/E204) and declares the chapters beyond WCAG.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a11y_toolkit.a11yaudit import audit_html                       # noqa: E402
from a11y_toolkit.a11yscope import build_scope        # noqa: E402

failures = []


def check(name, cond, detail=''):
    print(('  OK ' if cond else '  FAIL ') + name + ('' if cond else f' — {detail}'))
    if not cond:
        failures.append(name)


DOC = '<html lang="es"><head><title>Tienda</title></head><body><h2>Ofertas</h2><img src="a.png"><input placeholder="x"><nav><a href="/m">menú</a></nav></body></html>'
R = audit_html(DOC)

print('== 2. criteria --list --filters (Quick Ref offline)')
out = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ycrit', '--list',
                      '--level', 'AA', '--new-in', '2.2', '--lang', 'es'],
                     capture_output=True, text=True)
d = json.loads(out.stdout)
check('AA + nuevo en 2.2 → 4 criterios', d['count'] == 4, str(d['count']))
check('filas con flag new_in_22', all(c['new_in_22'] for c in d['criteria']))
out2 = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ycrit', '--list',
                       '--signal-filter', 'no', '--lang', 'en'],
                      capture_output=True, text=True)
d2 = json.loads(out2.stdout)
check('sin señal → los 4 manuales', d2['count'] == 4
      and {c['code'] for c in d2['criteria']} == {'1.2.1', '1.2.4', '2.3.1', '3.3.7'},
      str([c['code'] for c in d2['criteria']]))
out3 = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ycrit', '--list',
                       '--level', 'AA', '--lang', 'es'], capture_output=True, text=True)
from a11y_toolkit.a11ycrit import _C as _CAT
aa_total = sum(1 for v in _CAT.values() if v[0] == 'AA')
check('AA completo → el catálogo entero', json.loads(out3.stdout)['count'] == aa_total)

print('== 3. scope multi-target (ART multi-item)')
r_web = audit_html(DOC)
sc_multi = build_scope([r_web], standard='en301549', target='web',
                       targets=['web', 'documents'], lang='en')
row = next(c for c in sc_multi['criteria'] if c['criterion'].startswith('1.1.1'))
check('criterio lleva clauses dict por target',
      row.get('clauses') == {'web': '9.1.1.1', 'documents': '10.1.1.1'},
      str(row.get('clauses')))
check('cláusula primaria = primer target', row.get('clause') == '9.1.1.1')
sc_single = build_scope([r_web], lang='en')
check('sin multi-target: sin clauses dict',
      all('clauses' not in c for c in sc_single['criteria']))

print('== 11. F3: familias con estado por target')
sc_mt = build_scope([R], standard='en301549', target='web',
                    targets=['web', 'documents'], lang='en')
fam6 = next(f for f in sc_mt['en301549_families'] if f['family'] == '6')
check('familia 6 con status_per_target',
      fam6.get('status_per_target') == {'web': 'proposed-excluded',
                                        'documents': 'human-review'},
      str(fam6.get('status_per_target')))

print('== 12. F4: criteria --list --standard en301549')
out4 = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ycrit', '--list',
                       '--level', 'AA', '--standard', 'en301549',
                       '--target', 'documents', '--lang', 'en'],
                      capture_output=True, text=True)
d4 = json.loads(out4.stdout)
first = d4['criteria'][0]
check('cláusula 10.x en las filas', first['clause'].startswith('10.'),
      str(first.get('clause')))
out5 = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ycrit', '--list',
                       '--level', 'AA', '--standard', 'en301549', '--lang', 'en'],
                      capture_output=True, text=True)
d5 = json.loads(out5.stdout)
check('sin --target → 9.x por defecto',
      d5['criteria'][0]['clause'].startswith('9.'))


print('== 13. RGAA: el dato abierto del gobierno francés')
from a11y_toolkit import a11yrgaa                                    # noqa: E402
check('106 criterios en 13 temas', len(a11yrgaa.CRITERIA) == 106
      and len(a11yrgaa.TOPICS) == 13)
check('sin markdown en títulos (flatten)', all('](' not in c['title'] for c in a11yrgaa.CRITERIA))
check('todos con mapeo WCAG', all(c['wcag'] for c in a11yrgaa.CRITERIA))
check('puente mecánico: 1.1.1 → 19 criterios RGAA',
      len(a11yrgaa.rgaa_for_sc('1.1.1')) == 19)
check('criterio completo accesible',
      a11yrgaa.criterion('1.1')['tests'] and a11yrgaa.criterion('1.1')['title'])
r_rgaa = audit_html(DOC, standard='rgaa', lang='es')
check('audit rgaa: bloque standard + hallazgos con criterios RGAA',
      r_rgaa['standard']['name'].startswith('RGAA 4.1')
      and all(h.get('rgaa') for h in r_rgaa['findings']))
sc_rg = build_scope([r_rgaa], standard='rgaa', lang='es')
check('scope rgaa: 106 filas en alcance', sc_rg['counters']['criteria'] == 106)
check('scope rgaa: norma nombrada', sc_rg['standard'] == 'RGAA 4.1 (France)')


print('== 14. wizard: el canadiense invertido en el terminal (sin 508/anexo: pro)')
import tempfile
td = tempfile.mkdtemp()
wiz = os.path.join(td, 'wiz')
os.makedirs(wiz)
hp = os.path.join(wiz, 'pagina.html')
open(hp, 'w', encoding='utf-8').write(
    '<html lang="es"><head><title>Tienda</title></head><body><h2>Ofertas</h2>'
    '<img src="lampara.jpg"><input placeholder="correo"></body></html>')
# flujo: target=2 documents, std=2 EN (el anexo y el árbol 508 viven en el pro)
ans = '2\n2\n'
pr = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ywiz', '--file', hp,
                     '--lang', 'es', '-o', os.path.join(wiz, 'scope.json')],
                    input=ans, capture_output=True, text=True, timeout=120)
check('wizard exit 0', pr.returncode == 0, pr.stderr[-200:] if pr.returncode else '')
check('resumen con nota y contadores', 'Nota:' in pr.stdout and 'en alcance:' in pr.stdout)
scope_wiz = json.load(open(os.path.join(wiz, 'scope.json'), encoding='utf-8'))
check('scope EN documents', scope_wiz['standard'] == 'EN 301 549 V4.1.1 (2026)'
      and scope_wiz['target'] == 'documents')
check('sin sección 508 en el público', 'section508' not in scope_wiz
      or scope_wiz['section508'] is None)
# stdin vacío → abort elegante con los comandos no-interactivos como salida
pr3 = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ywiz', '--file', hp,
                      '--lang', 'en'], input='', capture_output=True, text=True, timeout=60)
check('stdin vacío → abort elegante con comandos como mensaje',
      pr3.returncode == 1 and 'a11ytoolkit scope' in pr3.stdout)

if failures:
    print(f'STANDARDS: {len(failures)} fallos — {failures}')
    sys.exit(1)
print('STANDARDS OK ✓ (Quick Ref filters, multi-target, RGAA, wizard, doctrina intacta)')

# ── revisión externa ronda 2: --standard rgaa ya NO se descarta en site/crawl ──
from a11y_toolkit.a11yaudit import _apply_standard as _aps
_fake = {'mode': 'site', 'url': 'https://x', 'reports': [
    {'mode': 'static', 'url': 'https://x/a', 'findings': [
        {'severity': 'high', 'criterion': '1.1.1 Non-text Content', 'signal': 'img_no_alt',
         'issue': 'x', 'remediation': 'y'}]}]}
_out = _aps(_fake, 'rgaa', None, 'es')
assert 'standard' in _out and _out['reports'][0]['findings'][0].get('rgaa'), \
    'rgaa descartado en modo site (el enrichment post-hoc no corrió)'
print('rgaa aplicado post-hoc en site/crawl ✓')
