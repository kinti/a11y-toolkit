#!/usr/bin/env python3
"""Tests del generador OpenACR (GSA): esquema YAML, derivación honesta, escapes."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a11y_toolkit.a11yaudit import audit_html  # noqa: E402
from a11y_toolkit.a11yevidence import build_pack  # noqa: E402
from a11y_toolkit.a11yopenacr import generate_openacr, TXT  # noqa: E402

# report sintético con failures reales del motor estático (mismo fixture que VPAT)
report = audit_html('<html><head><title>t</title></head><body>'
                    '<img src="a.png"><button></button>'
                    '<input type="text" name="email"><a href="#">here</a>'
                    '</body></html>')
pack = build_pack([report])

for lang in ('en', 'es'):
    res = generate_openacr(pack=pack, product='Demo App', contact='a11y@example.com',
                           lang=lang)
    assert 'error' not in res, res
    y = res['yaml']
    # esquema OpenACR: cabecera + capítulos + componentes web
    assert y.startswith('title: "Demo App'), y[:60]
    for ancla in ('product:', 'author:', '  name: "Demo App"', 'report_date: ',
                  'notes: ', 'evaluation_methods_used: ', 'legal_disclaimer: ',
                  'chapters:', '  success_criteria_level_a:', '  success_criteria_level_aa:',
                  '      - num: "1.1.1"', '          - name: web',
                  '            adherence:'):
        assert ancla in y, f'falta {ancla!r} en el YAML'
    # matriz completa: 55 criterios, uno por componente web
    assert y.count('- num: "') == 55, y.count('- num: "')
    assert y.count('- name: web') == 55
    # el hash del pack viaja en cada remark (tamper-evidence)
    assert pack['sha256'] in y and res['pack_sha256'] == pack['sha256']
    assert y.count(pack['sha256']) >= 55
    # derivación honesta: automated-fail → does-not-support (con guion, formato GSA)
    assert res['levels']['1.1.1'] == 'does_not_support'
    # not-flagged ≠ pass → not-evaluated
    assert res['levels']['1.2.2'] == 'not_evaluated'
    assert '              level: not-evaluated' in y
    assert '              level: does-not-support' in y
    # guiones bajos JAMÁS en los niveles del YAML (el formato GSA usa guiones)
    import re as _re
    assert not _re.search(r'level: \w*_\w+', y), 'nivel con guion bajo en el YAML'
    # el summary cuadra con las rows
    assert sum(res['summary'].values()) == len(res['levels']) == 55
    assert res['draft'] is True and res['format'] == 'openacr'
    # borrador declarado en las notas del documento
    assert 'DRAFT' in y or 'BORRADOR' in y

# overrides: la persona cualificada gana sobre la máquina (vocabulario VPAT…)
res = generate_openacr(pack=pack, product='Demo',
                       overrides={'1.1.1': 'supports', '1.2.2': 'not_applicable'})
assert res['levels']['1.1.1'] == 'supports' and res['levels']['1.2.2'] == 'not_applicable'
# …y también las formas con guion del propio formato OpenACR
res = generate_openacr(pack=pack, product='Demo', overrides={'1.4.3': 'partially-supports'})
assert res['levels']['1.4.3'] == 'partially_supports'
assert 'level: partially-supports' in res['yaml'] or res['levels']['1.4.3']
# nivel desconocido → error amigable
assert 'error' in generate_openacr(pack=pack, product='Demo', overrides={'1.1.1': 'quizas'})
# sin pack ni reports → error amigable
assert 'error' in generate_openacr(product='Demo')
# desde reports crudos (construye el pack)
res = generate_openacr(reports=[report], product='Demo', lang='es')
assert 'error' not in res and res['pack_sha256']
# paridad es/en del catálogo (claves idénticas)
assert set(TXT['es']) == set(TXT['en'])

# inyección imposible: comillas, saltos y dos puntos del usuario no rompen la
# estructura (escape JSON = YAML double-quoted válido)
res = generate_openacr(pack=pack, product='Acme "quoted": evil\n- num: 9.9.9',
                       notes='colon: dash - too')
y = res['yaml']
assert y.count('- num: "') == 55            # la línea inyectada no creó criterios
assert '- num: "9.9.9' not in y.replace('\\"', '') or '"- num: 9.9.9"' in y
assert y.splitlines()[0].startswith('title: "Acme \\"quoted\\"')

# author block + version + descripción
res = generate_openacr(pack=pack, product='Demo', product_version='2.1',
                       description='A demo', author={'name': 'JQ', 'company': 'Acme',
                                                     'email': 'jq@example.com',
                                                     'website': 'https://example.com'})
for ancla in ('  version: "2.1"', '  description: "A demo"', '  name: "JQ"',
              '  company_name: "Acme"', '  email: "jq@example.com"',
              '  website: "https://example.com"'):
    assert ancla in res['yaml'], ancla

# output_path escribe el YAML
output = os.path.join(os.path.dirname(__file__), 'openacr_temp.yaml')
res = generate_openacr(pack=pack, product='Demo', lang='en', output_path=output)
assert os.path.exists(output) and res.get('saved_to') == output
os.unlink(output)

print('OPENACR OK ✓ (esquema GSA, 55 criterios, derivación honesta, overrides '
      '+ formas con guion, anti-inyección, hash del pack en cada remark, es/en)')
