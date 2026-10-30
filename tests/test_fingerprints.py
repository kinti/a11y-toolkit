#!/usr/bin/env python3
"""a11y_fingerprints — fingerprints multi-hash de plantillas (gemelas).

Lo que este test clava (nació con el módulo):
  1. DETERMINISMO: mismas páginas → informe idéntico (sin red ni azar).
  2. GEMELAS: mismo esqueleto con texto/ids/urls distintos → UNA plantilla,
     muestra de 1 (el ruido de contenido no parte plantillas).
  3. REDISEÑO: reestructurar la nav → plantilla nueva (la vista structure
     sí discrimina esqueleto).
  4. LOCALIZACIÓN: solo cambiar clases del header → divergencia EXACTA
     (header, classes); solo cambiar un attr en main → (main, attributes).
  5. VOLÁTILES: id/name/href/csrf NO divergen (denylist por diseño); un
     cambio REAL de attr (aria-expanded) sí.
  6. HTML HOSTIL: vacío, cierres huérfanos, landmarks cruzados, attrs
     duplicados — nada rompe el parser.
  7. MUESTRA WCAG-EM: sample_suggestion = un representante por plantilla,
     regla declarada (mínimo lexicográfico), orden estable.
  8. CLI: el subcomando `fingerprints` ejecuta de verdad (vía subprocess).
"""

import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
sys.path.insert(0, ROOT)

from a11y_toolkit.a11yfingerprints import (  # noqa: E402
    fingerprint_html, fingerprint_pages)

# ── fixtures ───────────────────────────────────────────────────────────────
# gemelas: MISMO esqueleto; varían título (texto), href, name/csrf y id —
# justo lo que hoy rompería un hash ingenuo de página completa
TWIN = '''<html lang="en"><head><title>{t}</title></head><body>
<header><nav><ul><li><a href="/x{p}">Home</a></li><li><a href="/y{p}">Docs</a></li></ul></nav></header>
<main><h1>{t}</h1><form><label for="e">Email</label><input id="e" name="csrf-{p}" type="email" autocomplete="email"><button type="submit">Send</button></form></main>
<footer><p>(c) ACME</p></footer></body></html>'''

BASE = '''<html><body><header><nav class="menu main-nav"><a href="/1">H</a></nav></header>
<main><h1>T</h1><p class="lead">x</p></main><footer><p>F</p></footer></body></html>'''

HOSTILES = [
    '',
    '<html><body><div><div></div>',          # sin cerrar
    '</p></p></p>',                          # cierres huérfanos
    '<header><nav></header></nav>',          # landmarks cruzados
    '<img src=x onerror=y>',                 # void con attr sucio
    '<p a=1 a=2 A=3>',                       # attrs duplicados
    '<main><main><main>',                    # landmarks anidados
    '<b><i></b></i><br><hr/><input/>',       # mezcla imposible + self-closed
]

# 1. determinismo
pages = [{'page': 'a.html', 'html': TWIN.format(t='Alpha', p='1')},
         {'page': 'b.html', 'html': TWIN.format(t='Beta', p='2')}]
r1 = fingerprint_pages(pages)
r2 = fingerprint_pages(pages)
assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True), \
    'mismas páginas, fingerprints distintos: no es determinista'
print('1. determinismo ✓')

# 2. gemelas → una plantilla, muestra de 1
twins = [{'page': 'a.html', 'html': TWIN.format(t='Alpha', p='1')},
         {'page': 'b.html', 'html': TWIN.format(t='Beta', p='2')},
         {'page': 'c.html', 'html': TWIN.format(t='Gamma', p='3')}]
r = fingerprint_pages(twins)
assert r['templates_total'] == 1 and r['pages_total'] == 3
assert len(r['templates'][0]['pages']) == 3
assert r['templates'][0]['divergence'] == [], \
    f'contenido/ids/urls variando rompen la plantilla: {r["templates"][0]["divergence"]}'
assert r['sample_suggestion'] == ['a.html']
print('2. gemelas: 3 páginas → 1 plantilla, cero divergencia, muestra de 1 ✓')

# 3. rediseño → plantilla nueva (la estructura discrimina)
redesign = TWIN.format(t='Delta', p='4').replace(
    '<ul><li><a href="/x4">Home</a></li><li>',
    '<div><a href="/x4">Home</a><a href="/z4">More</a></div><ul>')
r = fingerprint_pages(twins + [{'page': 'd.html', 'html': redesign}])
assert r['templates_total'] == 2, 'reestructurar la nav no abrió plantilla nueva'
assert r['sample_suggestion'] == ['a.html', 'd.html']  # ordenada, no por hash
print('3. rediseño: esqueleto distinto → 2 plantillas, muestra de 2 ✓')

# 4. localización exacta de la divergencia
div_pages = [{'page': 'a.html', 'html': BASE},
             {'page': 'b.html', 'html': BASE.replace(
                 'menu main-nav', 'menu main-nav dark')},
             {'page': 'c.html', 'html': BASE.replace(
                 '<p class="lead">x</p>',
                 '<p class="lead" aria-expanded="false">x</p>')}]
r = fingerprint_pages(div_pages)
assert r['templates_total'] == 1
div = {(d['page'], d['region'], d['view']) for d in r['templates'][0]['divergence']}
assert ('b.html', 'header', 'classes') in div, f'falta header/classes: {div}'
assert ('c.html', 'main', 'attributes') in div, f'falta main/attributes: {div}'
assert not any(d[1] == 'footer' or d[1] == 'nav' for d in div), \
    f'divergencia fantasma en regiones intactas: {div}'
print('4. localización: (header, classes) y (main, attributes) exactos ✓')

# 5. volátiles: denylist completa no diverge; cambio real sí
volatil = BASE  # base con id=1 en href (volátil)
vol_pages = [{'page': 'a.html', 'html': volatil},
             {'page': 'b.html', 'html': BASE.replace('href="/1"', 'href="/totally-different"')
                                           .replace('<p>F</p>', '<p id="fresh-99">F</p>')}]
r = fingerprint_pages(vol_pages)
assert r['templates_total'] == 1
assert r['templates'][0]['divergence'] == [], \
    f'href/id (volátiles) partieron o divergieron: {r["templates"][0]["divergence"]}'
real = [{'page': 'a.html', 'html': BASE},
        {'page': 'b.html', 'html': BASE.replace('<a href="/1">H</a>',
                                                '<a href="/1" aria-current="page">H</a>')}]
r = fingerprint_pages(real)
assert {'page': 'b.html', 'region': 'header', 'view': 'attributes'} \
    in r['templates'][0]['divergence'], 'un cambio real de attr no divergió'
print('5. volátiles ignorados / cambio real detectado ✓')

# 6. HTML hostil no rompe (y sigue determinista)
for h in HOSTILES:
    fp = fingerprint_html(h)
    assert fp['template'].startswith('t-')
    assert set(fp['hashes']) == {'structure', 'classes', 'attributes'}
assert json.dumps(fingerprint_html('<div>'), sort_keys=True) == \
       json.dumps(fingerprint_html('<div>'), sort_keys=True)
# landmarks anidados del MISMO tipo: el cierre interno no puede corromper el
# orden externo→interno (el <p> tras el </nav> interno vive en la nav EXTERNA)
fp_nested = fingerprint_html('<nav><aside><nav></nav><p>x</p></aside></nav>')
assert fp_nested['regions'] == ['nav'], \
    f'landmark anidado corrompió la región vigente: {fp_nested["regions"]}'
print(f'6. hostil: {len(HOSTILES)} entradas retorcidas + landmark anidado ✓')

# 7. muestra WCAG-EM: un representante por plantilla, regla declarada
mixed = twins + [{'page': '0-redesign.html', 'html': redesign}]
r = fingerprint_pages(mixed)
reps = [t['representative'] for t in r['templates']]
assert reps == ['0-redesign.html', 'a.html'], \
    f'representante no es el mínimo lexicográfico por plantilla: {reps}'
assert sorted(r['sample_suggestion']) == sorted(reps)
assert len(set(reps)) == r['templates_total']
print('7. muestra: mínimo lexicográfico, un representante por plantilla ✓')

# 8. CLI por subprocess (la vía pública real)
import tempfile  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    for name, page in (('p1.html', twins[0]), ('p2.html', twins[1]),
                       ('p3.html', {'html': redesign})):
        with open(os.path.join(td, name), 'w', encoding='utf-8') as f:
            f.write(page['html'])
    out_path = os.path.join(td, 'report.json')
    rr = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y', 'fingerprints',
                         '--dir', td, '-o', out_path],
                        cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert rr.returncode == 0, rr.stderr[-400:]
    out = json.loads(rr.stdout)
    assert out['mode'] == 'template-fingerprints' and out['templates_total'] == 2
    assert os.path.exists(out_path), 'no escribió el -o'
    assert json.load(open(out_path, encoding='utf-8'))['templates_total'] == 2
    rr_err = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y',
                             'fingerprints'], cwd=ROOT, capture_output=True,
                            text=True, timeout=60)
    assert rr_err.returncode != 0, 'sin páginas debe fallar honestamente'
    # determinismo CROSS-PROCESO: hash seed distinto, salida idéntica (la
    # promesa del producto no vale solo dentro de un mismo intérprete)
    outs = set()
    for seed in ('1', '2'):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        rp = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11y',
                             'fingerprints', '--dir', td],
                            cwd=ROOT, capture_output=True, text=True,
                            timeout=120, env=env)
        assert rp.returncode == 0, rp.stderr[-300:]
        outs.add(rp.stdout)
    assert len(outs) == 1, 'la salida varió con PYTHONHASHSEED: orden de set fugándose'
print('8. CLI `a11ytoolkit fingerprints` ejecuta, -o, exige páginas, cross-proceso ✓')

# nota bilingüe (patrón de mutants: superficie pública inglés, es bajo lang=)
assert fingerprint_pages(pages, lang='es')['note'] != fingerprint_pages(pages)['note']
print('nota es/en ✓')

print('FINGERPRINTS OK ✓ (3 vistas × regiones, gemelas/rediseño/localización, '
      'volátiles a prueba de csrf, hostil domado, CLI real)')
