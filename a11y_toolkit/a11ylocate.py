#!/usr/bin/env python3
"""a11y_locate — find an element by its accessible name, or refuse honestly.

Given raw HTML and a query, returns the deterministic element route (the same
`tag:nth-of-type(n)` identity the auditor and annotate() share) of the element
whose accessible name matches, with a confidence — and the honesty rule of the
house: when several elements share the name, it refuses to pick one
(`ambiguous: true` + the full candidate list). What has no accessible name is
never indexed, so a match is never invented.

Indexed surfaces (only what the engine computes with full fidelity):
  controls (button, link, area, input:*, role:*) · headings h1-h6 ·
  images with alt · iframes with title · fields with an explicit accessible
  name (aria-label, aria-labelledby, title, name-from-content roles).

Output:
  {'query': str, 'role': str|None, 'found': bool, 'ambiguous': bool,
   'selector': str|None,       # deterministic route — annotate()-compatible
   'confidence': 'high'|'medium'|None,
   'count': int,               # total candidates before the cap
   'matches': [{path, tag, id, role, name, match}],   # capped at 10
   'note': str}                # honest explanation, in the requested language

CLI:
  a11ytoolkit locate --file page.html --query "Submit" [--role button] [-o r.json]
"""

import argparse
import json
import sys

from . import a11yi18n
from .a11yaudit import MAX_HTML, _Auditor

T = a11yi18n.pair('locate')   # locales/<lang>.json — community-editable


def _t(lang, key, n=None):
    value = T.get(lang, T['en']).get(key, key)
    return a11yi18n.plural_entry(value, lang, n) if n is not None else value


# aliases accepted by the `role` filter → the raw kinds the auditor records
_ROLE_ALIASES = {
    'button': {'button', 'input:submit', 'input:button', 'input:reset',
               'input:image', 'role:button'},
    'link': {'a', 'area', 'link', 'role:link'},
    'textbox': {'input:text', 'input:search', 'input:email', 'input:tel',
                'input:url', 'input:number', 'input:password', 'textarea',
                'search', 'role:textbox', 'role:searchbox', 'spinbutton'},
    'checkbox': {'input:checkbox', 'role:checkbox', 'role:menuitemcheckbox',
                 'role:option'},
    'radio': {'input:radio', 'role:radio', 'role:menuitemradio'},
    'combobox': {'select', 'role:combobox', 'role:listbox'},
    'image': {'img', 'role:img', 'input:image'},
    'heading': {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'},
}
# roles whose name may come from content (mirrors the auditor's set)
_NAME_FROM_CONTENT = {'checkbox', 'radio', 'switch', 'option', 'menuitem',
                      'menuitemcheckbox', 'menuitemradio', 'tab', 'treeitem'}
_MATCH_CAP = 10


def _norm(text):
    return ' '.join((text or '').split()).casefold()


def _tag_of(path):
    return (path or '').split('>')[-1].split(':nth')[0]


def _allowed_roles(role):
    """Set of raw kinds the `role` filter admits (None → no filter)."""
    if not role:
        return None
    rl = role.strip().lower()
    if rl in _ROLE_ALIASES:
        return set(_ROLE_ALIASES[rl])
    return {rl, '*' + rl, 'input:' + rl, 'role:' + rl, 'h' + rl if rl.isdigit() else rl}


def _role_allowed(item_role, allowed):
    if allowed is None:
        return True
    if item_role in allowed:
        return True
    # 'button' también admite 'role:button' sin alias explícito, etc.
    tail = item_role.split(':', 1)[-1]
    return tail in allowed


def _index(p):
    """Named elements from the auditor's records, in document order."""
    items, seen = [], set()

    def _name_sources(a):
        lb = ' '.join((p._id_texts.get(i, '') or '').strip()
                      for i in (a.get('aria-labelledby') or '').split()).strip()
        return lb, (a.get('aria-label') or '').strip(), (a.get('title') or '').strip()

    def _add(a, role, name, match_extra=None, route=None):
        if not name or id(a) in seen:
            return
        path = route or p._elem_paths.get(id(a))
        if not path:
            return
        seen.add(id(a))
        it = {'path': path, 'tag': _tag_of(path), 'id': (a.get('id') or '').strip(),
              'role': role, 'name': ' '.join(name.split())[:120]}
        if match_extra:
            it.update(match_extra)
        items.append(it)

    for kind, a, text, img_attrs, hidden in p.controls_raw:
        if hidden or 'disabled' in a:
            continue
        lb, al, ti = _name_sources(a)
        if kind.startswith('input:'):
            # el value de un input NO es su nombre accesible (solo en botones
            # reales lo es el texto): aquí solo nombran aria/title/labelledby
            _add(a, kind, al or lb or ti)
            continue
        img_names = []
        for ia in img_attrs:
            ilb, ial, iti = _name_sources(ia)
            img_names.append((ia.get('alt') or '').strip() or ial or ilb or iti)
        # orden accname de la spec: labelledby → aria-label → contenido
        # (texto, imgs internas, alt) → title
        _add(a, kind, lb or al or text.strip()
             or ' '.join(x for x in img_names if x).strip()
             or (a.get('alt') or '').strip() or ti)

    for level, a, text, hidden, route in p.headings_raw:
        if hidden:
            continue
        lb, al, _ti = _name_sources(a)
        _add(a, f'h{level}', lb or al or text.strip(), route=route)

    for a, hidden in p.imgs_all:
        if hidden:
            continue
        lb, al, ti = _name_sources(a)
        _add(a, 'img', (a.get('alt') or '').strip() or al or lb or ti)

    for a, hidden in p.iframes_all:
        if hidden:
            continue
        lb, al, ti = _name_sources(a)
        _add(a, 'iframe', (a.get('title') or '').strip() or al or lb)

    direct_text = {tid: ' '.join(buf).strip()
                   for tid, buf in getattr(p, '_field_buffers', {}).items()}
    for tag, kind, a, _en_label, hidden in p.fields_raw:
        if hidden:
            continue
        lb, al, ti = _name_sources(a)
        content_name = direct_text.get(a.get('id') or '', '') \
            if kind.split(':', 1)[-1] in _NAME_FROM_CONTENT else ''
        # el kind de un input es su type ('email'): normalizo al formato
        # 'input:email' que usan los aliases de rol
        role_kind = f'input:{kind}' if tag == 'input' else kind
        _add(a, role_kind, lb or al or ti or content_name)

    return items


def locate(html_text, query, role=None, multiple=False, lang='en'):
    """Localiza por nombre accesible; se niega si la elección es ambigua."""
    if not isinstance(query, str) or not query.strip():
        return {'query': query, 'role': role, 'found': False, 'ambiguous': False,
                'selector': None, 'confidence': None, 'count': 0, 'matches': [],
                'note': _t(lang, 'loc_no_query')}
    allowed = _allowed_roles(role)
    p = _Auditor()
    try:
        p.feed((html_text or '')[:MAX_HTML])
        p.close()
    except Exception as e:  # noqa: BLE001 — html hostil: sin índice, sin caída
        return {'query': query, 'role': role, 'found': False, 'ambiguous': False,
                'selector': None, 'confidence': None, 'count': 0, 'matches': [],
                'error': f'unparseable HTML: {e}'}

    for _id, _parts in p._id_text_parts.items():
        p._id_texts[_id] = ' '.join(_parts).strip()

    items = [it for it in _index(p) if _role_allowed(it['role'], allowed)]
    qn = _norm(query)
    exact = [it for it in items if _norm(it['name']) == qn]
    partial = [it for it in items if it not in exact and qn and qn in _norm(it['name'])]

    def _out(found, ambiguous, selector, confidence, matches, total, note):
        return {'query': query, 'role': role, 'found': found, 'ambiguous': ambiguous,
                'selector': selector, 'confidence': confidence, 'count': total,
                'matches': matches[:_MATCH_CAP], 'note': note}

    if exact:
        if len(exact) == 1:
            return _out(True, False, exact[0]['path'], 'high',
                        exact, len(exact), '')
        if multiple:
            return _out(True, False, None, 'high', exact, len(exact),
                        _t(lang, 'loc_multiple'))
        return _out(True, True, None, None, exact, len(exact),
                    _t(lang, 'loc_ambiguous', n=len(exact)).format(n=len(exact), q=query))
    if partial:
        if len(partial) == 1:
            return _out(True, False, partial[0]['path'], 'medium',
                        partial, 1, _t(lang, 'loc_partial').format(q=query))
        return _out(True, True, None, None, partial, len(partial),
                    _t(lang, 'loc_partial_ambiguous', n=len(partial)).format(
                        n=len(partial), q=query))
    return _out(False, False, None, None, [], 0,
                _t(lang, 'loc_no_match').format(q=query.strip()))


def main(argv):
    ap = argparse.ArgumentParser(
        description='Locate an element by its accessible name — honest '
                    'refusal when the match is ambiguous')
    ap.add_argument('html_file', nargs='?', help='the HTML to search')
    ap.add_argument('--file', dest='html_opt', help='the HTML to search (alt form)')
    ap.add_argument('--query', '-q', required=True, help='accessible name to find')
    ap.add_argument('--role', help='filter: button, link, textbox, heading, h1, image…')
    ap.add_argument('--multiple', action='store_true',
                    help='list every exact match instead of refusing')
    ap.add_argument('--lang', default='en', choices=['es', 'en'])
    ap.add_argument('-o', '--out', help='write the result JSON here')
    a = ap.parse_args(argv)
    path = a.html_file or a.html_opt
    if not path:
        ap.error('an HTML file is required (positional or --file)')
    html_text = open(path, encoding='utf-8', errors='replace').read()
    res = locate(html_text, a.query, role=a.role, multiple=a.multiple, lang=a.lang)
    payload = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(payload)
        print(json.dumps({'out': a.out, 'found': res['found'],
                          'selector': res['selector'],
                          'confidence': res['confidence']}, ensure_ascii=False))
    else:
        print(payload)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
