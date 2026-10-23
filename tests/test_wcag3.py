#!/usr/bin/env python3
"""WCAG 3 preview — invariantes de honestidad y cobertura.

Lo que este test clava (nació con la tool en 5.14.0):
  1. COBERTURA: todo criterio alcanzable por señales del toolkit tiene su
     mapeo a outcomes del borrador (un hallazgo mapeable nunca cae a
     unmapped por descuido del mapa).
  2. INTEGRIDAD DEL REGISTRO: cada outcome referido existe en _OUTCOMES con
     el nombre exacto del borrador; el draft metadata cita el TR real.
  3. HONESTIDAD ESTRUCTURAL: la salida NUNCA lleva score/tier/claim — ni
     como clave ni anidada; el disclaimer/mapping_note están presentes.
  4. ROBUSTEZ: informes hostiles (None, sin findings, señales desconocidas,
     findings sin criterion) no crashean y se reportan como unmapped/error.
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
sys.path.insert(0, ROOT)

from a11y_toolkit.a11ywcag3 import preview, _OUTCOMES, _CRIT_OUTCOME, DRAFT  # noqa: E402
from a11y_toolkit.a11ycrit import _SIGNAL_CRIT  # noqa: E402
from a11y_toolkit.a11yaudit import audit_html  # noqa: E402

# 1. cobertura: 100% de los criterios alcanzables por señales
_alcanzables = set(_SIGNAL_CRIT.values())
_sin_cubrir = sorted(_alcanzables - set(_CRIT_OUTCOME))
assert not _sin_cubrir, f'criterios alcanzables sin outcome WCAG 3: {_sin_cubrir}'
# y todo criterio mapeado es un criterio real del catálogo (no typos)
from a11y_toolkit.a11ycrit import _C  # noqa: E402
_mal_codigo = sorted(set(_CRIT_OUTCOME) - set(_C))
assert not _mal_codigo, f'mapeo con criterios inexistentes: {_mal_codigo}'

# 2. integridad del registro de outcomes
_rotas = [(c, o) for c, outs in _CRIT_OUTCOME.items() for o in outs if o not in _OUTCOMES]
assert not _rotas, f'outcomes referidos que no existen: {_rotas}'
assert all(_OUTCOMES[o].strip() for o in _OUTCOMES), 'outcome sin nombre'
assert len(_OUTCOMES) == 46, f'registro divergente del draft: {len(_OUTCOMES)} outcomes (re-baseline pendiente)'
assert DRAFT['url'] == 'https://www.w3.org/TR/wcag-3.0/' and DRAFT['draft_date'] == '10 September 2026'


def _sin_score(nodo, ruta='root'):
    """Recorre: ninguna clave se llama score/tier/level con valor de claim."""
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            assert k not in ('score', 'tier', 'conformance'), f'clave prohibida {ruta}.{k}'
            _sin_score(v, f'{ruta}.{k}')
    elif isinstance(nodo, list):
        for i, v in enumerate(nodo):
            _sin_score(v, f'{ruta}[{i}]')


# 3. round-trip real: auditar de verdad y previsualizar en ambos idiomas
for lang in ('en', 'es'):
    rep = audit_html('<html lang="en"><head><title>t</title></head><body>'
                     '<img src="x"><a href="#" onclick="f()">click</a>'
                     '<input type="text"></body></html>', lang=lang)
    p = preview(rep, lang=lang)
    assert p['mode'] == 'wcag3-preview' and p['lang'] == lang
    assert p['counts']['findings_total'] == len(rep['findings'])
    assert p['counts']['findings_mapped'] + p['counts']['findings_unmapped'] == p['counts']['findings_total']
    assert p['counts']['outcomes_touched'] == len(p['outcomes'])
    assert p['disclaimer'] and p['mapping_note'] and p['no_score']
    assert p['draft']['url'].startswith('https://www.w3.org/TR/')
    _sin_score(p)
    # cada outcome: nombre del registro exacto, señales y criterios 2.2
    for o in p['outcomes']:
        num, nombre = o['outcome'].split(' ', 1)
        assert _OUTCOMES[num] == nombre, f'nombre divergente: {o["outcome"]}'
        assert o['findings'] == sum(o['severity'].values())
        assert o['criteria_22'] and o['signals']

# sumatorio por severidad global coherente con el informe de origen: el mapa
# es n:m (p. ej. 1.1.1 → 2 outcomes), así que el total por outcome puede
# SUPERAR el de findings mapeados — nunca ser menor
rep = audit_html('<html><body><img src="x"><video src="v"></video></body></html>', lang='en')
p = preview(rep, lang='en')
_tot = {s: sum(o['severity'][s] for o in p['outcomes']) for s in ('high', 'medium', 'low')}
assert sum(_tot.values()) >= p['counts']['findings_mapped'], 'severidades descuadradas'
# un hallazgo n:m (1.1.1 → 2 outcomes) cuenta en ambos: el total por outcome
# puede superar el de findings — pero nunca ser menor
for o in p['outcomes']:
    assert o['findings'] >= 1

# 4. hostiles
assert 'error' in preview(None)
assert 'error' in preview({'sin': 'findings'})
# severidades deformes: 'findings'/'signals' como severity NO pueden colarse
# en los acumuladores (corrupción de conteos) ni crashear (TypeError set+=int)
p_hostil = preview({'findings': [
    {'signal': 'no_existe', 'severity': 'high'},
    {'criterion': '9.9.9 Nada', 'severity': 'low'},
    'no-dict',
    {'criterion': '1.1.1 Non-text Content', 'signal': 'img_no_alt', 'severity': 'findings'},
    {'criterion': '1.1.1 Non-text Content', 'signal': 'img_no_alt', 'severity': 'signals'},
    {'criterion': '1.1.1 Non-text Content', 'signal': 'img_no_alt', 'severity': ''},
]}, lang='en')
assert p_hostil['counts']['findings_unmapped'] == 3 and p_hostil['counts']['findings_mapped'] == 3
assert len(p_hostil['unmapped']) == 3
for o in p_hostil['outcomes']:  # los 3 hallazgos 1.1.1 cuentan UNA vez cada uno
    # (ni inflados por severity='findings' ni TypeError por severity='signals')
    assert o['findings'] == 3 and sum(o['severity'].values()) == 0
p2 = p_hostil
# fallback señal→criterio cuando el finding no trae criterion legible
p3 = preview({'findings': [{'signal': 'img_no_alt', 'severity': 'high'}]}, lang='en')
assert p3['counts']['findings_mapped'] == 1
assert p3['outcomes'][0]['criteria_22'] == ['1.1.1']

# locales: disclaimer presente y distinto por idioma (paridad la pinnea test_locales)
pe, ps = preview({'findings': []}, 'en'), preview({'findings': []}, 'es')
assert pe['disclaimer'] != ps['disclaimer']
assert '10 September 2026' in pe['disclaimer'] and '10 de septiembre de 2026' in ps['disclaimer']

# invoke MCP: el contrato del server entrega el mismo modo
from a11y_toolkit import server  # noqa: E402
_rep = {'mode': 'static', 'url': 'https://t', 'findings': [
    {'severity': 'high', 'criterion': '1.1.1 Non-text Content', 'signal': 'img_no_alt',
     'issue': 'x', 'remediation': 'y'}]}
_out = json.loads(server.invoke('a11y_wcag3_preview', {'report': _rep, 'lang': 'en'})['content'][0]['text'])
assert _out['mode'] == 'wcag3-preview' and _out['counts']['findings_mapped'] == 1

print('WCAG3 PREVIEW OK ✓ (mapa 100% de señales, 46 outcomes exactos, sin score '
      'por construcción, hostil cubierto)')
