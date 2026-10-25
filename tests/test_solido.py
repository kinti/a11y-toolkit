#!/usr/bin/env python3
"""Invariantes de diseño — lo que debe ser cierto SIEMPRE, o el test grita.

Nació del análisis de fragilidad (2026-09): tres clases de bug se repitieron
porque nada obligaba a que fueran falsas. Aquí quedan clavadas:
  1. Catálogo de mensajes: es/en parejos, todo finding con _rem, CRIT parejo.
     (El KeyError 'input_img_alt_rem' already ocurrió una vez.)
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# ---------- 1. catálogo ----------
from a11y_toolkit.a11yaudit import T, CRIT, audit_html  # noqa: E402
from a11y_toolkit.a11ydom import _TD  # noqa: E402

es, en = set(T['es']), set(T['en'])
assert es == en, f"catálogo desparejo: solo es={sorted(es-en)[:3]} solo en={sorted(en-es)[:3]}"
_hallazgo = {k for k in es
             if not k.endswith(('_rem', '_nota')) and k not in
             ('limits', 'interp', 'criteria', 'score_note', 'lightening', 'darkening',
              'no_post_copy', 'invalid_color', 'invalid_region', 'region_outside',
              'no_pixels', 'load_error', 'opaque_text', 'fetch_error',
              'rendered_reason')}   # dato del namespace audit, no un finding
sin_rem = sorted(k for k in _hallazgo if f'{k}_rem' not in es)
assert not sin_rem, f"findings sin _rem (KeyError al emitir): {sin_rem}"
assert set(CRIT['es']) == set(CRIT['en']), 'CRIT desparejo es/en'
# enlace oficial Understanding por criterio (5.12): el catálogo nunca queda
# con un criterio sin su fuente en w3.org
from a11y_toolkit.a11ycrit import _UNDERSTANDING, _C, _SIGNAL_CRIT, criterion as _crit  # noqa: E402
_sin_link = [c for c in _C if c not in _UNDERSTANDING]
assert not _sin_link, f'criterios sin enlace Understanding: {_sin_link}'
# biblia COMPLETA: los 86 criterios de WCAG 2.2 (A/AA/AAA) contra la fuente
# canónica ingesta da (w3c/wcag, snapshot generado por scripts/wcag22_ingest.py)
_sc_src = json.load(open(os.path.join(ROOT, 'docs', 'wcag22-criteria-source.json'),
                         encoding='utf-8'))['criteria']
_fuente = {s['num']: s['level'] for s in _sc_src}
assert len(_fuente) == 86 and len(_C) == 86, f'biblia incompleta: fuente {len(_fuente)}, catálogo {len(_C)}'
_des = {c: v[0] for c, v in _C.items() if c in _fuente and _fuente[c] != v[0]}
assert not _des, f'niveles ≠ fuente canónica: {_des}'
assert set(_C) == set(_fuente), 'el catálogo y la fuente canónica divergen'
_r = _crit('1.4.3', 'en')
assert _r['understanding'].startswith('https://www.w3.org/WAI/WCAG22/Understanding/') and _r['understanding'].endswith('.html')

# 5.12: mapa señal→criterio sincronizado con los puntos de emisión que el regex
# alcanza (llamadas add() y dicts literales) — una señal así emitida sin entrada
# (o con criterio cambiado) rompe la suite. Emisiones multi-línea o de clave
# variable (target_small, vtt_*) se mantienen manualmente y se listan abajo.
import glob as _glob
import re as _re
_CODE = _re.compile(r"(?:\.get\('|'criterion':\s*'|,\s*')([\d]\.[\d]{1,2}\.[\d]{1,2})")
_derivado = {}
for _f in _glob.glob(os.path.join(ROOT, 'a11y_toolkit', '*.py')):
    _lineas = open(_f, encoding='utf-8').read().splitlines()
    for _i, _l in enumerate(_lineas):
        for _m in _re.finditer(r"(?:_add_ej|_add|add_ej|add|_agrega|agrega)\(\s*(?:findings|hallazgos)?\s*,?\s*(?:lang\s*,\s*)?[^,]*,\s*'([\d.]+)'\s*,\s*'([a-z0-9_]+)'", _l):
            _derivado[_m.group(2)] = _m.group(1)
        for _m in _re.finditer(r"'signal':\s*'([a-z0-9_]+)'", _l):
            _antes = _CODE.findall(' '.join(_lineas[max(0, _i-4):_i]) + ' ' + _l[:_m.start()])
            _despues = _CODE.findall(_l[_m.end():] + ' ' + ' '.join(_lineas[_i+1:_i+3]))
            if _antes:
                _derivado[_m.group(1)] = _antes[-1]
            elif _despues:
                _derivado[_m.group(1)] = _despues[0]
        for _m in _re.finditer(r"'([a-z0-9_]{5,45})':\s*\('([\d.]+)',\s*'(?:high|medium|low)'", _l):
            _derivado[_m.group(1)] = _m.group(2)
assert set(_derivado) <= set(_SIGNAL_CRIT), (
    f'señales emitidas fuera del mapa: {sorted(set(_derivado) - set(_SIGNAL_CRIT))[:5]}')
_div = [(k, _derivado[k], _SIGNAL_CRIT[k]) for k in _derivado if _SIGNAL_CRIT[k] != _derivado[k]]
assert not _div, f'señal→criterio divergente entre código y mapa: {_div[:5]}'
# emisiones no derivables por regex (multi-línea/clave variable) — mantenimiento manual
for _manual in ('target_small', 'vtt_malformed', 'vtt_overlap', 'vtt_too_fast'):
    assert _manual in _SIGNAL_CRIT, f'señal manual {_manual} perdida del mapa'
# toda señal con regla ACT present criterio, y las URLs/status son honestos
from a11y_toolkit.a11yact import ACT_MAP, act_rules_for
_sin = sorted(set(ACT_MAP) - set(_SIGNAL_CRIT))
assert not _sin, f'señales ACT sin criterio: {_sin}'
for _senal in ACT_MAP:
    for _r in act_rules_for(_senal):
        assert _r['url'].startswith('https://www.w3.org/WAI/standards-guidelines/act/rules/') and _r['url'].endswith('/')
        assert _r['status'] in ('published', 'proposed')

# lo mismo para el catálogo del modo renderizado
for lang in ('es', 'en'):
    pass  # _TD comparte claves por diseño; la paridad de T already lo cubre
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
from a11y_toolkit.a11yevidence import MANUAL_AA, build_pack  # noqa: E402
from a11y_toolkit.a11yjourney import _J  # noqa: E402

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
assert not _nivel_mal, f'levels ≠ normativo: {_nivel_mal}'
assert not ({m.split(' ')[0] for m in MANUAL_AA} - _NORM), 'MANUAL_AA removed del conjunto A/AA'
assert set(_EFFORT) == _NORM, 'la tabla de esfuerzo debe cubrir exactamente los 55 A/AA'
assert effort('1.4.3')['class'] == 'MAX' and effort('9.9.9') is None
assert set(_J['es']) == set(_J['en']), 'catálogo journey desparejo'
assert all(_J['es'][k][0] == _J['en'][k][0] and _J['es'][k][1] == _J['en'][k][1] for k in _J['en']), 'journey: criterion/severidad divergen'
from collections import Counter  # noqa: E402
_dist = Counter(c for c, _ in _EFFORT.values())
assert _dist == Counter({'MIN': 23, 'MED': 19, 'MAX': 13}), f'distribución de esfuerzo derivó: {dict(_dist)}'
assert '51 of 55 A/AA criteria carry automated signals (93%)' in readme, 'claim de cobertura en README'
_tools_doc = open(os.path.join(ROOT, 'docs', 'tools.md'), encoding='utf-8').read()
_faltan_tabla = [t['name'] for t in server.TOOLS if f'[`{t["name"]}`](docs/tools.md' not in readme]
assert not _faltan_tabla, f'tools sin fila en la tabla del README: {_faltan_tabla}'
_faltan_doc = [t['name'] for t in server.TOOLS if f'#### `{t["name"]}`' not in _tools_doc]
assert not _faltan_doc, f'tools sin entry completa en docs/tools.md: {_faltan_doc}'
_faltan_prompts = [p2['name'] for p2 in server._PROMPTS if f'`{p2["name"]}`' not in readme]
assert not _faltan_prompts, f'prompts sin entry en README: {_faltan_prompts}'
assert 'of 54' not in readme and '94%' not in readme, 'quedan restos del conteo antiguo en README'
# pack de evidencia: exactamente 55 rows, todas con esfuerzo, totales del seed
_pack = build_pack([{'mode': 'static', 'url': 'https://t', 'score': 90, 'findings': []}])
assert len(_pack['criteria']) == 55, f'matriz del pack: {len(_pack["criteria"])} rows'
assert all('effort' in m for m in _pack['criteria']), 'row del pack sin esfuerzo'
assert _pack['effort_pending']['total_minutes'] == [313, 649], \
    f"totales derivados: {_pack['effort_pending']['total_minutes']}"


# ---------- 3d. ARCHITECTURE.md: el mapa no puede derivar ----------
_mapa = open(os.path.join(ROOT, 'docs', 'ARCHITECTURE.md'), encoding='utf-8').read()
_mods = [f[:-3] for f in os.listdir(os.path.join(ROOT, 'a11y_toolkit'))
         if f.endswith('.py') and f != '__init__.py']
_sin_mapa = [m for m in _mods if f'`{m}.py`' not in _mapa]
assert not _sin_mapa, f'módulos ausentes del mapa (docs/ARCHITECTURE.md): {_sin_mapa}'
assert 'D12' in _mapa and 'T12' in _mapa, 'el mapa perdió secciones (decisiones/trampas)'
assert f'{len(server.TOOLS)} tools' in _mapa or f'{len(server.TOOLS)} MCP' in _mapa, 'el mapa no refleja el conteo de tools'

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

# ---------- 5. higiene: lo interno no entra en el repo público ----------
# 2026-10: .zcodeignore (fichero que el editor escribe en el workspace y que
# lista rutas internas) viajó barrida por git add -A en 23 releases, desde
# v4.0.1. Clavado: no vuelve a trackearse, y el nombre de ninguna ubicación
# interna aparece en fichero trackeado alguno (el hook bloquea al commit).
_tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.split()
assert '.zcodeignore' not in _tracked, '.zcodeignore trackeada — git rm --cached .zcodeignore'
_aguja = b'a11y-' + b'drafts'  # partida: el propio test no contiene el literal que busca
for _f in _tracked:
    with open(os.path.join(ROOT, _f), 'rb') as _fh:
        assert _aguja not in _fh.read().lower(), f'nombre de ubicación interna publicado en {_f}'

print('INVARIANTES OK ✓ (catálogo parejo, _rem completo, versiones alineadas, '
      f'conteos = {len(server.TOOLS)}+{len(server._PROMPTS)} en todas las superficies, '
      'fuzz hostil sin caídas, superficie interna limpia)')
