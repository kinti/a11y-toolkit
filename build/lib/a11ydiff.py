#!/usr/bin/env python3
"""Diff de accesibilidad entre builds — detecta regresiones antes de producción.

Dos comandos:

  snapshot   Captura de una URL: elementos interactivos (tag, rol, nombre
             accesible, href) en orden DOM + orden de tabulación real (Tab a
             Tab). Requiere Playwright (pip install playwright && playwright
             install chromium).

  diff       Compara dos snapshots: interactivos añadidos/eliminados/renom-
             brados (mismo id, distinto nombre accesible) y cambios en el
             orden de foco.

Uso:
  a11ydiff.py snapshot https://jquin.net --out antes.json
  # ...deploy...
  a11ydiff.py snapshot https://jquin.net --out despues.json
  a11ydiff.py diff antes.json despues.json
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


def snapshot(url, salida=None):
    """Captura una URL. Con salida=None devuelve los datos sin escribir fichero."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page()
        page.goto(url, wait_until='networkidle', timeout=45000)
        elementos = page.evaluate(COLECTOR)

        orden = []
        page.keyboard.press('Tab')
        vistos = set()
        for _ in range(len(elementos) * 2 + 10):
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
            clave = info + '@' + str(len(vistos))
            if info in vistos:
                break
            vistos.add(info)
            orden.append(info)
            page.keyboard.press('Tab')
        nav.close()

    datos = {'url': url, 'ts': datetime.now(timezone.utc).isoformat(),
             'elementos': elementos, 'orden_foco': orden}
    if salida:
        with open(salida, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
    return datos


def diff(a, b):
    ea = {x['key']: x for x in a['elementos']}
    eb = {x['key']: x for x in b['elementos']}
    aniadidos = sorted(set(eb) - set(ea))
    eliminados = sorted(set(ea) - set(eb))
    renombrados = []
    for k in set(ea) & set(eb):
        if ea[k]['name'] != eb[k]['name']:
            renombrados.append({'key': k, 'antes': ea[k]['name'], 'despues': eb[k]['name']})

    oa, ob = a['orden_foco'], b['orden_foco']
    comun_a = [x for x in oa if x in set(ob)]
    comun_b = [x for x in ob if x in set(oa)]
    foco_cambia = comun_a != comun_b
    primera_divergencia = next((i for i, (x, y) in enumerate(zip(comun_a, comun_b)) if x != y), None)

    ok = not (aniadidos or eliminados or renombrados or foco_cambia)
    return {
        'ok': ok,
        'resumen': {
            'elementos': {'antes': len(ea), 'despues': len(eb)},
            'aniadidos': len(aniadidos), 'eliminados': len(eliminados),
            'renombrados': len(renombrados),
            'orden_foco_cambia': foco_cambia,
        },
        'aniadidos': aniadidos, 'eliminados': eliminados, 'renombrados': renombrados,
        'foco': {'antes': oa, 'despues': ob, 'primera_divergencia': primera_divergencia},
        'nota': ('Elementos sin id se casan por tag+nombre+href: renombrar produce '
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
        d = snapshot(a.url, a.out)
        print(json.dumps({'url': d['url'], 'elementos': len(d['elementos']),
                          'pasos_foco': len(d['orden_foco']), 'salida': a.out},
                         ensure_ascii=False, indent=1))
        return 0
    with open(a.a, encoding='utf-8') as f:
        ja = json.load(f)
    with open(a.b, encoding='utf-8') as f:
        jb = json.load(f)
    print(json.dumps(diff(ja, jb), ensure_ascii=False, indent=1))
    return 0 if True else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
