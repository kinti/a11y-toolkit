#!/usr/bin/env python3
"""Tests del núcleo de contraste con valores canónicos WCAG."""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contrast import pair, parse_color, ratio, sugerir  # noqa: E402


def cerca(a, b, tol=0.01):
    assert abs(a - b) <= tol, f'{a} != {b}'


# 1. Casos canónicos de la especificación
cerca(ratio(parse_color('#ffffff'), parse_color('#000000')), 21.0)
cerca(ratio(parse_color('#000000'), parse_color('#ffffff')), 21.0)  # simetría
cerca(ratio(parse_color('#767676'), parse_color('#ffffff')), 4.54, 0.02)  # frontera AA
r = pair('#999999', '#ffffff')
cerca(r['ratio'], 2.85, 0.02)
assert r['veredictos'][0]['cumple'] is False  # texto normal AA falla
assert r['veredictos'][4]['cumple'] is False  # 1.4.11 (3:1) también falla
r2 = pair('#1f2328', '#fbfaf7')
cerca(r2['ratio'], 15.13, 0.02)

# 2. Formatos de entrada
assert parse_color('rgb(255, 0, 0)') == {'r': 255, 'g': 0, 'b': 0}
assert parse_color('#f00') == {'r': 255, 'g': 0, 'b': 0}
assert parse_color('naranja') is None

# 3. Sugerencia: desde #999999 sobre blanco debe alcanzar AA
s = sugerir(parse_color('#999999'), parse_color('#ffffff'), 4.5)
assert s and s['ratio'] >= 4.5, s
cerca(ratio(parse_color(s['color']), parse_color('#ffffff')), s['ratio'], 0.02)

# 4. Modo imagen con PPM sintético (gradiente blanco→negro)
with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as f:
    w = h = 100
    f.write(b'P6\n%d %d\n255\n' % (w, h))
    for j in range(h):
        v = int(255 * j / h)
        f.write(bytes([v, v, v]) * w)
    ruta = f.name
from contrast import image_contrast  # noqa: E402
res = image_contrast(ruta, '#ffffff', sample=2)
os.unlink(ruta)
cerca(res['ratio_peor'], 1.05, 0.02)          # contra la fila más clara (v=252)
assert res['ratio_mediana'] >= 3             # mitad de la rampa ya es oscura
assert res['area_pasa_aa_texto_normal_4_5'] > 40
# región inválida → error amigable, no traceback
assert 'error' in image_contrast('/dev/null', '#fff', region='a,b,c')

# 5. CLI end-to-end
out = subprocess.run(
    [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'contrast.py'),
     'pair', '#767676', '#ffffff'],
    capture_output=True, text=True)
d = json.loads(out.stdout)
cerca(d['ratio'], 4.54, 0.02)

print('TODOS LOS TESTS DE CONTRASTE PASAN ✓')
