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
import tomllib

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

# ---------- 1. catálogo ----------
from a11yaudit import T, CRIT, audit_html  # noqa: E402
from a11ydom import _TD  # noqa: E402

es, en = set(T['es']), set(T['en'])
assert es == en, f"catálogo desparejo: solo es={sorted(es-en)[:3]} solo en={sorted(en-es)[:3]}"
_hallazgo = {k for k in es
             if not k.endswith(('_rem', '_nota')) and k not in
             ('limites', 'interp', 'criterios', 'score_nota', 'aclarar', 'oscurecer',
              'sin_copia', 'color_invalido', 'region_invalida', 'region_fuera',
              'sin_pixeles', 'carga_error', 'texto_opaco')}
sin_rem = sorted(k for k in _hallazgo if f'{k}_rem' not in es)
assert not sin_rem, f"hallazgos sin _rem (KeyError al emitir): {sin_rem}"
assert set(CRIT['es']) == set(CRIT['en']), 'CRIT desparejo es/en'
# lo mismo para el catálogo del modo renderizado
for lang in ('es', 'en'):
    pass  # _TD comparte claves por diseño; la paridad de T ya lo cubre
assert set(_TD['es']) == set(_TD['en']), 'catálogo DOM desparejo'

# ---------- 2. versiones ----------
import server  # noqa: E402
pp = tomllib.load(open(os.path.join(AQUI, 'pyproject.toml'), 'rb'))['project']['version']
sj = json.load(open(os.path.join(AQUI, 'server.json')))['version']
assert pp == server.VERSION == sj, f'versión derivada: pyproject={pp} server={server.VERSION} server.json={sj}'

# ---------- 3. conteos en las superficies públicas ----------
readme = open(os.path.join(AQUI, 'README.md'), encoding='utf-8').read()
m_intro = re.search(r'\*\*(\d+) MCP tools \+ (\d+) prompts', readme)
m_tabla = re.search(r'The tools \((\d+)\)', readme)
assert m_intro and int(m_intro.group(1)) == len(server.TOOLS), f'README intro dice {m_intro and m_intro.group(1)}, hay {len(server.TOOLS)}'
assert int(m_intro.group(2)) == len(server._PROMPTS), f'README prompts: {m_intro.group(2)} vs {len(server._PROMPTS)}'
assert m_tabla and int(m_tabla.group(1)) == len(server.TOOLS), f'README tabla: {m_tabla and m_tabla.group(1)} vs {len(server.TOOLS)}'
vis = open(os.path.join(AQUI, 'docs', 'gen-visuals.py'), encoding='utf-8').read()
m_gif = re.search(r'\((\d+) tools · (\d+) prompts\)', vis)
assert m_gif and int(m_gif.group(1)) == len(server.TOOLS) and int(m_gif.group(2)) == len(server._PROMPTS), \
    f'GIF dice {m_gif and m_gif.groups()}, hay {len(server.TOOLS)}+{len(server._PROMPTS)} — regenera docs/gen-visuals.py'
doc_server = server.__doc__
assert all(t['name'] in doc_server for t in server.TOOLS), 'docstring del server incompleto'

# ---------- 4. fuzz determinista: HTML hostil no crashea ----------
HOSTILES = [
    '<html><body><p' * 40 + 'x',                       # anidamiento roto
    '<a href="' + 'x' * 5000 + '">l</a>',              # atributo gigante
    '<div aria-labelledby="a b c d e">',               # refs vacías
    '<ul><li><ul><li><div>' * 30,                      # listas profundas sin cerrar
    '<img src=x alt=',                                 # atributo cortado
    '<table><tr><td>' + 'celda' * 2000,                # tabla enorme sin cerrar
    '\x00\x01<html><body>binario',                     # bytes de control
    '<h1><h2><h3><h4><h5><h6><h7>skip',                # h7 inexistente
    '<label for="a"><label for="a"><input id="a">',    # labels anidados
    '<div onclick="f()" role="bottun" aria-hidden="si">',  # sopa de atributos
    '',                                                # vacío
    '<html lang="' + 'e' * 300 + '">',                 # lang absurdo
]
for h in HOSTILES:
    r = audit_html(h, lang='en')
    assert isinstance(r, dict) and ('hallazgos' in r or 'error' in r), f'crasheó con: {h[:40]!r}'

# el diff de snapshots con JSON malformado no traza (vía CLI sí; vía API lanza
# ValueError controlado por el servidor — aquí solo la garantía del auditor)

print('INVARIANTES OK ✓ (catálogo parejo, _rem completo, versiones alineadas, '
      f'conteos = {len(server.TOOLS)}+{len(server._PROMPTS)} en todas las superficies, fuzz hostil sin caídas)')
