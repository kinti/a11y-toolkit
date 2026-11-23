#!/usr/bin/env python3
"""DOCX accessibility screening — the other half of enterprise paperwork.

Un .docx es un ZIP: word/document.xml (el cuerpo), word/styles.xml, y las
imágenes en word/media/. Los fallos raíz de accesibilidad de documentos son
mecánicamente detectables sin dependencias: imágenes sin texto alternativo
(el bloque <wp:docPr> sin descr o con descr vacío), idioma del documento sin
declarar, y cabeceras falsas (párrafos que solo ponen negrita grande en vez
de estilos de encabezado — el "falso encabezado" que deshabilita el panel de
navegación y el índice automático).

Honestidad: el cribado de PDF y de DOCX comparten filosofía — encuentra lo
que hace inútil la revisión completa; no sustituye la revisión humana.

CLI:
  a11ydocx.py documento.docx [--lang en]
"""

import argparse
import json
import re
import sys
import zipfile
from . import a11yi18n

T = a11yi18n.pair('docx')  # locales/<lang>.json — community-editable

# techo de ingesta por miembro ZIP: 40 MB descomprimidos — un .docx legítimo
# no llega ni de lejos; una bomba ZIP sí
_MAX_MEMBER_BYTES = 40 * 1024 * 1024

_CRIT = {
    'docx_no_alt': ('1.1.1', 'high'), 'docx_fake_headings': ('1.3.1', 'medium'),
    'docx_no_lang': ('3.1.1', 'medium'), 'docx_table_no_header': ('1.3.1', 'low'),
    'docx_fake_list': ('1.3.1', 'medium'), 'docx_heading_skips': ('1.3.1', 'low'),
    'docx_generic_link': ('2.4.4', 'medium'),
}

# texto genérico de enlace (2.4.4): la misma familia del HTML, en la voz de
# los documentos (es/en); cuenta como genérico SOLO repetido (2+), un
# «descargar» solitario puede ser específico en contexto
_GENERIC_LINK = {
    'aquí', 'aquí.', 'pincha aquí', 'pulsa aquí', 'haz clic aquí', 'click here',
    'here', 'read more', 'leer más', 'más', 'ver más', 'more', 'download',
    'descargar', 'este enlace', 'this link', 'enlace', 'link', 'detalles',
    'details', 'más información', 'more information',
}
_BULLET = '•●▪◦‣·'


def _t(lang, key):
    return T.get(lang, T['en'])[key]


class _OverCap(Exception):
    """Un miembro del ZIP declara más bytes de los que la ingesta admite."""


def _capped_read(z, member):
    """Texto de un miembro del ZIP (None si no existe). El techo de
    descompresión por miembro vive AQUÍ, en la única puerta de lectura del
    cribado: file_size es el declarado del directorio central, el estándar
    contra bombas ZIP de los descompresores serios. Toda lectura pasa por
    esta función (document.xml y styles.xml lo hacían por una comprobación
    previa; la de document.xml.rels la eludía)."""
    try:
        info = z.getinfo(member)
    except KeyError:
        return None
    if info.file_size > _MAX_MEMBER_BYTES:
        raise _OverCap(f'{member} declares {info.file_size} bytes '
                       f'(>{_MAX_MEMBER_BYTES}): over the intake cap')
    return z.read(member).decode('utf-8', errors='replace')


def docx_screen(path, lang='en'):
    """Cribado de accesibilidad de un .docx (solo stdlib: zipfile + regex XML)."""
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError, IsADirectoryError, PermissionError) as e:
        return {'error': f'no es un .docx legible: {e}'}
    if 'word/document.xml' not in z.namelist():
        return {'error': 'ZIP without word/document.xml (is this really a .docx?)'}
    try:
        return _screen_zip(z, lang, path)
    except _OverCap as e:
        # contenido NO confiable: la ingesta no descomprime sin límite
        return {'error': str(e)}


def _screen_zip(z, lang, path):
    body = _capped_read(z, 'word/document.xml')

    findings = []

    def add(key):
        crit, sev = _CRIT[key]
        findings.append({'severity': sev, 'criterion': f'{crit} (DOCX)',
                          'signal': key, 'issue': _t(lang, key),
                          'remediation': _t(lang, key + '_rem')})

    # imágenes: cada <wp:docPr> es una imagen/gráfico; descr = alt text
    docprs = re.findall(r'<wp:docPr\b[^>]*>', body)
    no_alt = [d for d in docprs
               if 'descr=' not in d or re.search(r'descr="\s*"', d)]
    if docprs and no_alt:
        n = len(no_alt)
        findings.append({'severity': 'high', 'criterion': '1.1.1 (DOCX)',
                          'signal': 'docx_no_alt',
                          'issue': _t(lang, 'docx_no_alt').format(n=n),
                          'remediation': _t(lang, 'docx_no_alt_rem')})

    # idioma: w:lang en styles.xml (default del documento)
    language = None
    styles = _capped_read(z, 'word/styles.xml')
    if styles is not None:
        m = re.search(r'<w:lang[^>]*w:val="([^"]+)"', styles)
        language = m.group(1) if m else None
    if not language:
        add('docx_no_lang')

    # tablas sin fila de encabezado (tblHeader) — POR TABLA (5ª pasada: el
    # encabezado de la primera tapaba la falta de la segunda con un conteo
    # global, y <w:tblHeader w:val="true"/> —con atributos— no casaba con el
    # regex de elemento vacío)
    n_tables = len(re.findall(r'<w:tbl>', body))
    tables_missing = 0
    for tbl in re.findall(r'<w:tbl>.*?</w:tbl>', body, re.S):
        marked = [m for m in re.findall(r'<w:tblHeader\b[^>]*/?>', tbl)
                    if not re.search(r'w:val="(?:0|false|off)"', m, re.I)]
        if not marked:
            tables_missing += 1
    if n_tables and tables_missing:
        add('docx_table_no_header')

    # falsos encabezados: párrafo todo-bold + tamaño grande sin estilo Heading
    fake = 0
    for para in re.findall(r'<w:p\b.*?</w:p>', body, re.S):
        if 'w:val="Heading' in para:
            continue
        # bold real: <w:b> presente SIN val de apagado explícito (0/false)
        # — `<w:b w:val="0"/>` es bold-OFF y no cuenta
        has_bold = any(not re.search(r'w:val="(?:0|false)"', tag)
                       for tag in re.findall(r'<w:b\b[^>]*>', para))
        m_sz = re.search(r'<w:sz w:val="(\d+)"', para)
        large = bool(m_sz) and int(m_sz.group(1)) >= 28
        text = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', para)).strip()
        if has_bold and large and 2 < len(text) < 120:
            fake += 1
    if fake:
        findings.append({'severity': 'medium', 'criterion': '1.3.1 (DOCX)',
                          'signal': 'docx_fake_headings',
                          'issue': _t(lang, 'docx_fake_headings').format(n=fake),
                          'remediation': _t(lang, 'docx_fake_headings_rem')})

    # ── listas falsas: párrafos con viñetas/números TIPOGRAFIADOS en vez de
    # lista de Word (sin w:numPr). Umbral anti-FP: 2+ párrafos CONSECUTIVOS
    # con glifo de viñeta, o 3+ consecutivos numerados con incremento +1
    # (los «1. Enero» de las fechas no incrementan y quedan fuera).
    _doc_paragraphs = re.findall(r'<w:p\b.*?</w:p>|<w:p\b[^>]*/>', body, re.S)
    def _ptext(p):
        return ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p)).strip()
    fake_list_groups, _run = 0, []
    def _flush():
        nonlocal _run, fake_list_groups
        n_bul = sum(1 for t in _run if t[0] == 'b')
        if n_bul >= 2:
            fake_list_groups += 1
        elif len(_run) >= 3:
            nums = [t[1] for t in _run if t[0] == 'n']
            if len(nums) == len(_run):
                ok = all(nums[i+1] == nums[i] + 1 for i in range(len(nums)-1))
                if ok and nums[0] in (0, 1):
                    fake_list_groups += 1
        _run = []
    for p in _doc_paragraphs:
        if '<w:numPr' in p:
            _flush(); continue
        t = _ptext(p)
        if not t:
            _flush(); continue
        if t[0] in _BULLET:
            _run.append(('b', None)); continue
        m = re.match(r'^(\d{1,3})[.)]\s+\S', t)
        if m:
            _run.append(('n', int(m.group(1)))); continue
        _flush()
    _flush()
    if fake_list_groups:
        findings.append({'severity': 'medium', 'criterion': '1.3.1 (DOCX)',
                          'signal': 'docx_fake_list',
                          'issue': _t(lang, 'docx_fake_list').format(n=fake_list_groups),
                          'remediation': _t(lang, 'docx_fake_list_rem')})

    # ── saltos de nivel de encabezado: Heading1 → Heading3 aplana la
    # navegación. Niveles por pStyle directo (HeadingN) O por styles.xml
    # (los Word localizados escriben styleIds numéricos cuyo NOMBRE es
    # «heading N» / «Encabezado N» / «Título N»)
    _style_heads = {}
    sx = _capped_read(z, 'word/styles.xml') or ''
    for m in re.finditer(
            r'<w:style [^>]*w:styleId="([^"]+)"[^>]*>.*?'
            r'<w:name w:val="([^"]*)"', sx, re.S):
        mn = re.match(r'(?i)^(?:heading|encabezado|t[ií]tulo|'
                      r'berschrift|titre)\s*([1-9])$', m.group(2).strip())
        if mn:
            _style_heads[m.group(1)] = int(mn.group(1))
    levels = []
    for p in _doc_paragraphs:
        ms = re.search(r'<w:pStyle w:val="([^"]+)"', p)
        if not ms:
            continue
        sid = ms.group(1)
        if re.match(r'(?i)^TOC\d|Sumario|TDC', sid):
            continue
        md = re.match(r'(?i)^Heading([1-9])$', sid)
        if md:
            levels.append(int(md.group(1)))
        elif sid in _style_heads:
            levels.append(_style_heads[sid])
    skips = sum(1 for i in range(1, len(levels))
                if levels[i] > levels[i-1] + 1)
    if levels and skips:
        findings.append({'severity': 'low', 'criterion': '1.3.1 (DOCX)',
                          'signal': 'docx_heading_skips',
                          'issue': _t(lang, 'docx_heading_skips').format(n=skips),
                          'remediation': _t(lang, 'docx_heading_skips_rem')})

    # ── enlaces genéricos: «pincha aquí» (repetido), la URL cruda como
    # texto, o el mismo genérico apuntando a destinos distintos. Relaciones
    # desde word/_rels/document.xml.rels
    rels = {}
    rx = _capped_read(z, 'word/_rels/document.xml.rels') or ''
    for m in re.finditer(r'<Relationship [^>]*Id="([^"]+)"[^>]*Target="([^"]+)"', rx):
        rels[m.group(1)] = m.group(2)
    gen_counts, gen_multi, raw_url, img_links_noalt = {}, 0, 0, 0
    for hl in re.findall(r'<w:hyperlink\b.*?</w:hyperlink>', body, re.S):
        txt = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', hl)).strip()
        target = ''
        mr = re.search(r'r:id="([^"]+)"', hl)
        if mr:
            target = rels.get(mr.group(1), '')
        low = txt.lower().rstrip('.…: ')
        if txt and target and txt.replace(' ', '') in target:
            raw_url += 1
        elif low in _GENERIC_LINK:
            if gen_counts.get(low, (0, set()))[0] >= 1:
                gen_multi += 1
            n0, t0 = gen_counts.get(low, (0, set()))
            gen_counts[low] = (n0 + 1, t0 | {target})
        # enlace solo-imagen sin alt (el docPr dentro del hyperlink sin descr)
        if '<w:drawing' in hl or '<a:blip' in hl:
            for dp in re.findall(r'<wp:docPr\b[^>]*>', hl):
                if 'descr=' not in dp or re.search(r'descr="\s*"', dp):
                    img_links_noalt += 1
    generic_n = gen_multi + raw_url + img_links_noalt
    if generic_n:
        findings.append({'severity': 'medium', 'criterion': '2.4.4 (DOCX)',
                          'signal': 'docx_generic_link',
                          'issue': _t(lang, 'docx_generic_link').format(n=generic_n),
                          'remediation': _t(lang, 'docx_generic_link_rem')})

    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])

    # misma puntuación que pdf/vtt: compute_score compartido (12/6/2) — los
    # scores cross-mode son comparables
    from .a11yaudit import compute_score

    return {
        'mode': 'docx', 'file': str(path).rsplit('/', 1)[-1],
        'language': language, 'images': len(docprs),
        'tables': n_tables, 'tables_without_header': tables_missing,
        'heading_levels': levels,
        'score': compute_score(findings),
        'findings': findings,
        'summary': {s2: sum(1 for h in findings if h['severity'] == s2)
                    for s2 in ('high', 'medium', 'low')},
        'limits': _t(lang, 'limits'),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('docx', help='local .docx file')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    a = ap.parse_args(argv)
    print(json.dumps(docx_screen(a.docx, lang=a.lang), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
