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

_CRIT = {
    'docx_no_alt': ('1.1.1', 'high'), 'docx_fake_headings': ('1.3.1', 'medium'),
    'docx_no_lang': ('3.1.1', 'medium'), 'docx_table_no_header': ('1.3.1', 'low'),
}


def _t(lang, key):
    return T.get(lang, T['en'])[key]


def docx_screen(path, lang='en'):
    """Cribado de accesibilidad de un .docx (solo stdlib: zipfile + regex XML)."""
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError, IsADirectoryError, PermissionError) as e:
        return {'error': f'no es un .docx legible: {e}'}
    if 'word/document.xml' not in z.namelist():
        return {'error': 'ZIP sin word/document.xml (¿es un .docx de verdad?)'}

    body = z.read('word/document.xml').decode('utf-8', errors='replace')

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
    try:
        styles = z.read('word/styles.xml').decode('utf-8', errors='replace')
        m = re.search(r'<w:lang[^>]*w:val="([^"]+)"', styles)
        language = m.group(1) if m else None
    except KeyError:
        pass
    if not language:
        add('docx_no_lang')

    # tablas sin fila de encabezado (tblHeader)
    n_tables = len(re.findall(r'<w:tbl>', body))
    n_tblheader = len(re.findall(r'<w:tblHeader\s*/?>', body))
    if n_tables and not n_tblheader:
        add('docx_table_no_header')

    # falsos encabezados: párrafo todo-bold + tamaño grande sin estilo Heading
    fake = 0
    for para in re.findall(r'<w:p\b.*?</w:p>', body, re.S):
        if 'w:val="Heading' in para:
            continue
        has_bold = '<w:b/>' in para or '<w:b ' in para
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

    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])

    def score(hs):
        return max(0, 100 - 25 * sum(1 for h in hs if h['severity'] == 'high')
                   - 10 * sum(1 for h in hs if h['severity'] == 'medium')
                   - 5 * sum(1 for h in hs if h['severity'] == 'low'))

    return {
        'mode': 'docx', 'file': str(path).rsplit('/', 1)[-1],
        'language': language, 'images': len(docprs),
        'tables': n_tables, 'tables_with_header': n_tblheader,
        'score': score(findings),
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
