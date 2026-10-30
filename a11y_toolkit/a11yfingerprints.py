#!/usr/bin/env python3
"""a11y_fingerprints — multi-hash template fingerprints (twin-page detection).

Cross-industry translation: multi-hash identification. One hash of a page
breaks the moment a csrf token or a timestamp changes; several independent
hashes over DIFFERENT normalizations identify by intersection — a template
stays recognizable when its volatile parts change, and the view that
diverges tells what KIND of change it was.

Three views of the document, text always excluded (content varies per page;
that is the point):
  structure   tag + depth            — the skeleton (defines the template)
  classes     + sorted class list    — the skin (design-system change)
  attributes  + stable attributes    — real attribute changes, with the
              id-referencing / volatile attrs excluded by design (id, for,
              name, href, src, …) so per-page ids and csrf tokens can never
              split a template

Regions: the landmark containers (header/nav/main/aside/footer) plus
`document` for everything outside them. Each (view, region) → sha256[:12].

Template = the complete structure view (same skeleton = same template — a
declared rule, not fuzzy similarity). Inside a template every page is
compared view-by-view against the representative (the lexicographically
smallest page id); each mismatch is a localized {page, region, view} entry:
"header diverges in classes, footer identical".

sample_suggestion = one representative per template, the structured-sample
helper for WCAG-EM Step 3. The evaluator still owns the sample; identical
structure does not guarantee identical findings after rendering.

CLI:
  a11yfingerprints.py page1.html page2.html [--dir pages/] [--lang es] [-o out.json]
"""

import argparse
import hashlib
import json
import os
import sys
from html.parser import HTMLParser

VIEWS = ('structure', 'classes', 'attributes')

# landmarks que abren región propia; lo que queda fuera vive en 'document'
_REGIONS = ('header', 'nav', 'main', 'aside', 'footer')

# attrs volátiles por construcción: referencian ids únicos por página o
# cambian con cada petición — si entraran en una vista, partirían plantillas
# falsamente (el csrf/token/per-page-id NO es un rediseño)
_VOLATILE = frozenset((
    'id', 'for', 'name', 'href', 'src', 'srcset', 'action', 'headers',
    'list', 'style', 'value', 'aria-controls', 'aria-describedby',
    'aria-labelledby', 'aria-owns', 'aria-details', 'aria-errormessage',
))

_VOID = frozenset(('area', 'base', 'br', 'col', 'embed', 'hr', 'img',
                   'input', 'link', 'meta', 'param', 'source', 'track',
                   'wbr', 'path', 'circle', 'rect', 'line', 'polyline',
                   'polygon', 'ellipse', 'stop', 'use'))

# vistas que se comparan dentro de una plantilla (structure NO puede divergir
# por definición — es la clave de agrupación)
_DIVERGENCE_VIEWS = ('classes', 'attributes')

_NOTES = {
    'en': ('Suggests a structured sample: one representative per detected '
           'template (WCAG-EM Step 3 helper). The evaluator still owns sample '
           'selection; identical structure does not guarantee identical '
           'findings after rendering. Volatile attributes (per-page ids, '
           'urls, tokens) are excluded by design so they cannot split '
           'templates.'),
    'es': ('Sugiere una muestra estructurada: un representante por plantilla '
           'detectada (ayudante del paso 3 de WCAG-EM). El evaluador sigue '
           'siendo dueño de la selección; estructura idéntica no garantiza '
           'hallazgos idénticos tras el render. Los atributos volátiles '
           '(ids por página, urls, tokens) se excluyen a propósito para que '
           'no puedan partir plantillas.'),
}


def _digest(lines):
    return hashlib.sha256('\n'.join(lines).encode('utf-8')).hexdigest()[:12]


class _Serializer(HTMLParser):
    """Serializa el documento a 3 vistas × regiones. Tolerante al HTML hostil:
    cierres sin apertura, anidación imposible y attrs duplicados no rompen
    nada (el parser de stdlib ya de-duplica attrs; los cierres huérfanos se
    ignoran, los abiertos sin cerrar se limpian al final)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = {v: {} for v in VIEWS}   # view -> region -> [lines]
        self._stack = []                      # [(tag, era_landmark_antes)]
        self._landmarks = []                  # landmarks abiertos (externo→interno)

    # región vigente: el landmark MÁS EXTERNO abierto; si ninguno, 'document'
    def _region(self):
        return self._landmarks[0] if self._landmarks else 'document'

    def _close_landmark(self, tag):
        """Cierra el landmark MÁS RECIENTE de ese tag (LIFO, como el stack).
        remove() a secas borraría el primero y corrompería el orden
        externo→interno con landmarks anidados del mismo tipo."""
        for i in range(len(self._landmarks) - 1, -1, -1):
            if self._landmarks[i] == tag:
                del self._landmarks[i]
                return

    def _emit(self, tag, attrs, depth):
        region = self._region()
        cls = sorted((attrs.get('class') or '').split())
        # sin \n/\r en los valores: un attr hostil no puede falsificar
        # líneas del material que se hashea (dos documentos distintos, un
        # mismo digest sería una divergencia perdida)
        stable = sorted('{}={}'.format(k, v.replace('\n', ' ').replace('\r', ' '))
                        for k, v in attrs.items()
                        if k not in _VOLATILE and k != 'class')
        for view, extra in (('structure', ''),
                            ('classes', ' .' + '.'.join(cls) if cls else ''),
                            ('attributes', ' ' + ' '.join(stable) if stable else '')):
            self.lines[view].setdefault(region, []).append(
                '{} {}{}'.format(depth, tag, extra))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        adict = {}
        for k, v in attrs:                    # parser stdlib ya deduplica,
            adict.setdefault(k, v or '')      # pero no perdemos nada siendo explícitos
        depth = len(self._stack)
        if tag in _REGIONS:
            # el propio landmark pertenece a SU región: abre antes de emitir
            # (append: el PRIMERO de la lista es el más externo → _region())
            self._landmarks.append(tag)
        self._emit(tag, adict, depth)
        if tag not in _VOID:
            self._stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        # <tag/> autocontenido: emite sin apilar (el mismo elemento, una vez)
        self.handle_starttag(tag, attrs)
        if self._stack and self._stack[-1] == tag and tag not in _VOID:
            self._stack.pop()
        if tag in self._landmarks:
            self._close_landmark(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self._stack:
            # pop hasta el cierre correcto; lo que quede abierto fuera se ignora
            while self._stack:
                open_tag = self._stack.pop()
                if open_tag in _REGIONS:
                    self._close_landmark(open_tag)
                if open_tag == tag:
                    break
        elif tag in _REGIONS and tag in self._landmarks:
            self._close_landmark(tag)


def fingerprint_html(html_text):
    """html (str) → {hashes: {view: {region: digest}}, template, regions}.

    Determinista: mismas vistas, mismo sha, sin red ni azar."""
    s = _Serializer()
    try:
        s.feed(html_text or '')
        s.close()
    except Exception:
        pass  # el parser stdlib no lanza con entrada hostil, pero si algo
              # escapa, lo YA serializado sigue siendo un fingerprint válido
    hashes = {v: {r: _digest(ls) for r, ls in s.lines[v].items()}
              for v in VIEWS}
    structure = hashes['structure']
    template = 't-' + hashlib.sha256(
        '|'.join('{}:{}'.format(r, structure[r]) for r in sorted(structure))
        .encode('utf-8')).hexdigest()[:8]
    return {'hashes': hashes, 'template': template,
            'regions': sorted(structure)}


def fingerprint_pages(pages, lang='en'):
    """pages: [{'page': id, 'html': str}] → informe completo.

    Agrupa por plantilla (vista structure), localiza la divergencia vista a
    vista contra el representante (id lexicográfico mínimo — regla
    declarada) y sugiere una muestra de un representante por plantilla
    (ayudante del paso 3 de WCAG-EM; el evaluador decide)."""
    if not isinstance(pages, list) or not all(
            isinstance(p, dict) and 'page' in p and 'html' in p for p in pages):
        raise ValueError('pages must be a list of {page, html} dicts')

    entries = []
    for p in pages:
        fp = fingerprint_html(p['html'])
        entries.append({'page': p['page'], 'hashes': fp['hashes'],
                        'regions': fp['regions'], 'template': fp['template']})

    groups = {}
    for e in entries:
        groups.setdefault(e['template'], []).append(e)

    templates = []
    for tid in sorted(groups):
        members = sorted(groups[tid], key=lambda e: e['page'])
        rep = members[0]
        rep_h = rep['hashes']
        divergence = []
        for m in members[1:]:
            for view in _DIVERGENCE_VIEWS:
                regions = set(rep_h[view]) | set(m['hashes'][view])
                for r in sorted(regions):
                    if rep_h[view].get(r) != m['hashes'][view].get(r):
                        divergence.append({'page': m['page'],
                                           'region': r, 'view': view})
        templates.append({
            'template': tid,
            'pages': [m['page'] for m in members],
            'page_count': len(members),
            'representative': rep['page'],
            'divergence': divergence,
        })

    return {
        'mode': 'template-fingerprints',
        'pages_total': len(entries),
        'templates_total': len(templates),
        'views': list(VIEWS),
        'volatile_attrs_ignored': sorted(_VOLATILE),
        'pages': entries,
        'templates': templates,
        'sample_suggestion': sorted(t['representative'] for t in templates),
        'note': _NOTES['es' if lang == 'es' else 'en'],
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pages', nargs='*', help='HTML pages to fingerprint')
    ap.add_argument('--dir', help='also read every *.html/*.htm in this '
                                  'directory (sorted)')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('-o', '--out', help='also write the report to this file')
    a = ap.parse_args(argv)

    names = list(a.pages)
    if a.dir:
        for f in sorted(os.listdir(a.dir)):
            if f.lower().endswith(('.html', '.htm')):
                names.append(os.path.join(a.dir, f))
    if not names:
        ap.error('no pages: pass pages and/or --dir')

    pages = []
    for name in names:
        with open(name, encoding='utf-8', errors='replace') as f:
            pages.append({'page': name, 'html': f.read()})

    report = fingerprint_pages(pages, lang=a.lang)
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
