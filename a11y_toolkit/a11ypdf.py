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
        'pdf_low_contrast': '{n} fragmentos de texto con color de relleno cercano al fondo (ratio < 4.5): el PDF no tiene cascada — el color actual lo fija el operador `rg` antes del Tj, y es medible. Ejemplos: {ej}.',
        'pdf_low_contrast_rem': 'Sube el contraste del texto: en PDF el fondo por defecto es blanco si nadie lo pinta. m viewed con veraPDF/acrobat para confirmar el fondo real.',
        'pdf_fake_link': '{n} textos con apariencia de enlace (color azulado / subrayado con rectángulo) sin anotación /A << /S /URI >> en la página: el lector de pantalla NO los anuncia como enlace (2.4.4).',
        'pdf_fake_link_rem': 'Usa anotaciones de enlace reales (/Subtype /Link /A << /S /URI /URI (…) >>) sobre el texto del enlace.',
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
        'pdf_low_contrast': '{n} text fragments with fill color near the background (ratio < 4.5): a PDF has no cascade — the current color is set by the `rg` operator before each Tj, and it is measurable. Examples: {ej}.',
        'pdf_low_contrast_rem': 'Raise the text contrast: a PDF\'s default background is white if nothing is painted. Confirm the real background with veraPDF/acrobat.',
        'pdf_fake_link': '{n} text fragments styled like links (bluish fill / underlined with a rectangle) with no /A << /S /URI >> annotation on the page: screen readers do NOT announce them as links (2.4.4).',
        'pdf_fake_link_rem': 'Use real link annotations (/Subtype /Link /A << /S /URI /URI (…) >>) over the link text.',
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

    # ── 1.4.3 en PDF: contraste del texto contra el fondo efectivo ──
    # Parseo de la secuencia: `rg` cambia el color de relleno de texto,
    # `re` + `f` pinta un rectángulo (fondo), `Tj`/`TJ` escriben texto.
    # El fondo por defecto del PDF es blanco si nadie lo pinta. Si un rect
    # oscuro precede al texto, el fondo efectivo es ese fill — no acusar
    # blanco-sobre-oscuro como bajo (el mismo bug que CSS var() en HTML).
    def _l(r, g, b):
        def lin(v):
            v /= 255.0
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    def _ratio(f, b):
        l1, l2 = max(f, b), min(f, b)
        return (l1 + 0.05) / (l2 + 0.05)

    blanc = _l(255, 255, 255)
    bajos = []
    for flujo in flujos:
        texto = flujo.decode('latin-1', 'replace')
        texto_color = (0, 0, 0)
        fondo_color = (255, 255, 255)   # el PDF no pinta fondo por defecto
        fondo_pintado = False
        for m in re.finditer(
                r'([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(rg|re)\b'
                r'|\b(f)\b'
                r'|\((?:[^()\\]|\\.)*\)\s*(Tj|TJ)'
                , texto):
            op = m.group(4) or m.group(5) or m.group(6)
            if op in ('rg', 're'):
                try:
                    texto_color = tuple(
                        max(0, min(255, round(float(x) * 255)))
                        for x in m.groups()[:3])
                except ValueError:
                    pass
                if op == 're':
                    # el rect se pinta con el fill actual: es el FONDO
                    fondo_color = texto_color
            elif op == 'f':
                pass  # el f pinta con el fill ya establecido (fondo ya guardado)
            else:  # Tj / TJ
                lt = _l(*texto_color)
                lb = _l(*fondo_color)
                ratio = _ratio(lt, lb)
                if ratio < 4.5:
                    ej = (f'rgb({texto_color[0]},{texto_color[1]},{texto_color[2]})'
                          f' sobre rgb({fondo_color[0]},{fondo_color[1]},{fondo_color[2]})'
                          f' \u2192 {ratio:.2f}:1')
                    if ej not in [x.split(' \u2014 ')[0] for x in bajos]:
                        bajos.append(ej)
        if len(bajos) >= 4:
            break
    if bajos:
        hallazgos.append({
            'severity': 'medium', 'criterion': '1.4.3 (PDF)',
            'signal': 'pdf_low_contrast',
            'issue': _t(lang, 'pdf_low_contrast').format(n=len(bajos), ej='; '.join(bajos[:3])),
            'remediation': _t(lang, 'pdf_low_contrast_rem')})

    # ── 2.4.4 en PDF: falso affordance de enlace ──
    # texto azulado sin /Annot URI en la misma página
    azules, n_uri = [], len(re.findall(rb'/S\s*/URI', datos))
    for flujo in flujos:
        texto = flujo.decode('latin-1', 'replace')
        for m in re.finditer(
                r'0\s+0\s+1\s+rg\s*(?:\n|.)*?\(([^)]{4,80})\)\s*Tj', texto):
            azules.append(m.group(1)[:40])
            if len(azules) >= 3:
                break
        if len(azules) >= 3:
            break
    if azules and n_uri == 0:
        hallazgos.append({
            'severity': 'medium', 'criterion': '2.4.4 (PDF)',
            'signal': 'pdf_fake_link',
            'issue': _t(lang, 'pdf_fake_link').format(n=len(azules)),
            'remediation': _t(lang, 'pdf_fake_link_rem'),
            'examples': azules})

    def add(key):
        crit, sev = _CRIT[key]
        hallazgos.append({'severity': sev, 'criterion': f'{crit} (PDF)',
                          'signal': key, 'issue': _t(lang, key),
                          'remediation': _t(lang, key + '_rem')})

    # detecciones de contenido: contraste y falso enlace (necesitan hallazgos)


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
