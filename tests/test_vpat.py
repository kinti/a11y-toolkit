#!/usr/bin/env python3
"""Tests del generador VPAT 2.5 (rules de honestidad, derivación, overrides)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a11y_toolkit.a11yaudit import audit_html  # noqa: E402
from a11y_toolkit.a11yevidence import build_pack  # noqa: E402
from a11y_toolkit.a11yvpat import generate_vpat, LEVELS, _STATUS_TO_LEVEL  # noqa: E402

# report sintético con failures reales del motor estático
report = audit_html('<html><head><title>t</title></head><body>'
                     '<img src="a.png"><button></button>'
                     '<input type="text" name="email"><a href="#">here</a>'
                     '</body></html>')
pack = build_pack([report])

for lang in ('en', 'es'):
    res = generate_vpat(pack=pack, product='Demo App', contact='a11y@example.com',
                       lang=lang)
    assert 'error' not in res, res
    html = res['html']
    # documento accesible por construcción
    assert f'<html lang="{lang}">' in html
    assert '<caption>' in html and 'scope="col"' in html and 'scope="row"' in html
    # el hash del pack es la referencia de firma (tamper-evidence)
    assert pack['sha256'] in html and res['pack_sha256'] == pack['sha256']
    # derivación: automated-fail → does_not_support
    assert res['levels']['1.1.1'] == 'does_not_support', res['levels']['1.1.1']
    # not-flagged ≠ pass → not_evaluated (honestidad VPAT)
    assert res['levels']['1.2.2'] == 'not_evaluated', res['levels']['1.2.2']
    # el summary cuadra con las rows
    assert sum(res['summary'].values()) == len(res['levels'])
    assert res['draft'] is True
    # todos los criterios del pack presentes (55 A/AA)
    for row in pack['criteria']:
        code = row['criterion'].split(' ')[0]
        assert code in res['levels'], f'falta {code}'
    # borrador declarado y block de firma vacío
    assert 'BORRADOR' in html or 'DRAFT' in html

# overrides: la persona cualificada gana sobre la máquina
res = generate_vpat(pack=pack, product='Demo', overrides={
    '1.1.1': 'supports', '1.2.2': 'not_applicable'}, lang='en')
assert res['levels']['1.1.1'] == 'supports'
assert res['levels']['1.2.2'] == 'not_applicable'
# la firma de la máquina nunca borra el state: el remark sigue citando el fallo
assert 'automated-fail' in res['html'] or 'issue:' in res['html']

# overrides con level desconocido → error amigable
res = generate_vpat(pack=pack, product='Demo', overrides={'1.1.1': 'quizas'})
assert 'error' in res

# sin pack ni reports → error amigable
assert 'error' in generate_vpat(product='Demo')

# desde reports crudos (construye el pack)
res = generate_vpat(reports=[report], product='Demo', lang='es')
assert 'error' not in res and res['pack_sha256']

# paridad es/en del catálogo de levels y de la derivación
assert set(LEVELS['es']) == set(LEVELS['en'])
assert _STATUS_TO_LEVEL['automated-fail'] == 'does_not_support'
assert _STATUS_TO_LEVEL['not-flagged'] == 'not_evaluated'
assert _STATUS_TO_LEVEL['agent-verified'] == 'not_evaluated'  # agente ≠ firma humana
# la evidencia de nivel review NO es un claim de conformidad: la máquina
# jamás imprime Partially Supports (regresión 4-nov: lo hacía)
assert _STATUS_TO_LEVEL['automated-review'] == 'not_evaluated'

# output_path escribe el HTML
output = os.path.join(os.path.dirname(__file__), 'vpat_temp.html')
res = generate_vpat(pack=pack, product='Demo', lang='en', output_path=output)
assert os.path.exists(output) and res.get('saved_to') == output
os.unlink(output)

# ── regresiones de la revisión externa (4-nov) ─────────────────────────────
# 1) un informe 'site' anida los informes por página: el pack NO puede
#    perderlos (antes: automated-fail 0 con fallos reales en las páginas)
site_report = {'mode': 'site', 'url': 'https://example.com/', 'score': 50,
               'summary': {'high': 2, 'medium': 0, 'low': 0},
               'reports': [
                   {'mode': 'static', 'url': 'https://example.com/a', 'score': 40,
                    'summary': {}, 'findings': [
                        {'criterion': '1.1.1 Non-text Content', 'severity': 'high',
                         'signal': 'img_no_alt', 'issue': '1 <img> without alt',
                         'remediation': 'add alt'}]},
                   {'mode': 'rendered', 'url': 'https://example.com/b', 'score': 41,
                    'summary': {}, 'findings': [
                        {'criterion': '1.4.3 Contrast (Minimum)', 'severity': 'high',
                         'signal': 'contrast_fail', 'issue': 'contrast ratio 2.1:1'}]},
               ]}
pack_site = build_pack([site_report])
assert pack_site['summary']['automated-fail'] == 2, pack_site['summary']
# el modo de los SUB-informes cuenta: 1.4.3 (solo medible en rendered) no
# puede quedar not-run cuando el propio crawl lo midió
row_143 = next(c for c in pack_site['criteria'] if c['criterion'].startswith('1.4.3'))
assert row_143['status'] == 'automated-fail', row_143['status']
assert row_143.get('value', {}).get('measured') == '2.1:1'
# …y un crawl puramente estático SÍ deja 1.4.3 not-run (contraste no mirado)
pack_static_crawl = build_pack([{'mode': 'site', 'url': 'https://x/', 'score': 100,
                                 'summary': {}, 'reports': [
                                     {'mode': 'static', 'url': 'https://x/a',
                                      'score': 100, 'summary': {}, 'findings': []}]}])
row_143s = next(c for c in pack_static_crawl['criteria']
                if c['criterion'].startswith('1.4.3'))
assert row_143s['status'] == 'not-run', row_143s['status']
# los artefactos siguen siendo UNO por informe de entrada (el sello no miente)
assert len(pack_site['artifacts']) == 1
assert pack_site['artifacts'][0]['type'] == 'report:site'

# 2) los Remarks citan solo hallazgos VIVOS: lo que el disprover rechazó no
#    es evidencia, y no puede enmascarar al confirmado del mismo código
disproved = {'mode': 'static', 'url': 'https://example.com', 'score': 1,
             'summary': {}, 'findings': [
                 {'criterion': '1.1.1 Non-text Content', 'severity': 'high',
                  'signal': 'img_no_alt', 'issue': 'rejected old snapshot',
                  'remediation': 'x', 'status': 'rejected'},
                 {'criterion': '1.1.1 Non-text Content', 'severity': 'high',
                  'signal': 'img_no_alt', 'issue': 'confirmed live failure',
                  'remediation': 'add alt'},
                 {'criterion': '3.2.1 On Focus', 'severity': 'low',
                  'signal': 'kbd_trap', 'issue': 'low review-level only',
                  'remediation': 'check with a11y_keyboard',
                  'disprover_status': 'not-rechecked'},
             ]}
pack_disp = build_pack([disproved])
res_disp = generate_vpat(pack=pack_disp, product='Demo', lang='en')
assert 'error' not in res_disp
assert res_disp['levels']['1.1.1'] == 'does_not_support'
assert 'confirmed live failure' in res_disp['html']
assert 'rejected old snapshot' not in res_disp['html'], \
    'un hallazgo desmentido jamás se imprime como evidencia viva'
# el not-rechecked tampoco se cita: hay DOS muertos y el vivo manda
assert 'low review-level only' not in res_disp['html']

# 3) nivel review → not_evaluated con la evidencia en Remarks (nunca un
#    Partially Supports impreso por la máquina)
pack_low = build_pack([{'mode': 'static', 'url': 'https://x', 'score': 80,
                        'summary': {}, 'findings': [
                            {'criterion': '3.2.1 On Focus', 'severity': 'low',
                             'signal': 'kbd_trap', 'issue': 'low severity review signal',
                             'remediation': 'check'}]}])
res_low = generate_vpat(pack=pack_low, product='Demo', lang='en')
assert res_low['levels']['3.2.1'] == 'not_evaluated', res_low['levels']['3.2.1']
assert 'low severity review signal' in res_low['html']   # la evidencia SÍ viaja
# la máquina imprime CERO niveles partially_supports: el claim es humano
assert res_low['summary'].get('partially_supports', 0) == 0
assert res_low['summary']['not_evaluated'] == 55

# 4) hostil: severity None / issue None no tumban el pack ni mienten fail
pack_hostil = build_pack([{'mode': 'static', 'url': 'u', 'score': 0,
                           'summary': {}, 'findings': [
                               {'criterion': '1.1.1 Non-text Content',
                                'signal': 'img_no_alt', 'severity': None, 'issue': None},
                               {'criterion': '2.4.4 Link Purpose (In Context)',
                                'signal': 'generic_link', 'severity': 'low', 'issue': None},
                           ]}])
row_111 = next(c for c in pack_hostil['criteria'] if c['criterion'].startswith('1.1.1'))
assert row_111['status'] == 'automated-review', 'sin severidad no hay fallo'
res_h = generate_vpat(pack=pack_hostil, product='Demo', lang='en')
assert 'error' not in res_h and res_h['levels']['1.1.1'] == 'not_evaluated'

# 5) single source del precio del esfuerzo: _MIN desaparece, a11ycrit manda
import a11y_toolkit.a11yevidence as _ev                                # noqa: E402
from a11y_toolkit.a11ycrit import _EFFORT_MINUTES as _EM               # noqa: E402
assert not hasattr(_ev, '_MIN'), '_MIN duplicado: el precio vive en a11ycrit'
assert _ev._EFFORT_MINUTES is _EM
# los totales no derivan con el refactor (pinned también en test_solido)
assert pack['effort_pending']['total_minutes'] == [313, 649]

# 6) statement hermana (RD 1112/EAA): la reclamación se ENLAZA y el reloj
#    se lee UNA vez (una ejecución que cruce medianoche no puede divergir)
from a11y_toolkit import a11ystatement as _stmt                       # noqa: E402
import inspect as _inspect                                             # noqa: E402
_st = _stmt.generate('Ent', 'https://e.example', 'partial',
                     complaints='https://claims.example/p?a=1&b=2', lang='en')
assert '<a href="https://claims.example/p?a=1&amp;b=2">' in _st['html'], \
    'RD 1112/2018 art. 10.1(b): la URL de reclamaciones es un enlace'
_st2 = _stmt.generate('Ent', 'https://e.example', 'partial',
                      complaints='front desk only', lang='en')
assert 'front desk only' in _st2['html'] and '<a href="front' not in _st2['html']
assert _inspect.getsource(_stmt.generate).count('TODAY()') == 1, \
    'el reloj se lee una sola vez por generate()'

print('VPAT OK ✓ (derivación honesta, overrides humanos, hash del pack en el documento, '
      'site crawls contados, hallazgos muertos fuera de Remarks, review ≠ nivel, es/en)')
