#!/usr/bin/env python3
"""Invariantes de diseño — lo que debe ser cierto SIEMPRE, o el test grita.

Nació del análisis de fragilidad (2026-09): tres clases de bug se repitieron
porque nada obligaba a que fueran falsas. Aquí quedan clavadas:
  1. Catálogo de mensajes: es/en parejos, todo hallazgo con _rem, CRIT parejo.
     (El KeyError 'input_img_alt_rem' ya ocurrió una vez.)
  2. Versiones: pyproject == server.VERSION == server.json. (Derivaron a mano
     durante 10 releases.)
  3. Conteos: README/GIF dicen las tools y prompts que hay de verdad.
     (El barrido manual quemó dos sesiones.)
  4. Robustez: el auditor no crashea ante HTML hostil (fuzz determinista).
"""

import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
sys.path.insert(0, ROOT)

# ---------- 1. catálogo ----------
from a11y_toolkit.a11yaudit import T, CRIT, audit_html  # noqa: E402
from a11y_toolkit.a11ydom import _TD  # noqa: E402

es, en = set(T['es']), set(T['en'])
assert es == en, f"catálogo desparejo: solo es={sorted(es-en)[:3]} solo en={sorted(en-es)[:3]}"
_hallazgo = {k for k in es
             if not k.endswith(('_rem', '_nota')) and k not in
             ('limits', 'interp', 'criteria', 'score_note', 'aclarar', 'oscurecer',
              'sin_copia', 'color_invalido', 'region_invalida', 'region_fuera',
              'sin_pixeles', 'carga_error', 'texto_opaco', 'descarga_error')}
sin_rem = sorted(k for k in _hallazgo if f'{k}_rem' not in es)
assert not sin_rem, f"hallazgos sin _rem (KeyError al emitir): {sin_rem}"
assert set(CRIT['es']) == set(CRIT['en']), 'CRIT desparejo es/en'
# lo mismo para el catálogo del modo renderizado
for lang in ('es', 'en'):
    pass  # _TD comparte claves por diseño; la paridad de T ya lo cubre
assert set(_TD['es']) == set(_TD['en']), 'catálogo DOM desparejo'

# ---------- 2. versiones ----------
from a11y_toolkit import server  # noqa: E402
pp = re.search(r'version = "([\d.]+)"', open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()).group(1)
sj = json.load(open(os.path.join(ROOT, 'server.json')))['version']
assert pp == server.VERSION == sj, f'versión derivada: pyproject={pp} server={server.VERSION} server.json={sj}'

# ---------- 3. conteos en las superficies públicas ----------
readme = open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read()
m_intro = re.search(r'(\d+) MCP tools, (\d+) prompts and a skill', readme)
m_tabla = re.search(r'The tools \((\d+)\)', readme)
assert m_intro and int(m_intro.group(1)) == len(server.TOOLS), f'README intro dice {m_intro and m_intro.group(1)}, hay {len(server.TOOLS)}'
assert int(m_intro.group(2)) == len(server._PROMPTS), f'README prompts: {m_intro.group(2)} vs {len(server._PROMPTS)}'
assert m_tabla and int(m_tabla.group(1)) == len(server.TOOLS), f'README tabla: {m_tabla and m_tabla.group(1)} vs {len(server.TOOLS)}'
vis = open(os.path.join(ROOT, 'docs', 'gen-visuals.py'), encoding='utf-8').read()
m_gif = re.search(r'\((\d+) tools · (\d+) prompts\)', vis)
assert m_gif and int(m_gif.group(1)) == len(server.TOOLS) and int(m_gif.group(2)) == len(server._PROMPTS), \
    f'GIF dice {m_gif and m_gif.groups()}, hay {len(server.TOOLS)}+{len(server._PROMPTS)} — regenera docs/gen-visuals.py'
doc_server = server.__doc__
assert all(t['name'] in doc_server for t in server.TOOLS), 'docstring del server incompleto'

# ---------- 3b. tool schema hygiene (the Glama/TDQS penalties, pinned) ----------
for _t in server.TOOLS:
    for _p, _d in _t['inputSchema'].get('properties', {}).items():
        assert _d.get('description'), f"{_t['name']}.{_p} lacks a description"
    assert ' — ' in _t['description'] or _t['name'] == 'a11y_badge', \
        f"{_t['name']} lacks sibling-routing guidance"
    for _k in ('title', 'annotations'):
        assert _t.get(_k), f"{_t['name']} lacks {_k}"

# ---------- 3c. conteos normativos WCAG 2.2 (fijados contra deriva) ----------
from a11y_toolkit.a11ycrit import _C as _CAT, _EFFORT, effort  # noqa: E402
from a11y_toolkit.a11yevidence import MANUAL_AA, empaquetar  # noqa: E402

# el conjunto A/AA normativo (w3.org/TR/WCAG22; 4.1.1 retirado; 3.2.6 y 3.3.7 son A)
_NORM_A = {'1.1.1', '1.2.1', '1.2.2', '1.2.3', '1.3.1', '1.3.2', '1.3.3', '1.4.1', '1.4.2',
           '2.1.1', '2.1.2', '2.1.4', '2.2.1', '2.2.2', '2.3.1', '2.4.1', '2.4.2', '2.4.3',
           '2.4.4', '2.5.1', '2.5.2', '2.5.3', '2.5.4', '3.1.1', '3.2.1', '3.2.2', '3.2.6',
           '3.3.1', '3.3.2', '3.3.7', '4.1.2'}
_NORM_AA = {'1.2.4', '1.2.5', '1.3.4', '1.3.5', '1.4.3', '1.4.4', '1.4.5', '1.4.10', '1.4.11',
            '1.4.12', '1.4.13', '2.4.5', '2.4.6', '2.4.7', '2.4.11', '2.5.7', '2.5.8', '3.1.2',
            '3.2.3', '3.2.4', '3.3.3', '3.3.4', '3.3.8', '4.1.3'}
_NORM = _NORM_A | _NORM_AA
assert len(_NORM) == 55 and len(_NORM_A) == 31 and len(_NORM_AA) == 24, 'fixture normativo corrupto'
_aa = {k for k, v in _CAT.items() if v[0] in ('A', 'AA')}
assert _aa == _NORM, f'catálogo A/AA ≠ normativo: {sorted(_aa ^ _NORM)}'
_nivel_mal = {k: (_CAT[k][0], 'AA' if k in _NORM_AA else 'A') for k in _NORM
              if _CAT[k][0] != ('AA' if k in _NORM_AA else 'A')}
assert not _nivel_mal, f'niveles ≠ normativo: {_nivel_mal}'
assert not ({m.split(' ')[0] for m in MANUAL_AA} - _NORM), 'MANUAL_AA fuera del conjunto A/AA'
assert set(_EFFORT) == _NORM, 'la tabla de esfuerzo debe cubrir exactamente los 55 A/AA'
assert effort('1.4.3')['class'] == 'MAX' and effort('9.9.9') is None
from collections import Counter  # noqa: E402
_dist = Counter(c for c, _ in _EFFORT.values())
assert _dist == Counter({'MIN': 23, 'MED': 19, 'MAX': 13}), f'distribución de esfuerzo derivó: {dict(_dist)}'
assert '51 of 55 A/AA criteria carry automated signals (93%)' in readme, 'claim de cobertura en README'
assert 'of 54' not in readme and '94%' not in readme, 'quedan restos del conteo antiguo en README'
# pack de evidencia: exactamente 55 filas, todas con esfuerzo, totales del seed
_pack = empaquetar([{'mode': 'static', 'url': 'https://t', 'score': 90, 'findings': []}])
assert len(_pack['criteria']) == 55, f'matriz del pack: {len(_pack["criteria"])} filas'
assert all('effort' in m for m in _pack['criteria']), 'fila del pack sin esfuerzo'
assert _pack['effort_pending']['total_minutes'] == [313, 649], \
    f"totales derivados: {_pack['effort_pending']['total_minutes']}"


# ---------- 4. fuzz determinista: HTML hostil no crashea ----------
HOSTILES = [
    '<html><body><p' * 40 + 'x',                       # anidamiento roto
    '<a href="' + 'x' * 5000 + '">l</a>',              # atributo gigante
    '<div aria-labelledby="a b c d e">',               # refs vacías
    '<ul><li><ul><li><div>' * 30,                      # listas profundas sin cerrar
    '<img src=x alt=',                                 # atributo cortado
    '<table><tr><td>' + 'cell' * 2000,                # tabla enorme sin cerrar
    '\x00\x01<html><body>binario',                     # bytes de control
    '<h1><h2><h3><h4><h5><h6><h7>skip',                # h7 inexistente
    '<label for="a"><label for="a"><input id="a">',    # labels anidados
    '<div onclick="f()" role="bottun" aria-hidden="si">',  # sopa de atributos
    '',                                                # vacío
    '<html lang="' + 'e' * 300 + '">',                 # lang absurdo
]
for h in HOSTILES:
    r = audit_html(h, lang='en')
    assert isinstance(r, dict) and ('findings' in r or 'error' in r), f'crasheó con: {h[:40]!r}'

# el diff de snapshots con JSON malformado no traza (vía CLI sí; vía API lanza
# ValueError controlado por el servidor — aquí solo la garantía del auditor)

print('INVARIANTES OK ✓ (catálogo parejo, _rem completo, versiones alineadas, '
      f'conteos = {len(server.TOOLS)}+{len(server._PROMPTS)} en todas las superficies, fuzz hostil sin caídas)')
