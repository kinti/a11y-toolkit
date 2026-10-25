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
from . import a11yi18n

T = a11yi18n.pair('pdf')  # locales/<lang>.json — community-editable

_CRIT = {
    'pdf_untagged': ('1.3.1', 'high'), 'pdf_no_title': ('2.4.2', 'low'),
    'pdf_no_lang': ('3.1.1', 'medium'), 'pdf_no_outline': ('1.3.1', 'low'),
    'pdf_no_alt': ('1.1.1', 'high'), 'pdf_encrypted': ('1.1.1', 'medium'),
    'pdf_scanned': ('1.1.1', 'high'),
    'pdf_form_no_label': ('3.3.2', 'medium'), 'pdf_button_no_name': ('4.1.2', 'high'),
}


def _t(lang, key):
    return T.get(lang, T['en'])[key]


def _uncompressed_streams(data, limit=60):
    """Los streams FlateDecode, descomprimidos (zlib es stdlib) — ahí viven
    el XMP, el contenido y buena parte de la estructura."""
    out = []
    for m in re.finditer(rb'stream\r?\n', data):
        start = m.end()
        end = data.find(b'endstream', start)
        if end == -1:
            continue
        chunk = data[start:end].rstrip(b'\r\n')
        try:
            d = zlib.decompressobj()
            out.append(d.decompress(chunk, 20_000_000))  # bomba: techo por stream
        except Exception:  # noqa: BLE001
            continue
        if len(out) >= limit:
            break
    return out


def pdf_screen(path_or_bytes, lang='en'):
    """Cribado estructural de accesibilidad de un PDF (fichero local)."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        data = bytes(path_or_bytes)
        name = '(bytes)'
        truncated = False
    else:
        tam = os.path.getsize(path_or_bytes)
        with open(path_or_bytes, 'rb') as f:
            data = f.read(30_000_000)  # techo duro: 30 MB
        truncated = tam > len(data)
        name = str(path_or_bytes).rsplit('/', 1)[-1]

    if not data.startswith(b'%PDF-'):
        return {'error': 'not a PDF (no %PDF- marker)'}

    streams = _uncompressed_streams(data)
    todo = data + b'\n'.join(streams[:40])

    def present(pat):
        return re.search(pat, todo) is not None

    encrypted = b'/Encrypt' in data  # el trailer vive al FINAL del fichero
    tagged = present(rb'/StructTreeRoot\s+\d+\s+0\s+R') or present(rb'/StructTreeRoot')
    marked = present(rb'/Marked\s+true')
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
    n_text = sum(len(re.findall(rb'\)\s*Tj|\]\s*TJ|\(\s*[A-Za-z0-9]', f)) for f in streams)
    n_text += len(re.findall(rb'\)\s*Tj|\]\s*TJ', data))

    findings = []

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
    low_hits = []
    for stream in streams:
        text = stream.decode('latin-1', 'replace')
        text_color = (0, 0, 0)
        bg_color = (255, 255, 255)   # el PDF no pinta fondo por defecto
        painted_bg = False
        for m in re.finditer(
                r'([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(rg|re)\b'
                r'|\b(f)\b'
                r'|\((?:[^()\\]|\\.)*\)\s*(Tj|TJ)'
                , text):
            op = m.group(4) or m.group(5) or m.group(6)
            if op in ('rg', 're'):
                try:
                    text_color = tuple(
                        max(0, min(255, round(float(x) * 255)))
                        for x in m.groups()[:3])
                except ValueError:
                    pass
                if op == 're':
                    # el rect se pinta con el fill actual: es el FONDO
                    bg_color = text_color
            elif op == 'f':
                pass  # el f pinta con el fill ya establecido (fondo ya guardado)
            else:  # Tj / TJ
                lt = _l(*text_color)
                lb = _l(*bg_color)
                ratio = _ratio(lt, lb)
                if ratio < 4.5:
                    ej = (f'rgb({text_color[0]},{text_color[1]},{text_color[2]})'
                          f' sobre rgb({bg_color[0]},{bg_color[1]},{bg_color[2]})'
                          f' \u2192 {ratio:.2f}:1')
                    if ej not in [x.split(' \u2014 ')[0] for x in low_hits]:
                        low_hits.append(ej)
        if len(low_hits) >= 4:
            break
    if low_hits:
        findings.append({
            'severity': 'medium', 'criterion': '1.4.3 (PDF)',
            'signal': 'pdf_low_contrast',
            'issue': _t(lang, 'pdf_low_contrast').format(n=len(low_hits), example='; '.join(low_hits[:3])),
            'remediation': _t(lang, 'pdf_low_contrast_rem')})

    # ── 2.4.4 en PDF: falso affordance de enlace ──
    # texto azulado sin /Annot URI en la misma página
    bluish, n_uri = [], len(re.findall(rb'/S\s*/URI', data))
    for stream in streams:
        text = stream.decode('latin-1', 'replace')
        for m in re.finditer(
                r'0\s+0\s+1\s+rg\s*(?:\n|.)*?\(([^)]{4,80})\)\s*Tj', text):
            bluish.append(m.group(1)[:40])
            if len(bluish) >= 3:
                break
        if len(bluish) >= 3:
            break
    if bluish and n_uri == 0:
        findings.append({
            'severity': 'medium', 'criterion': '2.4.4 (PDF)',
            'signal': 'pdf_fake_link',
            'issue': _t(lang, 'pdf_fake_link').format(n=len(bluish)),
            'remediation': _t(lang, 'pdf_fake_link_rem'),
            'examples': bluish})

    # ── 3.3.2 / 4.1.2 en PDF: campos AcroForm sin etiqueta accesible ──
    # /FT declara el tipo de campo (/Tx texto, /Ch lista, /Sig firma, /Btn
    # botón); /TU es el texto alternativo — LO que anuncia el lector de
    # pantalla. Sin /TU, el campo se oye con su nombre técnico o como
    # "button" a secas. Caso claro (ningún /TU): acusa por tipo. Caso
    # parcial: recuento único sin desglosar botones (la herencia /Parent
    # de los grupos de radio hace impredecible el emparejamiento campo a
    # campo en un cribado sin parser de objetos).
    n_fields_txt = len(re.findall(rb'/FT\s*/(?:Tx|Ch|Sig)\b', todo))
    n_fields_btn = len(re.findall(rb'/FT\s*/Btn\b', todo))
    n_tu = len(re.findall(rb'/TU\s*[<(]', todo))
    n_fields = n_fields_txt + n_fields_btn
    if n_fields and n_tu == 0:
        if n_fields_txt:
            findings.append({
                'severity': 'medium', 'criterion': '3.3.2 (PDF)',
                'signal': 'pdf_form_no_label',
                'issue': _t(lang, 'pdf_form_no_label').format(n=n_fields_txt, m=n_fields_txt),
                'remediation': _t(lang, 'pdf_form_no_label_rem')})
        if n_fields_btn:
            findings.append({
                'severity': 'high', 'criterion': '4.1.2 (PDF)',
                'signal': 'pdf_button_no_name',
                'issue': _t(lang, 'pdf_button_no_name').format(n=n_fields_btn),
                'remediation': _t(lang, 'pdf_button_no_name_rem')})
    elif n_tu < n_fields:
        findings.append({
            'severity': 'medium', 'criterion': '3.3.2 (PDF)',
            'signal': 'pdf_form_no_label',
            'issue': _t(lang, 'pdf_form_no_label').format(n=n_fields - n_tu, m=n_fields),
            'remediation': _t(lang, 'pdf_form_no_label_rem')})

    def add(key):
        crit, sev = _CRIT[key]
        findings.append({'severity': sev, 'criterion': f'{crit} (PDF)',
                          'signal': key, 'issue': _t(lang, key),
                          'remediation': _t(lang, key + '_rem')})

    # detecciones de contenido: contraste y falso enlace (necesitan hallazgos)


    if encrypted:
        add('pdf_encrypted')
    if not (tagged and marked):
        add('pdf_untagged')
    if not title_meta:
        add('pdf_no_title')
    if not lang_doc:
        add('pdf_no_lang')
    if n_pages > 8 and not n_outline:
        add('pdf_no_outline')
    if n_text == 0 and n_imgs > 0 and n_pages > 0:
        # sin texto Y con imágenes: patrón de escaneo. Sin imágenes no hay
        # base para acusar (vector puro, formularios vacíos…)
        add('pdf_scanned')
    elif tagged and n_imgs > 0 and n_alt == 0 and n_actual == 0:
        add('pdf_no_alt')

    from .a11yaudit import compute_score
    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])
    return {
        'mode': 'pdf', 'file': name,
        'pages': n_pages or None,
        'tagged': bool(tagged and marked),
        'encrypted': encrypted,
        'lang': lang_doc.group(1).decode('latin-1', 'replace') if lang_doc else None,
        'title': (title_meta.group(1).decode('utf-8', 'replace').strip()[:200]
                  if title_meta else None),
        'images': n_imgs, 'alt_entries': n_alt, 'actual_text': n_actual,
        'text_operators': n_text,
        'form_fields': n_fields, 'form_labels': n_tu,
        'truncated': truncated,
        'score': compute_score(findings),
        'findings': findings,
        'summary': {s: sum(1 for h in findings if h['severity'] == s)
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
