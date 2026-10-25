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
Supercalifragilisticexpialidocious text largo imposible de leer a esta velocidad

3
00:00:05.000 --> 00:00:08.000


4
00:00:07.000 --> 00:00:09.000
Solapa

00:00:10.000 --> 00:00:12.000
Final
"""

# 1-5. VTT: los seis juicios sobre contenido
_orig = audit_mod._fetch
audit_mod._fetch = lambda url, **kw: VTT
try:
    r = vtt_check('https://x/c.vtt', duration=15, lang='en')
finally:
    audit_mod._fetch = _orig
sig = {h['signal'] for h in r['findings']}
assert {'vtt_empty_cue', 'vtt_too_fast', 'vtt_overlap', 'vtt_coverage'} <= sig, sig
assert r['cues'] == 5 and r['mode'] == 'vtt'
print('1. VTT: vacío + rápido + solape + cobertura ✓')


def mini_pdf(tagged=True, title=True, lang=True, text=True, pages=3, img=False):
    objs = [b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R' +
            (b' /StructTreeRoot 5 0 R' if tagged else b'') +
            (b' /Lang (es-ES)' if lang else b'') + b' >>\nendobj\n']
    contenido = (b'BT (Hola documento) Tj ET\n' if text else b'') * 4
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
m = pdf_screen(mini_pdf(tagged=False, title=False, lang=False, text=False, img=True), lang='es')
assert {'pdf_untagged', 'pdf_no_title', 'pdf_no_lang', 'pdf_scanned'} <= {h['signal'] for h in m['findings']}
assert not pdf_screen(b'no-pdf').get('tagged', False) and 'error' in pdf_screen(b'no-pdf')
print('7. PDF malo: 4 señales raíz ✓  8. no-PDF rechazado ✓')

# 9. CLI real de ambos
ruta_pdf = os.path.join('/tmp', 'mini.pdf')
with open(ruta_pdf, 'wb') as f:
    f.write(mini_pdf(tagged=False, title=False, lang=False, text=False))
out = subprocess.run([sys.executable, '-m', 'a11y_toolkit.a11ypdf', ruta_pdf, '--lang', 'en'],
                     capture_output=True, text=True, cwd=ROOT, timeout=30)
d = json.loads(out.stdout)
assert d['mode'] == 'pdf' and d['findings']
print('9. CLI pdf ✓')

print('VTT+PDF OK ✓')

# 10. sin text PERO sin imágenes: no hay base para acusar escaneo
solo_estructura = pdf_screen(mini_pdf(tagged=False, title=False, lang=False, text=False), lang='es')
assert 'pdf_scanned' not in {h['signal'] for h in solo_estructura['findings']}
print('10. escaneo solo con patrón (img+sin text) ✓')


# 11-14. formularios AcroForm sin /TU (3.3.2/4.1.2 — el hueco que nadie cubría)
def form_pdf(campos):
    """PDF con campos AcroForm: campos = [(tipo, /TU?)] · tipo 'tx'|'btn'."""
    objs = [b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R /AcroForm << /Fields [' +
            b' '.join(b'%d 0 R' % (20 + i) for i in range(len(campos))) + b'] >> >>\nendobj\n',
            b'2 0 obj\n<< /Type /Pages /Kids [10 0 R] /Count 1 >>\nendobj\n',
            b'3 0 obj\n<< /Producer (t) >>\nendobj\n']
    for i, (tipo, tu) in enumerate(campos):
        ft = {'tx': b'/Tx', 'btn': b'/Btn'}[tipo]
        objs.append(b'%d 0 obj\n<< /FT %s /T (f%d)%s /Subtype /Widget >>\nendobj\n'
                    % (20 + i, ft, i, b' /TU (Etiqueta campo %d)' % i if tu else b''))
    objs.append(b'10 0 obj\n<< /Type /Page /Contents 6 0 R >>\nendobj\n')
    comp = zlib.compress(b'BT (Formulario) Tj ET\n')
    return (b'%PDF-1.7\n' + b''.join(objs)
            + b'6 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(comp)
            + comp + b'\nendstream\nendobj\n%%EOF\n')


sin_tu = pdf_screen(form_pdf([('tx', False), ('tx', False), ('btn', False)]), lang='es')
senales = {h['signal'] for h in sin_tu['findings']}
assert {'pdf_form_no_label', 'pdf_button_no_name'} <= senales
assert sin_tu['form_fields'] == 3 and sin_tu['form_labels'] == 0
h_form = next(h for h in sin_tu['findings'] if h['signal'] == 'pdf_form_no_label')
h_btn = next(h for h in sin_tu['findings'] if h['signal'] == 'pdf_button_no_name')
assert h_form['severity'] == 'medium' and h_form['criterion'].startswith('3.3.2')
assert h_btn['severity'] == 'high' and h_btn['criterion'].startswith('4.1.2')
print('11. forms sin /TU: 3.3.2 (2 campos, media) + 4.1.2 (botón, alta) ✓')

con_tu = pdf_screen(form_pdf([('tx', True), ('btn', True)]), lang='en')
assert 'pdf_form_no_label' not in {h['signal'] for h in con_tu['findings']}
assert 'pdf_button_no_name' not in {h['signal'] for h in con_tu['findings']}
assert con_tu['form_labels'] == 2
print('12. forms con /TU: limpios ✓')

parcial = pdf_screen(form_pdf([('tx', True), ('tx', False), ('btn', False)]), lang='es')
senales_p = {h['signal'] for h in parcial['findings']}
assert 'pdf_form_no_label' in senales_p and 'pdf_button_no_name' not in senales_p
h_p = next(h for h in parcial['findings'] if h['signal'] == 'pdf_form_no_label')
assert '2 de 3' in h_p['issue']   # recuento honesto sin desglosar botones
print('13. parcial: 2 de 3, sin desglosar botones (herencia /Parent) ✓')

sin_forms = pdf_screen(mini_pdf(), lang='es')
assert 'pdf_form_no_label' not in {h['signal'] for h in sin_forms['findings']}
assert sin_forms['form_fields'] == 0
print('14. sin forms: no acusa ✓')


# ── DOCX screening (5.9-c) ──
from a11y_toolkit.a11ydocx import docx_screen  # noqa: E402
W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

def docx_tmp(body, styles=None, name='t.docx'):
    path = os.path.join('/tmp', name)
    z = zipfile.ZipFile(path, 'w')
    z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types/>')
    z.writestr('word/document.xml', '<?xml version="1.0"?>' + body)
    z.writestr('word/styles.xml', styles or f'<?xml version="1.0"?><w:styles {W_NS}></w:styles>')
    z.close()
    return path

cuerpo_malo = f'<w:document {W_NS}><w:body>' \
    + '<w:p><w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr><w:t>Sección principal</w:t></w:r></w:p>' \
    + '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>a</w:t></w:r></w:p></w:tc></w:tr></w:tbl>' \
    + '<w:p><w:r><w:drawing><wp:docPr id="1" name="Img1"/></wp:drawing></w:r></w:p>' \
    + '</w:body></w:document>'
m = docx_screen(docx_tmp(cuerpo_malo, name='malo.docx'), lang='en')
sig_m = {h['signal'] for h in m['findings']}
assert {'docx_no_alt', 'docx_no_lang', 'docx_table_no_header', 'docx_fake_headings'} <= sig_m, sig_m
print('11. DOCX malo: 4 señales raíz ✓')

estilos_bien = (f'<?xml version="1.0"?><w:styles {W_NS}><w:docDefaults><w:rPrDefault>'
                f'<w:rPr><w:lang w:val="es-ES"/></w:rPr></w:rPrDefault></w:docDefaults></w:styles>')
cuerpo_bien = (f'<w:document {W_NS}><w:body>'
               + '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Sección</w:t></w:r></w:p>'
               + '<w:tbl><w:tr><w:trPr><w:tblHeader/></w:trPr><w:tc><w:p><w:r><w:t>a</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
               + '<w:p><w:r><w:drawing><wp:docPr id="1" name="i" descr="Gráfico de ventas"/></wp:drawing></w:r></w:p>'
               + '</w:body></w:document>')
b = docx_screen(docx_tmp(cuerpo_bien, estilos_bien, 'bien.docx'), lang='en')
assert not b['findings'] and b['language'] == 'es-ES', (b['findings'], b['language'])
print('12. DOCX bueno: sin señales, language detectado ✓')

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
