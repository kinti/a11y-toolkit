#!/usr/bin/env python3
"""PDF accessibility screening — the space nobody automated.

axe-core, pa11y, Lighthouse: HTML only. PDFs carry half the enterprise
documents and nobody screens them in CI. This module does the zero-dep
first pass: the structural facts that decide whether a PDF is even
*addressable* by assistive technology (tagged tree, title, language,
outline), plus markers of remediation (Alt entries, ActualText).

Honest limits, stated in every report: full PDF/UA-1 and PDF/UA-2
conformance needs a spec validator (veraPDF is the open-source one);
this screening finds the failures that make full validation pointless.

CLI:
  a11ypdf.py documento.pdf [--lang en]
"""

import argparse
import json
import os
import re
import sys
import zlib

T = {
    'es': {
        'pdf_untagged': 'sin árbol de estructura (/StructTreeRoot): el orden de lectura y los roles semánticos no existen para el lector. Es EL fallo raíz de los PDF inaccesibles (1.3.1).',
        'pdf_untagged_rem': 'Etiqueta el documento (exporta con «PDF etiquetado» desde authoring, o remedia con Acrobat): sin árbol, todo lo demás es cosmético.',
        'pdf_no_title': 'sin /Title en metadatos: el lector anuncia el nombre del fichero (2.4.2 en documentos).',
        'pdf_no_title_rem': 'Exporta con título de documento (propiedades del fichero), no con el nombre del archivo.',
        'pdf_no_lang': 'sin /Lang: los lectores no saben en qué idioma pronunciar (3.1.1 en documentos).',
        'pdf_no_lang_rem': 'Fija /Lang (p. ej. «es-ES») en las propiedades del documento.',
        'pdf_no_outline': 'sin marcadores/outline: un PDF largo sin navegación por encabezados (1.3.1).',
        'pdf_no_outline_rem': 'Genera marcadores desde los encabezados al exportar.',
        'pdf_no_alt': 'árbol etiquetado con imágenes pero 0 entradas /Alt: los gráficos son opacos (1.1.1).',
        'pdf_no_alt_rem': 'Añade texto alternativo a las figuras al exportar/remediar.',
        'pdf_encrypted': 'PDF cifrado: los lectores pueden no extraer nada.',
        'pdf_encrypted_rem': 'Publica sin cifrado (o con permisos de extracción completos).',
        'pdf_scanned': 'sin capa de texto (0 caracteres en el contenido): parece un escaneo — invisible por completo (1.1.1).',
        'pdf_scanned_rem': 'Aplica OCR con texto real y etiqueta el resultado.',
        'limits': ('Cribado estructural zero-dep: la conformidad PDF/UA completa '
                   'exige un validador de especificación (veraPDF). Este cribado '
                   'encuentra lo que hace inútil la validación completa.'),
    },
    'en': {
        'pdf_untagged': 'no structure tree (/StructTreeRoot): reading order and semantic roles do not exist for the reader. THE root failure of inaccessible PDFs (1.3.1).',
        'pdf_untagged_rem': 'Tag the document (export as tagged PDF from authoring, or remediate in Acrobat): without a tree, everything else is cosmetic.',
        'pdf_no_title': 'no /Title in metadata: readers announce the filename (2.4.2 for documents).',
        'pdf_no_title_rem': 'Export with a document title (file properties), not the filename.',
        'pdf_no_lang': 'no /Lang: readers do not know what language to pronounce (3.1.1 for documents).',
        'pdf_no_lang_rem': 'Set /Lang (e.g. "en" or "es-ES") in document properties.',
        'pdf_no_outline': 'no bookmarks/outline: a long PDF with no heading navigation (1.3.1).',
        'pdf_no_outline_rem': 'Generate bookmarks from headings on export.',
        'pdf_no_alt': 'tagged tree with images but 0 /Alt entries: figures are opaque (1.1.1).',
        'pdf_no_alt_rem': 'Add alternative text to figures on export/remediation.',
        'pdf_encrypted': 'encrypted PDF: readers may extract nothing.',
        'pdf_encrypted_rem': 'Publish unencrypted (or with full extraction permissions).',
        'pdf_scanned': 'no text layer (0 characters in content): looks like a scan — fully invisible (1.1.1).',
        'pdf_scanned_rem': 'Apply OCR with real text and tag the result.',
        'limits': ('Zero-dep structural screening: full PDF/UA conformance needs '
                   'a spec validator (veraPDF). This screening finds what makes '
                   'full validation pointless.'),
    },
}

_CRIT = {
    'pdf_untagged': ('1.3.1', 'high'), 'pdf_no_title': ('2.4.2', 'low'),
    'pdf_no_lang': ('3.1.1', 'medium'), 'pdf_no_outline': ('1.3.1', 'low'),
    'pdf_no_alt': ('1.1.1', 'high'), 'pdf_encrypted': ('1.1.1', 'medium'),
    'pdf_scanned': ('1.1.1', 'high'),
}


def _t(lang, key):
    return T.get(lang, T['en'])[key]


def _flujos_descomprimidos(datos, limite=60):
    """Los streams FlateDecode, descomprimidos (zlib es stdlib) — ahí viven
    el XMP, el contenido y buena parte de la estructura."""
    out = []
    for m in re.finditer(rb'stream\r?\n', datos):
        ini = m.end()
        fin = datos.find(b'endstream', ini)
        if fin == -1:
            continue
        trozo = datos[ini:fin].rstrip(b'\r\n')
        try:
            d = zlib.decompressobj()
            out.append(d.decompress(trozo, 20_000_000))  # bomba: techo por stream
        except Exception:  # noqa: BLE001
            continue
        if len(out) >= limite:
            break
    return out


def pdf_screen(path_or_bytes, lang='en'):
    """Cribado estructural de accesibilidad de un PDF (fichero local)."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        datos = bytes(path_or_bytes)
        nombre = '(bytes)'
        truncado = False
    else:
        tam = os.path.getsize(path_or_bytes)
        with open(path_or_bytes, 'rb') as f:
            datos = f.read(30_000_000)  # techo duro: 30 MB
        truncado = tam > len(datos)
        nombre = str(path_or_bytes).rsplit('/', 1)[-1]

    if not datos.startswith(b'%PDF-'):
        return {'error': 'no es un PDF (sin marca %PDF-)'}

    flujos = _flujos_descomprimidos(datos)
    todo = datos + b'\n'.join(flujos[:40])

    def tiene(pat):
        return re.search(pat, todo) is not None

    cifrado = b'/Encrypt' in datos  # el trailer vive al FINAL del fichero
    tagged = tiene(rb'/StructTreeRoot\s+\d+\s+0\s+R') or tiene(rb'/StructTreeRoot')
    marked = tiene(rb'/Marked\s+true')
    lang_doc = re.search(rb'/Lang\s*\(([^)]{2,20})\)', todo)
    title_meta = re.search(rb'/Title\s*\(([^)]{1,300})\)', todo) or \
        re.search(rb'<dc:title>.{0,200}?<rdf:li[^>]*>([^<]{1,300})</rdf:li>', todo, re.S)
    n_pages = len(re.findall(rb'/Type\s*/Page[^s]', todo))
    n_alt = len(re.findall(rb'/Alt\s*\(', todo))
    n_actual = len(re.findall(rb'/ActualText', todo))
    n_imgs = len(re.findall(rb'/Subtype\s*/Image', todo))
    n_outline = len(re.findall(rb'/Outlines\s+\d+\s+0\s+R', todo))
    # capa de texto: operadores Tj/TJ en TODA la muestra — streams Flate
    # descomprimidos Y bytes crudos (contenido sin comprimir es legítimo;
    # contar solo Flate acusaba en falso de 'escaneo' a PDFs reales)
    n_texto = sum(len(re.findall(rb'\)\s*Tj|\]\s*TJ|\(\s*[A-Za-z0-9]', f)) for f in flujos)
    n_texto += len(re.findall(rb'\)\s*Tj|\]\s*TJ', datos))

    hallazgos = []

    def add(key):
        crit, sev = _CRIT[key]
        hallazgos.append({'severity': sev, 'criterion': f'{crit} (PDF)',
                          'signal': key, 'issue': _t(lang, key),
                          'remediation': _t(lang, key + '_rem')})

    if cifrado:
        add('pdf_encrypted')
    if not (tagged and marked):
        add('pdf_untagged')
    if not title_meta:
        add('pdf_no_title')
    if not lang_doc:
        add('pdf_no_lang')
    if n_pages > 8 and not n_outline:
        add('pdf_no_outline')
    if n_texto == 0 and n_imgs > 0 and n_pages > 0:
        # sin texto Y con imágenes: patrón de escaneo. Sin imágenes no hay
        # base para acusar (vector puro, formularios vacíos…)
        add('pdf_scanned')
    elif tagged and n_imgs > 0 and n_alt == 0 and n_actual == 0:
        add('pdf_no_alt')

    from .a11yaudit import calcular_score
    orden = {'high': 0, 'medium': 1, 'low': 2}
    hallazgos.sort(key=lambda h: orden[h['severity']])
    return {
        'mode': 'pdf', 'file': nombre,
        'pages': n_pages or None,
        'tagged': bool(tagged and marked),
        'encrypted': cifrado,
        'lang': lang_doc.group(1).decode('latin-1', 'replace') if lang_doc else None,
        'title': (title_meta.group(1).decode('utf-8', 'replace').strip()[:200]
                  if title_meta else None),
        'images': n_imgs, 'alt_entries': n_alt, 'actual_text': n_actual,
        'text_operators': n_texto,
        'truncated': truncado,
        'score': calcular_score(hallazgos),
        'findings': hallazgos,
        'summary': {s: sum(1 for h in hallazgos if h['severity'] == s)
                    for s in ('high', 'medium', 'low')},
        'limits': _t(lang, 'limits'),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pdf', help='local PDF file')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    a = ap.parse_args(argv)
    print(json.dumps(pdf_screen(a.pdf, lang=a.lang), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
