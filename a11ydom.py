#!/usr/bin/env python3
"""Auditoría RENDERIZADA de accesibilidad vía Playwright (lo que el HTML estático no ve).

a11y_audit_dom carga la URL en Chromium y evalúa el DOM ya computado:

- Contraste REAL de todo el texto visible (color computado vs fondo efectivo con
  composición de transparencias) — criterio 1.4.3.
- Target Size mínimo 24×24 — criterio WCAG 2.2 nuevo 2.5.8 (con excepciones: enlaces
  inline en párrafo/lista).
- Indicador de foco visible (outline/box-shadow) — 2.4.7, heurístico.
- Las señales estáticas, sobre el DOM renderizado (alt, nombres accesibles, labels,
  encabezados, lang/title, viewport, tabindex, aria-hidden, videos, tablas, ids).

Requiere Playwright local: pip install playwright && playwright install chromium.
Es filtro, no veredicto: heurísticas honestas, las dudosas se marcan como «revisar».

CLI:
  a11ydom.py https://example.com [--lang en] [--timeout 45]
"""

import argparse
import json
import re
import sys

from a11yaudit import CRIT, T, calcular_score

MAX_EJEMPLOS = 6

_TD = {
    'es': {
        'contrast_fail': ('{n} zonas de texto con contraste insuficiente: {det}. '
                          '(fg/fondo computados, con composición de transparencias).'),
        'contrast_fail_rem': ('Sube el contraste a ≥4.5:1 (≥3:1 en texto grande). El fondo '
                              'efectivo ya incluye superposiciones y transparencias; si hay '
                              'imagen de fondo, verifica esa zona a mano.'),
        'contrast_review': '{n} zonas de texto con imagen de fondo o sombra: no calculables, revisar.',
        'contrast_review_rem': 'El contraste sobre imagen de fondo no es calculable aquí: usa a11y_contrast_image con una captura de esa región.',
        'target_small': ('{n} controles con área de toque menor de 24×24 px (WCAG 2.2, '
                         '2.5.8): {det}.'),
        'target_small_rem': ('Da a los controles al menos 24×24 px CSS (mejor 44×44) con padding o '
                             'min-width/min-height. Excepciones: enlaces inline equivalentes y '
                             'espaciado suficiente alrededor.'),
        'focus_invisible': ('{n} controles enfocables sin indicador de foco aparente '
                            '(outline y box-shadow ausentes): {det}. Revisar.'),
        'focus_invisible_rem': ('Asegura un indicador de foco visible: nunca outline:none sin '
                                'sustituto; usa :focus-visible con outline ≥2px o borde/sombra '
                                'contrastada (2.4.7).'),
        'focus_not_focusable': '{n} controles que no reciben foco con .focus(): {det}.',
        'focus_not_focusable_rem': 'Si debe ser interactivo, que sea enfocable (tabindex="0"); si no, quítalo de la ruta de tabulación.',
        'state_contrast': ('{n} controles con contraste insuficiente en estado :focus/:hover '
                           '(<3:1): {det}. Revisar.'),
        'state_contrast_rem': ('El texto del control también necesita contraste cuando está '
                               'enfocado o con el puntero encima (1.4.3); los controles '
                               'DESACTIVADOS están exentos por WCAG. Ajusta los colores de '
                               ':focus y :hover.'),
        'limites': ('Auditoría renderizada: heurística honesta, no sustituye lector de pantalla '
                    'ni revisión manual. Contraste calculado sobre fondos computados; los casos '
                    'con imagen de fondo se reportan como «revisar». 2.5.8 admite excepciones '
                    '(inline equivalente, espaciado) que aquí se aproximan.'),
    },
    'en': {
        'contrast_fail': ('{n} text areas with insufficient contrast: {det}. '
                          '(computed fg/background, with alpha compositing).'),
        'contrast_fail_rem': ('Raise contrast to ≥4.5:1 (≥3:1 for large text). The effective '
                              'background already includes overlays and translucency; with a '
                              'background image, check that area manually.'),
        'contrast_review': '{n} text areas over background images or with text-shadow: not computable, review.',
        'contrast_review_rem': 'Contrast over a background image is not computable here: use a11y_contrast_image with a screenshot of that region.',
        'target_small': ('{n} controls with a touch area smaller than 24×24 px (WCAG 2.2 '
                         '2.5.8): {det}.'),
        'target_small_rem': ('Give controls at least 24×24 CSS px (44×44 is better) via padding or '
                             'min-width/min-height. Exceptions: equivalent inline links and '
                             'sufficient surrounding spacing.'),
        'focus_invisible': ('{n} focusable controls with no apparent focus indicator '
                            '(outline and box-shadow absent): {det}. Review.'),
        'focus_invisible_rem': ('Guarantee a visible focus indicator: never outline:none without a '
                                'replacement; use :focus-visible with ≥2px outline or a contrasted '
                                'border/shadow (2.4.7).'),
        'focus_not_focusable': '{n} controls that never receive focus via .focus(): {det}.',
        'focus_not_focusable_rem': 'If it must be interactive, make it focusable (tabindex="0"); otherwise remove it from the tab path.',
        'limites': ('Rendered audit: honest heuristics, no substitute for a screen reader or '
                    'manual review. Contrast computed over computed backgrounds; cases with '
                    'background images are reported as "review". 2.5.8 allows exceptions '
                    '(equivalent inline, spacing) approximated here.'),
    },
}

CRIT['es']['2.5.8'] = '2.5.8 Tamaño del objetivo (mínimo)'
CRIT['en']['2.5.8'] = '2.5.8 Target Size (Minimum)'
CRIT['es']['2.4.7'] = '2.4.7 Foco visible'
CRIT['en']['2.4.7'] = '2.4.7 Focus Visible'


def _t(lang, key):
    return _TD.get(lang, _TD['es']).get(key) or T.get(lang, T['es']).get(key, key)


# ------------------------------------------------------------------- JS -----
_JS = r'''(maxEj) => {
  const INTER = 'a[href], button, input, select, textarea, summary, [role="button"], [role="link"], [tabindex]';
  const out = { contrast: {}, contrastReview: 0, targets: [], unnamed: [], fields: [],
                imgs: [], iframes: [], headings: [], tabindex: [], ariaHidden: [],
                blank: 0, videos: 0, videoSubs: 0, tables: 0, tableTh: 0,
                focus: [], focusFail: [], focusContrast: [], marks: 0, ids: {},
                lang: null, title: '', viewport: null, refresh: null,
                main: false, skip: false, elements: 0 };

  const vis = el => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none' && parseFloat(s.opacity || '1') > 0.05;
  };
  const path = el => {
    let p = el.tagName.toLowerCase();
    if (el.id) return '#' + el.id;
    let n = el, depth = 0;
    while (n.parentElement && depth < 2 && n.parentElement !== document.body) {
      n = n.parentElement;
      p = n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') + ' > ' + p;
      depth++;
    }
    return p;
  };

  // ---- contraste real: fondo efectivo con composición de alfas ----
  const parseCol = c => {
    const m = /rgba?\(([^)]+)\)/.exec(c || '');
    if (!m) return null;
    const p = m[1].split(',').map(x => parseFloat(x));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const over = (fg, bg) => ({
    r: Math.round(fg.r * fg.a + bg.r * (1 - fg.a)),
    g: Math.round(fg.g * fg.a + bg.g * (1 - fg.a)),
    b: Math.round(fg.b * fg.a + bg.b * (1 - fg.a)), a: 1 });
  const bgOf = el => {
    const stack = [];
    let n = el;
    while (n) {
      const s = getComputedStyle(n);
      if (s.backgroundImage && s.backgroundImage !== 'none') return { image: true };
      const c = parseCol(s.backgroundColor);
      if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; }
      if (n === document.documentElement) break;
      n = n.parentElement;
    }
    let color = { r: 255, g: 255, b: 255, a: 1 };
    for (const c of stack.reverse()) color = over(c, color);
    return color;
  };
  const lum = c => { const f = v => { v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const ratioOf = (a, b) => { const l1 = Math.max(lum(a), lum(b)), l2 = Math.min(lum(a), lum(b));
    return (l1 + 0.05) / (l2 + 0.05); };

  const fails = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const txt = (node.nodeValue || '').trim();
    if (!txt) continue;
    const el = node.parentElement;
    if (!el || el.closest('script, style, noscript, svg title')) continue;
    if (!vis(el)) continue;
    const s = getComputedStyle(el);
    const fg = parseCol(s.color);
    if (!fg) continue;
    if (s.textShadow && s.textShadow !== 'none') { out.contrastReview++; continue; }
    const bg = bgOf(el);
    if (bg.image) { out.contrastReview++; continue; }
    const px = parseFloat(s.fontSize);
    const bold = parseInt(s.fontWeight || '400', 10) >= 600;
    const large = px >= 24 || (bold && px >= 18.66);
    const r = ratioOf(fg, bg);
    const umbral = large ? 3.0 : 4.5;
    if (r >= umbral) continue;
    const fk = `rgb(${fg.r},${fg.g},${fg.b})`;
    const bk = `rgb(${bg.r},${bg.g},${bg.b})`;
    const key = fk + '|' + bk + '|' + (large ? 'L' : 'N');
    if (!fails.has(key)) fails.set(key, { fg: fk, bg: bk, large, ratio: Math.round(r * 100) / 100,
                                          n: 0, ej: path(el) });
    const f = fails.get(key);
    f.n++;
  }
  out.contrast = [...fails.values()].slice(0, 40);

  // ---- target size 2.5.8 ----
  for (const el of document.querySelectorAll(INTER)) {
    out.elements++;
    if (el.type === 'hidden' || !vis(el)) continue;
    const disp = getComputedStyle(el).display;
    if (el.tagName === 'A' && disp.includes('inline') && el.closest('p, li, dd, dt, td, figcaption, blockquote')) continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 2 || r.height <= 2) continue;   // patrón visualmente oculto (skip link)
    if (el.getAttribute('tabindex') === '-1') continue;
    if (r.width < 24 || r.height < 24) {
      if (out.targets.length < 40) out.targets.push(
        { ej: path(el), w: Math.round(r.width), h: Math.round(r.height),
          inline: disp.includes('inline') });
    }
  }

  // ---- nombres accesibles renderizados ----
  const nameOf = el => {
    let n = (el.getAttribute('aria-label') || '').trim();
    if (!n && el.labels && el.labels[0]) n = el.labels[0].innerText.trim();
    if (!n && el.getAttribute('aria-labelledby')) {
      const ref = document.getElementById(el.getAttribute('aria-labelledby'));
      if (ref) n = (ref.innerText || '').trim();
    }
    if (!n) n = (el.getAttribute('title') || '').trim();
    if (!n && el.tagName === 'INPUT' && ['submit', 'button', 'reset'].includes(el.type)) n = el.value || '';
    if (!n && el.tagName === 'INPUT' && el.type === 'image') n = el.alt || '';
    if (!n && ['A', 'BUTTON', 'SUMMARY'].includes(el.tagName)) n = (el.innerText || '').trim();
    if (!n && el.tagName === 'IMG') n = el.getAttribute('alt') || '';
    return n.trim();
  };
  for (const el of document.querySelectorAll('a[href], button, summary, [role="button"], [role="link"]')) {
    if (!vis(el) || el.closest('[aria-hidden="true"]')) continue;
    if (!nameOf(el) && out.unnamed.length < 30) out.unnamed.push(path(el));
  }
  for (const el of document.querySelectorAll('input, select, textarea')) {
    if (el.type === 'hidden' || el.type === 'submit' || el.type === 'button' || el.type === 'reset') continue;
    if (!vis(el)) continue;
    if (!nameOf(el) && out.fields.length < 30) out.fields.push(path(el));
  }
  for (const el of document.querySelectorAll('img')) {
    if (!vis(el)) continue;
    if (!el.hasAttribute('alt') && out.imgs.length < 30) out.imgs.push(el.getAttribute('src') || '');
  }
  for (const el of document.querySelectorAll('iframe')) {
    if (!((el.getAttribute('title') || '').trim() || (el.getAttribute('aria-label') || '').trim())
        && out.iframes.length < 20) out.iframes.push(el.getAttribute('src') || '');
  }

  // ---- estructura ----
  for (const h of document.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
    out.headings.push({ lvl: +h.tagName[1], text: (h.innerText || '').trim().slice(0, 80) });
  }
  for (const el of document.querySelectorAll('[tabindex]')) {
    const t = parseInt(el.getAttribute('tabindex') || '0', 10);
    if (t > 0 && out.tabindex.length < 20) out.tabindex.push(path(el));
  }
  for (const el of document.querySelectorAll('[aria-hidden="true"]')) {
    if (el.matches(INTER)) {
      if (el.getAttribute('tabindex') !== '-1') out.ariaHidden.push(path(el));
    } else if ([...(el.querySelectorAll(INTER) || [])]
               .some(d => d.getAttribute('tabindex') !== '-1')) {
      out.ariaHidden.push(path(el));
    }
  }
  for (const el of document.querySelectorAll('a[target="_blank"]')) {
    const t = (el.innerText || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '');
    if (!/(nueva|nuevo|ventana|pesta|tab\b|window|external|externo|exterior)/i.test(t)) out.blank++;
  }
  for (const v of document.querySelectorAll('video')) {
    out.videos++;
    if (v.querySelector('track[kind="captions"], track[kind="subtitles"]')) out.videoSubs++;
  }
  for (const tb of document.querySelectorAll('table')) {
    out.tables++;
    if (tb.querySelector('th')) out.tableTh++;
  }
  for (const el of document.querySelectorAll('[id]')) {
    out.ids[el.id] = (out.ids[el.id] || 0) + 1;
  }
  out.lang = document.documentElement.getAttribute('lang');
  out.title = document.title || '';
  const vp = document.querySelector('meta[name="viewport"]');
  out.viewport = vp ? vp.getAttribute('content') : null;
  const rf = document.querySelector('meta[http-equiv="refresh" i]');
  out.refresh = rf ? rf.getAttribute('content') : null;
  out.main = !!document.querySelector('main, [role="main"]');
  out.skip = !!document.querySelector('a[href^="#"]');

  // ---- marcas para contrastar estados (:hover) desde Python ----
  let mi = 0;
  for (const el of document.querySelectorAll(INTER)) {
    if (mi >= 25) break;
    if (el.type === 'hidden' || !vis(el)) continue;
    el.setAttribute('data-a11yidx', String(mi));
    mi++;
  }
  out.marks = mi;

  // ---- foco: indicador visible (heurístico) + contraste en estado focus ----
  const oculto = el => { const r = el.getBoundingClientRect();
    return (r.width <= 2 && r.height <= 2); };
  const stops = [...document.querySelectorAll(INTER)]
    .filter(el => vis(el) && !el.disabled && el.getAttribute('tabindex') !== '-1'
                  && !oculto(el)).slice(0, 40);
  const prevFocus = document.activeElement;
  for (const el of stops) {
    try { el.focus(); } catch (e) { /* no enfocable */ }
    if (document.activeElement !== el) {
      out.focusFail.push({ ej: path(el), why: 'nofocus' });
      continue;
    }
    const s = getComputedStyle(el);
    const outline = s.outlineStyle !== 'none' && parseFloat(s.outlineWidth || '0') > 0;
    const shadow = s.boxShadow && s.boxShadow !== 'none';
    if (!outline && !shadow) out.focus.push(path(el));
    const fgf = parseCol(s.color);
    const bgf = bgOf(el);
    if (fgf && !bgf.image) {
      const rf = ratioOf(fgf, bgf);
      if (rf < 3 && out.focusContrast.length < 20)
        out.focusContrast.push({ ej: path(el), ratio: Math.round(rf * 100) / 100 });
    }
  }
  if (prevFocus && prevFocus.blur) { try { prevFocus.focus(); } catch (e) {} }

  return out;
}'''


def _agrega(hallazgos, lang, severidad, code, key, ejemplos=None, **fmt):
    h = {'severidad': severidad, 'criterio': CRIT.get(lang, CRIT['es']).get(code, code),
         'senal': key,
         'hallazgo': _t(lang, key).format(**fmt), 'remediacion': _t(lang, key + '_rem').format(**fmt)}
    if ejemplos:
        h['ejemplos'] = ejemplos[:MAX_EJEMPLOS]
    hallazgos.append(h)


def audit_dom(datos, url='(rendered)', lang='es'):
    """Agrega los datos JS del DOM en un informe con la misma forma que audit_html."""
    hallazgos = []

    # 1. Contraste real
    fallos = datos.get('contrast') or []
    if fallos:
        det = '; '.join(f"{f['fg']} vs {f['bg']} = {f['ratio']}:1"
                        + (' (grande)' if f['large'] else '') + f" ×{f['n']}"
                        for f in fallos[:4])
        ejemplos = [f"{f['fg']} sobre {f['bg']} → {f['ratio']}:1 (p. ej. {f['ej']})" for f in fallos]
        _agrega(hallazgos, lang, 'alta', '1.4.3', 'contrast_fail',
                ejemplos=ejemplos, n=len(fallos), det=det)
    if datos.get('contrastReview'):
        _agrega(hallazgos, lang, 'baja', '1.4.3', 'contrast_review',
                n=datos['contrastReview'])

    # 2. Target size 2.5.8 (enlaces inline → baja: la excepción de espaciado
    #    probablemente aplica y no es medible aquí; bloques → media)
    targets = datos.get('targets') or []
    if targets:
        todos_inline = all(t.get('inline') for t in targets)
        det = ', '.join(f"{t['ej']} ({t['w']}×{t['h']})" for t in targets[:4])
        _agrega(hallazgos, lang, 'baja' if todos_inline else 'media', '2.5.8',
                'target_small',
                ejemplos=[f"{t['ej']} ({t['w']}×{t['h']}px)" for t in targets],
                n=len(targets), det=det)

    # 2.bis Estados focus/hover
    estados = list(datos.get('focusContrast') or []) + list(datos.get('hover') or [])
    if estados:
        det = ', '.join(f"{e['ej']} = {e['ratio']}:1" for e in estados[:4])
        _agrega(hallazgos, lang, 'media', '1.4.3', 'state_contrast',
                ejemplos=[f"{e['ej']} = {e['ratio']}:1" for e in estados],
                n=len(estados), det=det)

    # 3. Foco
    if datos.get('focus'):
        _agrega(hallazgos, lang, 'media', '2.4.7', 'focus_invisible',
                ejemplos=datos['focus'], n=len(datos['focus']),
                det=', '.join(datos['focus'][:4]))
    if datos.get('focusFail'):
        _agrega(hallazgos, lang, 'baja', '2.4.7', 'focus_not_focusable',
                ejemplos=[f['ej'] for f in datos['focusFail']],
                n=len(datos['focusFail']), det=', '.join(f['ej'] for f in datos['focusFail'][:4]))

    # 4. Resto de señales (renderizadas)
    if datos.get('unnamed'):
        _agrega(hallazgos, lang, 'alta', '4.1.2', 'ctrl_name',
                ejemplos=datos['unnamed'], n=len(datos['unnamed']), tag='control')
    if datos.get('fields'):
        _agrega(hallazgos, lang, 'alta', '3.3.2', 'field_label',
                ejemplos=datos['fields'], n=len(datos['fields']))
    if datos.get('imgs'):
        _agrega(hallazgos, lang, 'alta', '1.1.1', 'imgs_alt',
                ejemplos=datos['imgs'], n=len(datos['imgs']))
    if datos.get('ariaHidden'):
        _agrega(hallazgos, lang, 'alta', '4.1.2', 'aria_hidden_focusable',
                n=len(datos['ariaHidden']), tag='control')
    if not (datos.get('lang') or '').strip():
        _agrega(hallazgos, lang, 'media', '3.1.1', 'lang_missing')
    if not (datos.get('title') or '').strip():
        _agrega(hallazgos, lang, 'media', '2.4.2', 'title_missing')
    if datos.get('iframes'):
        _agrega(hallazgos, lang, 'media', '4.1.2', 'iframe_title',
                ejemplos=datos['iframes'], n=len(datos['iframes']))
    videos, subs = datos.get('videos', 0), datos.get('videoSubs', 0)
    if videos and subs < videos:
        _agrega(hallazgos, lang, 'media', '1.2.2', 'video_captions', n=videos - subs)
    vp = datos.get('viewport') or ''
    if re.search(r'user-scalable\s*=\s*(no|0)', vp, re.I):
        _agrega(hallazgos, lang, 'alta', '1.4.4', 'zoom_no')
    elif (m := re.search(r'maximum-scale\s*=\s*([\d.]+)', vp, re.I)) and float(m.group(1)) < 2:
        _agrega(hallazgos, lang, 'media', '1.4.4', 'zoom_max', v=m.group(1))
    if datos.get('refresh'):
        m = re.match(r'\s*(\d+)', str(datos['refresh']))
        segs = int(m.group(1)) if m else 0
        _agrega(hallazgos, lang, 'media' if segs > 0 else 'baja', '2.2.1', 'meta_refresh', v=segs)
    if datos.get('tabindex'):
        _agrega(hallazgos, lang, 'media', '2.4.3', 'tabindex_pos',
                ejemplos=datos['tabindex'], n=len(datos['tabindex']))
    if not (datos.get('main') or datos.get('skip')):
        _agrega(hallazgos, lang, 'media', '2.4.1', 'no_bypass')

    niveles = [h['lvl'] for h in (datos.get('headings') or []) if h['text']]
    h1s = sum(1 for h in datos.get('headings') or [] if h['lvl'] == 1 and h['text'])
    vacios = sum(1 for h in datos.get('headings') or [] if not h['text'])
    if niveles:
        if h1s == 0:
            _agrega(hallazgos, lang, 'media', '1.3.1', 'no_h1')
        elif h1s > 1:
            _agrega(hallazgos, lang, 'baja', '1.3.1', 'multi_h1', n=h1s)
        prev, saltos = 0, []
        for n in niveles:
            if prev and n > prev + 1:
                saltos.append(f'h{prev}→h{n}')
            prev = n
        if saltos:
            _agrega(hallazgos, lang, 'baja', '1.3.1', 'heading_skips',
                    skips=', '.join(saltos[:5]))
    else:
        _agrega(hallazgos, lang, 'media', '1.3.1', 'no_headings')
    if vacios:
        _agrega(hallazgos, lang, 'baja', '1.3.1', 'empty_heading', n=vacios)
    tablas, con_th = datos.get('tables', 0), datos.get('tableTh', 0)
    if tablas and con_th < tablas:
        _agrega(hallazgos, lang, 'media', '1.3.1', 'table_no_th', n=tablas - con_th)
    if datos.get('blank'):
        _agrega(hallazgos, lang, 'baja', '3.2.5', 'blank_no_warning', n=datos['blank'])
    dups = sum(1 for k in (datos.get('ids') or {}).values() if k > 1)
    if dups:
        _agrega(hallazgos, lang, 'baja', '4.1.2', 'dup_ids', n=dups)

    orden = {'alta': 0, 'media': 1, 'baja': 2}
    hallazgos.sort(key=lambda h: orden[h['severidad']])
    resumen = {s: sum(1 for h in hallazgos if h['severidad'] == s)
               for s in ('alta', 'media', 'baja')}
    return {
        'url': url,
        'modo': 'rendered',
        'iframes_anidados': datos.get('iframes_anidados', 0),
        'score': calcular_score(hallazgos),
        'score_nota': _t(lang, 'score_nota'),
        'elementos_interactivos': datos.get('elements', 0),
        'resumen': resumen,
        'hallazgos': hallazgos,
        'limites': _t(lang, 'limites'),
    }


_JS_HOVER = r'''(i) => {
  const el = document.querySelector('[data-a11yidx="' + i + '"]');
  if (!el) return null;
  const parseCol = c => { const m = /rgba?\(([^)]+)\)/.exec(c || '');
    if (!m) return null;
    const p = m[1].split(',').map(x => parseFloat(x));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const over = (fg, bg) => ({ r: Math.round(fg.r * fg.a + bg.r * (1 - fg.a)),
    g: Math.round(fg.g * fg.a + bg.g * (1 - fg.a)),
    b: Math.round(fg.b * fg.a + bg.b * (1 - fg.a)), a: 1 });
  const bgOf = el => { const stack = []; let n = el;
    while (n) { const c = parseCol(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; }
      if (n === document.documentElement) break;
      n = n.parentElement; }
    let color = { r: 255, g: 255, b: 255, a: 1 };
    for (const c of stack.reverse()) color = over(c, color);
    return color; };
  const lum = c => { const f = v => { v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const s = getComputedStyle(el);
  const fg = parseCol(s.color);
  if (!fg) return null;
  const bg = bgOf(el);
  if (bg.image) return null;
  const l1 = Math.max(lum(fg), lum(bg)), l2 = Math.min(lum(fg), lum(bg));
  return { fg: `rgb(${fg.r},${fg.g},${fg.b})`, bg: `rgb(${bg.r},${bg.g},${bg.b})`,
           ratio: Math.round(((l1 + 0.05) / (l2 + 0.05)) * 100) / 100 };
}'''

# claves de lista que se fusionan de iframes same-origin (con prefijo)
_LISTAS_IFRAME = ('contrast', 'targets', 'unnamed', 'fields', 'imgs', 'iframes',
                  'headings', 'tabindex', 'ariaHidden')
_CONTADORES_IFRAME = ('blank', 'videos', 'videoSubs', 'tables', 'tableTh',
                      'elements', 'contrastReview')


def _mezcla_iframes(datos):
    """Integra los escaneos de iframes same-origin en el informe principal."""
    subs = datos.pop('iframes_data', [])
    datos['iframes_anidados'] = len(subs)
    for sub in subs:
        pref = 'iframe: '
        for k in _LISTAS_IFRAME:
            for item in (sub.get(k) or [])[:12]:
                if isinstance(item, dict):
                    item = dict(item, ej=pref + str(item.get('ej', item)))
                else:
                    item = pref + str(item)
                datos.setdefault(k, [])
                if len(datos[k]) < 40:
                    datos[k].append(item)
        for k in _CONTADORES_IFRAME:
            datos[k] = datos.get(k, 0) + (sub.get(k) or 0)


def audit_dom_url(url, timeout=45, lang='es'):
    """Carga la URL en Chromium y devuelve el informe renderizado.

    Escanea también los iframes same-origin (hasta 4) y contrasta los estados
    :hover reales de los primeros controles marcados."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(400)
        except Exception as e:  # noqa: BLE001
            if not page.content() or page.url in ('about:blank', ''):
                nav.close()
                return {'error': f'no se pudo cargar: {e}'}
        try:
            datos = page.evaluate(_JS, MAX_EJEMPLOS)
            # iframes same-origin: mismo colector por frame
            subs = []
            for fr in page.frames[1:5]:
                try:
                    subs.append(fr.evaluate(_JS, MAX_EJEMPLOS))
                except Exception:  # noqa: BLE001
                    continue  # cross-origin o no escaneable
            datos['iframes_data'] = subs
            # hover real sobre los controles marcados
            hover = []
            for i in range(min(10, int(datos.get('marks', 0)))):
                try:
                    page.hover(f'[data-a11yidx="{i}"]', timeout=1000)
                    r = page.evaluate(_JS_HOVER, i)
                    if r and r['ratio'] < 3:
                        hover.append(dict(r, ej=f'hover #{i}'))
                except Exception:  # noqa: BLE001
                    continue
            datos['hover'] = hover
        finally:
            nav.close()
    _mezcla_iframes(datos)
    return audit_dom(datos, url, lang=lang)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('url')
    ap.add_argument('--lang', default='es', choices=['es', 'en'])
    ap.add_argument('--timeout', type=int, default=45)
    a = ap.parse_args(argv)
    try:
        res = audit_dom_url(a.url, timeout=a.timeout, lang=a.lang)
    except ImportError:
        print(json.dumps({'error': 'Playwright no instalado: pip install playwright && playwright install chromium'}))
        return 1
    except Exception as e:  # noqa: BLE001
        print(json.dumps({'error': str(e)}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
