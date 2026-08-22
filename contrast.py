#!/usr/bin/env python3
"""A11Y Contrast Toolkit — núcleo compartido (CLI, skill y MCP).

Comprobaciones WCAG 2.2 de contraste, en dos modalidades:

1. Par de colores planos  →  ratios y veredictos 1.4.3 / 1.4.6 / 1.4.11
2. Texto sobre imagen     →  muestreo píxel a píxel de la zona del texto:
   contraste peor / mediano / p95, % de área que pasa AA y AAA, y veredicto.

Cero dependencias: la decodificación de imágenes usa Pillow si está
disponible y, si no, `sips` (macOS) convirtiendo a PPM.

Uso:
  contrast.py pair "#ffffff" "#000000"
  contrast.py pair "#1f2328" "#fbfaf7" --suggest
  contrast.py image foto.jpg --text "#ffffff"
  contrast.py image foto.jpg --text "#333333" --region 120,40,420,90 --sample 4
"""

import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import os

# ---------------------------------------------------------------- colores ---

def parse_color(s):
    """'#rgb' | '#rrggbb' | 'rgb(r,g,b)' → dict r,g,b. None si no válido."""
    t = s.strip()
    m = re.fullmatch(r'#?([0-9a-f]{3})', t, re.I)
    if m:
        h = m.group(1)
        return {'r': int(h[0] * 2, 16), 'g': int(h[1] * 2, 16), 'b': int(h[2] * 2, 16)}
    m = re.fullmatch(r'#?([0-9a-f]{6})', t, re.I)
    if m:
        h = m.group(1)
        return {'r': int(h[0:2], 16), 'g': int(h[2:4], 16), 'b': int(h[4:6], 16)}
    m = re.fullmatch(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', t, re.I)
    if m:
        r, g, b = (min(255, int(x)) for x in m.groups())
        return {'r': r, 'g': g, 'b': b}
    return None


def hexs(c):
    return '#%02x%02x%02x' % (c['r'], c['g'], c['b'])


def _lin(v):
    c = v / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(c):
    return 0.2126 * _lin(c['r']) + 0.7152 * _lin(c['g']) + 0.0722 * _lin(c['b'])


def ratio(fg, bg):
    l1, l2 = sorted((luminancia(fg), luminancia(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


CRITERIOS = [
    ('1.4.3 Contraste (mínimo) · texto normal', 'AA', 4.5),
    ('1.4.3 Contraste (mínimo) · texto grande', 'AA', 3.0),
    ('1.4.6 Contraste (mejorado) · texto normal', 'AAA', 7.0),
    ('1.4.6 Contraste (mejorado) · texto grande', 'AAA', 4.5),
    ('1.4.11 Contraste no textual (UI, iconos, bordes)', 'AA', 3.0),
]


def veredictos(r):
    return [
        {'criterio': n, 'nivel': lvl, 'umbral': u, 'cumple': r >= u}
        for n, lvl, u in CRITERIOS
    ]


def sugerir(fg, bg, objetivo=4.5):
    """Color más cercano al original que cumple el objetivo (mezcla con blanco/negro)."""
    def mez(c, blanco, t):
        o = 255 if blanco else 0
        return {'r': round(c['r'] + (o - c['r']) * t),
                'g': round(c['g'] + (o - c['g']) * t),
                'b': round(c['b'] + (o - c['b']) * t)}
    mejor = None
    for blanco in (True, False):
        for paso in range(1, 51):
            t = paso / 50
            c = mez(fg, blanco, t)
            if ratio(c, bg) >= objetivo:
                if mejor is None or t < mejor['paso']:
                    mejor = {'color': hexs(c), 'ratio': round(ratio(c, bg), 2),
                             'accion': 'aclarar' if blanco else 'oscurecer', 'paso': t}
                break
    return mejor


def pair(fg_s, bg_s, con_sugerencia=True):
    fg, bg = parse_color(fg_s), parse_color(bg_s)
    if not fg or not bg:
        return {'error': 'color no válido (usa #rgb, #rrggbb o rgb(r,g,b))'}
    r = ratio(fg, bg)
    out = {
        'texto': hexs(fg), 'fondo': hexs(bg),
        'ratio': round(r, 2),
        'veredictos': veredictos(r),
    }
    if con_sugerencia and r < 4.5:
        s = sugerir(fg, bg, 4.5)
        if s:
            out['sugerencia_aa'] = s
    return out

# ---------------------------------------------------------------- imagen ----

def _cargar_ppm(ruta):
    """PPM P6 → (ancho, alto, bytes RGB)."""
    with open(ruta, 'rb') as f:
        datos = f.read()
    if not datos.startswith(b'P6'):
        raise ValueError('no es PPM P6')
    pos = 2
    campos = []
    while len(campos) < 3:
        while pos < len(datos) and datos[pos:pos + 1].isspace():
            pos += 1
        if datos[pos:pos + 1] == b'#':
            while datos[pos:pos + 1] not in (b'\n', b''):
                pos += 1
            continue
        ini = pos
        while pos < len(datos) and not datos[pos:pos + 1].isspace():
            pos += 1
        campos.append(int(datos[ini:pos]))
    pos += 1
    w, h, _maxv = campos
    return w, h, datos[pos:pos + w * h * 3]


def cargar_imagen(ruta):
    """Devuelve (ancho, alto, bytes RGB) desde PNG/JPG/PPM. Pillow si existe; si no, sips."""
    try:
        from PIL import Image
        im = Image.open(ruta).convert('RGB')
        return im.width, im.height, im.tobytes()
    except ImportError:
        pass
    if ruta.lower().endswith('.ppm'):
        return _cargar_ppm(ruta)
    if not shutil.which('sips'):
        raise RuntimeError('necesitas Pillow (pip install pillow) o macOS (sips)')
    with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as tf:
        tmp = tf.name
    try:
        subprocess.run(['sips', '-s', 'format', 'ppm', ruta, '--out', tmp],
                       check=True, capture_output=True)
        return _cargar_ppm(tmp)
    finally:
        os.unlink(tmp)


def _percentil(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[k]


def image_contrast(ruta, texto_color, region=None, sample=4):
    """
    Muestrea el fondo de una imagen y calcula el contraste del color de
    texto contra cada píxel de la región (por defecto, toda la imagen).

    region: "x,y,ancho,alto" en píxeles. sample: paso de muestreo (1 = todos).
    """
    c = parse_color(texto_color)
    if not c:
        return {'error': 'color de texto no válido'}
    if region:
        try:
            x, y, rw, rh = (int(v) for v in region.split(','))
        except ValueError:
            return {'error': 'region debe ser x,y,ancho,alto (números separados por comas)'}
    try:
        w, h, rgb = cargar_imagen(ruta)
    except Exception as e:  # noqa: BLE001
        return {'error': f'no se pudo cargar la imagen: {e}'}
        x, y = max(0, x), max(0, y)
        rw = min(rw, w - x)
        rh = min(rh, h - y)
        if rw <= 0 or rh <= 0:
            return {'error': 'región fuera de la imagen'}
    else:
        x, y, rw, rh = 0, 0, w, h

    sample = max(1, int(sample))
    l_texto = luminancia(c)
    ratios = []
    n = 0
    for j in range(y, y + rh, sample):
        fila = j * w
        for i in range(x, x + rw, sample):
            o = (fila + i) * 3
            lpix = (0.2126 * _lin(rgb[o]) + 0.7152 * _lin(rgb[o + 1])
                    + 0.0722 * _lin(rgb[o + 2]))
            l1, l2 = (l_texto, lpix) if l_texto > lpix else (lpix, l_texto)
            ratios.append((l1 + 0.05) / (l2 + 0.05))
            n += 1
    if not ratios:
        return {'error': 'sin píxeles en la región'}

    pasa45 = sum(1 for v in ratios if v >= 4.5)
    pasa30 = sum(1 for v in ratios if v >= 3.0)
    out = {
        'imagen': os.path.basename(ruta),
        'color_texto': hexs(c),
        'region': {'x': x, 'y': y, 'ancho': rw, 'alto': rh, 'pixeles_muestreados': n,
                   'paso': sample},
        'ratio_peor': round(min(ratios), 2),
        'ratio_mediana': round(_percentil(ratios, 50), 2),
        'ratio_p95': round(_percentil(ratios, 95), 2),
        'area_pasa_aa_texto_normal_4_5': round(100.0 * pasa45 / n, 1),
        'area_pasa_aa_minimo_3_0': round(100.0 * pasa30 / n, 1),
        'interpretacion': (
            'El contraste del texto debe evaluarse contra el FONDO REAL tras él: '
            'usa ratio_peor para saber la zona más hostil y area_pasa_aa_texto_normal '
            'para saber cuánta superficie es segura. Si area_pasa < 100% con texto '
            'sobre imagen, se necesita velo/overlay o texto alternativo posicionado.'
        ),
    }
    return out

# ---------------------------------------------------------------- CLI -------

def main(argv):
    if len(argv) < 1 or argv[0] not in ('pair', 'image'):
        print(__doc__)
        return 1
    cmd = argv[0]
    flags = {'--suggest': False}
    posicionales = []
    i = 1
    while i < len(argv):
        v = argv[i]
        if v in ('--suggest',):
            flags[v] = True
        elif v in ('--region', '--sample', '--text'):
            if i + 1 >= len(argv):
                print(f'falta el valor de {v}')
                return 1
            flags[v] = argv[i + 1]
            i += 1
        else:
            posicionales.append(v)
        i += 1
    if cmd == 'pair':
        if len(posicionales) < 2:
            print('uso: contrast.py pair "#texto" "#fondo"')
            return 1
        res = pair(posicionales[0], posicionales[1], con_sugerencia=True)
    else:
        if not posicionales or '--text' not in flags:
            print('uso: contrast.py image ruta.jpg --text "#ffffff" [--region x,y,w,h] [--sample N]')
            return 1
        res = image_contrast(posicionales[0], flags['--text'],
                             region=flags.get('--region'),
                             sample=flags.get('--sample', 4))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
