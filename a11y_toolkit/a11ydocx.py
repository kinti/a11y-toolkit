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
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET
from . import a11yi18n

T = a11yi18n.pair('docx')  # locales/<lang>.json — community-editable

# techo de ingesta por miembro ZIP: 40 MB descomprimidos — un .docx legítimo
# no llega ni de lejos; una bomba ZIP sí
_MAX_MEMBER_BYTES = 40 * 1024 * 1024
_WORD_NS = ('http://schemas.openxmlformats.org/wordprocessingml/2006/main',
            'http://purl.oclc.org/ooxml/wordprocessingml/main')
_DRAWING_PROPERTIES = {
    '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr',
    '{http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing}docPr',
}
_RELATIONSHIP_IDS = (
    '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id',
    '{http://purl.oclc.org/ooxml/officeDocument/relationships}id',
)
_RELATIONSHIP = '{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'
_HEADING_NAME = re.compile(r'^(?:heading|encabezado|t[ií]tulo|überschrift|titre)\s*([1-9])$', re.I)

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
    """Bytes de un miembro del ZIP (None si no existe). El techo de
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
    return z.read(member)


class _DocumentTree(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ET.ParseError('DOCTYPE is not supported in DOCX parts')


def _read_xml(z, member):
    data = _capped_read(z, member)
    if data is None:
        return None
    return ET.fromstring(data, parser=ET.XMLParser(target=_DocumentTree()))


def docx_screen(path, lang='en'):
    """Screen a local DOCX using the standard library ZIP and XML readers."""
    try:
        with zipfile.ZipFile(path) as archive:
            return _screen_zip(archive, lang, path)
    except (OSError, zipfile.BadZipFile, RuntimeError, ET.ParseError, ValueError, _OverCap) as error:
        message = 'No se pudo leer el DOCX' if lang == 'es' else 'Could not read DOCX'
        return {'error': f'{message}: {error}', 'mode': 'docx', 'file': os.path.basename(path)}


def _screen_zip(z, lang, path):
    body = _read_xml(z, 'word/document.xml')
    if body is None or body.tag not in {f'{{{uri}}}document' for uri in _WORD_NS}:
        message = ('Falta el documento XML de WordprocessingML' if lang == 'es'
                   else 'Missing WordprocessingML document')
        return {'error': message, 'mode': 'docx', 'file': os.path.basename(path)}
    word = body.tag.split('}', 1)[0] + '}'
    namespaces = {'w': word[1:-1]}
    value = word + 'val'
    styles = _read_xml(z, 'word/styles.xml')
    relationships = _read_xml(z, 'word/_rels/document.xml.rels')
    findings = []

    def add(key, **fields):
        criterion, severity = _CRIT[key]
        findings.append({'severity': severity, 'criterion': f'{criterion} (DOCX)',
                          'signal': key, 'issue': _t(lang, key).format(**fields),
                          'remediation': _t(lang, key + '_rem')})

    def paragraph_text(element):
        return ''.join(text.text or '' for text in element.iter(word + 't')).strip()

    docprs = [node for node in body.iter() if node.tag in _DRAWING_PROPERTIES]
    no_alt = sum(not node.get('descr', '').strip() for node in docprs)
    if no_alt:
        add('docx_no_alt', n=no_alt)

    language = None
    if styles is not None:
        default = styles.find('w:docDefaults/w:rPrDefault/w:rPr/w:lang', namespaces)
        if default is None:
            default = styles.find('.//w:lang', namespaces)
        if default is not None:
            language = default.get(value)
    if not language:
        add('docx_no_lang')

    tables = list(body.iter(word + 'tbl'))
    tables_missing = 0
    for table in tables:
        pending, has_header = list(table), False
        for node in pending:
            if node.tag == word + 'tr':
                header = node.find('w:trPr/w:tblHeader', namespaces)
                if header is not None and header.get(value, 'true').lower() not in ('0', 'false', 'off'):
                    has_header = True
                    break
            elif node.tag != word + 'tbl':
                pending.extend(node)
        if not has_header:
            tables_missing += 1
    if tables_missing:
        add('docx_table_no_header', n=tables_missing)

    heading_styles = {}
    if styles is not None:
        for style in styles.iter(word + 'style'):
            name = style.find('w:name', namespaces)
            if name is not None:
                match = _HEADING_NAME.fullmatch(name.get(value, '').strip())
                if match:
                    heading_styles[style.get(word + 'styleId')] = int(match.group(1))

    levels, fake = [], 0
    fake_list_groups, sequence = 0, []

    def flush():
        nonlocal fake_list_groups
        if sequence.count(None) >= 2:
            fake_list_groups += 1
        elif (len(sequence) >= 3 and sequence[0] in (0, 1)
              and all(number == sequence[0] + i for i, number in enumerate(sequence))):
            fake_list_groups += 1
        sequence.clear()

    for paragraph in body.iter(word + 'p'):
        style = paragraph.find('w:pPr/w:pStyle', namespaces)
        style_id = style.get(value, '') if style is not None else ''
        direct = re.fullmatch(r'Heading([1-9])', style_id, re.I)
        level = int(direct.group(1)) if direct else heading_styles.get(style_id)
        text = paragraph_text(paragraph)
        if level and not re.match(r'(?i)^TOC\d|Sumario|TDC', style_id):
            levels.append(level)
        elif not style_id.startswith('Heading') and 2 < len(text) < 120:
            has_bold = any(node.get(value, 'true').lower() not in ('0', 'false')
                           for node in paragraph.iter(word + 'b'))
            size = paragraph.find('.//w:sz', namespaces)
            size_value = size.get(value, '') if size is not None else ''
            if has_bold and size_value.isascii() and size_value.isdecimal() and int(size_value) >= 28:
                fake += 1

        if not text or paragraph.find('.//w:numPr', namespaces) is not None:
            flush()
        elif text[0] in _BULLET:
            sequence.append(None)
        else:
            number = re.match(r'^(\d{1,3})[.)]\s+\S', text)
            if number:
                sequence.append(int(number.group(1)))
            else:
                flush()
    flush()
    if fake:
        add('docx_fake_headings', n=fake)
    if fake_list_groups:
        add('docx_fake_list', n=fake_list_groups)
    skips = sum(right > left + 1 for left, right in zip(levels, levels[1:]))
    if skips:
        add('docx_heading_skips', n=skips)

    targets = ({rel.get('Id'): rel.get('Target', '') for rel in relationships.iter(_RELATIONSHIP)}
               if relationships is not None else {})
    generic_links, seen_generic = 0, set()
    for hyperlink in body.iter(word + 'hyperlink'):
        text = paragraph_text(hyperlink)
        rel_id = hyperlink.get(_RELATIONSHIP_IDS[0]) or hyperlink.get(_RELATIONSHIP_IDS[1])
        target = targets.get(rel_id, '')
        label = text.lower().rstrip('.…: ')
        if text and target and text.replace(' ', '') in target:
            generic_links += 1
        elif label in _GENERIC_LINK:
            if label in seen_generic:
                generic_links += 1
            seen_generic.add(label)
        generic_links += sum(not node.get('descr', '').strip() for node in hyperlink.iter()
                             if node.tag in _DRAWING_PROPERTIES)
    if generic_links:
        add('docx_generic_link', n=generic_links)

    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])

    # misma puntuación que pdf/vtt: compute_score compartido (12/6/2) — los
    # scores cross-mode son comparables
    from .a11yaudit import compute_score

    return {
        'mode': 'docx', 'file': os.path.basename(path),
        'language': language, 'images': len(docprs),
        'tables': len(tables), 'tables_without_header': tables_missing,
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
    result = docx_screen(a.docx, lang=a.lang)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 1 if 'error' in result else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
