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

T = {
    'es': {
        'docx_no_alt': '{n} imágenes sin texto alternativo (docPr sin descr o descr vacío): invisibles para el lector de pantalla (1.1.1).',
        'docx_no_alt_rem': 'Clic derecho en cada imagen → «Editar texto alternativo» y descríbela. Las decorativas: marca la casilla «decorativa».',
        'docx_falsos_encabezados': '{n} párrafos con solo negrita/grande: parecen encabezados pero no lo son — el panel de navegación y el índice no los ven (1.3.1).',
        'docx_falsos_encabezados_rem': 'Aplica estilo «Título 1/2» en vez de negrita manual: así existen en el panel de navegación y en el índice.',
        'docx_sin_idioma': 'idioma del documento sin declarar: la voz sintética y el corrector no saben (3.1.1).',
        'docx_sin_idioma_rem': 'Revisar → Idioma → establece el idioma del documento completo.',
        'docx_sin_tabla_header': '{n} tablas sin fila de encabezado marcada: las celdas pierden su contexto de columna (1.3.1).',
        'docx_sin_tabla_header_rem': 'Tabla → fila de encabezado marcada («Repetir filas de encabezado» en tablas multi-página).',
        'limits': ('Cribado estructural del XML: no sustituye la revisión humana '
                   '(orden de lectura de tablas complejas, significado de imágenes '
                   'con alt insuficiente, gráficos incrustados).'),
    },
    'en': {
        'docx_no_alt': '{n} images with no alternative text (docPr without descr, or empty): invisible to screen readers (1.1.1).',
        'docx_no_alt_rem': 'Right-click each image → "Edit Alt Text" and describe it. Decorative ones: tick "decorative".',
        'docx_falsos_encabezados': '{n} paragraphs with just bold/large text: they LOOK like headings but are not — navigation pane and auto-TOC cannot see them (1.3.1).',
        'docx_falsos_encabezados_rem': 'Apply the "Heading 1/2" style instead of manual bold: then they exist in the navigation pane and the TOC.',
        'docx_sin_idioma': 'document language not declared: synthetic voice and spellcheck cannot pick (3.1.1).',
        'docx_sin_idioma_rem': 'Review → Language → set the whole-document language.',
        'docx_sin_tabla_header': '{n} tables with no marked header row: cells lose their column context (1.3.1).',
        'docx_sin_tabla_header_rem': 'Table → mark the header row ("Repeat header rows" for multi-page tables).',
        'limits': ('Structural XML screening: not a substitute for human review '
                   '(reading order of complex tables, meaning of under-described '
                   'images, embedded charts).'),
    },
}

_CRIT = {
    'docx_no_alt': ('1.1.1', 'high'), 'docx_falsos_encabezados': ('1.3.1', 'medium'),
    'docx_sin_idioma': ('3.1.1', 'medium'), 'docx_sin_tabla_header': ('1.3.1', 'low'),
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

    cuerpo = z.read('word/document.xml').decode('utf-8', errors='replace')

    hallazgos = []

    def add(key):
        crit, sev = _CRIT[key]
        hallazgos.append({'severity': sev, 'criterion': f'{crit} (DOCX)',
                          'signal': key, 'issue': _t(lang, key),
                          'remediation': _t(lang, key + '_rem')})

    # imágenes: cada <wp:docPr> es una imagen/gráfico; descr = alt text
    docprs = re.findall(r'<wp:docPr\b[^>]*>', cuerpo)
    sin_alt = [d for d in docprs
               if 'descr=' not in d or re.search(r'descr="\s*"', d)]
    if docprs and sin_alt:
        n = len(sin_alt)
        hallazgos.append({'severity': 'high', 'criterion': '1.1.1 (DOCX)',
                          'signal': 'docx_no_alt',
                          'issue': _t(lang, 'docx_no_alt').format(n=n),
                          'remediation': _t(lang, 'docx_no_alt_rem')})

    # idioma: w:lang en styles.xml (default del documento)
    idioma = None
    try:
        estilos = z.read('word/styles.xml').decode('utf-8', errors='replace')
        m = re.search(r'<w:lang[^>]*w:val="([^"]+)"', estilos)
        idioma = m.group(1) if m else None
    except KeyError:
        pass
    if not idioma:
        add('docx_sin_idioma')

    # tablas sin fila de encabezado (tblHeader)
    n_tablas = len(re.findall(r'<w:tbl>', cuerpo))
    n_tblheader = len(re.findall(r'<w:tblHeader\s*/?>', cuerpo))
    if n_tablas and not n_tblheader:
        add('docx_sin_tabla_header')

    # falsos encabezados: párrafo todo-bold + tamaño grande sin estilo Heading
    falsos = 0
    for para in re.findall(r'<w:p\b.*?</w:p>', cuerpo, re.S):
        if 'w:val="Heading' in para:
            continue
        tiene_bold = '<w:b/>' in para or '<w:b ' in para
        m_sz = re.search(r'<w:sz w:val="(\d+)"', para)
        grande = bool(m_sz) and int(m_sz.group(1)) >= 28
        texto = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', para)).strip()
        if tiene_bold and grande and 2 < len(texto) < 120:
            falsos += 1
    if falsos:
        hallazgos.append({'severity': 'medium', 'criterion': '1.3.1 (DOCX)',
                          'signal': 'docx_falsos_encabezados',
                          'issue': _t(lang, 'docx_falsos_encabezados').format(n=falsos),
                          'remediation': _t(lang, 'docx_falsos_encabezados_rem')})

    orden = {'high': 0, 'medium': 1, 'low': 2}
    hallazgos.sort(key=lambda h: orden[h['severity']])

    def score(hs):
        return max(0, 100 - 25 * sum(1 for h in hs if h['severity'] == 'high')
                   - 10 * sum(1 for h in hs if h['severity'] == 'medium')
                   - 5 * sum(1 for h in hs if h['severity'] == 'low'))

    return {
        'mode': 'docx', 'file': str(path).rsplit('/', 1)[-1],
        'idioma': idioma, 'images': len(docprs),
        'tables': n_tablas, 'tables_with_header': n_tblheader,
        'score': score(hallazgos),
        'findings': hallazgos,
        'summary': {s2: sum(1 for h in hallazgos if h['severity'] == s2)
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
