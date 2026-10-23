#!/usr/bin/env python3
"""Tests del mapeo ACT Rules y la exportación EARL."""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a11y_toolkit.a11yact import ACT_MAP, ACT_NOTES, earl, act_ids  # noqa: E402
from a11y_toolkit.a11yaudit import T as _TS  # noqa: E402
from a11y_toolkit.a11ydom import _TD  # noqa: E402

# 1. Toda regla mapeada tiene id ACT canónico (6 alfanuméricos minúscula —
#    p. ej. afw4f7 incluye una 'w': los ids ACT no son hexadecimales) y toda
#    señal existe en algún catálogo
for signal, rules in ACT_MAP.items():
    assert signal in _TS['es'] or signal in _TD['es'], f'señal huérfana: {signal}'
    for rid, name in rules:
        assert re.fullmatch(r'[0-9a-z]{6}', rid), f'id no canónico: {rid}'
        assert name and not name.endswith('.')

# 2. Las notas de honestidad solo cubren señales mapeadas
assert set(ACT_NOTES) <= set(ACT_MAP)

# 3. act_ids: vacío para señales sin regla publicada (nunca se inventa)
assert act_ids('no_existe') == []
assert '23a2a8' in act_ids('img_no_alt')

# 4. EARL: high/medium → failed, low → cantTell, señales sin mapeo se omiten
report = {
    'url': 'https://example.com', 'mode': 'static', 'score': 64,
    'findings': [
        {'criterion': '1.1.1 Non-text Content', 'severity': 'high',
         'signal': 'img_no_alt', 'issue': '2 <img> without alt'},
        {'criterion': '2.4.4 Link Purpose', 'severity': 'low',
         'signal': 'generic_link', 'issue': 'generic links'},   # sin mapeo ACT → omitido
        {'criterion': '2.2.1 Timing Adjustable', 'severity': 'low',
         'signal': 'meta_refresh', 'issue': 'refresh 5s'},
        {'criterion': '1.1.1', 'severity': 'high', 'signal': 'img_no_alt',
         'issue': 'x', 'status': 'rejected'},                    # desmentido → omitido
    ],
}
res = earl(report)
assert isinstance(res['@graph'], list)
assert len(res['@graph']) == 2, res['@graph']  # img_no_alt failed + meta_refresh cantTell
outcomes = {a['earl:result']['outcome'] for a in res['@graph']}
assert outcomes == {'earl:failed', 'earl:cantTell'}, outcomes
a0 = res['@graph'][0]
assert a0['earl:test']['url'].startswith('https://www.w3.org/WAI/standards-guidelines/act/rules/23a2a8/')
assert a0['earl:subject']['url'] == 'https://example.com'
assert a0['earl:mode'] == 'earl:automatic'
# la ausencia de findings nunca se afirma como pass
vacio = earl({'url': 'https://example.com', 'findings': []})
assert vacio['@graph'] == []
assert 'never' in vacio['meta']['note']

# 5. CLI --list funciona sin red
out = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11yact', '--list'],
                     capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = json.loads(out.stdout)
assert set(d['act_map']) == set(ACT_MAP)
assert out.returncode == 0

print(f'ACT/EARL OK ✓ ({len(ACT_MAP)} señales mapeadas, {sum(len(v) for v in ACT_MAP.values())} rules; sin rules inventadas)')
