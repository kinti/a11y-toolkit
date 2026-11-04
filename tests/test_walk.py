#!/usr/bin/env python3
"""Tests del pase perceptual (contrast_walk, `contrast-dom --walk`) contra un
fixture local file://: umbral large-text por font computada, muestreo por
píxeles del fondo con imagen, delta de esquema de color (dark).

Se auto-omiten si Playwright no está instalado (misma doctrina que test_dom:
el núcleo cero-dependencias ya está cubierto por las suites estáticas).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# ── herméticos del pase de foco del snapshot (2026-11): corren SIEMPRE ──────
# Regresión: dos enfocables con la MISMA firma (dos botones-icono sin name,
# un Edit por fila) truncaban el walk a la segunda aparición; y el diff
# colapsaba claves duplicadas («sin cambios» ante una duplicación).
from a11y_toolkit.a11ydiff import (FOCUS_KEY_JS, _walk_focus,  # noqa: E402
                                   _WALK_STAMP_JS, _WALK_IS_STAMPED_JS,
                                   _WALK_CLEAN_JS, diff)

# 0a. las expresiones de parada son estáticas y por IDENTIDAD de elemento
assert 'dataset.__a11yWalk' in _WALK_STAMP_JS and 'dataset' in _WALK_IS_STAMPED_JS
assert "__a11yWalk === '0'" in _WALK_IS_STAMPED_JS
for _js in (_WALK_STAMP_JS, _WALK_IS_STAMPED_JS, _WALK_CLEAN_JS):
    assert isinstance(_js, str) and '{' not in _js.split('=>', 1)[0]


class _FakeFocusRing:
    """Anillo de foco con firmas DUPLICADAS a mitad del pase: el stop es la
    IDENTIDAD del primer elemento (marca dataset), no la firma repetida."""

    class _KB:
        def __init__(self, ring):
            self.ring = ring

        def press(self, key):
            if key == 'Tab' and self.ring.sigs:
                r = self.ring
                r.i = 0 if r.i == -1 else (r.i + 1) % len(r.sigs)

    def __init__(self, sigs):
        self.sigs = sigs
        self.i = -1                  # body: nada enfocado aún
        self.stamped = None
        self.keyboard = self._KB(self)

    def evaluate(self, expr):
        if expr == _WALK_STAMP_JS:
            self.stamped = self.i
            return self.i >= 0
        if expr == _WALK_IS_STAMPED_JS:
            return self.stamped is not None and self.i == self.stamped
        if expr == _WALK_CLEAN_JS:
            self.stamped = None
            return None
        if expr == FOCUS_KEY_JS:
            return self.sigs[self.i] if self.i >= 0 else None
        raise AssertionError('evaluate inesperado: %r' % expr[:50])


# 0b. el walk atraviesa la firma duplicada y para en la vuelta (identidad)
_ring = _FakeFocusRing(['button:pay', 'button:edit', 'button:edit', 'button:del'])
_order = _walk_focus(_ring, 20)
assert _order == ['button:pay', 'button:edit', 'button:edit', 'button:del'], _order
assert _ring.stamped is None, 'la marca se limpia al terminar'
print('0b. walk por identidad: firma duplicada no trunca; vuelta detectada ✓')

# 0c. nada enfocable → orden vacío sin crash
assert _walk_focus(_FakeFocusRing(['a:x']), 5) == ['a:x']
assert _walk_focus(_FakeFocusRing([]), 5) == []
print('0c. walk sin enfocables → [] ✓')

# 0d. diff multiset: duplicar un control con el mismo nombre ES un cambio
SNAPA = {'elements': [{'key': 'button:edit', 'name': 'Edit'},
                      {'key': 'button:del', 'name': 'Del'}],
         'focus_order': ['button:edit', 'button:del']}
SNAPB = {'elements': [{'key': 'button:edit', 'name': 'Edit'},
                      {'key': 'button:edit', 'name': 'Edit'},
                      {'key': 'button:del', 'name': 'Del'}],
         'focus_order': ['button:edit', 'button:edit', 'button:del']}
_d = diff(SNAPA, SNAPB)
assert not _d['ok'] and _d['added'] == ['button:edit'], _d
assert _d['summary']['elements'] == {'before': 2, 'after': 3}
assert diff(SNAPA, SNAPA)['ok']            # idénticos siguen ok
_d2 = diff(SNAPB, SNAPA)
assert _d2['removed'] == ['button:edit']   # y a la inversa
print('0d. diff multiset: la duplicación cuenta como añadido ✓')

try:
    import playwright  # noqa: F401
except ImportError:
    print('SKIP test_walk: Playwright no instalado')
    sys.exit(0)

from a11y_toolkit.a11ydom import contrast_walk, contrast_dom_main  # noqa: E402

FIXTURE = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Fixture walk</title>
<style>
body { background: #ffffff; }
.good { color: #333333; font-size: 16px; }
.bad { color: #999999; font-size: 16px; }
.large-ok3 { color: #8a8a8a; font-size: 26px; font-weight: 700; }
.over-image { color: #999999; font-size: 20px; background-image: linear-gradient(90deg, #cccccc, #eeeeee); }
.dark-ok { color: #999999; }
.ghost { color: rgba(20, 20, 20, 0.35); }
@media (prefers-color-scheme: dark) {
  body { background: #111111; }
  .dark-ok { color: #cccccc; }
  .bad { color: #dddddd; }
}
</style></head><body>
<p class="good">Fine text passes with a comfortable margin</p>
<p class="bad">Failing body text for the 4.5 threshold</p>
<h1 class="large-ok3">Large heading at the 3.0 threshold</h1>
<p class="over-image">Text over a light gradient must be pixel sampled</p>
<p class="dark-ok">Color scheme sensitive paragraph</p>
<p class="ghost">Translucent text is skipped and counted</p>
</body></html>'''

fixture_path = os.path.join('/tmp', 'a11y_walk_fixture.html')
with open(fixture_path, 'w', encoding='utf-8') as fh:
    fh.write(FIXTURE)
url = 'file://' + fixture_path

# --- 1. pase claro: 5 textos visibles, translúcido saltado y contado ---
r = contrast_walk(url, max_walk=50, max_sample=8)
assert r['mode'] == 'contrast-walk' and r['scheme'] == 'light'
assert r['checked'] == 5, r['checked']
assert r['summary']['translucent_text_skipped'] == 1
assert not any('ghost' in e['path'] for e in r['elements'])
print('1. colección: 5 textos, translúcido saltado+contado ✓')

by = {e['path'].split(' > ')[-1]: e for e in r['elements']}
good, bad, large, over, dark = (by['p:nth-of-type(1)'], by['p:nth-of-type(2)'],
                                by['h1'], by['p:nth-of-type(3)'], by['p:nth-of-type(4)'])

# --- 2. umbral large-text por font-size/weight COMPUTADOS (3.0, no 4.5) ---
assert good['threshold'] == 4.5 and good['large_text'] is False
assert large['large_text'] is True and large['threshold'] == 3.0
assert large['font_px'] == 26.0 and large['bold'] is True
assert large['verdict'] == 'pass' and 3.0 <= large['ratio'] < 4.0, large
assert good['verdict'] == 'pass' and good['ratio'] > 10
print('2. large-text computado → umbral 3.0; texto normal → 4.5 ✓')

# --- 3. fallos reales ---
assert bad['verdict'] == 'fail' and bad['ratio'] < 3.0
assert r['summary']['fails_4_5_normal_text'] == 3
assert r['summary']['fails_3_0_large_text'] == 0
print('3. fallos 1.4.3 contados por umbral ✓')

# --- 4. fondo con imagen → muestreo por píxeles (peor caso) ---
assert over['pixel_sampled'] is True and over['bg_image'], over
assert over['ratio'] is not None and over['verdict'] == 'fail'
assert r['summary']['pixel_sampled'] == 1
print('4. gradiente muestreado por píxeles ✓')

# --- 5. sugerencia de color en el peor fallo plano ---
assert r['summary']['worst_ratio'] is not None and r['summary']['worst_element']
sugg = [e for e in r['elements'] if 'suggestion' in e]
assert sugg, 'ninguna sugerencia generada'
s0 = sugg[0]['suggestion']
assert s0['color'] and s0['ratio'] >= sugg[0]['threshold'] and s0['action']
print('5. sugerencia de color alcanza el umbral del elemento ✓')

# --- 6. pase dark + delta: el media query reescribe y el delta lo ve ---
r2 = contrast_walk(url, max_walk=50, max_sample=8, dark=True)
assert 'dark' in r2 and r2['dark']['checked'] == 5
delta = r2['dark_delta']
assert set(delta) >= {'new_fails', 'resolved'}
# la página responde al media query pero rompe el texto bueno en dark: #333 sobre #111
assert any('p:nth-of-type(1)' in p for p in delta['new_fails']), delta
# y repara los dos que fallaban en claro
assert any('p:nth-of-type(2)' in p for p in delta['resolved']), delta
print('6. dark delta: nuevos fallos y resueltos detectados ✓')

# --- 7. límites declarados, veredicto honesto ---
assert 'unmeasured' in r['limits'] and '1.4.3' in r['limits']
print('7. límites honestos en el informe ✓')

# --- 8. CLI: --walk sin --selector; sin nada → error; exit codes ---
assert contrast_dom_main([url, '--walk']) == 0
assert contrast_dom_main([url]) == 1                      # sin selector ni walk
assert contrast_dom_main([url, '--walk', '--selector', 'p']) == 1  # contradictorio
print('8. CLI contrast-dom --walk ✓')

os.remove(fixture_path)
print('OK test_walk: 8 checks')
