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

# 1. Toda regla mapeada present id ACT canónico (6 alfanuméricos minúscula —
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
# revisión externa, 3ª pasada: un crawl con portada limpia y un fallo en
# /gallery atribuía el fallo a la PORTADA (el aplanado perdía la URL)
crawl = {'url': 'https://example.com/', 'mode': 'site', 'findings': [], 'reports': [
    {'url': 'https://example.com/gallery', 'findings': [
        {'criterion': '1.1.1', 'severity': 'high', 'signal': 'img_no_alt',
         'issue': 'x'}]}]}
res_c = earl(crawl)
assert len(res_c['@graph']) == 1
assert res_c['@graph'][0]['earl:subject']['url'] == 'https://example.com/gallery', \
    res_c['@graph'][0]['earl:subject']
vacio = earl({'url': 'https://example.com', 'findings': []})
assert vacio['@graph'] == []
assert 'never' in vacio['meta']['note']

from pathlib import Path
from tempfile import TemporaryDirectory
from a11y_toolkit.a11ysarif import from_report

failed = {'url': report['url'], 'error': 'HTTP 503'}
partial = {'mode': 'site', 'url': report['url'], 'reports': [report],
           'page_errors': [dict(failed, url=report['url'] + '/unavailable')]}
with TemporaryDirectory() as directory:
    for command, export in (('earl', earl), ('sarif', from_report)):
        for source in (failed, partial):
            verdict = export(source)
            assert 'error' in verdict and len(verdict) <= 2
            if source is partial:
                assert verdict['pages_failed'] == [partial['page_errors'][0]['url']]
            source_path = Path(directory) / 'input.json'
            output = Path(directory) / 'output.json'
            source_path.write_text(json.dumps(source), encoding='utf-8')
            result = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y', command,
                                     '--from-audit', str(source_path), '-o', str(output)],
                                    capture_output=True, text=True, timeout=20)
            assert result.returncode == 1 and json.loads(result.stdout) == verdict
            assert not output.exists(), output

# 5. CLI --list funciona sin red
out = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11yact', '--list'],
                     capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = json.loads(out.stdout)
assert set(d['act_map']) == set(ACT_MAP)
assert out.returncode == 0

# 6. _NOT_DEAD: única fuente (a11yact) — vpat y sarif filtran con EL MISMO
#    conjunto (regresión 4-nov: cada módulo tenía el suelto y Remarks/SARIF
#    citaban hallazgos desmentidos)
import a11y_toolkit.a11yvpat as _vp                                # noqa: E402
import a11y_toolkit.a11ysarif as _sf                               # noqa: E402
from a11y_toolkit.a11yact import _NOT_DEAD                         # noqa: E402
assert _NOT_DEAD == {'rejected', 'not-rechecked'}
assert _vp._NOT_DEAD is _NOT_DEAD and _sf._NOT_DEAD is _NOT_DEAD

print(f'ACT/EARL OK ✓ ({len(ACT_MAP)} señales mapeadas, {sum(len(v) for v in ACT_MAP.values())} rules; sin rules inventadas, _NOT_DEAD única fuente)')
