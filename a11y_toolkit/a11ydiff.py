#!/usr/bin/env python3
"""Accessibility regression diff between builds — catch regressions before production.

Two commands:

  snapshot   Capture a URL: interactive elements (tag, role, accessible name,
             href) in DOM order + the REAL tab order + the computed
             accessibility tree. Requires Playwright.

  diff       Compare two snapshots: added/removed/renamed interactives,
             focus-order and accessibility-tree changes.

Usage:
  a11ydiff.py snapshot https://jquin.net --out before.json
  # …deploy…
  a11ydiff.py snapshot https://jquin.net --out after.json
  a11ydiff.py diff before.json after.json     # exit 0 ok / 2 regressions
"""

import argparse
import json
import sys
from datetime import datetime, timezone

COLECTOR = r'''() => {
  const sel = 'a[href], button, input, select, textarea, summary, [tabindex], ' +
              '[contenteditable], video[controls], audio[controls]';
  const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  return [...document.querySelectorAll(sel)].filter(visible).map((el, i) => {
    let name = el.getAttribute('aria-label') || '';
    if (!name && el.labels && el.labels[0]) name = el.labels[0].innerText;
    if (!name) name = el.getAttribute('title') || '';
    if (!name && el.tagName === 'INPUT' && ['submit', 'button', 'reset'].includes(el.type))
      name = el.value || '';
    if (!name) name = (el.innerText || '').replace(/\s+/g, ' ').trim();
    if (!name) name = el.getAttribute('alt') || '';
    const link = el.closest('a[href]');
    return {
      key: el.id ? '#' + el.id
                 : el.tagName.toLowerCase() + ':' + name.slice(0, 60).toLowerCase() +
                   (link ? ':' + link.getAttribute('href') : ''),
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      role: el.getAttribute('role') || el.tagName.toLowerCase(),
      name: name.trim().slice(0, 90),
      href: link ? link.getAttribute('href') : null,
      dom: i,
    };
  });
}'''


def snapshot(url, output=None, auth_state=None):
    """Captura una URL. Con salida=None devuelve los datos sin escribir fichero."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        page.goto(url, wait_until='networkidle', timeout=45000)
        elements = page.evaluate(COLECTOR)

        # Árbol de accesibilidad REAL (roles/nombres computados, lo que anuncia
        # un lector de pantalla). Playwright ≥1.49; si no está, se omite.
        tree = None
        try:
            tree = page.locator('body').aria_snapshot()
            if len(tree) > 60_000:
                tree = tree[:60_000] + '\n… (truncado)'
        except Exception:  # noqa: BLE001
            tree = None

        order = []
        page.keyboard.press('Tab')
        seen = set()
        for _ in range(len(elements) * 2 + 10):
            info = page.evaluate(r'''() => {
              const el = document.activeElement;
              if (!el || el === document.body) return null;
              const link = el.closest('a[href]');
              let name = el.getAttribute('aria-label') || (el.innerText || '')
                .replace(/\s+/g,' ').trim() || el.getAttribute('title') ||
                (el.tagName==='INPUT' && el.value) || '';
              return el.id ? '#'+el.id : el.tagName.toLowerCase()+':'+name.slice(0,60).toLowerCase()+
                (link ? ':'+link.getAttribute('href') : '');
            }''')
            if info is None:
                break
            entry_key = info + '@' + str(len(seen))
            if info in seen:
                break
            seen.add(info)
            order.append(info)
            page.keyboard.press('Tab')
        nav.close()

    data = {'url': url, 'ts': datetime.now(timezone.utc).isoformat(),
             'elements': elements, 'focus_order': order}
    if tree is not None:
        data['arbol_accesible'] = tree
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    return data


def diff(a, b):
    ea = {x['key']: x for x in a['elements']}
    eb = {x['key']: x for x in b['elements']}
    aniadidos = sorted(set(eb) - set(ea))
    eliminados = sorted(set(ea) - set(eb))
    renombrados = []
    for k in set(ea) & set(eb):
        if ea[k]['name'] != eb[k]['name']:
            renombrados.append({'key': k, 'before': ea[k]['name'], 'after': eb[k]['name']})

    oa, ob = a['focus_order'], b['focus_order']
    common_a = [x for x in oa if x in set(ob)]
    common_b = [x for x in ob if x in set(oa)]
    foco_eliminado = [x for x in oa if x not in set(ob)]   # perdió el Tab: regresión real
    foco_aniadido = [x for x in ob if x not in set(oa)]    # nuevo enfocable: cambio, no pérdida
    foco_cambia = common_a != common_b
    primera_divergencia = next((i for i, (x, y) in enumerate(zip(common_a, common_b)) if x != y), None)

    # Árbol de accesibilidad: si ambos snapshots lo traen, detecta cambios en
    # roles/nombres computados que la lista de interactivos no ve.
    tree_changed = None
    tree_diff = None
    if 'arbol_accesible' in a and 'arbol_accesible' in b:
        la, lb = a['arbol_accesible'].splitlines(), b['arbol_accesible'].splitlines()
        tree_changed = la != lb
        if tree_changed:
            tree_diff = [f'- {la[i]}' for i in range(min(len(la), len(lb)))
                          if la[i] != lb[i]][:5]
            tree_diff += [f'+ {lb[i]}' for i in range(min(len(la), len(lb)))
                           if i < len(lb) and la[i] != lb[i]][:5]

    # perder un elemento del orden de foco ES la regresión que este diff
    # existe para cazar (p. ej. tabindex="-1" añadido al botón de pago):
    # el elemento sigue existiendo, pero ya no es alcanzable por teclado.
    ok = not (aniadidos or eliminados or renombrados or foco_cambia
              or foco_eliminado or tree_changed)
    return {
        'ok': ok,
        'summary': {
            'elements': {'before': len(ea), 'after': len(eb)},
            'added': len(aniadidos), 'removed': len(eliminados),
            'renamed': len(renombrados),
            'focus_order_changed': foco_cambia or bool(foco_eliminado),
        },
        'added': aniadidos, 'removed': eliminados, 'renamed': renombrados,
        'focus': {'before': oa, 'after': ob, 'first_divergence': primera_divergencia,
                  'removed': foco_eliminado, 'added': foco_aniadido,
                  'reordered': bool(foco_cambia and not foco_eliminado and not foco_aniadido)},
        'tree': {'changed': tree_changed, 'first_differences': tree_diff},
        'note': ('Elementos sin id se casan por tag+nombre+href: renombrar produce '
                 'eliminado+añadido, no un diff fino. Usa ids estables para trazabilidad.'),
    }


def main(argv):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s1 = sub.add_parser('snapshot')
    s1.add_argument('url')
    s1.add_argument('--out', default='snapshot.json')
    s2 = sub.add_parser('diff')
    s2.add_argument('a')
    s2.add_argument('b')
    a = p.parse_args(argv)

    if a.cmd == 'snapshot':
        try:
            d = snapshot(a.url, a.out)
        except ImportError:
            print(json.dumps({'error': 'Playwright no instalado: pip install playwright && playwright install chromium'}))
            return 1
        print(json.dumps({'url': d['url'], 'elements': len(d['elements']),
                          'focus_steps': len(d['focus_order']), 'out': a.out},
                         ensure_ascii=False, indent=1))
        return 0
    with open(a.a, encoding='utf-8') as f:
        ja = json.load(f)
    with open(a.b, encoding='utf-8') as f:
        jb = json.load(f)
    print(json.dumps(diff(ja, jb), ensure_ascii=False, indent=1))
    veredicto = diff(ja, jb)
    return 0 if veredicto['ok'] else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
