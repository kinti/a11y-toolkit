#!/usr/bin/env python3
"""VTT caption quality + PDF screening — the nobody-automated-them tools."""

import json
import os
import subprocess
import sys
import zlib
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import a11y_toolkit.a11yaudit as audit_mod  # noqa: E402
from a11y_toolkit.a11yvtt import vtt_check  # noqa: E402
from a11y_toolkit.a11ypdf import pdf_screen  # noqa: E402

VTT = """WEBVTT

1
00:00:00.000 --> 00:00:03.000
Hola mundo

2
00:00:04.000 --> 00:00:04.500
Supercalifragilisticexpialidocious texto largo imposible de leer a esta velocidad

3
00:00:05.000 --> 00:00:08.000


4
00:00:07.000 --> 00:00:09.000
Solapa

00:00:10.000 --> 00:00:12.000
Final
"""

# 1-5. VTT: los seis juicios sobre contenido
_orig = audit_mod._descarga
audit_mod._descarga = lambda url, **kw: VTT
try:
    r = vtt_check('https://x/c.vtt', duration=15, lang='en')
finally:
    audit_mod._descarga = _orig
sig = {h['signal'] for h in r['findings']}
assert {'vtt_empty_cue', 'vtt_too_fast', 'vtt_overlap', 'vtt_coverage'} <= sig, sig
assert r['cues'] == 5 and r['mode'] == 'vtt'
print('1. VTT: vacío + rápido + solape + cobertura ✓')


def mini_pdf(tagged=True, title=True, lang=True, texto=True, pages=3, img=False):
    objs = [b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R' +
            (b' /StructTreeRoot 5 0 R' if tagged else b'') +
            (b' /Lang (es-ES)' if lang else b'') + b' >>\nendobj\n']
    contenido = (b'BT (Hola documento) Tj ET\n' if texto else b'') * 4
    objs.append(b'2 0 obj\n<< /Type /Pages /Kids [' +
                b' '.join(b'%d 0 R' % (10 + i) for i in range(pages)) + b'] /Count ' +
                str(pages).encode() + b' >>\nendobj\n')
    objs.append(b'3 0 obj\n<< ' + (b'/Title (Informe) ' if title else b'') +
                b'/Producer (t) >>\nendobj\n')
    if tagged:
        objs.append(b'5 0 obj\n<< /Type /StructTreeRoot /MarkInfo << /Marked true >> >>\nendobj\n')
    if img:
        im = zlib.compress(b'\x00' * 81)
        objs.append(b'11 0 obj\n<< /Type /XObject /Subtype /Image /Width 9 /Height 9 '
                    b'/Filter /FlateDecode /Length %d >>\nstream\n' % len(im) + im + b'\nendstream\nendobj\n')
    comp = zlib.compress(contenido)
    body = b'%PDF-1.7\n' + b''.join(objs)
    body += b'6 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(comp) + comp + b'\nendstream\nendobj\n'
    for i in range(pages):
        body += (b'%d 0 obj\n<< /Type /Page /Contents 6 0 R' % (10 + i)
                 + (b' /Resources << /XObject << /Im0 11 0 R >> >>' if img else b'')
                 + b' >>\nendobj\n')
    return body + b'%%EOF\n'


# 6-8. PDF: bueno limpio, malo con las cuatro señales raíz
b = pdf_screen(mini_pdf(), lang='es')
assert b['tagged'] and b['lang'] == 'es-ES' and b['title'] == 'Informe' and not b['findings']
print('6. PDF bueno: 100 sin señales ✓')
m = pdf_screen(mini_pdf(tagged=False, title=False, lang=False, texto=False, img=True), lang='es')
assert {'pdf_untagged', 'pdf_no_title', 'pdf_no_lang', 'pdf_scanned'} <= {h['signal'] for h in m['findings']}
assert not pdf_screen(b'no-pdf').get('tagged', False) and 'error' in pdf_screen(b'no-pdf')
print('7. PDF malo: 4 señales raíz ✓  8. no-PDF rechazado ✓')

# 9. CLI real de ambos
ruta_pdf = os.path.join('/tmp', 'mini.pdf')
with open(ruta_pdf, 'wb') as f:
    f.write(mini_pdf(tagged=False, title=False, lang=False, texto=False))
out = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ypdf', ruta_pdf, '--lang', 'en'],
                     capture_output=True, text=True, cwd=ROOT, timeout=30)
d = json.loads(out.stdout)
assert d['mode'] == 'pdf' and d['findings']
print('9. CLI pdf ✓')

print('VTT+PDF OK ✓')

# 10. sin texto PERO sin imágenes: no hay base para acusar escaneo
solo_estructura = pdf_screen(mini_pdf(tagged=False, title=False, lang=False, texto=False), lang='es')
assert 'pdf_scanned' not in {h['signal'] for h in solo_estructura['findings']}
print('10. escaneo solo con patrón (img+sin texto) ✓')


# ── DOCX screening (5.9-c) ──
from a11y_toolkit.a11ydocx import docx_screen  # noqa: E402
W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

def docx_tmp(cuerpo, estilos=None, name='t.docx'):
    ruta = os.path.join('/tmp', name)
    z = zipfile.ZipFile(ruta, 'w')
    z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types/>')
    z.writestr('word/document.xml', '<?xml version="1.0"?>' + cuerpo)
    z.writestr('word/styles.xml', estilos or f'<?xml version="1.0"?><w:styles {W_NS}></w:styles>')
    z.close()
    return ruta

cuerpo_malo = f'<w:document {W_NS}><w:body>' \
    + '<w:p><w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr><w:t>Sección principal</w:t></w:r></w:p>' \
    + '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>a</w:t></w:r></w:p></w:tc></w:tr></w:tbl>' \
    + '<w:p><w:r><w:drawing><wp:docPr id="1" name="Img1"/></wp:drawing></w:r></w:p>' \
    + '</w:body></w:document>'
m = docx_screen(docx_tmp(cuerpo_malo, name='malo.docx'), lang='en')
sig_m = {h['signal'] for h in m['findings']}
assert {'docx_no_alt', 'docx_sin_idioma', 'docx_sin_tabla_header', 'docx_falsos_encabezados'} <= sig_m, sig_m
print('11. DOCX malo: 4 señales raíz ✓')

estilos_bien = (f'<?xml version="1.0"?><w:styles {W_NS}><w:docDefaults><w:rPrDefault>'
                f'<w:rPr><w:lang w:val="es-ES"/></w:rPr></w:rPrDefault></w:docDefaults></w:styles>')
cuerpo_bien = (f'<w:document {W_NS}><w:body>'
               + '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Sección</w:t></w:r></w:p>'
               + '<w:tbl><w:tr><w:trPr><w:tblHeader/></w:trPr><w:tc><w:p><w:r><w:t>a</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
               + '<w:p><w:r><w:drawing><wp:docPr id="1" name="i" descr="Gráfico de ventas"/></wp:drawing></w:r></w:p>'
               + '</w:body></w:document>')
b = docx_screen(docx_tmp(cuerpo_bien, estilos_bien, 'bien.docx'), lang='en')
assert not b['findings'] and b['idioma'] == 'es-ES', (b['findings'], b['idioma'])
print('12. DOCX bueno: sin señales, idioma detectado ✓')

assert 'error' in docx_screen('/tmp', lang='en')
print('13. no-docx rechazado ✓')

# 14. CLI real
out = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ydocx',
                      docx_tmp(cuerpo_malo, name='cli.docx'), '--lang', 'en'],
                     capture_output=True, text=True, cwd=ROOT, timeout=30)
d = json.loads(out.stdout)
assert d['mode'] == 'docx' and d['findings']
print('14. CLI docx ✓')

print('DOCX SCREENING OK ✓')
