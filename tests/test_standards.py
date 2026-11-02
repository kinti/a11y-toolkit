#!/usr/bin/env python3
"""Standards workbench (lane-A REA picks) — pinned.

The four wizard-pattern proposals, verified:
  solicitation: scope → procurement annex text (ART solicitation-language
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
from a11y_toolkit.a11yscope import build_scope, solicitation        # noqa: E402

failures = []


def check(name, cond, detail=''):
    print(('  OK ' if cond else '  FAIL ') + name + ('' if cond else f' — {detail}'))
    if not cond:
        failures.append(name)


DOC = '<html lang="es"><head><title>Tienda</title></head><body><h2>Ofertas</h2><img src="a.png"><input placeholder="x"><nav><a href="/m">menú</a></nav></body></html>'
R = audit_html(DOC)

print('== 1. solicitation: del alcance al pliego')
answers = {'1.2.4': {'status': 'excluded', 'reason': 'sin medios en directo'}}
sc = build_scope([R], standard='en301549', target='web',
                 answers=answers, lang='es')
text = solicitation(sc, lang='es')
check('título de anexo', 'Anexo de requisitos' in text)
check('norma citada', 'EN 301 549 V4.1.1 (2026)' in text)
check('cláusulas por principio', 'Principio 1 — Perceptible' in text
      and '9.1.1.1' in text)
check('exclusiones con razón', 'sin medios en directo' in text
      and 'excluido' in text)
check('evidencia exigida', 'auditoría' in text.lower()
      and 'SHA-256' in text)
check('nota de verificación', 'antes de la adjudicación' in text)
text_en = solicitation(build_scope([R], standard='en301549', target='web',
                                   answers=answers, lang='en'), lang='en')
check('versión EN', 'Accessibility requirements annex' in text_en
      and 'Principle 1' in text_en)

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

print('== 4. standard 508: árbol GSA')
r_508 = audit_html(DOC)
# target web: sin excepciones, capítulos de contenido
s_web = build_scope([r_508], standard='508', target='web', lang='en')
b = s_web['section508']
check('árbol GSA presente', b['standard'] == 'Section 508 (Revised, 2017)')
check('web-based pre-respondido por el audit', b['web_based']['answer'] == 'yes'
      and b['web_based']['source'] == 'machine')
check('web target: SIN excepciones WCAG', b['wcag_exceptions'] == [])
check('capítulos de contenido', set(b['chapters']) == {'602', '603'})
check('preguntas humanas pendientes', b['public_facing']['answer'] == 'pending')
# target documents sin web: las 4 excepciones propuestas
s_docs = build_scope([r_508], standard='508', target='documents', lang='en')
b2 = s_docs['section508']
check('documents no-web: excepciones E203/E204 propuestas',
      set(b2['wcag_exceptions']) == {'2.4.1', '2.4.5', '3.2.3', '3.2.4'})
exc_rows = [c for c in s_docs['criteria']
            if c['status'] == 'proposed-excluded'
            and c['criterion'].split(' ')[0] in b2['wcag_exceptions']]
check('excepciones como proposed-excluded con fuente machine:508',
      len(exc_rows) == 4 and all(c['evidence_source'] == 'machine:508' for c in exc_rows))
# respuesta humana: es web-based → sin excepciones
s_web_ans = build_scope([r_508], standard='508', target='documents',
                        answers={'508:web_based': {'answer': 'yes', 'reason': 'also ships as web app'}},
                        lang='en')
check('humano confirma web-based → excepciones retiradas',
      s_web_ans['section508']['wcag_exceptions'] == []
      and s_web_ans['section508']['web_based']['source'] == 'human')
# authoring tool → capítulo 504
s_auth = build_scope([r_508], standard='508', target='software',
                     answers={'508:authoring_tool': {'answer': 'yes'}}, lang='en')
check('authoring tool → capítulo 504',
      '504' in s_auth['section508']['chapters'])

print('== 5. doctrine intacta en 508 (propone, jamás excluye)')
check('508: sin excluded por máquina (solo propuestas)',
      not any(c['status'] == 'excluded' and c.get('evidence_source') == 'machine:508'
              for c in s_docs['criteria']))

print('== 6. CLI scope --targets --solicitation')
with tempfile.TemporaryDirectory() as td:
    rp = os.path.join(td, 'r.json')
    sp = os.path.join(td, 's.json')
    ap_ = os.path.join(td, 'pliego.txt')
    json.dump(r_web, open(rp, 'w'))
    pr = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11yscope', rp,
                         '--standard', 'en301549', '--targets', 'web,documents',
                         '--answers', os.devnull if False else '/dev/null',
                         '--solicitation', ap_, '-o', sp, '--lang', 'es'],
                        capture_output=True, text=True,
                        input=None)
    # /dev/null no es un answers JSON válido → el CLI leerá []; usar sin --answers
    if pr.returncode != 0:
        pr = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11yscope', rp,
                             '--standard', 'en301549', '--targets', 'web,documents',
                             '--solicitation', ap_, '-o', sp, '--lang', 'es'],
                            capture_output=True, text=True)
    check('CLI exit 0', pr.returncode == 0, pr.stderr[-200:])
    outd = json.loads(pr.stdout)
    check('CLI: multi-target y anexo anunciados',
          outd.get('solicitation') == ap_ and outd['counters']['criteria'] == 55)
    annex = open(ap_, encoding='utf-8').read()
    check('anexo con cláusulas y evidencia', '9.' in annex and 'auditoría' in annex.lower())


print('== 9. F1: exención de contenido (árbol GSA fiel)')
ans_exempt = {'508:public_facing': {'answer': 'no'},
              '508:official_comm': {'answer': 'no'}}
sc_ex = build_scope([R], standard='508', target='web',
                    answers=ans_exempt, lang='en')
b_ex = sc_ex['section508']
check('content_exempt=True (no público + no oficial)',
      b_ex['content_exempt'] is True)
check('los 55 criterios propuestos fuera con la respuesta humana',
      sc_ex['counters']['proposed_excluded'] == 55
      and 'human answers public_facing=no, official_comm=no'
          in sc_ex['criteria'][0]['evidence'])
check('razones 508 por catálogo (es)',
      'Revised 508' in sc_ex['criteria'][0]['evidence'])
sc_es = build_scope([R], standard='508', target='web',
                    answers=ans_exempt, lang='es')
check('razones 508 en es', 'exento según Revised 508'
      in sc_es['criteria'][0]['evidence']
      or 'exento' in sc_es['criteria'][0]['evidence'])
# official=yes + public=no → el contenido APLICA (comunicación oficial)
sc_off = build_scope([R], standard='508', target='web',
                     answers={'508:public_facing': {'answer': 'no'},
                              '508:official_comm': {'answer': 'yes'}}, lang='en')
check('comunicación oficial → el contenido aplica',
      sc_off['section508']['content_exempt'] is False)

print('== 10. F2: anexo sólido con 508 (excepciones, capítulos, trazabilidad, numeración)')
r_hw = audit_html(DOC)
sc_hw = build_scope([r_hw], standard='508', target='web', lang='en')
annex = solicitation(sc_hw, lang='en')
check('requisitos numerados R1…', 'R1 —' in annex and 'R2 —' in annex)
check('web target: sin sección de excepciones (vacía se omite)',
      'E203/E204' not in annex)
check('capítulos declarados en el anexo', '602' in annex)
# target documents: excepciones E203/E204 listadas en el anexo
r_docs = audit_html(DOC)
sc_docs = build_scope([r_docs], standard='508', target='documents', lang='en')
annex_docs = solicitation(sc_docs, lang='en')
check('excepciones 508 en sección propia (documents)',
      'WCAG 2.4.1' in annex_docs and 'E203/E204' in annex_docs)
check('trazabilidad: sha del alcance + motor',
      'sha256:' in annex and 'engine' in annex)
from a11y_toolkit.server import VERSION as ENG_V
check('versión del motor en la trazabilidad', ENG_V in annex)

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


print('== 14. wizard: el canadiense invertido en el terminal')
wiz = os.path.join(td, 'wiz')
os.makedirs(wiz)
hp = os.path.join(wiz, 'pagina.html')
open(hp, 'w', encoding='utf-8').write(
    '<html lang="es"><head><title>Tienda</title></head><body><h2>Ofertas</h2>'
    '<img src="lampara.jpg"><input placeholder="correo"></body></html>')
# flujo: target=2 documents, std=2 EN, público s, oficial n, anexo s, idioma es
ans = '2\n2\ns\nn\ns\nes\n'
pr = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ywiz', '--file', hp,
                     '--lang', 'es', '-o', os.path.join(wiz, 'scope.json')],
                    input=ans, capture_output=True, text=True, timeout=120)
check('wizard exit 0', pr.returncode == 0, pr.stderr[-200:] if pr.returncode else '')
check('resumen con nota y contadores', 'Nota:' in pr.stdout and 'en alcance:' in pr.stdout)
scope_wiz = json.load(open(os.path.join(wiz, 'scope.json'), encoding='utf-8'))
check('scope EN documents', scope_wiz['standard'] == 'EN 301 549 V4.1.1 (2026)'
      and scope_wiz['target'] == 'documents')
annex_path = os.path.join(wiz, 'anexo_pligo.txt')
check('anexo generado con requisitos numerados',
      os.path.exists(annex_path)
      and 'R1 — 10.' in open(annex_path, encoding='utf-8').read())
# 508: preguntas de producto fluyen a answers
ans_508 = '1\n3\nn\nn\nn\n'   # web, 508, público n, oficial n, sin anexo
pr2 = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ywiz', '--file', hp,
                      '--lang', 'en', '-o', os.path.join(wiz, 's508.json')],
                     input=ans_508, capture_output=True, text=True, timeout=120)
s508 = json.load(open(os.path.join(wiz, 's508.json'), encoding='utf-8'))
check('508: web + no público + no oficial → exento propuesto',
      s508['section508']['content_exempt'] is True
      and s508['counters']['proposed_excluded'] == 55)
# stdin vacío → abort elegante con los comandos no-interactivos como salida
pr3 = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ywiz', '--file', hp,
                      '--lang', 'en'], input='', capture_output=True, text=True, timeout=60)
check('stdin vacío → abort elegante con comandos como mensaje',
      pr3.returncode == 1 and 'a11ytoolkit scope' in pr3.stdout)

if failures:
    print(f'STANDARDS: {len(failures)} fallos — {failures}')
    sys.exit(1)
print('STANDARDS OK ✓ (solicitation es/en, Quick Ref filters, multi-target, '
      'árbol GSA 508 con excepciones y capítulos, doctrina intacta)')
