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

# output_path escribe el HTML
output = os.path.join(os.path.dirname(__file__), 'vpat_temp.html')
res = generate_vpat(pack=pack, product='Demo', lang='en', output_path=output)
assert os.path.exists(output) and res.get('saved_to') == output
os.unlink(output)

print('VPAT OK ✓ (derivación honesta, overrides humanos, hash del pack en el documento, es/en)')
