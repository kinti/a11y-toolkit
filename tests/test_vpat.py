#!/usr/bin/env python3
"""Tests del generador VPAT 2.5 (reglas de honestidad, derivación, overrides)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a11y_toolkit.a11yaudit import audit_html  # noqa: E402
from a11y_toolkit.a11yevidence import empaquetar  # noqa: E402
from a11y_toolkit.a11yvpat import generar_vpat, NIVELES, _ESTADO_A_NIVEL  # noqa: E402

# informe sintético con fallos reales del motor estático
informe = audit_html('<html><head><title>t</title></head><body>'
                     '<img src="a.png"><button></button>'
                     '<input type="text" name="email"><a href="#">here</a>'
                     '</body></html>')
pack = empaquetar([informe])

for lang in ('en', 'es'):
    res = generar_vpat(pack=pack, producto='Demo App', contacto='a11y@example.com',
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
    # el resumen cuadra con las filas
    assert sum(res['summary'].values()) == len(res['levels'])
    assert res['draft'] is True
    # todos los criterios del pack presentes (55 A/AA)
    for fila in pack['criteria']:
        code = fila['criterion'].split(' ')[0]
        assert code in res['levels'], f'falta {code}'
    # borrador declarado y bloque de firma vacío
    assert 'BORRADOR' in html or 'DRAFT' in html

# overrides: la persona cualificada gana sobre la máquina
res = generar_vpat(pack=pack, producto='Demo', overrides={
    '1.1.1': 'supports', '1.2.2': 'not_applicable'}, lang='en')
assert res['levels']['1.1.1'] == 'supports'
assert res['levels']['1.2.2'] == 'not_applicable'
# la firma de la máquina nunca borra el estado: el remark sigue citando el fallo
assert 'automated-fail' in res['html'] or 'issue:' in res['html']

# overrides con nivel desconocido → error amigable
res = generar_vpat(pack=pack, producto='Demo', overrides={'1.1.1': 'quizas'})
assert 'error' in res

# sin pack ni informes → error amigable
assert 'error' in generar_vpat(producto='Demo')

# desde informes crudos (construye el pack)
res = generar_vpat(reports=[informe], producto='Demo', lang='es')
assert 'error' not in res and res['pack_sha256']

# paridad es/en del catálogo de niveles y de la derivación
assert set(NIVELES['es']) == set(NIVELES['en'])
assert _ESTADO_A_NIVEL['automated-fail'] == 'does_not_support'
assert _ESTADO_A_NIVEL['not-flagged'] == 'not_evaluated'
assert _ESTADO_A_NIVEL['agent-verified'] == 'not_evaluated'  # agente ≠ firma humana

# output_path escribe el HTML
salida = os.path.join(os.path.dirname(__file__), 'vpat_temp.html')
res = generar_vpat(pack=pack, producto='Demo', lang='en', output_path=salida)
assert os.path.exists(salida) and res.get('guardado_en') == salida
os.unlink(salida)

print('VPAT OK ✓ (derivación honesta, overrides humanos, hash del pack en el documento, es/en)')
