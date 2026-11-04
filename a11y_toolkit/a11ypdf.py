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


# Techos anti-bomba de descompresión: por stream y ACUMULADO entre streams
# (una bomba repartida en 100 streams de 20MB no descomprime 2GB; lo que
# llegó hasta el techo basta para auditar — doctrina de lectura parcial).
_STREAM_CAP = 20_000_000      # 20 MB por stream descomprimido
_STREAM_BUDGET = 120_000_000  # 120 MB en total entre todos los streams


def _uncompressed_streams(data, limit=60):
    """Los streams FlateDecode, descomprimidos (zlib es stdlib) — ahí viven
    el XMP, el contenido y buena parte de la estructura."""
    out, total = [], 0
    for m in re.finditer(rb'stream\r?\n', data):
        if total >= _STREAM_BUDGET:
            break  # techo acumulado: dejar de inflar, auditar lo que llegó
        start = m.end()
        end = data.find(b'endstream', start)
        if end == -1:
            continue
        chunk = data[start:end].rstrip(b'\r\n')
        try:
            d = zlib.decompressobj()
            dec = d.decompress(chunk, _STREAM_CAP)  # bomba: techo por stream
        except Exception:  # noqa: BLE001
            continue
        out.append(dec)
        total += len(dec)
        if len(out) >= limit:
            break
    return out


# ── 1.4.3 en PDF: contraste del texto contra el fondo efectivo ──
# Parseo de la secuencia de operadores: `rg`/`g`/`k` cambian el color de
# relleno (con el que se escribe texto), `re` declara un rectángulo —
# candidato a FONDO solo si un operador de pintado (f/F/B/B*/b) lo pinta
# después, con el relleno VIGENTE —, y `Tj`/`TJ` escriben texto (TJ también
# en forma de array: `[(H) -3 (ola)] TJ`). El fondo por defecto del PDF es
# blanco si nadie lo pinta: un rect oscuro pintado antes del texto cambia
# el fondo efectivo — no acusar blanco-sobre-oscuro como bajo (el mismo bug
# que CSS var() en HTML). Los operandos de `re` NUNCA se interpretan como
# color (bug histórico: `0 0 612 792 re` se leía como triple RGB).
_RE_STREAM_OPS = re.compile(
    r'(?P<r>[\d.]+)\s+(?P<g>[\d.]+)\s+(?P<b>[\d.]+)\s+rg\b'                     # relleno RGB
    r'|(?P<gray>[\d.]+)\s+g\b'                                                   # relleno gris
    r'|(?P<k1>[\d.]+)\s+(?P<k2>[\d.]+)\s+(?P<k3>[\d.]+)\s+(?P<k4>[\d.]+)\s+k\b'  # relleno CMYK
    r'|(?P<x1>[\d.]+)\s+(?P<y1>[\d.]+)\s+(?P<w1>[\d.]+)\s+(?P<h1>[\d.]+)\s+re\b'  # rectángulo
    r'|(?P<paint>\b[fFBb]\*?(?![\w*]))'                                          # pintado del path
    r'|(?P<text>\((?:[^()\\]|\\.)*\)\s*(?:Tj|TJ)|\]\s*TJ)')                      # texto (cadena o array)


def _l(r, g, b):
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _ratio(f, b):
    l1, l2 = max(f, b), min(f, b)
    return (l1 + 0.05) / (l2 + 0.05)


def _stream_low_contrast(text):
    """Un content stream (ya decodificado latin-1) → lista de ejemplos
    'color sobre fondo' por debajo de 4.5:1. Escaneo secuencial
    determinista de los operadores de color/pintado/texto."""
    hits = []
    fill = (0, 0, 0)         # relleno vigente: el color con el que se escribe
    bg = (255, 255, 255)     # fondo efectivo: blanco salvo rect pintado
    rect_pending = False     # un `re` declarado, esperando su operador de pintado
    for m in _RE_STREAM_OPS.finditer(text):
        if m.group('r') is not None:            # rg — relleno RGB
            try:
                fill = tuple(max(0, min(255, round(float(x) * 255)))
                             for x in (m.group('r'), m.group('g'), m.group('b')))
            except ValueError:
                pass
        elif m.group('gray') is not None:       # g — relleno en escala de grises
            try:
                v = max(0, min(255, round(float(m.group('gray')) * 255)))
                fill = (v, v, v)
            except ValueError:
                pass
        elif m.group('k1') is not None:         # k — relleno CMYK (aprox. naive)
            try:
                c_, mm_, y_, black = (max(0.0, min(1.0, float(x))) for x in
                                      (m.group('k1'), m.group('k2'),
                                       m.group('k3'), m.group('k4')))
                fill = tuple(max(0, min(255, round(255 * (1 - x) * (1 - black))))
                             for x in (c_, mm_, y_))
            except ValueError:
                pass
        elif m.group('x1') is not None:         # re — rectángulo: solo candidato a fondo
            rect_pending = True                 # sin pintado posterior no cambia nada
        elif m.group('paint') is not None:      # f/F/B/B*/b — pinta el path pendiente
            if rect_pending:
                bg = fill   # pintado con el relleno VIGENTE: ese rect es el fondo
                rect_pending = False
        else:                                   # Tj / TJ — texto con el relleno vigente
            ratio_ = _ratio(_l(*fill), _l(*bg))
            if ratio_ < 4.5:
                hits.append(f'rgb({fill[0]},{fill[1]},{fill[2]})'
                            f' sobre rgb({bg[0]},{bg[1]},{bg[2]})'
                            f' \u2192 {ratio_:.2f}:1')
    return hits


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
    # `todo` respeta el MISMO presupuesto acumulado: ensamblar 40 streams de
    # 20MB sería una segunda bomba
    parts, total_todo = [data], len(data)
    for s in streams[:40]:
        if total_todo + len(s) > _STREAM_BUDGET:
            break
        parts += [b'\n', s]
        total_todo += len(s) + 1
    todo = b''.join(parts)

    def present(pat):
        return re.search(pat, todo) is not None

    encrypted = b'/Encrypt' in data  # el trailer vive al FINAL del fichero
    # tagged: la forma canónica es la referencia del catálogo (/StructTreeRoot
    # N 0 R). Una mención suelta (p. ej. dentro de un content stream) solo
    # cuenta como estructura cuando el documento además declara /Marked true.
    marked = present(rb'/Marked\s+true')
    tagged = present(rb'/StructTreeRoot\s+\d+\s+0\s+R') or \
        (marked and present(rb'/StructTreeRoot'))
    lang_doc = re.search(rb'/Lang\s*\(([^)]{2,20})\)', todo)
    title_meta = re.search(rb'/Title\s*\(([^)]{1,300})\)', todo) or \
        re.search(rb'<dc:title>.{0,200}?<rdf:li[^>]*>([^<]{1,300})</rdf:li>', todo, re.S)
    n_pages = len(re.findall(rb'/Type\s*/Page[^s]', todo))
    # /Alt acepta literal (/Alt (…)) y hex (/Alt <FEFF…>, la forma natural
    # UTF-16BE para alt no latino) — misma paridad que /TU
    n_alt = len(re.findall(rb'/Alt\s*[<(]', todo))
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
    low_hits = []
    for stream in streams:
        for ej in _stream_low_contrast(stream.decode('latin-1', 'replace')):
            if ej not in low_hits:
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
