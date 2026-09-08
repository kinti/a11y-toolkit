#!/usr/bin/env python3
"""Auditor de SCROLL INFINITO — el desastre accesible documentado que nadie automatiza.

Fuentes: guía de Deque «Infinite Scrolling & Role=Feed Accessibility Issues» y el
patrón Feed de WAI-ARIA APG. NO existe técnica de fallo oficial W3C (verificado
2026-09); los criterios aplicables son 2.4.3 (orden de foco), 4.1.3 (mensajes de
estado) y 2.2.2 (contenido auto-actualizado).

Lo que mide, con Tab/foco reales y un observador de regiones vivas:
  1. ¿El foco sobrevive a cada tanda de carga? (si el elemento enfocado desaparece
     o queda fuera de pantalla, es el fallo documentado)
  2. ¿Se anuncia el contenido nuevo? (regiones aria-live/status/feed que reciben
     texto durante la carga; contenedor con role="feed")
  3. ¿El feed termina o al menos ofrece alternativa? (botón «cargar más»,
     alcance del pie de página, fin detectable)
  4. Estructura: role="feed" + role="article" (patrón APG) como señal positiva.

Requiere Playwright local. Es filtro con juicio honesto, no veredicto.

CLI:
  a11yscroll.py https://medio.con/seccion [--tandas 5] [--lang en]
"""

import argparse
import json
import sys

from a11yaudit import CRIT, T, calcular_score

_TD = {
    'es': {
        'scroll_focus': 'El elemento con foco {destino} tras cargar una tanda ({detalle}). Fallo documentado del scroll infinito: quien navega con teclado pierde su punto de lectura (2.4.3).',
        'scroll_focus_rem': 'No re-renderices el contenedor del feed: AÑADE nodos al final (appendChild/insertAdjacentHTML). Si el foco cae en contenido eliminado, devuélvelo al equivalente nuevo.',
        'scroll_no_announce': '{n} tandas cargadas sin ningún anuncio: no hay región aria-live/status que reciba texto durante la carga ni role="feed" en el contenedor (4.1.3).',
        'scroll_no_announce_rem': 'Añade una región role="status" con texto «Cargando más…»/«10 elementos nuevos» y marca el contenedor como role="feed" con aria-busy durante la carga.',
        'scroll_no_end': 'Feed infinito sin fin visible en {n} tandas y sin botón «cargar más» alternativo: el pie de página queda inalcanzable (guía Deque; afín a 2.2.2).',
        'scroll_no_end_rem': 'Ofrece un botón «Cargar más» (mejor opción accesible: carga explícita y foco predecible), o un fin real del feed, o un control para pausar la carga automática.',
        'scroll_no_feed': 'El contenedor del feed no usa role="feed" con hijos role="article" (patrón Feed de ARIA APG): los lectores de pantalla no pueden saltar de artículo en artículo.',
        'scroll_no_feed_rem': 'Marca el contenedor como role="feed", cada elemento como role="article" con aria-labelledby, y usa aria-busy durante la carga.',
        'limites': ('Auditor de scroll infinito: heurística con foco real y observador de '
                    'regiones vivas en {n} tandas. No sustituye la prueba con lector de '
                    'screen reader en el feed real.'),
    },
    'en': {
        'scroll_focus': 'The focused element {destino} after loading a batch ({detalle}). Documented infinite-scroll failure: keyboard users lose their reading point (2.4.3).',
        'scroll_focus_rem': 'Do not re-render the feed container: APPEND nodes at the end (appendChild/insertAdjacentHTML). If focus lands on removed content, move it to the new equivalent.',
        'scroll_no_announce': '{n} batches loaded with zero announcements: no aria-live/status region receives text during loading and the container lacks role="feed" (4.1.3).',
        'scroll_no_announce_rem': 'Add a role="status" region with "Loading more…"/"10 new items" text and mark the container role="feed" with aria-busy while loading.',
        'scroll_no_end': 'Infinite feed with no visible end after {n} batches and no "load more" button alternative: the footer stays unreachable (Deque guidance; akin to 2.2.2).',
        'scroll_no_end_rem': 'Offer a "Load more" button (the most accessible option: explicit loading, predictable focus), a real feed end, or a control to pause auto-loading.',
        'scroll_no_feed': 'The feed container does not use role="feed" with role="article" children (ARIA APG Feed pattern): screen readers cannot jump article by article.',
        'scroll_no_feed_rem': 'Mark the container role="feed", each item role="article" with aria-labelledby, and use aria-busy during loading.',
        'limites': ('Infinite-scroll auditor: heuristics with real focus and a live-region '
                    'observer over {n} batches. Not a substitute for screen-reader testing '
                    'on the real feed.'),
    },
}

_MON = r"""() => {
  window.__a11yscroll = { eventos: [], n: 0 };
  const esViva = el => el.closest && el.closest('[aria-live], [role="status"], [role="alert"], [role="log"], [role="feed"]');
  const anota = (tipo, texto) => {
    if (window.__a11yscroll.eventos.length < 50)
      window.__a11yscroll.eventos.push({ tipo, texto: (texto || '').trim().slice(0, 80) });
  };
  new MutationObserver(muts => {
    for (const m of muts) {
      if (m.type === 'characterData' || m.type === 'childList') {
        const el = m.target.nodeType === 1 ? m.target : m.target.parentElement;
        if (el && esViva(el)) {
          const vivo = el.closest('[aria-live], [role="status"], [role="alert"], [role="log"], [role="feed"]');
          anota('anuncio', vivo.innerText || vivo.textContent || '');
        }
      }
    }
  }).observe(document.body, { subtree: true, childList: true, characterData: true });
}"""

_ESTADO = r"""() => {
  const items = document.querySelectorAll('article, [role="article"]').length
    || document.querySelectorAll('main li').length;
  const feed = document.querySelector('[role="feed"]');
  const activo = document.activeElement;
  const fuera = activo && activo !== document.body
    ? (() => { const r = activo.getBoundingClientRect();
        return r.bottom < -8 || r.top > innerHeight + 8 || (r.width === 0 && r.height === 0); })()
    : false;
  const mas = [...document.querySelectorAll('button, a')]
    .some(b => /más|more|cargar|load/i.test((b.innerText || '').trim()) && b.offsetParent);
  return { items, hayFeed: !!feed, hayFooter: !!document.querySelector('footer, [role="contentinfo"]'),
           foco: activo && activo !== document.body
             ? (activo.tagName.toLowerCase() + (activo.id ? '#' + activo.id : '')) : null,
           focoFuera: !!fuera, hayMas: mas,
           scroll: document.documentElement.scrollHeight,
           eventos: window.__a11yscroll ? window.__a11yscroll.eventos : [] };
}"""


def _agrega(hallazgos, lang, sev, code, key, **fmt):
    hallazgos.append({
        'severidad': sev, 'criterio': CRIT.get(lang, CRIT['es']).get(code, code),
        'senal': key, 'hallazgo': _TD.get(lang, _TD['es'])[key].format(**fmt),
        'remediacion': _TD.get(lang, _TD['es'])[key + '_rem'].format(**fmt),
    })


def audit_scroll(url, max_tandas=5, lang='es', timeout=45):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={'width': 1280, 'height': 800})
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(500)
        except Exception as e:  # noqa: BLE001
            nav.close()
            return {'error': f'no se pudo cargar: {e}'}
        page.evaluate(_MON)
        page.evaluate("(() => { const c = document.querySelector("
                      "  'article a[href], [role=article] a[href], main li a[href]');"
                      " if (c) c.focus(); })()")
        antes = page.evaluate(_ESTADO)
        foco_inicial = antes['foco']

        tandas = []
        fin_alcanzado = False
        via_clic = False
        for _t in range(max_tandas):
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            crecio = False
            for _espera in range(6):   # hasta ~3 s esperando nueva tanda
                page.wait_for_timeout(500)
                e = page.evaluate(_ESTADO)
                if e['items'] > (tandas[-1]['items'] if tandas else antes['items']) \
                        or e['scroll'] > (tandas[-1]['scroll'] if tandas else antes['scroll']):
                    crecio = True
                    break
            if not crecio and not via_clic:
                # el scroll no trae nada: ¿hay botón «cargar más»? (la alternativa sana)
                via_clic = page.evaluate(
                    "() => [...document.querySelectorAll('button, a')].some(b =>"
                    " /más|more|cargar|load/i.test((b.innerText || '').trim()) && b.offsetParent)")
                if via_clic:
                    page.evaluate(
                        "() => { const b = [...document.querySelectorAll('button, a')].find("
                        "b => /más|more|cargar|load/i.test((b.innerText || '').trim()) && b.offsetParent);"
                        " if (b) b.click(); }")
                    for _espera in range(6):
                        page.wait_for_timeout(500)
                        e2 = page.evaluate(_ESTADO)
                        if e2['items'] > (tandas[-1]['items'] if tandas else antes['items']):
                            crecio = True
                            break
            e = page.evaluate(_ESTADO)
            tandas.append(e)
            if not crecio:
                fin_alcanzado = True
                break

        nav.close()

    hallazgos = []
    ultimo = tandas[-1] if tandas else antes

    # 1. foco (2.4.3): desaparecido o fuera de pantalla tras las tandas
    if foco_inicial:
        if ultimo['foco'] is None:
            _agrega(hallazgos, lang, 'alta', '2.4.3', 'scroll_focus',
                    destino='desapareció', detalle=f'estaba en {foco_inicial}')
        elif ultimo['focoFuera']:
            _agrega(hallazgos, lang, 'media', '2.4.3', 'scroll_focus',
                    destino='quedó fuera de pantalla', detalle=foco_inicial)

    # Guardián de honestidad: sin ítems detectados no hay feed que auditar
    hay_feed_real = antes['items'] > 0 or ultimo['items'] > antes['items']
    nota = None
    if not hay_feed_real:
        nota = ('no se detectaron ítems con los selectores estándar (article, role=article, '
                'li en main): o el feed está tras login/muro de bots, o usa marcado no estándar. '
                'Las señales de anuncios/fin se omiten; valida feeds propios con marcado conocido.')

    # 2. anuncios (4.1.3) — solo si hubo feed real
    if hay_feed_real and tandas and not ultimo['hayFeed'] and not ultimo['eventos']:
        _agrega(hallazgos, lang, 'media', '4.1.3', 'scroll_no_announce',
                n=len(tandas))

    # 3. fin/alternativa — solo si hubo feed real
    if hay_feed_real and not fin_alcanzado and not ultimo['hayMas']:
        _agrega(hallazgos, lang, 'media', '2.2.2', 'scroll_no_end', n=len(tandas))

    # 4. patrón APG
    if not ultimo['hayFeed']:
        _agrega(hallazgos, lang, 'baja', '1.3.1', 'scroll_no_feed')

    orden = {'alta': 0, 'media': 1, 'baja': 2}
    hallazgos.sort(key=lambda h: orden[h['severidad']])
    return {
        'url': url,
        'modo': 'scroll',
        'score': calcular_score(hallazgos),
        'resumen': {s_: sum(1 for h in hallazgos if h['severidad'] == s_)
                    for s_ in ('alta', 'media', 'baja')},
        'items': {'antes': antes['items'], 'despues': ultimo['items']},
        'tandas': len(tandas),
        'fin_alcanzado': fin_alcanzado,
        'anuncios_vivos': [e['texto'] for e in ultimo['eventos'][:5]],
        'foco': {'inicial': foco_inicial, 'final': ultimo['foco'],
                 'fuera_de_pantalla': ultimo['focoFuera']},
        'alternativa_cargar_mas': ultimo['hayMas'],
        'nota': nota,
        'hallazgos': hallazgos,
        'limites': _TD.get(lang, _TD['es'])['limites'].format(n=len(tandas)),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('url')
    ap.add_argument('--tandas', type=int, default=5)
    ap.add_argument('--lang', default='es', choices=['es', 'en'])
    ap.add_argument('--timeout', type=int, default=45)
    a = ap.parse_args(argv)
    try:
        res = audit_scroll(a.url, max_tandas=a.tandas, lang=a.lang, timeout=a.timeout)
    except ImportError:
        print(json.dumps({'error': 'Playwright no instalado'}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
