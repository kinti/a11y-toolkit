#!/usr/bin/env python3
"""Scope + EN 301 549 invariants — pinned.

The load-bearing rules under test (the honesty doctrine, mechanically):
  1. EN 301 549 V4.1.1 numbering identity: every WCAG 2.2 A/AA criterion
     maps to its mirrored clause in 9 (web), 10 (documents) AND 11 (software)
     — 55/55, no exceptions. AAA is never claimed by the map.
  2. The machine PROPOSES, never EXCLUDES: without a human answer no
     criterion may become not-applicable downstream, whatever the features
     block says.
  3. Positive evidence only: no features block (old reports) → zero
     proposals; embeds (iframe/embed/object) leave media undetermined.
  4. Only human-confirmed exclusions flow: pack matrix not-applicable with
     the reason; VPAT/OpenACR level not_applicable; overrides still win.
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a11y_toolkit import a11yen301549, server                       # noqa: E402
from a11y_toolkit.a11yaudit import audit_html                        # noqa: E402
from a11y_toolkit.a11ysarif import from_report                       # noqa: E402
from a11y_toolkit.a11yscope import build_scope, collect_features     # noqa: E402
from a11y_toolkit.a11yevidence import build_pack                     # noqa: E402
from a11y_toolkit.a11ycrit import _C                                 # noqa: E402
from a11y_toolkit.a11yvpat import generate_vpat                      # noqa: E402
from a11y_toolkit.a11yopenacr import generate_openacr                # noqa: E402

BARE = '<html lang="en"><title>t</title><body><h1>a</h1><p>text</p></body></html>'
WITH_MEDIA = ('<html lang="en"><title>t</title><body><video src="a.mp4"></video>'
              '<form><input name="q"></form></body></html>')
WITH_EMBED = ('<html lang="en"><title>t</title><body>'
              '<iframe src="https://www.youtube.com/embed/x"></iframe></body></html>')

failures = []


def check(name, cond, detail=''):
    print(('  OK ' if cond else '  FAIL ') + name + (f' — {detail}' if detail and not cond else ''))
    if not cond:
        failures.append(name)


print('== 1. EN 301 549 numbering identity (55/55 × 9/10/11)')
codes_aa = sorted(k for k, v in _C.items() if v[0] in ('A', 'AA'))
check('A/AA son 55', len(codes_aa) == 55, str(len(codes_aa)))
for target, prefix in (('web', '9'), ('documents', '10'), ('software', '11')):
    bad = [c for c in codes_aa if a11yen301549.clause_for(c, target) != f'{prefix}.{c}']
    check(f'cláusula {prefix}.x: 55/55 espejo exacto', not bad, str(bad[:5]))
check('target por modo: pdf→documents, static→web',
      a11yen301549.target_for_mode('pdf') == 'documents'
      and a11yen301549.target_for_mode('static') == 'web')
check('código inválido → None', a11yen301549.clause_for('x.y') is None
      and a11yen301549.clause_for('1.2.3.4', 'web') is None)

print('== 2. la máquina propone, jamás excluye')
r = audit_html(BARE)
check('informe lleva features (vacío = evidencia)', 'features' in r)
s = build_scope([r], lang='en')
prop = [c for c in s['criteria'] if c['status'] == 'proposed-excluded']
check('página desnuda: 13 propuestas estructurales', len(prop) == 13, str(len(prop)))
check('todas las propuestas llevan evidence_source machine',
      all(p.get('evidence_source') == 'machine:features' for p in prop))
p_solo = build_pack([r], scope=s, lang='en')
check('solo propuestas → 0 not-applicable en pack',
      not [c for c in p_solo['criteria'] if c['status'] == 'not-applicable'])
check('aviso del scope presente', 'notice' in s and s['notice'])

print('== 3. evidencia positiva únicamente')
r_old = {k: v for k, v in r.items() if k != 'features'}
feats, seen = collect_features([r_old])
check('informe viejo: features no vistas', seen is False)
s_old = build_scope([r_old], lang='en')
check('informe viejo: 0 propuestas + limitación declarada',
      s_old['counters']['proposed_excluded'] == 0 and s_old.get('limitations'))
r_emb = audit_html(WITH_EMBED)
s_emb = build_scope([r_emb], lang='en')
emb_prop = [c['criterion'].split(' ')[0] for c in s_emb['criteria']
            if c['status'] == 'proposed-excluded' and c['criterion'].split(' ')[0].startswith(('1.2', '1.4.2'))]
check('solo iframe embebido: 1.2.x queda en alcance', not emb_prop, str(emb_prop))
r_med = audit_html(WITH_MEDIA)
s_med = build_scope([r_med], lang='en')
check('con vídeo+form: 0 propuestas', s_med['counters']['proposed_excluded'] == 0)
check('1.2.4 con medios: en alcance con nota de decisión humana',
      next(c for c in s_med['criteria'] if c['criterion'].startswith('1.2.4'))['status'] == 'in-scope')

print('== 4. solo lo humano confirmado fluye (y con su razón)')
answers = {'1.2.2': {'status': 'excluded', 'reason': 'no prerecorded media in the product'},
           '3.3.1': 'excluded'}
s_h = build_scope([r], answers=answers, lang='en')
excl = {c['criterion'].split(' ')[0]: c for c in s_h['criteria'] if c['status'] == 'excluded'}
check('respuestas humanas aplican (forma dict y forma string)',
      set(excl) == {'1.2.2', '3.3.1'} and excl['1.2.2'].get('reason'))
p = build_pack([r], scope=s_h, lang='en')
na = sorted(c['criterion'].split(' ')[0] for c in p['criteria'] if c['status'] == 'not-applicable')
check('pack: not-applicable exactamente las confirmadas', na == ['1.2.2', '3.3.1'], str(na))
check('pack: la razón viaja en la fila',
      'no prerecorded media in the product'
      in next(c for c in p['criteria'] if c['criterion'].startswith('1.2.2'))['note'])
check('pack: artefacto scope sellado dentro',
      any(a['type'] == 'scope:a11y' and a.get('sha256') for a in p['artifacts']))
check('pack: resumen cuenta not-applicable', p['summary'].get('not-applicable') == 2)
check('manual_pending no incluye las excluidas',
      not [m for m in p['manual_pending'] if m.split(' ')[0] in ('1.2.2', '3.3.1')])
v = generate_vpat(pack=p, product='T', lang='en')
check('vpat: not_applicable con la razón',
      v['levels']['1.2.2'] == 'not_applicable'
      and 'no prerecorded media' in json.dumps(v, ensure_ascii=False))
o = generate_openacr(pack=p, product='T', lang='en')
check('openacr: not_applicable', o['levels']['1.2.2'] == 'not_applicable')
v2 = generate_vpat(pack=p, product='T', overrides={'1.2.2': 'supports'}, lang='en')
check('overrides humanos ganan al scope', v2['levels']['1.2.2'] == 'supports')

print('== 5. EN 301 549 en audit y familias')
r_en = audit_html(BARE, standard='en301549')
check('bloque standard en informe', r_en.get('standard', {}).get('name') == 'EN 301 549 V4.1.1 (2026)')
check('hallazgos con cláusula 9.x',
      all(h.get('clause', '').startswith('9.') for h in r_en['findings']))
s_en = build_scope([r], standard='en301549', target='documents', lang='en')
check('cláusula 10.x en target documents',
      next(c for c in s_en['criteria'] if c['criterion'].startswith('1.1.1'))['clause'] == '10.1.1.1')
fams = {f['family']: f for f in s_en['en301549_families']}
check('familias EN presentes y no evaluadas por el motor',
      set(fams) == {'5', '6', '7', '8', '12', '13'}
      and all(f['evaluated_by_toolkit'] is False for f in fams.values()))
check('contadores cuadran',
      s_en['counters']['in_scope'] + s_en['counters']['proposed_excluded']
      + s_en['counters']['excluded'] == s_en['counters']['criteria'])
check('sello determinista (sin reloj)',
      build_scope([r], standard='en301549', target='documents',
                  lang='en')['sha256'] == s_en['sha256'])

print('== 6. hostil: respuestas malformadas no derriban')
try:
    build_scope([r], answers=[1, 2, 3], lang='en')
    check('answers lista → ValueError', False)
except ValueError:
    check('answers lista → ValueError', True)
try:
    build_scope([r], standard='wcag1', lang='en')
    check('standard desconocido → ValueError', False)
except ValueError:
    check('standard desconocido → ValueError', True)
s_hostil = build_scope([{'findings': 'no soy una lista'}, None, {}], lang='en')
check('informes basura → 55 filas in-scope, sin caída',
      s_hostil['counters']['criteria'] == 55)

print('== 8. regresiones de la revisión externa (8 bugs, 1-nov)')

# 3: clause_for con cola de texto — solo el primer token es el código
check('clause_for trocea el código con nombre',
      a11yen301549.clause_for('1.4.11 Non-text Contrast', 'web') == '9.1.4.11'
      and a11yen301549.clause_for('2.4.11 Focus not Obscured (Minimum)', 'software') == '11.2.4.11'
      and a11yen301549.clause_for('basura total', 'web') is None)

# 4: criterion no-string en findings no tira el scope
r_bad = {'mode': 'static', 'url': 'x', 'score': 50, 'summary': {},
         'findings': [{'criterion': 123, 'severity': 'high', 'signal': 'x'},
                      {'criterion': ['1.1.1'], 'severity': 'low', 'signal': 'y'},
                      {'criterion': '1.1.1 Images', 'severity': 'low', 'signal': 'z'}],
         'features': {}}
s_bad = build_scope([r_bad], lang='en')
check('findings hostiles: sin crash, el válido cuenta', s_bad['counters']['criteria'] == 55)

# 1: scope malformado no tira el pack (filas sin criterion, tipos raros)
bad_scope = {'format': 'a11y-scope/1', 'criteria': [
    {'status': 'excluded', 'reason': 'sin criterion'},
    'string suelto',
    {'status': 'excluded', 'criterion': 123},
    {'status': 'excluded', 'criterion': '1.2.2 Captions (Prerecorded)', 'reason': 'ok'},
], 'counters': {}}
p_bad = build_pack([r], scope=bad_scope, lang='en')
na_bad = sorted(c['criterion'].split(' ')[0] for c in p_bad['criteria']
                if c['status'] == 'not-applicable')
check('scope malformado: solo la fila válida cuenta', na_bad == ['1.2.2'], str(na_bad))
check('scope malformado: artefacto scope_block tampoco cae',
      p_bad['scope']['not_applicable'] == {'1.2.2': 'ok'})
try:
    build_pack([r], scope=['no', 'dict'], lang='en')
    check('scope no-dict → ValueError', False)
except ValueError:
    check('scope no-dict → ValueError', True)

# 2: pack YA construido + scope se aplica (no silencio)
base_pack = build_pack([r], lang='en')
v_packscope = generate_vpat(pack=base_pack, product='T',
                            scope=build_scope([r], answers={'1.2.2': {'status': 'excluded', 'reason': 'no media'}},
                                              lang='en'), lang='en')
check('vpat pack+scope aplica la exclusión', v_packscope['levels']['1.2.2'] == 'not_applicable')
check('apply_scope no muta el pack original',
      base_pack['sha256'] == build_pack([r], lang='en')['sha256']
      and not [c for c in base_pack['criteria'] if c['criterion'].startswith('1.2.2')
               and c['status'] == 'not-applicable'])
v_scopelist = generate_vpat(pack=base_pack, product='T', scope=['x'], lang='en')
check('vpat scope no-dict → error explícito', 'error' in v_scopelist)
o_packscope = generate_openacr(pack=base_pack, product='T',
                               scope=build_scope([r], answers={'1.2.2': 'excluded'}, lang='en'),
                               lang='en')
check('openacr pack+scope aplica la exclusión', o_packscope['levels']['1.2.2'] == 'not_applicable')

# 6: verified + excluded del mismo código → UNA fila (la exclusión gana)
p_conflict = build_pack([r], verified=['3.3.7'],
                        scope=build_scope([r], answers={'3.3.7': 'excluded'}, lang='en'),
                        lang='en')
rows_337 = [c for c in p_conflict['criteria'] if c['criterion'].startswith('3.3.7')]
check('verified+excluded: una sola fila y es not-applicable',
      len(rows_337) == 1 and rows_337[0]['status'] == 'not-applicable',
      f'{len(rows_337)} filas: {[c["status"] for c in rows_337]}')

# 7: target explícito en sarif recalcula aunque el hallazgo traiga cláusula
r_emb = audit_html(WITH_MEDIA, standard='en301549')   # cláusulas 9.x embebidas
sar = from_report(r_emb, standard='en301549', target='documents')
tag = next(rx['properties']['en301549'] for rx in sar['runs'][0]['tool']['driver']['rules']
           if rx.get('properties'))
check('sarif target explícito recalcula a 10.x', tag.startswith('10.'), tag)
sar2 = from_report(r_emb, standard='en301549')          # sin target: la embebida manda
tag2 = next(rx['properties']['en301549'] for rx in sar2['runs'][0]['tool']['driver']['rules']
            if rx.get('properties'))
check('sarif sin target respeta la cláusula embebida', tag2.startswith('9.'), tag2)

# 8: map_findings eliminado (contrato falso) — no existe
check('map_findings eliminado del módulo', not hasattr(a11yen301549, 'map_findings'))

print('== 7. servidor MCP y CLI reales')
resp = server.invoke('a11y_scope', {'reports': [r], 'standard': 'en301549'})
data = json.loads(resp['content'][0]['text'])
check('invoke a11y_scope (37 tools)', len(server.TOOLS) == 37
      and data['format'] == 'a11y-scope/1')
with tempfile.TemporaryDirectory() as td:
    rep = os.path.join(td, 'r.json')
    sc = os.path.join(td, 's.json')
    ans = os.path.join(td, 'a.json')
    json.dump(r, open(rep, 'w'))
    json.dump({'1.2.4': {'status': 'excluded', 'reason': 'x'}}, open(ans, 'w'))
    pr = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11yscope', rep,
                         '--standard', 'en301549', '--answers', ans, '-o', sc],
                        capture_output=True, text=True)
    check('CLI scope exit 0', pr.returncode == 0, pr.stderr[-200:])
    out = json.loads(pr.stdout)
    check('CLI confirma 1 exclusión', out['counters']['excluded'] == 1)

print('== 9. SARIF: hallazgos muertos fuera, hostiles degradados (4-nov)')
sar_disp = from_report({'mode': 'static', 'url': 'u', 'findings': [
    {'criterion': '1.1.1 Non-text Content', 'severity': 'high',
     'signal': 'img_no_alt', 'issue': 'live failure'},
    {'criterion': '1.1.1 Non-text Content', 'severity': 'high',
     'signal': 'img_no_alt', 'issue': 'rejected one', 'status': 'rejected'},
    {'criterion': '1.1.1 Non-text Content', 'severity': 'high',
     'signal': 'img_no_alt', 'issue': 'not rechecked one',
     'disprover_status': 'not-rechecked'},
]})
check('sarif: solo el hallazgo vivo navega a GitHub',
      [x['message']['text'] for x in sar_disp['runs'][0]['results']] == ['live failure'])
sar_bad = from_report({'mode': 'static', 'url': 'u', 'findings': [
    {'criterion': '1.1.1 x', 'severity': 'high', 'signal': 'img_no_alt', 'issue': 'ok'},
    {'criterion': '1.1.1 x', 'severity': 'high', 'signal': 'img_no_alt'},   # sin issue
    {'criterion': 7, 'severity': 'high', 'signal': 'x', 'issue': 'y'},      # criterion no-str
    'no soy un hallazgo',
]})
check('sarif hostil: sin KeyError, el válido cuenta',
      len(sar_bad['runs'][0]['results']) == 1
      and sar_bad['runs'][0]['results'][0]['message']['text'] == 'ok')
check('sarif hostil: lo saltado queda contado, no silenciado',
      sar_bad['runs'][0].get('properties', {}).get('skippedFindings') == 3)

print('== 10. apply_scope recalcula el esfuerzo pendiente (4-nov)')
from a11y_toolkit.a11yevidence import apply_scope                     # noqa: E402
from a11y_toolkit.a11ycrit import effort as _effort                   # noqa: E402
r_bare = audit_html(BARE)
base_pack = build_pack([r_bare], lang='en')
scoped_pack = apply_scope(base_pack, {'format': 'a11y-scope/1', 'criteria': [
    {'criterion': '1.2.1 Audio-only and Video-only (Prerecorded)',
     'status': 'excluded', 'reason': 'no audio in the product'},
    {'criterion': '3.3.7 Redundant Entry', 'status': 'excluded',
     'reason': 'single-step flow'},
]}, lang='en')
check('apply_scope: resumen cuenta las not-applicable',
      scoped_pack['summary']['not-applicable'] == 2)
drop = [a - b for a, b in zip(base_pack['effort_pending']['total_minutes'],
                              scoped_pack['effort_pending']['total_minutes'])]
expected = [sum(_effort(c)['minutes'][i] for c in ('1.2.1', '3.3.7')) for i in (0, 1)]
check('apply_scope: el esfuerzo cae EXACTO lo excluido', drop == expected,
      f'drop={drop} expected={expected}')
check('apply_scope: manual_pending ya no nombra las excluidas',
      not [m for m in scoped_pack['manual_pending']
           if m.split(' ')[0] in ('1.2.1', '3.3.7')])
check('apply_scope: by_class tampoco las cuenta',
      sum(v['criteria'] for v in scoped_pack['effort_pending']['by_class'].values())
      == sum(v['criteria'] for v in base_pack['effort_pending']['by_class'].values()) - 2)
check('apply_scope: el pack original queda intacto (sello)',
      not [c for c in base_pack['criteria'] if c['status'] == 'not-applicable'])

print('== 11. RGAA: las respuestas humanas aplican (4-nov)')
s_rgaa = build_scope([r_bare], standard='rgaa', lang='en',
                     answers={'1.1': {'status': 'excluded', 'reason': 'sin imágenes'},
                              '1.2.1': 'in-scope'})
rg11 = next(c for c in s_rgaa['criteria'] if c['criterion'].startswith('1.1 '))
check('rgaa: la exclusión humana aplica con su razón',
      rg11['status'] == 'excluded' and rg11.get('reason') == 'sin imágenes'
      and rg11.get('evidence_source') == 'human')
check('rgaa: counters cuentan la exclusión (antes siempre 0)',
      s_rgaa['counters']['excluded'] == 1
      and s_rgaa['counters']['criteria'] == 106)
check('rgaa: respuesta string in-scope también aplica (clave con cola de test)',
      next(c for c in s_rgaa['criteria']
           if c['criterion'].split(' ')[0] == '1.2')['status'] == 'in-scope')
s_rgaa_plain = build_scope([r_bare], standard='rgaa', lang='en')
check('rgaa sin respuestas: 106 in-scope, cero propuestas',
      s_rgaa_plain['counters']['excluded'] == 0
      and s_rgaa_plain['counters']['in_scope'] == 106)

print('== 12. (508 GSA tree: moved to the private pro layer — 4-nov)')

print('== 13. EN 301 549: cláusulas EN-only de software 11.5-11.7 (4-nov)')
s_sw = build_scope([r_bare], standard='en301549', target='software', lang='en')
sw = s_sw.get('en301549_software_clauses') or []
check('software: 11.5-11.7 presentes',
      [row['clause'] for row in sw] == ['11.5', '11.6', '11.7'])
check('software: revisión humana, no propuesta, no claim',
      all(row['status'] == 'human-review' and row['evaluated_by_toolkit'] is False
          for row in sw))
check('software: título del estándar + nota honesta',
      sw[0]['title'] == 'Interoperability with assistive technology'
      and all(row.get('note') for row in sw))
s_sw_es = build_scope([r_bare], standard='en301549', target='software', lang='es')
check('software: títulos bilingües',
      next(row for row in s_sw_es['en301549_software_clauses']
           if row['clause'] == '11.7')['title'] == 'Preferencias del usuario')
check('web/documents: las cláusulas de software NO aparecen',
      'en301549_software_clauses' not in build_scope([r_bare], standard='en301549',
                                                     target='web', lang='en')
      and 'en301549_software_clauses' not in build_scope([r_bare], standard='en301549',
                                                         target='documents', lang='en'))
check('multi-target con software también las trae',
      'en301549_software_clauses' in build_scope([r_bare], standard='en301549',
                                                  target='web', targets=['web', 'software'],
                                                  lang='en'))

if failures:
    print(f'SCOPE: {len(failures)} fallos — {failures}')
    sys.exit(1)
print('SCOPE OK ✓ (EN 301 549 55/55 × 3 cláusulas, la máquina propone y nunca '
      'excluye, solo lo humano confirmado fluye con su razón, RGAA escucha '
      'respuestas, sin 508 público, cláusulas software 11.5-11.7, CLI+MCP reales)')
