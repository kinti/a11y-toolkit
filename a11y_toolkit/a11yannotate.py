#!/usr/bin/env python3
"""Per-element annotation — the kernel that turns findings into marks.

A finding says "2 <img> without alt"; the kernel says WHICH imgs exactly:
the auditor now stamps every finding it can with `paths` (deterministic CSS
routes computed during the parse: tag:nth-of-type(n) from the root — ids are
ignored on purpose, duplicate ids cannot break identity), and
`annotate(html, report)` re-parses the SAME html with the SAME route
algorithm (shared: VOID_TAGS / path_segment from a11yaudit) to inject
`data-a11y-id="mN"` attributes at byte-exact positions — offset surgery,
the rest of the document is preserved byte for byte.

The honesty rule, same as everywhere: what cannot be located is returned in
`unplaced` — a finding without a mark, never a wrong mark. That includes the
whole-report case: if the report's `source_sha256` does not match this html,
NOTHING is injected (paths can collide by accident on a different document and
a mark would land on the wrong element) — every finding falls to `unplaced`
and the result carries `source_mismatch: True` plus a `note`.

Output:
  {'annotated_html': str,          # the COPY with data-a11y-id attrs
   'marks': [{id, path, criterion, severity, signal}, …],
   'unplaced': [{criterion, signal}, …],   # findings without paths
   'source_mismatch': bool, 'note': str}   # note only on mismatch

CLI:
  a11yannotate.py page.html --report audit.json -o copy.html [--marks m.json]
"""

import argparse
import json
import sys
from html.parser import HTMLParser

from .a11yaudit import VOID_TAGS, path_segment

# nota de mismatch, bilingüe (mismo patrón que _labels en a11yaudit):
# annotate no tiene idioma propio — 'en' por defecto, idioma explícito opcional
_NOTES = {
    'es': 'el informe no proviene de este html (source_sha256 distinto): '
          'sin marcas, todo el informe cae a unplaced — nunca una marca en el '
          'elemento equivocado',
    'en': 'the report did not come from this html (source_sha256 differs): '
          'no marks, the whole report falls to unplaced — never a '
          'wrong-element mark',
}


class _Locator(HTMLParser):
    """Re-parses the original html and records, for every element route, the
    byte offset where an attribute could be injected (right after the tag
    name). Same route algorithm as the auditor → same routes → exact match."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.route_offset = {}      # path → insertion offset
        self._line_starts = None    # built lazily at feed()
        self._stack = []            # mirrors the auditor's path stack

    def feed(self, data):
        lines = data.split('\n')
        starts, off = [], 0
        for _ln in lines:
            starts.append(off)
            off += len(_ln) + 1
        self._line_starts = starts
        super().feed(data)

    def handle_starttag(self, tag, attrs):
        pos = self.getpos()                 # (line, col) — 1-based line
        if self._stack:
            parent = self._stack[-1]
            parent[2][tag] = parent[2].get(tag, 0) + 1
            path = parent[1] + '>' + path_segment(tag, parent[2][tag])
        else:
            path = path_segment(tag, 1)
        # offset absoluto del '<' + largo de "<tag" → punto de inyección
        try:
            abs_off = self._line_starts[pos[0] - 1] + pos[1]
        except IndexError:
            return
        self.route_offset[path] = abs_off + 1 + len(tag)
        if tag not in VOID_TAGS:
            self._stack.append((tag, path, {}))

    def handle_endtag(self, tag):
        if self._stack:
            if self._stack[-1][0] == tag:
                self._stack.pop()
            else:
                for i in range(len(self._stack) - 1, -1, -1):
                    if self._stack[i][0] == tag:
                        del self._stack[i:]
                        break


def annotate(html_text, report, lang='en'):
    """Informe (dict de audit_html/audit_url) + html ORIGINAL → copia marcada.

    El html debe ser el mismo que produjo el informe (mismo parseo, mismas
    rutas). Si el informe sella un source_sha256 y no casa con este html, NO
    se inyecta nada — todo el informe cae a unplaced con source_mismatch True
    (los paths pueden colisionar por accidente en otro documento y la marca
    caería en el elemento equivocado).
    """
    import hashlib
    src_hash = report.get('source_sha256')
    mismatch = bool(src_hash) and src_hash != hashlib.sha256(
        html_text.encode('utf-8', 'replace')).hexdigest()

    loc = _Locator()
    try:
        loc.feed(html_text)
        loc.close()
    except Exception:   # noqa: BLE001  — html hostil: sin marcas, sin caída
        return {'annotated_html': html_text, 'marks': [],
                'unplaced': [{'criterion': h.get('criterion'), 'signal': h.get('signal')}
                             for h in report.get('findings', []) if isinstance(h, dict)]}

    findings = [h for h in report.get('findings', []) if isinstance(h, dict)]
    if mismatch:
        # la puerta del docstring: un informe de OTRO html jamás se inyecta
        return {'annotated_html': html_text, 'marks': [],
                'unplaced': [{'criterion': h.get('criterion'), 'signal': h.get('signal')}
                             for h in findings],
                'source_mismatch': True,
                'note': _NOTES.get(lang, _NOTES['en'])}

    marks, unplaced, injections = [], [], []      # injections: (offset, id)
    by_off = {}    # offset → id ya asignado: dos findings sobre el MISMO
                   # elemento comparten marca (dos data-a11y-id en el mismo
                   # offset serían HTML inválido — el DOM descarta el segundo)
    n = 0
    for h in findings:
        did_place = False
        for path in (h.get('paths') or []):
            off = loc.route_offset.get(path)
            if off is None:
                continue
            if off not in by_off:
                n += 1
                by_off[off] = f'm{n}'
                injections.append((off, by_off[off]))
            marks.append({'id': by_off[off], 'path': path,
                          'criterion': h.get('criterion'), 'severity': h.get('severity'),
                          'signal': h.get('signal')})
            did_place = True
        if not did_place:
            unplaced.append({'criterion': h.get('criterion'), 'signal': h.get('signal')})

    # cirugía por offsets, en orden DESCENDENTE para no invalidar posiciones
    out = html_text
    for off, mid in sorted(injections, key=lambda x: -x[0]):
        out = out[:off] + f' data-a11y-id="{mid}"' + out[off:]
    return {'annotated_html': out, 'marks': marks,
               'unplaced': unplaced, 'source_mismatch': mismatch}


def main(argv):
    ap = argparse.ArgumentParser(description='Annotate a copy of the HTML with '
                                             'per-element marks from an audit report')
    ap.add_argument('html_file', help='the ORIGINAL html the report audited')
    ap.add_argument('--report', required=True, help='audit report JSON (must carry paths)')
    ap.add_argument('-o', '--out', default='annotated.html')
    ap.add_argument('--marks', help='write the marks list here (JSON)')
    ap.add_argument('--lang', default='en', choices=['es', 'en'],
                    help='language of the mismatch note')
    a = ap.parse_args(argv)
    html_text = open(a.html_file, encoding='utf-8', errors='replace').read()
    report = json.load(open(a.report, encoding='utf-8'))
    res = annotate(html_text, report, lang=a.lang)
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(res['annotated_html'])
    if a.marks:
        with open(a.marks, 'w', encoding='utf-8') as f:
            json.dump(res['marks'], f, ensure_ascii=False, indent=1)
    print(json.dumps({'out': a.out, 'marks': len(res['marks']),
                      'unplaced': len(res['unplaced']),
                      'source_mismatch': res['source_mismatch']},
                     ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
