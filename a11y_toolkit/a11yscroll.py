#!/usr/bin/env python3
"""Infinite-scroll auditor — the documented a11y disaster nobody automates.

Sources: Deque's "Infinite Scrolling & Role=Feed Accessibility Issues" and the
WAI-ARIA APG Feed pattern. NO official W3C failure technique exists
(verified 2026-09); applicable criteria: 2.4.3 (focus order), 4.1.3 (status
messages) and 2.2.2 (auto-updating content).

What it measures, with real focus and a live-region observer:
  1. Does focus SURVIVE each loading batch? (re-rendering the container
     destroys it — the documented failure)
  2. Is new content ANNOUNCED? (aria-live/status regions receiving text
     during loading; role="feed" container)
  3. Does the feed END or offer an alternative? ("load more" button, footer
     reachability, detectable end)
  4. Structure: role="feed" + role="article" (APG pattern) as positive signal.

Requires local Playwright. A filter with honest judgment, not a verdict.

CLI:
  a11yscroll.py https://medium.com/section [--max-batches 5] [--lang es]
"""

import argparse
import json
import sys

from .a11yaudit import CRIT, T, compute_score

_TD = {
    'es': {
        'scroll_focus': 'El elemento con foco {where} tras cargar una tanda ({detail}). Fallo documentado del scroll infinito: quien navega con teclado pierde su punto de lectura (2.4.3).',
        'scroll_focus_rem': 'No re-renderices el contenedor del feed: AÑADE nodos al final (appendChild/insertAdjacentHTML). Si el foco cae en contenido eliminado, devuélvelo al equivalente nuevo.',
        'scroll_no_announce': '{n} tandas cargadas sin ningún anuncio: no hay región aria-live/status que reciba texto durante la carga ni role="feed" en el contenedor (4.1.3).',
        'scroll_no_announce_rem': 'Añade una región role="status" con texto «Cargando más…»/«10 elementos nuevos» y marca el contenedor como role="feed" con aria-busy durante la carga.',
        'scroll_no_end': 'Feed infinito sin fin visible en {n} tandas y sin botón «cargar más» alternativo: el pie de página queda inalcanzable (guía Deque; afín a 2.2.2).',
        'scroll_no_end_rem': 'Ofrece un botón «Cargar más» (mejor opción accesible: carga explícita y foco predecible), o un fin real del feed, o un control para pausar la carga automática.',
        'scroll_no_feed': 'El contenedor del feed no usa role="feed" con hijos role="article" (patrón Feed de ARIA APG): los lectores de pantalla no pueden saltar de artículo en artículo.',
        'scroll_no_feed_rem': 'Marca el contenedor como role="feed", cada elemento como role="article" con aria-labelledby, y usa aria-busy durante la carga.',
        'limits': ('Auditor de scroll infinito: heurística con foco real y observador de '
                    'regiones vivas en {n} tandas. No sustituye la prueba con lector de '
                    'screen reader en el feed real.'),
    },
    'en': {
        'scroll_focus': 'The focused element {where} after loading a batch ({detail}). Documented infinite-scroll failure: keyboard users lose their reading point (2.4.3).',
        'scroll_focus_rem': 'Do not re-render the feed container: APPEND nodes at the end (appendChild/insertAdjacentHTML). If focus lands on removed content, move it to the new equivalent.',
        'scroll_no_announce': '{n} batches loaded with zero announcements: no aria-live/status region receives text during loading and the container lacks role="feed" (4.1.3).',
        'scroll_no_announce_rem': 'Add a role="status" region with "Loading more…"/"10 new items" text and mark the container role="feed" with aria-busy while loading.',
        'scroll_no_end': 'Infinite feed with no visible end after {n} batches and no "load more" button alternative: the footer stays unreachable (Deque guidance; akin to 2.2.2).',
        'scroll_no_end_rem': 'Offer a "Load more" button (the most accessible option: explicit loading, predictable focus), a real feed end, or a control to pause auto-loading.',
        'scroll_no_feed': 'The feed container does not use role="feed" with role="article" children (ARIA APG Feed pattern): screen readers cannot jump article by article.',
        'scroll_no_feed_rem': 'Mark the container role="feed", each item role="article" with aria-labelledby, and use aria-busy during loading.',
        'limits': ('Infinite-scroll auditor: heuristics with real focus and a live-region '
                    'observer over {n} batches. Not a substitute for screen-reader testing '
                    'on the real feed.'),
    },
}

_MON = r"""() => {
  window.__a11yscroll = { events: [], n: 0 };
  const esViva = el => el.closest && el.closest('[aria-live], [role="status"], [role="alert"], [role="log"], [role="feed"]');
  const anota = (tipo, texto) => {
    if (window.__a11yscroll.events.length < 50)
      window.__a11yscroll.events.push({ type: tipo, text: (texto || '').trim().slice(0, 80) });
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

_STATE = r"""() => {
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
  return { items, hasFeed: !!feed, hasFooter: !!document.querySelector('footer, [role="contentinfo"]'),
           focus: activo && activo !== document.body
             ? (activo.tagName.toLowerCase() + (activo.id ? '#' + activo.id : '')) : null,
           focus_offscreen: !!fuera, hasMore: mas,
           scroll: document.documentElement.scrollHeight,
           events: window.__a11yscroll ? window.__a11yscroll.events : [] };
}"""


def _add(findings, lang, sev, code, key, **fmt):
    findings.append({
        'severity': sev, 'criterion': CRIT.get(lang, CRIT['es']).get(code, code),
        'signal': key, 'issue': _TD.get(lang, _TD['es'])[key].format(**fmt),
        'remediation': _TD.get(lang, _TD['es'])[key + '_rem'].format(**fmt),
    })


def audit_scroll(url, max_batches=5, lang='en', timeout=45, auth_state=None):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page(viewport={'width': 1280, 'height': 800}) if auth_state \
            else nav.new_page(viewport={'width': 1280, 'height': 800})
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
        before = page.evaluate(_STATE)
        initial_focus = before['focus']

        batches = []
        end_reached = False
        via_clic = False
        for _t in range(max_batches):
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            crecio = False
            for _espera in range(6):   # hasta ~3 s esperando nueva tanda
                page.wait_for_timeout(500)
                e = page.evaluate(_STATE)
                if e['items'] > (batches[-1]['items'] if batches else before['items']) \
                        or e['scroll'] > (batches[-1]['scroll'] if batches else before['scroll']):
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
                        e2 = page.evaluate(_STATE)
                        if e2['items'] > (batches[-1]['items'] if batches else before['items']):
                            crecio = True
                            break
            e = page.evaluate(_STATE)
            batches.append(e)
            if not crecio:
                end_reached = True
                break

        nav.close()

    findings = []
    last = batches[-1] if batches else before

    # 1. foco (2.4.3): desaparecido o fuera de pantalla tras las tandas
    if initial_focus:
        if last['focus'] is None:
            _add(findings, lang, 'high', '2.4.3', 'scroll_focus',
                    where='disappeared', detail=f'was on {initial_focus}')
        elif last['focus_offscreen']:
            _add(findings, lang, 'medium', '2.4.3', 'scroll_focus',
                    where='went offscreen', detail=initial_focus)

    # Guardián de honestidad: sin ítems detectados no hay feed que auditar
    hay_feed_real = before['items'] > 0 or last['items'] > before['items']
    nota = None
    if not hay_feed_real:
        nota = ('no standard items detected (article, role=article, li in main): the feed is '
                'behind a login/bot wall or uses non-standard markup. Announcement/end signals '
                'are skipped; audit feeds you own with known markup.' if lang == 'en' else
                'no se detectaron ítems con los selectores estándar (article, role=article, '
                'li en main): o el feed está tras login/muro de bots, o usa marcado no estándar. '
                'Las señales de anuncios/fin se omiten; valida feeds propios con marcado conocido.')

    # 2. anuncios (4.1.3) — solo si hubo feed real
    if hay_feed_real and batches and not last['hasFeed'] and not last['events']:
        _add(findings, lang, 'medium', '4.1.3', 'scroll_no_announce',
                n=len(batches))

    # 3. fin/alternativa — solo si hubo feed real
    if hay_feed_real and not end_reached and not last['hasMore']:
        _add(findings, lang, 'medium', '2.2.2', 'scroll_no_end', n=len(batches))

    # 4. patrón APG
    if not last['hasFeed']:
        _add(findings, lang, 'low', '1.3.1', 'scroll_no_feed')

    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])
    return {
        'url': url,
        'mode': 'scroll',
        'score': compute_score(findings),
        'summary': {s_: sum(1 for h in findings if h['severity'] == s_)
                    for s_ in ('high', 'medium', 'low')},
        'items': {'before': before['items'], 'after': last['items']},
        'batches': len(batches),
        'end_reached': end_reached,
        'live_announcements': [e['text'] for e in last['events'][:5]],
        'focus': {'initial': initial_focus, 'final': last['focus'],
                 'offscreen': last['focus_offscreen']},
        'load_more_alternative': last['hasMore'],
        'note': nota,
        'findings': findings,
        'limits': _TD.get(lang, _TD['es'])['limits'].format(n=len(batches)),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('url')
    ap.add_argument('--max-batches', type=int, default=5)
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--timeout', type=int, default=45)
    a = ap.parse_args(argv)
    try:
        res = audit_scroll(a.url, max_batches=a.max_batches, lang=a.lang, timeout=a.timeout)
    except ImportError:
        print(json.dumps({'error': 'Playwright no instalado'}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
