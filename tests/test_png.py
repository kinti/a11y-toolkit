#!/usr/bin/env python3
"""Tests del decodificador PNG puro y del núcleo de muestreo compartido."""
import struct
import sys
import zlib
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a11y_toolkit.contrast import (decodificar_png, sample_rgb, parse_color)  # noqa: E402


def _png(w, h, ct, rows):
    """PNG mínimo: color type ct; `rows` son rows YA codificadas (con byte de filtro)."""
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', w, h, 8, ct, 0, 0, 0)
    idat = b''.join(rows)
    chunks = b''
    for tipo, body in ((b'IHDR', ihdr), (b'IDAT', zlib.compress(idat)), (b'IEND', b'')):
        chunks += struct.pack('>I', len(body)) + tipo + body
        chunks += struct.pack('>I', zlib.crc32(tipo + body) & 0xffffffff)
    return sig + chunks


# 1. RGB puro, filtro 0 (None)
png = _png(2, 1, 2, [b'\x00' + bytes([255, 0, 0, 0, 255, 0])])
w, h, rgb = decodificar_png(png)
assert (w, h) == (2, 1), (w, h)
assert rgb == bytes([255, 0, 0, 0, 255, 0]), rgb.hex()

# 2. RGBA: alfa se compone sobre white
png = _png(1, 1, 6, [b'\x00' + bytes([255, 0, 0, 128])])
w, h, rgb = decodificar_png(png)
assert rgb == bytes([255, 127, 127]), rgb.hex()  # (255*128 + 255*127)//255; canales g/b = 127

# 3. Filtro Sub (1): cada píxel es delta respecto al anterior
row = bytes([10, 20, 30, 5, 5, 5])
cod = bytearray()
for i, v in enumerate(row):
    cod.append((v - (row[i - 3] if i >= 3 else 0)) & 255)
png = _png(2, 1, 2, [bytes([1]) + bytes(cod)])
w, h, rgb = decodificar_png(png)
assert rgb == row, rgb.hex()

# 4. Filtro Up (2): delta respecto a la row anterior
f0 = bytes([100, 100, 100, 100, 100, 100])
f1 = bytes([(120 - 100) & 255, (90 - 100) & 255, (110 - 100) & 255, 0, 0, 0])
png = _png(2, 2, 2, [b'\x00' + f0, bytes([2]) + f1])
w, h, rgb = decodificar_png(png)
assert rgb == f0 + bytes([120, 90, 110, 100, 100, 100]), rgb.hex()

# 5. Paleta (3) con PLTE
plte = b'\xff\x00\x00\x00\xff\x00'
ihdr = struct.pack('>IIBBBBB', 2, 1, 8, 3, 0, 0, 0)
sig = b'\x89PNG\r\n\x1a\n'
def _chunk(tipo, body):
    return struct.pack('>I', len(body)) + tipo + body + struct.pack('>I', zlib.crc32(tipo + body) & 0xffffffff)
idat = zlib.compress(b'\x00\x00\x01')
png = sig + _chunk(b'IHDR', ihdr) + _chunk(b'PLTE', plte) + _chunk(b'IDAT', idat) + _chunk(b'IEND', b'')
w, h, rgb = decodificar_png(png)
assert rgb == bytes([255, 0, 0, 0, 255, 0]), rgb.hex()

# 6. Gris (0)
ihdr = struct.pack('>IIBBBBB', 2, 1, 8, 0, 0, 0, 0)
idat = zlib.compress(b'\x00\x00\xff')
png = sig + _chunk(b'IHDR', ihdr) + _chunk(b'IDAT', idat) + _chunk(b'IEND', b'')
w, h, rgb = decodificar_png(png)
assert rgb == bytes([0, 0, 0, 255, 255, 255]), rgb.hex()

# 7. Rechazos claros
try:
    decodificar_png(b'no es un png')
    raise AssertionError('debería fallar')
except ValueError:
    pass
ihdr16 = struct.pack('>IIBBBBB', 1, 1, 16, 2, 0, 0, 0)
png16 = sig + _chunk(b'IHDR', ihdr16) + _chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\x00\x00')) + _chunk(b'IEND', b'')
try:
    decodificar_png(png16)
    raise AssertionError('16 bits debería fallar')
except ValueError:
    pass

# 8. sample_rgb: rampa white→negro con text white; exclude_text quita el text
w = h = 100
rgb = bytearray(w * h * 3)
for j in range(h):
    v = int(255 * j / h)
    for i in range(w):
        rgb[(j * w + i) * 3:(j * w + i) * 3 + 3] = bytes([v, v, v])
m = sample_rgb(w, h, bytes(rgb), parse_color('#ffffff'), sample=2)
assert abs(m['worst_ratio'] - 1.05) < 0.02, m['worst_ratio']
# con exclusión de text: la row más clara (~blanca, pegada al color del text) se salta
me = sample_rgb(w, h, bytes(rgb), parse_color('#ffffff'), sample=2, exclude_text=True)
assert me['worst_ratio'] > m['worst_ratio'], (me['worst_ratio'], m['worst_ratio'])
assert me['excluded_text_pixels'] > 0
# región 100% color de text → sin fondo medible → None
white = bytes([255, 255, 255]) * 100
assert sample_rgb(10, 10, white, parse_color('#ffffff'), exclude_text=True) is None
# región pequeña sin rejilla
peq = sample_rgb(10, 10, white, parse_color('#000000'))
assert 'worst_zone' not in peq and peq['worst_ratio'] == 21.0

print('PNG + muestreo OK ✓ (decodificador puro, filtros 0-4, paleta/gris/RGBA, exclusión de text)')
