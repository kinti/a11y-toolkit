#!/usr/bin/env python3
"""RENDERED accessibility audit via Playwright (what static HTML cannot see).

a11y_audit_dom loads the URL in Chromium and evaluates the computed DOM:
text contrast against effective backgrounds with alpha compositing, 24×24
target size (WCAG 2.2's 2.5.8), focus indicator heuristic, :focus/:hover state
contrast, open shadow DOM, same-origin iframes — plus the static signals on
the live DOM.

Requires local Playwright: pip install playwright && playwright install chromium.
Honest heuristics — a filter, not a verdict.

CLI:
  a11ydom.py https://example.com [--lang es] [--timeout 45]
"""

import argparse
import json
import re
import sys

from a11yaudit import CRIT, T, calcular_score

# browser pool: Chromium reutilizable entre llamadas consecutivas
_POOL = {'playwright': None, 'browser': None}


def _get_browser(pw, headless=True):
    """Devuelve un browser del pool (o crea uno si no existe)."""
    if _POOL['browser'] is None or not _POOL['browser'].is_connected():
        _POOL['browser'] = pw.chromium.launch(headless=headless)
    return _POOL['browser']


def _close_pool():
    """Cierra el pool (llamar al terminar el proceso o bajo demanda)."""
    if _POOL['browser']:
        try:
            _POOL['browser'].close()
        except Exception:
            pass
    _POOL['browser'] = None
    _POOL['playwright'] = None

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
        'form_error_missing': ('{n} formularios enviados con datos inválidos SIN identificación de error: '
                               'nada de aria-invalid, aria-describedby con texto, role=alert ni texto de error (3.3.1).'),
        'form_error_missing_rem': ('Los errores deben describirse en texto y asociarse al campo: aria-invalid="true" + '
                                   'un mensaje enlazado con aria-describedby (o un resumen con focus al enviar). '
                                   'El borde rojo solo no es un error identificado.'),
        'form_error_no_suggestion': ('{n} campos con error identificado pero sin sugerencia de corrección '
                                     'detectable (3.3.3). Revisar.'),
        'form_error_no_suggestion_rem': ('Cuando la corrección se conoce, dila: «Usa DD/MM/AAAA», no «Fecha inválida» (3.3.3). '
                                         'Sugerimos patrón: texto con formato/ejemplo cerca del campo.'),
        'form_navigated': 'El formulario navega al enviar; el comportamiento del error no es medible en la página ({ej}).',
        'form_navigated_rem': 'Captura la página de destino o prueba con un intercepto; el juicio del error requiere ver el DOM tras el envío.',
        'focus_navigates': 'Al recibir foco, {ej} provocó un cambio de contexto (URL cambió a {url}) — 3.2.1.',
        'focus_navigates_rem': 'Recibir foco nunca debe cambiar el contexto (3.2.1): revisa focus→location.href, focus→form.submit(), focus→window.open().',
        'input_navigates': 'Cambiar {ej} provocó navegación automática (URL: {url}) — 3.2.2.',
        'input_navigates_rem': 'Cambiar un ajuste nunca debe navegar sin petición del usuario (3.2.2): añade un botón «Aplicar» o confirma antes de enviar.',
        'hover_not_dismissible': '{n} tooltips/overlays aparecen al hover/focus que NO se cierran con Escape (1.4.13).',
        'hover_not_dismissible_rem': 'El contenido emergente debe poder cerrarse con Escape sin mover el puntero (1.4.13): añade keydown Escape que oculte el tooltip.',
        'focus_obscured': ('{n} controles quedan tapados por elementos fijos/sticky al '
                           'recibir el foco (cabeceras sticky, banners): {det}. Revisar (2.4.11).'),
        'focus_obscured_rem': ('Un elemento fijo no debe ocultar el elemento enfocado (2.4.11, '
                               'nuevo en WCAG 2.2 AA): usa scroll-padding-top igual a la altura '
                               'del header fijo, o hazlo auto-colapsable.'),
        'state_contrast': ('{n} controles con contraste insuficiente en estado :focus/:hover '
                           '(<3:1): {det}. Revisar.'),
        'state_contrast_rem': ('El texto del control también necesita contraste cuando está '
                               'enfocado o con el puntero encima (1.4.3); los controles '
                               'DESACTIVADOS están exentos por WCAG. Ajusta los colores de '
                               ':focus y :hover.'),
        'kbd_trap': ('TRAMPA DE TECLADO: {n} controles atrapados en un ciclo ({ciclo}) y '
                     'Escape no libera. El foco no puede salir (2.1.2).'),
        'kbd_trap_rem': ('Todo componente con foco contenido (modal, menú) debe liberarse con '
                         'Escape (y idealmente clic fuera): ciérralo y devuelve el foco al '
                         'disparador. Pruébalo solo con teclado.'),
        'reflow_fail': ('{n} elementos desbordan a {w}px de ancho (scroll horizontal): {det}. '
                        'Con reflujo correcto, a 320px no hay scroll en una dimensión (1.4.10).'),
        'reflow_fail_rem': ('Usa layouts fluidos (flex/grid, max-width en vez de width fija) y '
                            'media queries: el contenido debe reflujo a 320px sin scroll '
                            'horizontal. Los excepciones: tablas de datos, mapas, gráficos.'),
        'limites': ('Auditoría renderizada: heurística honesta, no sustituye lector de pantalla '
                    'ni revisión manual. Contraste calculado sobre fondos computados; los casos '
                    'con imagen de fondo se reportan como «revisar». 2.5.8 admite excepciones '
                    '(inline equivalente, espaciado) que aquí se aproximan.'),
    },
    'en': {
        'form_error_missing': ('{n} forms submitted with invalid data with NO error identification: no '
                               'aria-invalid, aria-describedby with text, role=alert, or error text (3.3.1).'),
        'form_error_missing_rem': ('Errors must be described in text and associated with the field: '
                                   'aria-invalid="true" + a message linked via aria-describedby (or a summary '
                                   'that takes focus on submit). A red border alone is not an identified error.'),
        'form_error_no_suggestion': ('{n} fields with an identified error but no detectable correction '
                                     'suggestion (3.3.3). Review.'),
        'form_error_no_suggestion_rem': ('When the correction is known, say it: "Use DD/MM/YYYY", not "Invalid date" (3.3.3). '
                                         'Suggestion pattern: format/example text near the field.'),
        'form_navigated': 'The form navigates on submit; error behavior is not measurable in-page ({ej}).',
        'form_navigated_rem': 'Capture the destination page or intercept the submit; judging errors requires the post-submit DOM.',
        'focus_navigates': 'Receiving focus on {ej} triggered a context change (URL changed to {url}) — 3.2.1.',
        'focus_navigates_rem': 'Receiving focus must never change context (3.2.1): check focus→location.href, focus→form.submit(), focus→window.open().',
        'input_navigates': 'Changing {ej} triggered automatic navigation (URL: {url}) — 3.2.2.',
        'input_navigates_rem': 'Changing a setting must never navigate without user request (3.2.2): add an "Apply" button or confirm before submitting.',
        'hover_not_dismissible': '{n} tooltips/overlays appearing on hover/focus that do NOT dismiss on Escape (1.4.13).',
        'hover_not_dismissible_rem': 'Hover/focus-triggered content must be dismissible with Escape without moving the pointer (1.4.13): add a keydown Escape handler that hides the tooltip.',
        'focus_obscured': ('{n} controls end up hidden behind fixed/sticky elements '
                           'when focused (sticky headers, banners): {det}. Review (2.4.11).'),
        'focus_obscured_rem': ('Author-fixed content must not hide the focused element '
                               '(2.4.11, new in WCAG 2.2 AA): set scroll-padding-top to the '
                               'fixed header height, or make it auto-collapse.'),
        'kbd_trap': ('KEYBOARD TRAP: {n} controls caught in a cycle ({ciclo}) and Escape '
                     'does not release. Focus cannot leave (2.1.2).'),
        'kbd_trap_rem': ('Every focus-containing component (modal, menu) must release with '
                         'Escape (ideally click-outside too): close it and return focus to '
                         'the trigger. Test it with the keyboard alone.'),
        'reflow_fail': ('{n} elements overflow at {w}px width (horizontal scroll): {det}. '
                        'With correct reflow there is no one-dimensional scroll at 320px (1.4.10).'),
        'reflow_fail_rem': ('Use fluid layouts (flex/grid, max-width instead of fixed width) '
                            'and media queries: content must reflow to 320px without '
                            'horizontal scroll. Exceptions: data tables, maps, charts.'),
        'state_contrast': ('{n} controls with insufficient :focus/:hover state contrast '
                           '(<3:1): {det}. Review.'),
        'state_contrast_rem': ('The control text needs contrast when focused or hovered too '
                               '(1.4.3); DISABLED controls are exempt under WCAG. Adjust the '
                               ':focus and :hover colors.'),
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



def _t(lang, key):
    return _TD.get(lang, _TD['es']).get(key) or T.get(lang, T['es']).get(key, key)


# ------------------------------------------------------------------- JS -----
_JS = r'''(maxEj) => {
  const INTER = 'a[href], button, input, select, textarea, summary, [role="button"], [role="link"], [tabindex]';
  const out = { contrast: {}, contrastReview: 0, targets: [], unnamed: [], fields: [],
                imgs: [], iframes: [], headings: [], tabindex: [], ariaHidden: [],
                blank: 0, videos: 0, videoSubs: 0, tables: 0, tableTh: 0,
                focus: [], focusFail: [], focusContrast: [], focusObscured: [], marks: 0,
                ids: {}, lang: null, title: '', viewport: null, refresh: null,
                main: false, skip: false, elements: 0, shadow_roots: 0,
                colorOnly: [], orderInversions: 0, loopingAnims: 0 };
  const fijos = [...document.querySelectorAll('*')].filter(el => {
    const s = getComputedStyle(el);
    return (s.position === 'fixed' || s.position === 'sticky') && s.display !== 'none'
           && el.getBoundingClientRect().height > 8;
  }).slice(0, 12);

  // ---- raíces: document + shadow roots ABIERTOS (tope 20, profundidad 6) ----
  const roots = [document];
  const colecta_raices = (base, prof) => {
    if (prof > 6 || roots.length >= 20) return;
    for (const el of base.querySelectorAll('*')) {
      if (el.shadowRoot) { roots.push(el.shadowRoot); colecta_raices(el.shadowRoot, prof + 1); }
    }
  };
  try { colecta_raices(document, 0); } catch (e) { /* no bloquear por raíces */ }
  out.shadow_roots = roots.length - 1;
  const deepQ = sel => {
    const acc = [];
    for (const r of roots) {
      for (const el of r.querySelectorAll(sel)) { acc.push(el); if (acc.length >= 600) return acc; }
    }
    return acc;
  };

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
    while (n && depth < 3) {
      if (n === document.body) break;
      if (!n.parentElement && n.getRootNode && n.getRootNode().host) {
        n = n.getRootNode().host;
        p = (n.id ? '#' + n.id : n.tagName.toLowerCase()) + ' ::slotted> ' + p;
        depth++;
        continue;
      }
      if (!n.parentElement) break;
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
      n = n.parentElement || (n.getRootNode && n.getRootNode().host) || null;
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

  // ---- contraste de texto en TODAS las raíces ----
  const fails = new Map();
  const escanea_textos = root => {
    const walker = document.createTreeWalker(root.body || root, NodeFilter.SHOW_TEXT);
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
  };
  for (const r of roots) escanea_textos(r);
  out.contrast = [...fails.values()].slice(0, 40);

  // ---- 1.4.1 use of color: inline links distinguishable ONLY by color ----
  for (const el of deepQ('a[href]')) {
    if (out.colorOnly.length >= 12) break;
    if (!getComputedStyle(el).display.includes('inline')) continue;
    const cont = el.closest('p, li, dd, dt, td, figcaption, blockquote');
    if (!cont || cont.textContent.trim().length < 40) continue;   // needs surrounding prose
    const s = getComputedStyle(el);
    if (s.textDecorationLine.includes('underline') || parseInt(s.fontWeight || '400', 10) >= 600) continue;
    if (el.querySelector('img, svg')) continue;                    // icon = extra cue
    const cl = parseCol(s.color), cp = parseCol(getComputedStyle(cont).color);
    if (cl && cp && ratioOf(cl, cp) < 3)
      out.colorOnly.push(path(el));
  }

  // ---- 1.3.2 meaningful sequence: DOM order vs visual order, same parent ----
  {
    const porPadre = new Map();
    for (const el of deepQ('p, li, h1, h2, h3, h4, h5, h6')) {
      if (porPadre.size > 200) break;
      if (!el.offsetParent) continue;
      const r = el.getBoundingClientRect();
      if (r.height < 4 || r.width < 4) continue;
      const p = el.parentElement;
      if (!p) continue;
      if (!porPadre.has(p)) porPadre.set(p, []);
      porPadre.get(p).push({ top: r.top });
    }
    let inv = 0;
    for (const lista of porPadre.values()) {
      for (let i = 0; i < lista.length - 1; i++)
        if (lista[i + 1].top + 4 < lista[i].top) inv++;   // next-in-DOM clearly above
    }
    out.orderInversions = inv;
  }

  // ---- 2.2.2 computed looping animations (review-only count) ----
  {
    let n = 0;
    for (const r of roots) {
      for (const el of r.querySelectorAll('*')) {
        if (n >= 30) break;
        const cs = getComputedStyle(el);
        if (cs.animationIterationCount === 'infinite' && cs.animationName !== 'none') {
          const durs = (cs.animationDuration || '0s').split(',').map(x => {
            const v = parseFloat(x) || 0; return x.includes('ms') ? v / 1000 : v; });
          if (Math.max(...durs, 0) > 0.15) n++;
        }
      }
    }
    out.loopingAnims = n;
  }

  // ---- target size 2.5.8 (todas las raíces) ----
  for (const el of deepQ(INTER)) {
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
      const root = el.getRootNode();
      const ref = root.getElementById ? root.getElementById(el.getAttribute('aria-labelledby'))
                                      : root.querySelector('#' + CSS.escape(el.getAttribute('aria-labelledby')));
      if (ref) n = (ref.innerText || '').trim();
    }
    if (!n) n = (el.getAttribute('title') || '').trim();
    if (!n && el.tagName === 'INPUT' && ['submit', 'button', 'reset'].includes(el.type)) n = el.value || '';
    if (!n && el.tagName === 'INPUT' && el.type === 'image') n = el.alt || '';
    if (!n && ['A', 'BUTTON', 'SUMMARY'].includes(el.tagName)) {
      n = (el.innerText || '').trim();
      // accname: a descendant image's alt contributes to the link's name
      if (!n) { const im = el.querySelector('img[alt]'); if (im) n = (im.getAttribute('alt') || '').trim(); }
    }
    if (!n && el.tagName === 'IMG') n = el.getAttribute('alt') || '';
    return n.trim();
  };
  for (const el of deepQ('a[href], button, summary, [role="button"], [role="link"]')) {
    if (!vis(el) || el.closest('[aria-hidden="true"]')) continue;
    if (!nameOf(el) && out.unnamed.length < 30) out.unnamed.push(path(el));
  }
  for (const el of deepQ('input, select, textarea')) {
    if (el.type === 'hidden' || el.type === 'submit' || el.type === 'button' || el.type === 'reset') continue;
    if (!vis(el)) continue;
    if (!nameOf(el) && out.fields.length < 30) out.fields.push(path(el));
  }
  for (const el of deepQ('img')) {
    if (!vis(el)) continue;
    if (!el.hasAttribute('alt') && out.imgs.length < 30) out.imgs.push(el.getAttribute('src') || '');
  }
  for (const el of deepQ('iframe')) {
    if (!((el.getAttribute('title') || '').trim() || (el.getAttribute('aria-label') || '').trim())
        && out.iframes.length < 20) out.iframes.push(el.getAttribute('src') || '');
  }

  // ---- estructura ----
  for (const h of deepQ('h1,h2,h3,h4,h5,h6')) {
    out.headings.push({ lvl: +h.tagName[1], text: (h.innerText || '').trim().slice(0, 80) });
  }
  for (const el of deepQ('[tabindex]')) {
    const t = parseInt(el.getAttribute('tabindex') || '0', 10);
    if (t > 0 && out.tabindex.length < 20) out.tabindex.push(path(el));
  }
  for (const r of roots) {
    for (const el of r.querySelectorAll('[aria-hidden="true"]')) {
      if (el.matches(INTER)) {
        if (el.getAttribute('tabindex') !== '-1') out.ariaHidden.push(path(el));
      } else if ([...(el.querySelectorAll(INTER) || [])]
                 .some(d => d.getAttribute('tabindex') !== '-1')) {
        out.ariaHidden.push(path(el));
      }
    }
  }
  for (const el of deepQ('a[target="_blank"]')) {
    const t = (el.innerText || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '');
    if (!/(nueva|nuevo|ventana|pesta|tab\b|window|external|externo|exterior)/i.test(t)) out.blank++;
  }
  for (const el of deepQ('video')) {
    out.videos++;
    if (el.querySelector('track[kind="captions"], track[kind="subtitles"]')) out.videoSubs++;
  }
  for (const el of deepQ('table')) {
    out.tables++;
    if (el.querySelector('th')) out.tableTh++;
  }
  for (const r of roots) {
    for (const el of r.querySelectorAll('[id]')) out.ids[el.id] = (out.ids[el.id] || 0) + 1;
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
  for (const el of deepQ(INTER)) {
    if (mi >= 25) break;
    if (el.type === 'hidden' || !vis(el)) continue;
    try { el.setAttribute('data-a11yidx', String(mi)); } catch (e) { continue; }
    mi++;
  }
  out.marks = mi;

  // ---- foco: indicador visible (heurístico) + contraste en estado focus ----
  const oculto = el => { const r = el.getBoundingClientRect();
    return (r.width <= 2 && r.height <= 2); };
  const stops = deepQ(INTER)
    .filter(el => vis(el) && !el.disabled && el.getAttribute('tabindex') !== '-1'
                  && !oculto(el)).slice(0, 40);
  const activo = () => { let a = document.activeElement;
    while (a && a.shadowRoot && a.shadowRoot.activeElement) a = a.shadowRoot.activeElement;
    return a; };
  const prevFocus = document.activeElement;
  for (const el of stops) {
    try { el.focus(); } catch (e) { /* no enfocable */ }
    if (activo() !== el) {
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
      const rf2 = ratioOf(fgf, bgf);
      if (rf2 < 3 && out.focusContrast.length < 20)
        out.focusContrast.push({ ej: path(el), ratio: Math.round(rf2 * 100) / 100 });
    }
    // (2.4.11 por parada se cubre abajo con la causa raíz)
  }
  // 2.4.11 causa raíz: header fijo arriba sin scroll-padding-top suficiente →
  // saltos de ancla y de foco aterrizan tapados. Determinista y sin falsos
  // negativos de recorridos.
  if (fijos.length && out.focusObscured.length === 0) {
    const sp = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
    const top_fijos = fijos.map(f => f.getBoundingClientRect()).filter(q => q.top <= 20);
    const hmax = top_fijos.length ? Math.max(...top_fijos.map(q => q.height)) : 0;
    if (hmax > sp + 4) {
      out.focusObscured.push('header fijo de ' + Math.round(hmax) + 'px con scroll-padding-top de '
                             + Math.round(sp) + 'px');
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


def audit_dom(datos, url='(rendered)', lang='en'):
    """Agrega los datos JS del DOM en un informe con la misma forma que audit_html."""
    hallazgos = []

    # 1. Contraste real
    fallos = datos.get('contrast') or []
    if fallos:
        det = '; '.join(f"{f['fg']} vs {f['bg']} = {f['ratio']}:1"
                        + (' (grande)' if f['large'] else '') + f" ×{f['n']}"
                        for f in fallos[:4])
        _sobre, _pej = ('sobre', 'p. ej.') if lang == 'es' else ('over', 'e.g.')
        ejemplos = [f"{f['fg']} {_sobre} {f['bg']} → {f['ratio']}:1 ({_pej} {f['ej']})" for f in fallos]
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

    # 2.ter 2.4.11 foco ocultado por fijos
    if datos.get('focusObscured'):
        _agrega(hallazgos, lang, 'media', '2.4.11', 'focus_obscured',
                ejemplos=datos['focusObscured'], n=len(datos['focusObscured']),
                det=', '.join(datos['focusObscured'][:3]))

    # v3.12 rendered-only partial signals (review-severity honesty)
    if datos.get('colorOnly'):
        _agrega(hallazgos, lang, 'baja', '1.4.1', 'color_only_link',
                ejemplos=datos['colorOnly'], n=len(datos['colorOnly']))
    if datos.get('orderInversions'):
        _agrega(hallazgos, lang, 'baja', '1.3.2', 'dom_visual_order',
                n=datos['orderInversions'])
    if datos.get('loopingAnims'):
        _agrega(hallazgos, lang, 'baja', '2.2.2', 'motion_moving',
                ejemplos=[], n=datos['loopingAnims'],
                ej=f"{datos['loopingAnims']} looping CSS animations")
    if datos.get('spacingClipped'):
        _agrega(hallazgos, lang, 'media', '1.4.12', 'text_spacing_clip',
                ejemplos=datos['spacingClipped'], n=len(datos['spacingClipped']))

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
        'shadow_roots': datos.get('shadow_roots', 0),
        'score': calcular_score(hallazgos),
        'score_nota': _t(lang, 'score_nota'),
        'elementos_interactivos': datos.get('elements', 0),
        'resumen': resumen,
        'hallazgos': hallazgos,
        'limites': _t(lang, 'limites'),
    }


_JS_FORM_FILL = r'''() => {
  // Fill every validatable field with INVALID data, then submit. Returns what we touched.
  const CAMPOS = 'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]):not([type=image]), select, textarea';
  const invalidos = {email: 'not-an-email', url: 'not-a-url', number: 'abc', tel: 'no-phone'};
  const tocados = [];
  for (const f of document.querySelectorAll('form')) {
    if (f.querySelector('[novalidate]') || f.hasAttribute('novalidate')) { /* still try: JS may validate */ }
    for (const el of f.querySelectorAll(CAMPOS)) {
      if (el.disabled || el.readOnly) continue;
      const tipo = (el.type || el.tagName.toLowerCase()).toLowerCase();
      const exige = el.required || el.getAttribute('aria-required') === 'true'
        || el.hasAttribute('pattern') || el.hasAttribute('minlength') || el.hasAttribute('min');
      let val = '';
      if (invalidos[tipo]) val = invalidos[tipo];
      else if (tipo === 'checkbox' || tipo === 'radio') { continue; }
      else if (!exige) continue;
      else val = tipo === 'number' ? 'abc' : '';
      el.value = val;
      el.dispatchEvent(new Event('input', {bubbles: true}));
      el.dispatchEvent(new Event('change', {bubbles: true}));
      tocados.push({form: f.id || f.action || f.getAttribute('class') || 'form',
                    campo: (el.name || el.id || tipo).toString().slice(0, 40)});
    }
    const btn = f.querySelector('button[type=submit], input[type=submit], button:not([type])');
    if (btn) btn.click(); else if (f.requestSubmit) f.requestSubmit();
  }
  return tocados;
}'''

_JS_FORM_STATE = r'''() => {
  // After submit: how were errors identified and announced?
  const RX_ERR = /(error|invalid|required|obligatorio|requerido|inv[áa]lido|incorrecto|falta|requerid)/i;
  const RX_SUG = /(format|example|ejemplo|usa |use |dd\/mm|mm\/dd|pattern|como |like |must be|debe)/i;
  const out = { forms: [], alerts: 0 };
  for (const a of document.querySelectorAll('[role=alert], [aria-live]')) {
    if ((a.innerText || '').trim() && RX_ERR.test(a.innerText)) out.alerts++;
  }
  const CAMPOS = 'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]):not([type=image]), select, textarea';
  for (const f of document.querySelectorAll('form')) {
    const info = { form: f.id || f.action || 'form', campos: 0, identificados: 0,
                   sugeridos: 0, nativos: 0 };
    for (const el of f.querySelectorAll(CAMPOS)) {
      if (el.disabled) continue;
      info.campos++;
      let identificado = false, sugerido = false;
      if (el.getAttribute('aria-invalid') === 'true') identificado = true;
      const db = el.getAttribute('aria-describedby');
      if (db) for (const id of db.split(/\s+/)) {
        const r = document.getElementById(id);
        if (r && (r.innerText || '').trim()) { identificado = true; if (RX_SUG.test(r.innerText)) sugerido = true; }
      }
      const cerca = el.closest('div, p, li, td, fieldset');
      if (cerca && RX_ERR.test(cerca.innerText || '')) {
        identificado = true;
        const lbl = el.labels && el.labels[0] ? el.labels[0].innerText : '';
        if (RX_SUG.test(cerca.innerText || '') ) sugerido = true;
      }
      // native validation only identifies errors when the form lets it fire
      // (a novalidate form never shows the browser message — the API lying ≠ UX)
      if (!f.noValidate && el.willValidate !== undefined && !el.checkValidity() && el.validationMessage) {
        identificado = true; info.nativos++;
      }
      if (identificado) info.identificados++;
      if (sugerido) info.sugeridos++;
    }
    out.forms.push(info);
  }
  return out;
}'''

def audit_forms(url, timeout=45, lang='en', auth_state=None):
    """3.3.1 Error Identification / 3.3.3 Error Suggestion — the guided flow:
    fill every validatable field with INVALID data, really submit, then judge
    how errors are identified and announced in the post-submit DOM."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(400)
        except Exception as e:  # noqa: BLE001
            nav.close()
            return {'error': _t(lang, 'descarga_error').format(e=e)}
        url_antes = page.url
        tocados = page.evaluate(_JS_FORM_FILL)
        page.wait_for_timeout(900)
        navegado = page.url.split('#')[0] != url_antes.split('#')[0]
        estado = None if navegado else page.evaluate(_JS_FORM_STATE)
        nav.close()

    hallazgos = []

    def agrega(sev, code, key, **fmt):
        hallazgos.append({'severidad': sev, 'criterio': CRIT.get(lang, CRIT['es']).get(code, code),
                          'senal': key, 'hallazgo': _t(lang, key).format(**fmt),
                          'remediacion': _t(lang, key + '_rem').format(**fmt)})

    if navegado:
        agrega('baja', '3.3.1', 'form_navigated', ej=page.url if False else 'submit')
    elif tocados and estado is not None:
        sin_identificar = [f['form'] for f in estado['forms']
                           if f['campos'] and f['identificados'] == 0 and f['nativos'] == 0
                           and estado['alerts'] == 0]
        if sin_identificar:
            agrega('alta', '3.3.1', 'form_error_missing', n=len(sin_identificar))
        campos_err = sum(f['identificados'] for f in estado['forms'])
        campos_sug = sum(f['sugeridos'] for f in estado['forms'])
        if campos_err > 0 and campos_sug == 0:
            agrega('baja', '3.3.3', 'form_error_no_suggestion', n=campos_err)

    from a11yaudit import calcular_score
    return {
        'url': url, 'modo': 'forms',
        'campos_invalidados': len(tocados),
        'detalle': tocados[:10],
        'score': calcular_score(hallazgos),
        'resumen': {s_: sum(1 for h in hallazgos if h['severidad'] == s_)
                    for s_ in ('alta', 'media', 'baja')},
        'hallazgos': hallazgos,
        'limites': _t(lang, 'limites'),
    }


def sr_transcript(url, timeout=45, lang='en', auth_state=None):
    """Screen reader transcript: what a blind user HEARS on this page.

    Walks the accessibility tree linearly (the order a screen reader reads)
    and outputs the announcement text with roles, names and states — the
    linearized reading experience. This is what `a11y_snapshot` captures as
    structure; this function returns it as prose an agent can READ and
    understand from a blind user's perspective.
    """
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    nav = _get_browser(pw)
    ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
    page = ctx.new_page() if auth_state else nav.new_page()
    try:
        page.goto(url, wait_until='load', timeout=timeout * 1000)
        page.wait_for_timeout(400)
    except Exception as e:
        ctx.close()
        _close_pool()
        return {'error': str(e)[:100]}

    try:
        arbol = page.locator('body').aria_snapshot()
    except Exception:
        arbol = None
    try:
        ctx.close()
    except Exception:
        pass

    if not arbol:
        return {'url': url, 'modo': 'sr-transcript',
                'error': 'accessibility tree not available (Playwright >= 1.49 required)'}

    # parse the YAML-like snapshot into linearized announcements
    import re
    anuncios = []
    for linea in arbol.split('\n'):
        stripped = linea.strip()
        if not stripped.startswith('- '):
            continue
        # quitar el guion inicial; el resto es el anuncio
        anuncio = stripped[2:].rstrip(':')
        if anuncio:
            anuncios.append(anuncio)

    return {
        'url': url,
        'modo': 'sr-transcript',
        'anuncios': anuncios[:200],  # cap
        'total': len(anuncios),
        'arbol_raw': arbol[:5000] if len(arbol) > 5000 else arbol,
        'nota': ('Linearized announcement order — what a screen reader user hears. '
                 'Roles and names as computed by the browser. Use this to understand '
                 'the page from a blind user\'s perspective.'),
    }


_JS_HOVER_TEST = r'''() => {
  // find elements that show tooltips/overlays on hover
  const candidatos = [];
  for (const el of document.querySelectorAll('[title], [data-tooltip], [aria-describedby]')) {
    if (candidatos.length >= 10) break;
    const r = el.getBoundingClientRect();
    if (r.width > 10 && r.height > 10 && r.top >= 0 && r.top < innerHeight) {
      candidatos.push({
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        desc: el.getAttribute('aria-describedby') || el.getAttribute('title') || '',
        rect: {x: r.x, y: r.y, w: r.width, h: r.height}
      });
    }
  }
  return candidatos;
}'''

def audit_hover(url, timeout=45, lang='en', auth_state=None):
    """1.4.13 Content on Hover or Focus: do tooltips dismiss on Escape?"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(400)
        except Exception as e:
            nav.close()
            return {'error': str(e)[:100]}

        candidatos = page.evaluate(_JS_HOVER_TEST)
        no_dismissibles = []
        for c in candidatos[:8]:
            try:
                # hover sobre el elemento
                sel = f'{c["tag"]}#{c["id"]}' if c['id'] else c['tag']
                page.hover(sel, timeout=2000)
                page.wait_for_timeout(400)
                # ¿apareció algo?
                visibles_antes = page.evaluate(
                    "() => document.querySelectorAll('[role=tooltip], [class*=tooltip], [class*=popover]:not([hidden])').length")
                if visibles_antes == 0:
                    continue  # no tooltip → no aplica
                # Escape
                page.keyboard.press('Escape')
                page.wait_for_timeout(300)
                visibles_despues = page.evaluate(
                    "() => document.querySelectorAll('[role=tooltip], [class*=tooltip], [class*=popover]:not([hidden])').length")
                if visibles_despues == visibles_antes:
                    no_dismissibles.append(f'{c["tag"]}#{c["id"] or "no-id"}')
            except Exception:
                continue
        nav.close()

    hallazgos = []
    if no_dismissibles:
        from a11yaudit import calcular_score
        hallazgos.append({
            'severidad': 'baja', 'criterio': CRIT.get(lang, CRIT['es']).get('1.4.13', '1.4.13'),
            'senal': 'hover_not_dismissible',
            'hallazgo': _t(lang, 'hover_not_dismissible').format(n=len(no_dismissibles)),
            'remediacion': _t(lang, 'hover_not_dismissible_rem'),
            'ejemplos': no_dismissibles[:4]})
        return {'url': url, 'modo': 'hover', 'score': calcular_score(hallazgos),
                'resumen': {'alta': 0, 'media': 0, 'baja': len(hallazgos)},
                'hallazgos': hallazgos}
    return {'url': url, 'modo': 'hover', 'score': 100,
            'resumen': {'alta': 0, 'media': 0, 'baja': 0}, 'hallazgos': []}


_JS_SPACING = r'''() => {
  // WCAG 1.4.12 Text Spacing: the documented override set, applied globally,
  // then measure which texts get clipped by height-constrained containers.
  const css = document.createElement('style');
  css.id = 'a11y-spacing-1412';
  css.textContent = '*{line-height:1.5!important;letter-spacing:0.12em!important;'
    + 'word-spacing:0.16em!important} p{margin-bottom:2em!important}';
  document.head.appendChild(css);
  const clip = [];
  for (const el of document.querySelectorAll('p, li, h1, h2, h3, h4, h5, h6, a, span, label')) {
    if (clip.length >= 15) break;
    if (!el.offsetParent) continue;
    const s = getComputedStyle(el);
    const clipped = (s.overflow === 'hidden' || s.overflowY === 'hidden')
                    && el.scrollHeight > el.clientHeight + 3;
    if (clipped) clip.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : ''));
  }
  css.remove();
  return clip;
}'''

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


_JS_OVERFLOW = r'''() => {
  const vw = document.documentElement.clientWidth;
  const malos = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.right > vw + 8 && r.width > 8) {
      const s = getComputedStyle(el);
      if (s.position === 'fixed' || s.position === 'absolute') continue;
      if (malos.length < 8) malos.push({ ej: el.tagName.toLowerCase()
            + (el.id ? '#' + el.id : '')
            + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : ''),
          w: Math.round(r.width) });
    }
  }
  return { vw, scroll: document.documentElement.scrollWidth, malos };
}'''


def audit_reflow(url, timeout=45, lang='en', auth_state=None):
    """Reflujo 320px — criterio 1.4.10 (AA), la comprobación que ni axe ni
    Lighthouse automatizan. Nota de método: el estándar define el reflujo como
    «320 CSS px, equivalente a 1280px al 400% de zoom», y el zoom real del
    navegador RE-HACE el layout a ese ancho — por eso la medición correcta es
    un viewport de 320px, no emular zoom con CSS (validado empíricamente:
    el truco de zoom CSS marca en falso páginas sanas porque no re-lleva a cabo
    el layout)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={'width': 1280, 'height': 800})
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(300)
        except Exception as e:  # noqa: BLE001
            nav.close()
            return {'error': f'no se pudo cargar: {e}'}

        page.set_viewport_size({'width': 320, 'height': 800})
        page.wait_for_timeout(500)
        r320 = page.evaluate(_JS_OVERFLOW)
        nav.close()

    hallazgos = []

    def agrega(sev, code, key, ejemplos, **fmt):
        hallazgos.append({'severidad': sev, 'criterio': CRIT.get(lang, CRIT['es']).get(code, code),
                          'senal': key, 'hallazgo': _t(lang, key).format(**fmt),
                          'remediacion': _t(lang, key + '_rem').format(**fmt),
                          'ejemplos': ejemplos[:6]})

    ok320 = r320['scroll'] <= r320['vw'] + 1
    if not ok320:
        agrega('alta', '1.4.10', 'reflow_fail',
               [f"{m['ej']} ({m['w']}px)" for m in r320['malos']],
               n=len(r320['malos']), w=r320['vw'],
               det=', '.join(f"{m['ej']} ({m['w']}px)" for m in r320['malos'][:3]))

    from a11yaudit import calcular_score
    return {
        'url': url,
        'modo': 'reflow',
        'score': calcular_score(hallazgos),
        'resumen': {s_: sum(1 for h in hallazgos if h['severidad'] == s_)
                    for s_ in ('alta', 'media', 'baja')},
        'mediciones': {'reflow_320': {'scroll': r320['scroll'], 'viewport': r320['vw'],
                                      'ok': ok320}},
        'hallazgos': hallazgos,
        'limites': _t(lang, 'limites'),
    }


_JS_STOP = r"""(i) => {
  let a = document.activeElement;
  while (a && a.shadowRoot && a.shadowRoot.activeElement) a = a.shadowRoot.activeElement;
  if (!a || a === document.body || a === document.documentElement) return null;
  if (a.tagName === 'IFRAME') return 'iframe:' + ((a.src || '').slice(0, 50));
  if (!a.hasAttribute('data-a11ystop')) {
    a.setAttribute('data-a11ystop', String(i));
    const ruta = a.tagName.toLowerCase() + (a.id ? '#' + a.id : '')
      + (a.innerText && a.innerText.trim() ? ' "' + a.innerText.trim().slice(0, 24) + '"' : '');
    a.setAttribute('data-a11yruta', ruta);
  }
  return parseInt(a.getAttribute('data-a11ystop'), 10);
}"""

_STOP_META = r"""(i) => {
  const el = document.querySelector('[data-a11ystop="' + i + '"]');
  return el ? el.getAttribute('data-a11yruta') : ('parada ' + i);
}"""


def audit_keyboard(url, max_pasos=60, lang='en', timeout=45, auth_state=None):
    """Detección de TRAMPAS DE TECLADO (2.1.2) con Tab real.

    Recorre hasta max_pasos tabulaciones reales en Chromium, registra la
    secuencia de paradas, detecta ciclos (el patrón de un modal) y comprueba si
    ESCAPE libera el ciclo. Un modal que cicla y suelta con Escape es correcto;
    uno que no suelta es trampa — hallazgo 'alta'.
    """
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(400)
        except Exception as e:  # noqa: BLE001
            nav.close()
            return {'error': f'no se pudo cargar: {e}'}

        page.evaluate("document.querySelectorAll('[data-a11ystop]').forEach(e => {"
                      " e.removeAttribute('data-a11ystop'); e.removeAttribute('data-a11yruta'); })")
        url_antes = page.url
        seq = []
        rutas = {}
        for i in range(max_pasos):
            page.keyboard.press('Tab')
            try:
                stop = page.evaluate(_JS_STOP, i)
            except Exception:  # noqa: BLE001
                # execution context destroyed = LA NAVEGACIÓN OCURRIÓ al enfocar (3.2.1)
                break
            if stop is None:
                break
            seq.append(stop)
            if stop not in rutas:
                rutas[stop] = page.evaluate(_STOP_META, stop)
        # detección de ciclo: el final de la secuencia se repite con periodo p
        ciclo = None
        for p_ in range(1, min(12, len(seq) // 2) + 1):
            if seq[-p_:] == seq[-2 * p_:-p_] and len(set(seq[-p_:])) >= 1:
                # exige al menos 2 repeticiones completas del periodo
                reps = sum(1 for k in range(len(seq) - p_, 0, -p_)
                           if seq[k:k + p_] == seq[-p_:])
                if reps >= 2:
                    ciclo = seq[-p_:]
                    break

        # 3.2.1: ¿el foco provocó navegación? (context destroyed = navegación)
        foco_navego = None
        try:
            if page.url != url_antes:
                foco_navego = page.url
        except Exception:
            foco_navego = url_antes + ' → (navigated away)'

        # 3.2.2: ¿un select provoca navegación al cambiar?
        input_navego = None
        input_elem = None
        if not foco_navego:
            try:
                sel = page.query_selector('select')
                if sel:
                    opts = sel.query_selector_all('option')
                    if len(opts) > 1:
                        url_pre = page.url
                        sel.select_option(index=1)
                        page.wait_for_timeout(600)
                        if page.url != url_pre:
                            input_navego = page.url
                            input_elem = 'select'
            except Exception:
                pass

        esc_libera = None
        if ciclo and not foco_navego:
            try:
                en_ciclo = set(ciclo)
                page.keyboard.press('Escape')
                page.wait_for_timeout(150)
                for _ in range(3):
                    page.keyboard.press('Tab')
                    page.wait_for_timeout(80)
                    stop = page.evaluate(_JS_STOP, len(seq))
                    if stop is None or stop not in en_ciclo:
                        esc_libera = True
                        break
                else:
                    esc_libera = False
            except Exception:
                esc_libera = None
        try:
            nav.close()
        except Exception:
            pass

    hallazgos = []
    if foco_navego:
        hallazgos.append({
            'severidad': 'alta', 'criterio': CRIT.get(lang, CRIT['es']).get('3.2.1', '3.2.1'),
            'senal': 'focus_navigates',
            'hallazgo': _t(lang, 'focus_navigates').format(ej='un elemento', url=foco_navego[:60]),
            'remediacion': _t(lang, 'focus_navigates_rem')})
    if input_navego:
        hallazgos.append({
            'severidad': 'alta', 'criterio': CRIT.get(lang, CRIT['es']).get('3.2.2', '3.2.2'),
            'senal': 'input_navigates',
            'hallazgo': _t(lang, 'input_navigates').format(ej=input_elem, url=input_navego[:60]),
            'remediacion': _t(lang, 'input_navigates_rem')})
    if ciclo and esc_libera is False:
        elems = [rutas.get(i, f'parada {i}') for i in ciclo]
        hallazgos.append({
            'severidad': 'alta', 'criterio': CRIT.get(lang, CRIT['es']).get('2.1.2', '2.1.2'),
            'senal': 'kbd_trap', 'hallazgo': _t(lang, 'kbd_trap').format(
                n=len(ciclo), ciclo=' ↔ '.join(elems)),
            'remediacion': _t(lang, 'kbd_trap_rem'),
            'ejemplos': elems,
        })
    from a11yaudit import calcular_score
    return {
        'url': url,
        'modo': 'keyboard',
        'score': calcular_score(hallazgos),
        'resumen': {s_: sum(1 for h in hallazgos if h['severidad'] == s_)
                    for s_ in ('alta', 'media', 'baja')},
        'pasos': len(seq),
        'paradas': [rutas.get(i, f'parada {i}') for i in seq],
        'ciclo': {'detectado': bool(ciclo),
                  'elementos': [rutas.get(i, f'parada {i}') for i in ciclo] if ciclo else [],
                  'escape_libera': esc_libera},
        'hallazgos': hallazgos,
        'limites': ('Recorrido con Tab real en Chromium (tope {n} pasos). El foco dentro de '
                    'iframes entre dominios no es rastreable y se marca como tal. Un ciclo '
                    'con Escape operativo (modal correcto) NO se reporta como hallazgo.'
                    ).format(n=max_pasos),
    }


def audit_dom_url(url, timeout=45, lang='en', auth_state=None):
    """Carga la URL en Chromium y devuelve el informe renderizado.

    Escanea también los iframes same-origin (hasta 4) y contrasta los estados
    :hover reales de los primeros controles marcados. auth_state: ruta a un
    storage_state de Playwright (cookies/localStorage exportados con la sesión
    iniciada) para auditar detrás de login."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(400)
        except Exception as e:  # noqa: BLE001
            if not page.content() or page.url in ('about:blank', ''):
                nav.close()
                return {'error': f'no se pudo cargar: {e}'}
        try:
            datos = page.evaluate(_JS, MAX_EJEMPLOS)
            # 1.4.12: inject the WCAG spacing overrides, count clipped texts
            datos['spacingClipped'] = page.evaluate(_JS_SPACING)
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
            try:
                ctx.close()
            except Exception:
                pass
    _mezcla_iframes(datos)
    return audit_dom(datos, url, lang=lang)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('url')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
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


def reflow_main(argv):
    ap = argparse.ArgumentParser(description='Reflujo 320px (1.4.10)')
    ap.add_argument('url')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--timeout', type=int, default=45)
    a = ap.parse_args(argv)
    try:
        res = audit_reflow(a.url, timeout=a.timeout, lang=a.lang)
    except ImportError:
        print(json.dumps({'error': 'Playwright no instalado'}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


def forms_main(argv):
    ap = argparse.ArgumentParser(description='Form errors: fill invalid + submit + judge (3.3.1/3.3.3)')
    ap.add_argument('url')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--timeout', type=int, default=45)
    a = ap.parse_args(argv)
    try:
        res = audit_forms(a.url, timeout=a.timeout, lang=a.lang)
    except ImportError:
        print(json.dumps({'error': 'Playwright not installed'}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


def kbd_main(argv):
    ap = argparse.ArgumentParser(description='Trampas de teclado (2.1.2) con Tab real')
    ap.add_argument('url')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--max-pasos', type=int, default=60)
    a = ap.parse_args(argv)
    try:
        res = audit_keyboard(a.url, max_pasos=a.max_pasos, lang=a.lang)
    except ImportError:
        print(json.dumps({'error': 'Playwright no instalado'}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
