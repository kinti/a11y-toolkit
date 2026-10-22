#!/usr/bin/env python3
"""A11Y Contrast Toolkit — shared core (CLI, skill and MCP). Bilingual es/en.

1. Flat color pair     →  ratios and 1.4.3 / 1.4.6 / 1.4.11 verdicts
2. Text over image     →  pixel-by-pixel sampling of the text area

Zero dependencies: Pillow if present, else `sips` (macOS); PPM always.

Usage:
  contrast.py pair "#ffffff" "#000000" [--lang es]
  contrast.py image photo.jpg --text "#ffffff" [--region 120,40,420,90] [--sample 4] [--lang es]
"""

import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import os

T = {
    'es': {
        'criteria': [
            ('1.4.3 Contraste (mínimo) · texto normal', 'AA', 4.5),
            ('1.4.3 Contraste (mínimo) · texto grande', 'AA', 3.0),
            ('1.4.6 Contraste (mejorado) · texto normal', 'AAA', 7.0),
            ('1.4.6 Contraste (mejorado) · texto grande', 'AAA', 4.5),
            ('1.4.11 Contraste no textual (UI, iconos, bordes)', 'AA', 3.0),
        ],
        'invalid_color': 'color no válido (usa #rgb, #rrggbb o rgb(r,g,b))',
        'invalid_region': 'region debe ser x,y,ancho,alto (números separados por comas)',
        'region_outside': 'región fuera de la imagen',
        'no_pixels': 'sin píxeles en la región',
        'load_error': 'no se pudo cargar la imagen',
        'opaque_text': 'para texto sobre imagen usa un color opaco (sin alfa)',
        'selector_missing': 'selector {s} no encontrado en la página',
        'no_box': 'el elemento que coincide con {s} no tiene caja visible que muestrear',
        'lightening': 'aclarando', 'darkening': 'oscureciendo',
        'no_post_copy': 'sin copia específica del post: base a secas',
        'interp': ('El contraste del texto debe evaluarse contra el FONDO REAL tras él: '
                   'usa worst_ratio para saber la zona más hostil y area_passes_aa_normal_text_4_5 '
                   'para saber cuánta superficie es segura. Si area_passes_aa_normal_text_4_5 < 100% con texto '
                   'sobre imagen, se necesita velo/overlay o texto alternativo posicionado.'),
    },
    'en': {
        'criteria': [
            ('1.4.3 Contrast (Minimum) · normal text', 'AA', 4.5),
            ('1.4.3 Contrast (Minimum) · large text', 'AA', 3.0),
            ('1.4.6 Contrast (Enhanced) · normal text', 'AAA', 7.0),
            ('1.4.6 Contrast (Enhanced) · large text', 'AAA', 4.5),
            ('1.4.11 Non-text Contrast (UI, icons, borders)', 'AA', 3.0),
        ],
        'invalid_color': 'invalid color (use #rgb, #rrggbb or rgb(r,g,b))',
        'invalid_region': 'region must be x,y,width,height (comma-separated numbers)',
        'region_outside': 'region outside the image',
        'no_pixels': 'no pixels in region',
        'load_error': 'could not load image',
        'opaque_text': 'use an opaque color for text over images (no alpha)',
        'selector_missing': 'selector {s} not found on the page',
        'no_box': 'the element matched by {s} has no visible box to sample',
        'lightening': 'lightening', 'darkening': 'darkening',
        'no_post_copy': 'no specific copy of the post: base only',
        'interp': ('Text contrast must be evaluated against the REAL background behind it: '
                   'use worst_ratio to find the most hostile area and '
                   'area_passes_aa_normal_text_4_5 to know how much surface is safe. If '
                   'area_passes_aa_normal_text_4_5 < 100% for text over image, you need an overlay/scrim or '
                   'repositioned alternative text.'),
    },
}


def _t(lang):
    return T.get(lang, T['es'])

# ---------------------------------------------------------------- colores ---

# Nombres CSS (X11/CSS Color Module Level 4), 148 entradas
_NAMES = '''
aliceblue:f0f8ff antiquewhite:faebd7 aqua:00ffff aquamarine:7fffd4 azure:f0ffff
beige:f5f5dc bisque:ffe4c4 black:000000 blanchedalmond:ffebcd blue:0000ff
blueviolet:8a2be2 brown:a52a2a burlywood:deb887 cadetblue:5f9ea0 chartreuse:7fff00
chocolate:d2691e coral:ff7f50 cornflowerblue:6495ed cornsilk:fff8dc crimson:dc143c
cyan:00ffff darkblue:00008b darkcyan:008b8b darkgoldenrod:b8860b darkgray:a9a9a9
darkgreen:006400 darkgrey:a9a9a9 darkkhaki:bdb76b darkmagenta:8b008b
darkolivegreen:556b2f darkorange:ff8c00 darkorchid:9932cc darkred:8b0000
darksalmon:e9967a darkseagreen:8fbc8f darkslateblue:483d8b darkslategray:2f4f4f
darkslategrey:2f4f4f darkturquoise:00ced1 darkviolet:9400d3 deeppink:ff1493
deepskyblue:00bfff dimgray:696969 dimgrey:696969 dodgerblue:1e90ff firebrick:b22222
floralwhite:fffaf0 forestgreen:228b22 fuchsia:ff00ff gainsboro:dcdcdc ghostwhite:f8f8ff
gold:ffd700 goldenrod:daa520 gray:808080 green:008000 greenyellow:adff2f grey:808080
honeydew:f0fff0 hotpink:ff69b4 indianred:cd5c5c indigo:4b0082 ivory:fffff0
khaki:f0e68c lavender:e6e6fa lavenderblush:fff0f5 lawngreen:7cfc00
lemonchiffon:fffacd lightblue:add8e6 lightcoral:f08080 lightcyan:e0ffff
lightgoldenrodyellow:fafad2 lightgray:d3d3d3 lightgreen:90ee90 lightgrey:d3d3d3
lightpink:ffb6c1 lightsalmon:ffa07a lightseagreen:20b2aa lightskyblue:87cefa
lightslategray:778899 lightslategrey:778899 lightsteelblue:b0c4de lightyellow:ffffe0
lime:00ff00 limegreen:32cd32 linen:faf0e6 magenta:ff00ff maroon:800000
mediumaquamarine:66cdaa mediumblue:0000cd mediumorchid:ba55d3 mediumpurple:9370db
mediumseagreen:3cb371 mediumslateblue:7b68ee mediumspringgreen:00fa9a
mediumturquoise:48d1cc mediumvioletred:c71585 midnightblue:191970 mintcream:f5fffa
mistyrose:ffe4e1 moccasin:ffe4b5 navajowhite:ffdead navy:000080 oldlace:fdf5e6
olive:808000 olivedrab:6b8e23 orange:ffa500 orangered:ff4500 orchid:da70d6
palegoldenrod:eee8aa palegreen:98fb98 paleturquoise:afeeee palevioletred:db7093
papayawhip:ffefd5 peachpuff:ffdab9 peru:cd853f pink:ffc0cb plum:dda0dd
powderblue:b0e0e6 purple:800080 rebeccapurple:663399 red:ff0000 rosybrown:bc8f8f
royalblue:4169e1 saddlebrown:8b4513 salmon:fa8072 sandybrown:f4a460 seagreen:2e8b57
seashell:fff5ee sienna:a0522d silver:c0c0c0 skyblue:87ceeb slateblue:6a5acd
slategray:708090 slategrey:708090 snow:fffafa springgreen:00ff7f steelblue:4682b4
tan:d2b48c teal:008080 thistle:d8bfd8 tomato:ff6347 turquoise:40e0d0 violet:ee82ee
wheat:f5deb3 white:ffffff whitesmoke:f5f5f5 yellow:ffff00 yellowgreen:9acd32
'''
COLOR_NAMES = {n: h for n, h in (par.split(':') for par in _NAMES.split())}


def _hsl_a_rgb(h, s, l):
    """h [0,360), s/l [0,1] → (r,g,b) 0-255."""
    h = (h % 360) / 360.0
    def f(n):
        k = (n + h * 12) % 12
        a = s * min(l, 1 - l)
        return round(255 * (l - a * max(-1, min(k - 3, 9 - k, 1))))
    return f(0), f(8), f(4)


def parse_color(s):
    """'#rgb' | '#rrggbb' | '#rrggbbaa' | rgb()/rgba() | hsl()/hsla() | nombre CSS
    → dict r,g,b (y 'a' si hay alfa). Acepta comas o espacios como separadores.
    None si no válido."""
    t = s.strip().lower()
    m = re.fullmatch(r'#?([0-9a-f]{3})', t)
    if m:
        h = m.group(1)
        return {'r': int(h[0] * 2, 16), 'g': int(h[1] * 2, 16), 'b': int(h[2] * 2, 16)}
    m = re.fullmatch(r'#?([0-9a-f]{6})', t)
    if m:
        h = m.group(1)
        return {'r': int(h[0:2], 16), 'g': int(h[2:4], 16), 'b': int(h[4:6], 16)}
    m = re.fullmatch(r'#?([0-9a-f]{8})', t)
    if m:
        h = m.group(1)
        return {'r': int(h[0:2], 16), 'g': int(h[2:4], 16), 'b': int(h[4:6], 16),
                'a': int(h[6:8], 16) / 255.0}
    # rgb()/rgba()/hsl()/hsla() con comas o espacios (sintaxis CSS moderna)
    m = re.fullmatch(r'(rgba?|hsla?)\(\s*([^)]*)\)', t)
    if m:
        body = m.group(2)
        alfa_ext = None
        if '/' in body:
            body, alfa_ext = re.split(r'\s*/\s*', body, 1)
        parts = [p for p in (x.strip() for x in re.split(r'[\s,]+', body)) if p]
        kind, v = m.group(1), parts
        if kind.startswith('rgb'):
            if len(v) < 3:
                return None
            def _channel(x):
                if x.endswith('%'):
                    return max(0, min(255, round(float(x[:-1]) * 2.55)))
                return max(0, min(255, int(float(x))))
            c = {'r': _channel(v[0]), 'g': _channel(v[1]), 'b': _channel(v[2])}
            if len(v) >= 4:
                c['a'] = max(0.0, min(1.0, float(v[3].rstrip('%')) / (100 if v[3].endswith('%') else 1)))
            elif alfa_ext:
                c['a'] = max(0.0, min(1.0, float(alfa_ext.strip().rstrip('%')) / (100 if alfa_ext.strip().endswith('%') else 1)))
            return c
        if len(v) < 3:
            return None
        h_ = float(v[0].rstrip('deg')) % 360
        s_ = max(0.0, min(1.0, float(v[1].rstrip('%')) / 100.0))
        l_ = max(0.0, min(1.0, float(v[2].rstrip('%')) / 100.0))
        r, g, b = _hsl_a_rgb(h_, s_, l_)
        c = {'r': max(0, min(255, r)), 'g': max(0, min(255, g)),
             'b': max(0, min(255, b))}
        if len(v) >= 4:
            c['a'] = max(0.0, min(1.0, float(v[3].rstrip('%')) / (100 if v[3].endswith('%') else 1)))
        return c
    if t in COLOR_NAMES:
        h = COLOR_NAMES[t]
        return {'r': int(h[0:2], 16), 'g': int(h[2:4], 16), 'b': int(h[4:6], 16)}
    return None


WHITE = {'r': 255, 'g': 255, 'b': 255}


def composite(c, bg):
    """Compone c (con alfa) sobre fondo opaco → dict opaco r,g,b."""
    a = c.get('a', 1.0)
    return {'r': round(c['r'] * a + bg['r'] * (1 - a)),
            'g': round(c['g'] * a + bg['g'] * (1 - a)),
            'b': round(c['b'] * a + bg['b'] * (1 - a))}


def hexs(c):
    # defensa: canales fuera de [0,255] (parse malformado) → acotados, hex válido
    return '#%02x%02x%02x' % (max(0, min(255, c['r'])),
                              max(0, min(255, c['g'])),
                              max(0, min(255, c['b'])))


def _lin(v):
    c = v / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(c):
    return 0.2126 * _lin(c['r']) + 0.7152 * _lin(c['g']) + 0.0722 * _lin(c['b'])


def ratio(fg, bg):
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def verdicts(r, lang='en'):
    return [
        {'criterion': n, 'level': lvl, 'threshold': u, 'passes': r >= u}
        for n, lvl, u in _t(lang)['criteria']
    ]


def suggest(fg, bg, target=4.5, lang='en'):
    """Color opaco más cercano (distancia RGB) al original que cumple el objetivo.

    Prueba mezclas hacia blanco y hacia negro y elige la de menor distancia real,
    con búsqueda fina de 400 pasos."""
    t9 = _t(lang)
    fg0 = composite(fg, bg) if fg.get('a', 1) < 1 else fg
    if ratio(fg0, bg) >= target:
        return None
    best = None
    for white in (True, False):
        o = (255, 255, 255) if white else (0, 0, 0)
        for step in range(1, 401):
            tt = step / 400
            c = {'r': round(fg0['r'] + (o[0] - fg0['r']) * tt),
                 'g': round(fg0['g'] + (o[1] - fg0['g']) * tt),
                 'b': round(fg0['b'] + (o[2] - fg0['b']) * tt)}
            if ratio(c, bg) >= target:
                d = (c['r'] - fg0['r']) ** 2 + (c['g'] - fg0['g']) ** 2 + (c['b'] - fg0['b']) ** 2
                if best is None or d < best['_d']:
                    best = {'color': hexs(c), 'ratio': round(ratio(c, bg), 2),
                             'action': t9['lightening'] if white else t9['darkening'],
                             'step': tt, '_d': d}
                break
    if best:
        del best['_d']
    return best


def pair(fg_s, bg_s, con_sugerencia=True, lang='en'):
    fg, bg = parse_color(fg_s), parse_color(bg_s)
    if not fg or not bg:
        return {'error': _t(lang)['invalid_color']}
    nota_alfa = None
    if bg.get('a', 1) < 1:
        bg = composite(bg, WHITE)
        nota_alfa = hexs(bg)
    if fg.get('a', 1) < 1:
        fg = composite(fg, bg)
        nota_alfa = hexs(fg)
    r = ratio(fg, bg)
    out = {
        'text': hexs(fg), 'background': hexs(bg),
        'ratio': round(r, 2),
        'verdicts': verdicts(r, lang),
    }
    if nota_alfa:
        out['effective_color'] = nota_alfa
    if con_sugerencia and r < 4.5:
        s = suggest(fg, bg, 4.5, lang)
        if s:
            out['aa_suggestion'] = s
    return out

# ---------------------------------------------------------------- imagen ----

def _load_ppm(path):
    with open(path, 'rb') as f:
        data = f.read()
    if not data.startswith(b'P6'):
        raise ValueError('no es PPM P6')
    pos = 2
    fields = []
    while len(fields) < 3:
        while pos < len(data) and data[pos:pos + 1].isspace():
            if data[pos:pos + 2] == b'\r\n':
                pos += 2
            else:
                pos += 1
        if data[pos:pos + 1] == b'#':
            while data[pos:pos + 1] not in (b'\n', b''):
                pos += 1
            continue
        start = pos
        while pos < len(data) and not data[pos:pos + 1].isspace():
            pos += 1
        fields.append(int(data[start:pos]))
    # tras maxval: saltar UN fin de línea (\n o \r\n) — con CRLF un solo
    # byte desplazaría TODOS los píxeles (salida plausible y falsa)
    if data[pos:pos + 2] == b'\r\n':
        pos += 2
    else:
        pos += 1
    w, h, _maxv = fields
    return w, h, data[pos:pos + w * h * 3]


def load_image(path):
    # .ppm → parser propio: PIL desplaza los píxeles cuando el header lleva
    # CRLF (el \n del fin de línea entra como primer byte de la imagen)
    if path.lower().endswith('.ppm'):
        return _load_ppm(path)
    try:
        from PIL import Image
        im = Image.open(path).convert('RGB')
        return im.width, im.height, im.tobytes()
    except ImportError:
        pass
    if not shutil.which('sips'):
        raise RuntimeError('need Pillow (pip install pillow) or macOS (sips)')
    with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as tf:
        tmp = tf.name
    try:
        subprocess.run(['sips', '-s', 'format', 'ppm', path, '--out', tmp],
                       check=True, capture_output=True)
        return _load_ppm(tmp)
    finally:
        os.unlink(tmp)


def _percentile(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[k]


# ---------------------------------------------------------------- PNG puro ---
# Playwright devuelve capturas PNG; sin Pillow no hay forma de leerlas, así que
# el core decodifica PNG por sí mismo (zero-dep): IHDR/PLTE/IEND, filtros 0-4,
# color types 0/2/3/6 a 8 bits. Lo que no sepa → ValueError con mensaje claro.


def decodificar_png(data):
    """Bytes PNG → (ancho, alto, bytes RGB). Sin dependencias.

    Soporta color types 0 (gris), 2 (RGB), 3 (paleta) y 6 (RGBA) a 8 bits;
    el alfa se compone sobre blanco (las capturas de navegador son opacas).
    Lanza ValueError si el PNG está fuera de ese soporte (p. ej. 16 bits)."""
    import struct
    import zlib
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG file')
    pos, idat, w, h, bd, ct, plte = 8, b'', 0, 0, 0, 0, None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if kind == b'IHDR':
            w, h, bd, ct = struct.unpack('>IIBB', body[:10])
        elif kind == b'IDAT':
            idat += body
        elif kind == b'PLTE':
            plte = body
        elif kind == b'IEND':
            break
        pos += 12 + ln
    if bd != 8:
        raise ValueError(f'PNG bit depth {bd} unsupported (8-bit only)')
    canales = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ct)
    if canales is None:
        raise ValueError(f'PNG color type {ct} unsupported')
    if ct == 3 and not plte:
        raise ValueError('PNG palette without PLTE chunk')
    crudo = zlib.decompress(idat)
    step = w * canales
    rows = []
    for y in range(h):
        base = y * (step + 1)
        filtro = crudo[base]
        f = bytearray(crudo[base + 1:base + 1 + step])
        prev = rows[-1] if rows else bytearray(step)
        for i in range(step):
            a = f[i - canales] if i >= canales else 0
            b = prev[i]
            c = prev[i - canales] if i >= canales else 0
            if filtro == 1:
                f[i] = (f[i] + a) & 255
            elif filtro == 2:
                f[i] = (f[i] + b) & 255
            elif filtro == 3:
                f[i] = (f[i] + ((a + b) >> 1)) & 255
            elif filtro == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                f[i] = (f[i] + pr) & 255
        rows.append(f)
    out = bytearray(w * h * 3)
    for y in range(h):
        f = rows[y]
        for x in range(w):
            o = x * canales
            if ct == 0:
                r = g = b = f[o]
            elif ct == 2:
                r, g, b = f[o], f[o + 1], f[o + 2]
            elif ct == 3:
                i = f[o] * 3
                r, g, b = plte[i], plte[i + 1], plte[i + 2]
            else:  # ct 6
                r, g, b, al = f[o], f[o + 1], f[o + 2], f[o + 3]
                if al < 255:
                    r = (r * al + 255 * (255 - al)) // 255
                    g = (g * al + 255 * (255 - al)) // 255
                    b = (b * al + 255 * (255 - al)) // 255
            p = (y * w + x) * 3
            out[p], out[p + 1], out[p + 2] = r, g, b
    return w, h, bytes(out)


def sample_rgb(w, h, rgb, text_color, sample=4, exclude_text=False):
    """Núcleo de muestreo compartido: bytes RGB + color de texto opaco → métricas.

    excluir_texto=True salta los píxeles próximos al color del texto (distancia
    RGB < 40): así, al capturar un elemento ENTERO (captura de navegador), se
    mide el FONDO real y no el propio texto (que siempre fallaría 1:1). Cuando
    se excluye >90% de la región no hay fondo medible → None.
    Incluye la rejilla 3×3 de zona hostil cuando la región es ≥99×99."""
    l_text = luminance(text_color)
    tr, tg, tb = text_color['r'], text_color['g'], text_color['b']
    ratios = []
    excluded = 0
    use_grid = w >= 99 and h >= 99
    cells = [[0, 0] for _ in range(9)]
    for j in range(0, h, sample):
        row = j * w
        cy = (j * 3) // h if use_grid else 0
        for i in range(0, w, sample):
            o = (row + i) * 3
            if exclude_text and ((rgb[o] - tr) ** 2 + (rgb[o + 1] - tg) ** 2
                                  + (rgb[o + 2] - tb) ** 2) < 1600:
                excluded += 1
                continue
            lpix = (0.2126 * _lin(rgb[o]) + 0.7152 * _lin(rgb[o + 1])
                    + 0.0722 * _lin(rgb[o + 2]))
            l1, l2 = (l_text, lpix) if l_text > lpix else (lpix, l_text)
            r = (l1 + 0.05) / (l2 + 0.05)
            ratios.append(r)
            if use_grid:
                cx = (i * 3) // w
                cells[cy * 3 + cx][1] += 1
                if r >= 4.5:
                    cells[cy * 3 + cx][0] += 1
    if not ratios:
        return None
    if exclude_text and excluded / max(1, len(ratios) + excluded) > 0.9:
        return None
    passes45 = sum(1 for v in ratios if v >= 4.5)
    passes30 = sum(1 for v in ratios if v >= 3.0)
    out = {
        'worst_ratio': round(min(ratios), 2),
        'median_ratio': round(_percentile(ratios, 50), 2),
        'p95_ratio': round(_percentile(ratios, 95), 2),
        'area_passes_aa_normal_text_4_5': round(100.0 * passes45 / len(ratios), 1),
        'area_passes_aa_min_3_0': round(100.0 * passes30 / len(ratios), 1),
        'sampled_pixels': len(ratios),
    }
    if exclude_text:
        out['excluded_text_pixels'] = excluded
    if use_grid:
        worst = min(range(9), key=lambda k: (cells[k][0] / cells[k][1]) if cells[k][1] else 1)
        py_, px_ = worst // 3, worst % 3
        out['worst_zone'] = {
            'cell': f'{["top","middle","bottom"][py_]}-{["left","center","right"][px_]}',
            'x': (w * px_) // 3, 'y': (h * py_) // 3,
            'width': w // 3, 'height': h // 3,
            'pct_passes_aa': round(100.0 * cells[worst][0] / cells[worst][1], 1) if cells[worst][1] else None,
        }
    return out


def image_contrast(path, text_color, region=None, sample=4, lang='en'):
    t9 = _t(lang)
    c = parse_color(text_color)
    if not c:
        return {'error': t9['invalid_color']}
    if c.get('a', 1) < 1:
        return {'error': t9['opaque_text']}
    if region:
        try:
            x, y, rw, rh = (int(v) for v in region.split(','))
        except ValueError:
            return {'error': t9['invalid_region']}
    try:
        w, h, rgb = load_image(path)
    except Exception as e:  # noqa: BLE001
        return {'error': f'{t9["load_error"]}: {e}'}
    if region:
        x, y = max(0, x), max(0, y)
        rw = min(rw, w - x)
        rh = min(rh, h - y)
        if rw <= 0 or rh <= 0:
            return {'error': t9['region_outside']}
    else:
        x, y, rw, rh = 0, 0, w, h

    sample = max(1, int(sample))
    # Guardián de rendimiento: regiones gigantes aumentan el paso automáticamente.
    budget = 2_000_000
    if (rw // sample) * (rh // sample) > budget:
        sample = max(sample, int(((rw * rh) / budget) ** 0.5) + 1)
    recorte = bytearray(rw * rh * 3)
    for j in range(rh):
        recorte[j * rw * 3:(j + 1) * rw * 3] = rgb[(y + j) * w * 3 + x * 3:
                                                    (y + j) * w * 3 + (x + rw) * 3]
    m = sample_rgb(rw, rh, bytes(recorte), c, sample)
    if not m:
        return {'error': t9['no_pixels']}

    out = {
        'image': os.path.basename(path),
        'text_color': hexs(c),
        'region': {'x': x, 'y': y, 'width': rw, 'height': rh,
                   'sampled_pixels': m.pop('sampled_pixels'), 'step': sample},
        'worst_ratio': m['worst_ratio'],
        'median_ratio': m['median_ratio'],
        'p95_ratio': m['p95_ratio'],
        'area_passes_aa_normal_text_4_5': m['area_passes_aa_normal_text_4_5'],
        'area_passes_aa_min_3_0': m['area_passes_aa_min_3_0'],
        'interpretation': t9['interp'],
    }
    if 'worst_zone' in m:
        out['worst_zone'] = m['worst_zone']
    return out

# ---------------------------------------------------------------- CLI -------

def main(argv):
    if len(argv) < 1 or argv[0] not in ('pair', 'image'):
        print(__doc__)
        return 1
    lang = 'en'
    flags = {}
    posicionales = []
    i = 1
    while i < len(argv):
        v = argv[i]
        if v == '--lang' and i + 1 < len(argv):
            lang = argv[i + 1]
            i += 1
        elif v in ('--region', '--sample', '--text'):
            if i + 1 >= len(argv):
                print(f'missing value for {v}')
                return 1
            flags[v] = argv[i + 1]
            i += 1
        elif v == '--suggest':
            flags['--suggest'] = True
        else:
            posicionales.append(v)
        i += 1
    if argv[0] == 'pair':
        if len(posicionales) < 2:
            print('usage: contrast.py pair "#text" "#background" [--lang es|en]')
            return 1
        res = pair(posicionales[0], posicionales[1], con_sugerencia=True, lang=lang)
    else:
        if not posicionales or '--text' not in flags:
            print('usage: contrast.py image photo.jpg --text "#ffffff" [--region x,y,w,h] [--sample N] [--lang es|en]')
            return 1
        res = image_contrast(posicionales[0], flags['--text'],
                             region=flags.get('--region'),
                             sample=flags.get('--sample', 4), lang=lang)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
