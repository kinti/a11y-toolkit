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

# 1b. HTTP REAL con Content-Type: text/vtt (revisión externa, 3ª pasada): el
# descargador rechazaba EL MIME del formato con err_not_html — y la suite no
# lo veía porque sustituía _fetch. El parámetro accept_ct ya existía.
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _VTTHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = VTT.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/vtt; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


_srv = HTTPServer(('127.0.0.1', 0), _VTTHandler)
threading.Thread(target=_srv.serve_forever, daemon=True).start()
try:
    r_http = vtt_check(f'http://127.0.0.1:{_srv.server_port}/c.vtt',
                       duration=15, lang='en')
finally:
    _srv.shutdown()
assert 'error' not in r_http, r_http.get('error')
assert r_http['cues'] == 5, r_http.get('cues')
print('1b. VTT sobre HTTP real con text/vtt: analizado, no err_not_html ✓')


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
        objs.append(b'9 0 obj\n<< /S /H1 >>\nendobj\n')   # doc limpio = con jerarquía
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

# 29. trío de estructura PDF: TD-sin-TH, sin H1-H6, contradicción PDF/UA
def _pdf_struct(struct=b'', xmp=b'', pages=3, lang=True, title=True):
    import zlib as _z2
    objs = [b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R /StructTreeRoot 5 0 R'
            + (b' /Lang (es-ES)' if lang else b'') + b' >>\nendobj\n',
            b'2 0 obj\n<< /Type /Pages /Kids ['
            + b' '.join(b'%d 0 R' % (10 + i) for i in range(pages))
            + b'] /Count ' + str(pages).encode() + b' >>\nendobj\n',
            b'3 0 obj\n<< ' + (b'/Title (Informe) ' if title else b'')
            + b'/Producer (t) >>\nendobj\n',
            b'5 0 obj\n<< /Type /StructTreeRoot /MarkInfo << /Marked true >> >>\nendobj\n']
    if struct:
        objs.append(struct)
    if xmp:
        objs.append(xmp)
    comp = _z2.compress(b'BT (Hola) Tj ET' * 4)
    out = b'%PDF-1.7\n' + b''.join(objs)
    offs = [out.find(t) for t in (b'1 0 obj', b'2 0 obj', b'3 0 obj', b'5 0 obj')]
    out += (b'6 0 obj\n<< /Length ' + str(len(comp)).encode()
            + b' /Filter /FlateDecode >>\nstream\n' + comp + b'\nendstream\nendobj\n')
    for i in range(pages):
        out += b'%d 0 obj\n<< /Type /Page /Contents 6 0 R >>\nendobj\n' % (10 + i)
    xref_at = len(out)
    out += (b'xref\n0 16\n0000000000 65535 f \n'
            + b''.join(('%010d 00000 n \n' % o).encode() for o in offs))
    out += b'trailer\n<< /Size 16 /Root 1 0 R >>\nstartxref\n' \
           + str(xref_at).encode() + b'\n%%EOF'
    import tempfile as _tf2, os as _os2
    d = _tf2.mkdtemp()
    p = _os2.path.join(d, 't.pdf')
    open(p, 'wb').write(out)
    return p
_TD = b'7 0 obj\n<< /S /TD >>\nendobj\n'
_TH = b'8 0 obj\n<< /S /TH >>\nendobj\n'
_H1 = b'9 0 obj\n<< /S /H1 >>\nendobj\n'
_XMP_UA = (b'11 0 obj\n<< /Type /Metadata /Subtype /XML >>\nstream\n'
           b'<?xpacket?><rdf:RDF xmlns:pdfuaid="u">'
           b'<rdf:Description pdfuaid:part="2"/></rdf:RDF></xpacket>\nendstream\nendobj\n')
assert 'pdf_table_no_header' in {h['signal'] for h in pdf_screen(_pdf_struct(struct=_TD), lang='es')['findings']}
assert 'pdf_table_no_header' not in {h['signal'] for h in pdf_screen(_pdf_struct(struct=_TD + _TH + _H1), lang='es')['findings']}
assert 'pdf_no_heading_tags' in {h['signal'] for h in pdf_screen(_pdf_struct(struct=b'7 0 obj\n<< /S /P >>\nendobj\n'), lang='es')['findings']}
assert 'pdf_no_heading_tags' not in {h['signal'] for h in pdf_screen(_pdf_struct(struct=_H1), lang='es')['findings']}
_r_ua = pdf_screen(_pdf_struct(struct=_TD, xmp=_XMP_UA, lang=False, title=False), lang='es')
assert 'pdfua_contradiction' in {h['signal'] for h in _r_ua['findings']} and _r_ua['pdfua_claimed'] == 2
_r_uo = pdf_screen(_pdf_struct(struct=_TD + _TH + _H1, xmp=_XMP_UA), lang='es')
assert 'pdfua_contradiction' not in {h['signal'] for h in _r_uo['findings']}
print('29. trío estructura PDF: TD/TH, jerarquía y sello PDF/UA ✓')

# 29b. la declaración PDF/UA viaja de dos formas en el XMP: como atributo (la
# única que se leía) y como elemento RDF. Mismo PDF de prueba, misma lectura:
# con el elemento, pdfua_claimed quedaba en None y el sello que miente sobre
# su documento pasaba sin aviso
def _xmp_elem(body):
    return (b'11 0 obj\n<< /Type /Metadata /Subtype /XML >>\nstream\n'
            b'<?xpacket?><rdf:RDF xmlns:pdfuaid="u">' + body
            + b'</rdf:RDF></xpacket>\nendstream\nendobj\n')


for _xmp in (_xmp_elem(b'<rdf:Description><pdfuaid:part>2</pdfuaid:part></rdf:Description>'),
             _xmp_elem(b'<rdf:Description>\n  <pdfuaid:part>\n    2\n  </pdfuaid:part>\n'
                       b'</rdf:Description>')):
    _r_el = pdf_screen(_pdf_struct(struct=_TD, xmp=_xmp, lang=False, title=False), lang='es')
    assert _r_el['pdfua_claimed'] == 2, _r_el['pdfua_claimed']
    assert 'pdfua_contradiction' in {h['signal'] for h in _r_el['findings']}, _r_el
    _r_el_ok = pdf_screen(_pdf_struct(struct=_TD + _TH + _H1, xmp=_xmp), lang='es')
    assert _r_el_ok['pdfua_claimed'] == 2
    assert 'pdfua_contradiction' not in {h['signal'] for h in _r_el_ok['findings']}, _r_el_ok
assert pdf_screen(_pdf_struct(struct=_TD), lang='es')['pdfua_claimed'] is None
print('29b. PDF/UA: la declaración se lee como atributo y como elemento XMP ✓')

from a11y_toolkit.a11ydocx import docx_screen as _dx_screen  # noqa: E402

# 30. trío DOCX: lista falsa, salto de título, enlace genérico (fixtures ZIP)
def _docx(paras, rels=None):
    import zipfile as _zf, tempfile as _tf3, os as _os3
    d = _tf3.mkdtemp()
    p = _os3.path.join(d, 't.docx')
    with _zf.ZipFile(p, 'w') as z:
        z.writestr('word/document.xml',
                   '<?xml version="1.0"?><w:document xmlns:w="x" xmlns:r="y"><w:body>'
                   + paras + '</w:body></w:document>')
        z.writestr('word/styles.xml',
                   '<w:styles><w:style w:styleId="T1" w:type="paragraph">'
                   '<w:name w:val="heading 1"/></w:style>'
                   '<w:style w:styleId="T3" w:type="paragraph">'
                   '<w:name w:val="heading 3"/></w:style></w:styles>')
        if rels:
            z.writestr('word/_rels/document.xml.rels', rels)
    return p
def _P(text, style=None, num=False):
    st = f'<w:pStyle w:val="{style}"/>' if style else ''
    np_ = '<w:numPr><w:ilvl w:val="0"/></w:numPr>' if num else ''
    return f'<w:p><w:pPr>{np_}{st}</w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'
def _HL(text):
    return f'<w:hyperlink r:id="rId7"><w:r><w:t>{text}</w:t></w:r></w:hyperlink>'
_RELS = ('<?xml version="1.0"?><Relationships>'
         '<Relationship Id="rId7" Target="https://e.com/informe.pdf"/></Relationships>')
_r1 = _dx_screen(_docx(_P('• una') + _P('• dos') + _P('• tres')), lang='es')
assert 'docx_fake_list' in {h['signal'] for h in _r1['findings']}
assert 'docx_fake_list' not in {h['signal'] for h in _dx_screen(_docx(_P('una', num=True) + _P('dos', num=True)), lang='es')['findings']}
_r2 = _dx_screen(_docx(_P('T', 'T1') + _P('S', 'T3')), lang='es')
assert 'docx_heading_skips' in {h['signal'] for h in _r2['findings']}
assert 'docx_heading_skips' not in {h['signal'] for h in _dx_screen(_docx(_P('T', 'T1') + _P('S', 'Heading2')), lang='es')['findings']}
_r3 = _dx_screen(_docx(_HL('pincha aquí') + _HL('pincha aquí') + _P('x')
                        + _HL('https://e.com/informe.pdf'), rels=_RELS), lang='es')
assert 'docx_generic_link' in {h['signal'] for h in _r3['findings']}
print('30. trío DOCX: lista falsa, salto de títulos, enlaces genéricos ✓')


# 28. modo de render del texto: Tr 3 puro = capa OCR (dato + nota), mezcla = no
import zlib as _z
def _pdf_tr(content):
    comp = _z.compress(content)
    head = (b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
            b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
            b'3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n')
    stream = (b'4 0 obj\n<< /Length ' + str(len(comp)).encode()
              + b' /Filter /FlateDecode >>\nstream\n' + comp + b'\nendstream\nendobj\n')
    xref_at = len(head) + len(stream)
    xref = b'xref\n0 5\n0000000000 65535 f \n'
    for tag in (b'1 0 obj', b'2 0 obj', b'3 0 obj', b'4 0 obj'):
        xref += ('%010d 00000 n \n' % head.find(tag)).encode()
    tail = b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n' + str(xref_at).encode() + b'\n%%EOF'
    return head + stream + xref + tail
_r_ocr = pdf_screen(_pdf_tr(b'BT 3 Tr (capa invisible) Tj ET'), lang='es')
assert _r_ocr['ocr_layer_only'] is True and _r_ocr['ocr_layer_note'], _r_ocr.get('text_render')
_r_mix = pdf_screen(_pdf_tr(b'BT 3 Tr (inv) Tj 0 Tr (vis) Tj ET'), lang='es')
assert _r_mix['ocr_layer_only'] is False and 'ocr_layer_note' not in _r_mix
print('28. PDF Tr3 (capa OCR): puro dispara dato+nota, mixto no ✓')
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


# ── Regresiones: parseo de contraste en content streams PDF ──
# (bug: `0 0 612 792 re` se leía como triple RGB → fondo cian falso)
from a11y_toolkit.a11ypdf import _stream_low_contrast  # noqa: E402
import a11y_toolkit.a11ypdf as pdf_mod  # noqa: E402

# 15. re+f pinta el fondo: header BLANCO sobre rect oscuro → ratio ~17, sin acusación
assert _stream_low_contrast('0.1 0.1 0.1 rg 0 0 612 792 re f 1 1 1 rg (Header) Tj') == []
# el mismo header blanco SIN rect pintado (fondo blanco) → acusación
hits = _stream_low_contrast('1 1 1 rg (Header) Tj')
assert len(hits) == 1 and hits[0].startswith('rgb(255,255,255)'), hits

# 16. gris claro sobre blanco → acusación con el rgb correcto (0.7*255 ≈ 178)
hits = _stream_low_contrast('0.7 0.7 0.7 rg (x) Tj')
assert len(hits) == 1 and hits[0].startswith('rgb(178,178,178)'), hits

# 17. `re` SIN operador de pintado no cambia nada (operandos nunca son color)
assert _stream_low_contrast('0 0 612 792 re 0 0 0 rg (x) Tj') == []

# 18. TJ en forma de array cuenta como op de texto (paridad con n_text)
hits = _stream_low_contrast('0.7 0.7 0.7 rg [(B) 2 (ad)] TJ')
assert len(hits) == 1, hits

# 18b. `g` (gris) y `k` (CMYK) también fijan el color de relleno
assert len(_stream_low_contrast('0.75 g (x) Tj')) == 1            # gris 191 sobre blanco
assert _stream_low_contrast('0 0 0 1 k (x) Tj') == []             # negro CMYK → 21:1
print('15-18. content streams: rg/g/k vs re+f, TJ array ✓')

# 18c. end-to-end: pdf_low_contrast emerge de pdf_screen con ejemplo correcto
comp_lc = zlib.compress(b'BT 0.7 0.7 0.7 rg (texto gris claro) Tj ET\n')
hdr_lc = b'6 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(comp_lc)
pdf_lc = (b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
          b'2 0 obj\n<< /Type /Pages /Kids [10 0 R] /Count 1 >>\nendobj\n'
          + hdr_lc + comp_lc + b'\nendstream\nendobj\n'
          b'10 0 obj\n<< /Type /Page /Contents 6 0 R >>\nendobj\n%%EOF\n')
r_lc = pdf_screen(pdf_lc, lang='en')
h_lc = next(h for h in r_lc['findings'] if h['signal'] == 'pdf_low_contrast')
assert 'rgb(178,178,178)' in h_lc['issue'], h_lc['issue']
print('18c. pdf_low_contrast end-to-end con rgb correcto ✓')


def small_pdf(catalog=b'<< /Type /Catalog /Pages 2 0 R >>', extra_objs=b'',
              contenido=b'BT (doc) Tj ET\n', img=False):
    objs = [b'1 0 obj\n' + catalog + b'\nendobj\n',
            b'2 0 obj\n<< /Type /Pages /Kids [10 0 R] /Count 1 >>\nendobj\n',
            b'3 0 obj\n<< /Title (t) >>\nendobj\n', extra_objs]
    if img:
        objs.append(b'11 0 obj\n<< /Type /XObject /Subtype /Image /Width 2 /Height 2 '
                    b'/Length 0 >>\nstream\n\nendstream\nendobj\n')
    comp = zlib.compress(contenido)
    body = b'%PDF-1.7\n' + b''.join(objs)
    body += b'6 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(comp) \
        + comp + b'\nendstream\nendobj\n'
    body += b'10 0 obj\n<< /Type /Page /Contents 6 0 R' \
        + (b' /Resources << /XObject << /Im0 11 0 R >> >>' if img else b'') \
        + b' >>\nendobj\n%%EOF\n'
    return body


# 19. /Alt en hex (<FEFF...>, UTF-16BE natural para alt no latino) cuenta —
# paridad con /TU que ya aceptaba [<(]
alt_hex = small_pdf(
    catalog=b'<< /Type /Catalog /Pages 2 0 R /StructTreeRoot 5 0 R /Lang (es) >>',
    extra_objs=b'5 0 obj\n<< /Type /StructTreeRoot /MarkInfo << /Marked true >> >>\nendobj\n'
               b'12 0 obj\n<< /Type /StructElem /S /Figure /Alt <FEFF0041> >>\nendobj\n',
    img=True)
r19 = pdf_screen(alt_hex, lang='en')
assert r19['alt_entries'] == 1, r19['alt_entries']
assert 'pdf_no_alt' not in {h['signal'] for h in r19['findings']}
print('19. /Alt <hex> cuenta como alt entry ✓')

# 20. mención suelta de /StructTreeRoot dentro de un content stream → NO tagged
stray = small_pdf(contenido=b'BT (/StructTreeRoot suelto en el texto) Tj ET\n')
r20 = pdf_screen(stray, lang='en')
assert r20['tagged'] is False and 'pdf_untagged' in {h['signal'] for h in r20['findings']}
print('20. mención suelta de /StructTreeRoot no cuenta como estructura ✓')

# 21. objeto /Type /StructTreeRoot + /Marked true (sin ref N 0 R) → tagged
mark_only = small_pdf(
    extra_objs=b'5 0 obj\n<< /Type /StructTreeRoot /MarkInfo << /Marked true >> >>\nendobj\n')
r21 = pdf_screen(mark_only, lang='en')
assert r21['tagged'] is True and 'pdf_untagged' not in {h['signal'] for h in r21['findings']}
print('21. /Type /StructTreeRoot + /Marked true → tagged ✓')

# 22. bomba de descompresión repartida: techo ACUMULADO además del por-stream
_cap, _budget = pdf_mod._STREAM_CAP, pdf_mod._STREAM_BUDGET
pdf_mod._STREAM_CAP, pdf_mod._STREAM_BUDGET = 100_000, 250_000
try:
    payload = zlib.compress(b'\x00' * 50_000)  # 50KB descomprimidos por stream
    bomb = b'%PDF-1.7\n' + b''.join(
        b'%d 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n' % (i, len(payload))
        + payload + b'\nendstream\nendobj\n' for i in range(1, 41)) + b'%%EOF\n'
    out = pdf_mod._uncompressed_streams(bomb)
    assert len(out) == 5 and sum(len(s) for s in out) == 250_000, \
        (len(out), sum(len(s) for s in out))
    r22 = pdf_mod.pdf_screen(bomb, lang='en')
    assert r22['mode'] == 'pdf' and r22['findings']
finally:
    pdf_mod._STREAM_CAP, pdf_mod._STREAM_BUDGET = _cap, _budget
print('22. bomba repartida en streams: techo acumulado ✓')


# ── Regresiones VTT: BOM y marcado inline ──
def _vtt_run(text, duration=None, lang='en'):
    _orig2 = audit_mod._fetch
    audit_mod._fetch = lambda url, **kw: text
    try:
        return vtt_check('https://x/c.vtt', duration=duration, lang=lang)
    finally:
        audit_mod._fetch = _orig2


# 23. BOM UTF-8 delante de WEBVTT es válido (lstrip no lo quitaba)
r23 = _vtt_run('\ufeffWEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHola\n')
assert r23['mode'] == 'vtt' and r23['cues'] == 1, r23
assert 'error' in _vtt_run('\ufeffhola\n')
print('23. VTT con BOM parsea; sin WEBVTT sigue siendo error ✓')

# 24. cue con etiqueta de voz <v> TAMBIÉN se mide (antes: excluidas del cps)
fast_v = ('WEBVTT\n\n00:00:00.000 --> 00:00:00.500\n'
          '<v Narrador>Supercalifragilistic texto larguisimo imposible</v>\n')
assert 'vtt_too_fast' in {h['signal'] for h in _vtt_run(fast_v)['findings']}

# 25. las etiquetas inline no cuentan como caracteres de lectura: mismo cps
# con y sin <i>/<b> envolviendo el MISMO texto visible
_base_fast = 'Supercalifragilistic texto larguisimo imposible'  # 47 chars / 2s = 23.5cps
_sin = f'WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n{_base_fast}\n'
_con = f'WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n<i>{_base_fast}</i>\n'
f_sin = [h for h in _vtt_run(_sin)['findings'] if h['signal'] == 'vtt_too_fast']
f_con = [h for h in _vtt_run(_con)['findings'] if h['signal'] == 'vtt_too_fast']
assert f_sin and f_sin == f_con, (f_sin, f_con)
# y una cue que SOLO pasa de 21 contando etiquetas → sin acusación
corta = 'WEBVTT\n\n00:00:00.000 --> 00:00:00.500\n<i>abcde</i>\n'  # 5 visibles / 0.5s = 10cps
assert 'vtt_too_fast' not in {h['signal'] for h in _vtt_run(corta)['findings']}
print('24-25. VTT: cues <v> medidas, etiquetas no cuentan ✓')


# ── Regresiones DOCX: bold-off y score compartido ──
# 26. `<w:b w:val="0"/>` es bold-OFF: no hace falso encabezado
cuerpo_bold_off = (f'<w:document {W_NS}><w:body>'
                   + '<w:p><w:r><w:rPr><w:b w:val="0"/><w:sz w:val="36"/></w:rPr>'
                   + '<w:t>No soy titulo</w:t></w:r></w:p>'
                   + '</w:body></w:document>')
r26 = docx_screen(docx_tmp(cuerpo_bold_off, estilos_bien, 'boldoff.docx'), lang='en')
assert 'docx_fake_headings' not in {h['signal'] for h in r26['findings']}
cuerpo_bold_on = (f'<w:document {W_NS}><w:body>'
                  + '<w:p><w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr>'
                  + '<w:t>Soy titulo fake</w:t></w:r></w:p>'
                  + '</w:body></w:document>')
r26b = docx_screen(docx_tmp(cuerpo_bold_on, estilos_bien, 'boldon.docx'), lang='en')
assert 'docx_fake_headings' in {h['signal'] for h in r26b['findings']}
print('26. w:b w:val="0" no es bold; <w:b/> sí ✓')

# 27. score docx == compute_score == mismo multiset de severidades que pdf
from a11y_toolkit.a11yaudit import compute_score  # noqa: E402
par_pdf = pdf_screen(mini_pdf(tagged=False, title=False, lang=False), lang='en')
cuerpo_par = (f'<w:document {W_NS}><w:body>'
              + '<w:p><w:r><w:drawing><wp:docPr id="1" name="Img1"/></wp:drawing></w:r></w:p>'
              + '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>a</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
              + '</w:body></w:document>')
par_docx = docx_screen(docx_tmp(cuerpo_par, name='par.docx'), lang='en')
assert par_docx['score'] == par_pdf['score'] == 80, (par_docx['score'], par_pdf['score'])
assert par_docx['score'] == compute_score(par_docx['findings'])
print('27. score docx = compute_score = score pdf (mismo multiset) ✓')

# 28. techo de descompresión por miembro (revisión externa 2026-11-22): la
# ingesta de un .docx hostil no puede descomprimir sin límite. Techo parcheado
# a 100 bytes para no fabricar 40 MB en el suite — el guard usa file_size
# declarado del directorio central ANTES de leer
import a11y_toolkit.a11ydocx as _mod_docx
_cuerpo_grande = (f'<w:document {W_NS}><w:body>'
                  + '<w:p><w:r><w:t>' + 'x' * 500 + '</w:t></w:r></w:p>'
                  + '</w:body></w:document>')
_grande = docx_tmp(_cuerpo_grande, name='grande.docx')
_techo_original = _mod_docx._MAX_MEMBER_BYTES
_mod_docx._MAX_MEMBER_BYTES = 100
try:
    r28 = docx_screen(_grande, lang='en')
finally:
    _mod_docx._MAX_MEMBER_BYTES = _techo_original
assert 'error' in r28 and 'cap' in r28['error'], r28
print('28. techo de ingesta ZIP: member > límite → error, sin descomprimir ✓')

# 28b. TODAS las lecturas del cribado pasan por el techo. La de
# word/_rels/document.xml.rels lo eludía: con el mismo tamaño que styles.xml,
# styles se rechazaba y las relaciones entraban. document.xml y styles.xml
# pequeños, relaciones por encima del techo
import zipfile as _zf_cap
import tempfile as _tf_cap
import os as _os_cap


def _docx_cap(rels_txt):
    p = _os_cap.path.join(_tf_cap.mkdtemp(), 'cap.docx')
    with _zf_cap.ZipFile(p, 'w') as z:
        z.writestr('word/document.xml',
                   '<w:document xmlns:w="x"><w:body><w:p/></w:body></w:document>')
        z.writestr('word/styles.xml', '<w:styles/>')
        z.writestr('word/_rels/document.xml.rels', rels_txt)
    return p


_mod_docx._MAX_MEMBER_BYTES = 100
try:
    r_rels = docx_screen(_docx_cap('<Relationships>' + ' ' * 500 + '</Relationships>'), lang='en')
    r_small = docx_screen(_docx_cap('<Relationships/>'), lang='en')
finally:
    _mod_docx._MAX_MEMBER_BYTES = _techo_original
assert 'error' in r_rels and 'document.xml.rels' in r_rels['error'] and 'cap' in r_rels['error'], r_rels
assert 'error' not in r_small, r_small
# pin estructural: una sola puerta de lectura del ZIP en todo el cribado
import inspect as _insp_cap
_src_cap = _insp_cap.getsource(_mod_docx)
assert len(_mod_docx.re.findall(r'\bz\.read\(', _src_cap)) == 1, 'lectura del ZIP fuera del techo'
assert 'def _capped_read' in _src_cap
print('28b. techo de ingesta ZIP: relaciones y cualquier otro miembro, por la misma puerta ✓')

print('Regresiones PDF/DOCX/VTT OK ✓')
