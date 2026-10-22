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

from .a11yaudit import CRIT, T, compute_score
from .contrast import parse_color, decodificar_png, sample_rgb, hexs

# browser pool: Chromium reutilizable entre llamadas consecutivas
_POOL = {'playwright': None, 'browser': None, 'type': None}

# cadena de detección: el primer navegador disponible gana.
# El usuario puede forzar con el parámetro 'browser' (chromium, firefox,
# webkit, chrome, msedge) o dejar 'auto' para que use lo que tenga.
_CHAIN = [
    ('chromium', lambda pw: pw.chromium.launch(headless=True)),
    ('firefox', lambda pw: pw.firefox.launch(headless=True)),
    ('webkit', lambda pw: pw.webkit.launch(headless=True)),
    ('chrome', lambda pw: pw.chromium.launch(channel='chrome', headless=True)),
    ('msedge', lambda pw: pw.chromium.launch(channel='msedge', headless=True)),
]

_BROWSER_POR_PARAM = {
    'chromium': lambda pw: pw.chromium.launch(headless=True),
    'firefox': lambda pw: pw.firefox.launch(headless=True),
    'webkit': lambda pw: pw.webkit.launch(headless=True),
    'chrome': lambda pw: pw.chromium.launch(channel='chrome', headless=True),
    'msedge': lambda pw: pw.chromium.launch(channel='msedge', headless=True),
}


def _detectar_browser(pw, preferido=None):
    """Devuelve (browser, nombre). Usa el preferido si está disponible,
    si no prueba la cadena completa y devuelve el primero que arranque."""
    if preferido and preferido != 'auto':
        fn = _BROWSER_POR_PARAM.get(preferido)
        if fn:
            try:
                br = fn(pw)
                return br, preferido
            except Exception:
                pass
    for name, fn in _CHAIN:
        try:
            br = fn(pw)
            return br, name
        except Exception:
            continue
    raise RuntimeError(
        'ningún navegador disponible. Instala uno: '
        'pip install playwright && playwright install chromium')


def _get_browser(pw, headless=True, preferido=None):
    """Devuelve un browser del pool (o crea uno si no existe)."""
    if _POOL['browser'] is not None and _POOL['browser'].is_connected() and \
            _POOL['type'] == (preferido or 'auto'):
        return _POOL['browser']
    _close_pool()
    br, kind = _detectar_browser(pw, preferido)
    _POOL['browser'] = br
    _POOL['type'] = kind
    return br


def _close_pool():
    """Cierra el pool (llamar al terminar el proceso o bajo demanda)."""
    if _POOL['browser']:
        try:
            _POOL['browser'].close()
        except Exception:
            pass
    _POOL['browser'] = None
    _POOL['playwright'] = None

MAX_EXAMPLES = 6

_TD = {
    'es': {
        'contrast_fail': ('{n} zonas de texto con contraste insuficiente: {det}. '
                          '(fg/fondo computados, con composición de transparencias).'),
        'contrast_fail_rem': ('Sube el contraste a ≥4.5:1 (≥3:1 en texto grande). El fondo '
                              'efectivo ya incluye superposiciones y transparencias; si hay '
                              'imagen de fondo, verifica esa zona a mano.'),
        'contrast_review': '{n} zonas de texto con imagen de fondo o sombra: no calculables, revisar.',
        'contrast_review_rem': ('El contraste sobre imagen de fondo no se pudo medir aquí: usa '
                                'a11y_contrast_image con una captura de esa región o '
                                'a11y_contrast_dom para medirlo directamente desde la página.'),
        'contrast_image_fail': ('{n} zonas de texto sobre imagen/degradado con contraste insuficiente, '
                                'MEDIDO por muestreo real de píxeles: {det}.'),
        'contrast_image_fail_rem': ('Añade un velo/scrim semitransparente sobre la imagen, oscurécela '
                                    'o mueve el texto a una zona segura. El ratio peor marca la zona '
                                    'hostil; si el área que pasa AA no es 100%, el fondo real no es seguro.'),
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
        'forced_colors_svg': '{n} SVG con fill coloreado hardcoded: en forced-colors (Windows High Contrast) el fill cae al heredado y el icono puede volverse invisible.',
        'forced_colors_svg_rem': 'Usa fill="currentColor" (hereda el color del texto que el sistema ya ajusta) o fuerza los keywords del sistema (CanvasText).',
        'reduced_motion_ignored': '{n} animaciones en bucle siguen moviéndose con prefers-reduced-motion activo (antes {n}, ahora {nr}): la preferencia del usuario se ignora (2.2.2).',
        'reduced_motion_ignored_rem': 'Envuelve las animaciones en @media (prefers-reduced-motion: reduce) { animation: none } — o paúsala con la API Animation. El usuario pidió menos movimiento; respóndelo.',
        'state_contrast': ('{n} controles con contraste insuficiente en estado :focus/:hover '
                           '(<3:1): {det}. Revisar.'),
        'state_contrast_rem': ('El texto del control también necesita contraste cuando está '
                               'enfocado o con el puntero encima (1.4.3); los controles '
                               'DESACTIVADOS están exentos por WCAG. Ajusta los colores de '
                               ':focus y :hover.'),
        'kbd_trap': ('TRAMPA DE TECLADO: {n} controles atrapados en un ciclo ({cycle}) y '
                     'Escape no libera. El foco no puede salir (2.1.2).'),
        'kbd_trap_rem': ('Todo componente con foco contenido (modal, menú) debe liberarse con '
                         'Escape (y idealmente clic fuera): ciérralo y devuelve el foco al '
                         'disparador. Pruébalo solo con teclado.'),
        'reflow_fail': ('{n} elementos desbordan a {w}px de ancho (scroll horizontal): {det}. '
                        'Con reflujo correcto, a 320px no hay scroll en una dimensión (1.4.10).'),
        'reflow_fail_rem': ('Usa layouts fluidos (flex/grid, max-width en vez de width fija) y '
                            'media queries: el contenido debe reflujo a 320px sin scroll '
                            'horizontal. Los excepciones: tablas de datos, mapas, gráficos.'),
        'limits': ('Auditoría renderizada: heurística honesta, no sustituye lector de pantalla '
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
        'kbd_trap': ('KEYBOARD TRAP: {n} controls caught in a cycle ({cycle}) and Escape '
                     'does not release. Focus cannot leave (2.1.2).'),
        'kbd_trap_rem': ('Every focus-containing component (modal, menu) must release with '
                         'Escape (ideally click-outside too): close it and return focus to '
                         'the trigger. Test it with the keyboard alone.'),
        'reflow_fail': ('{n} elements overflow at {w}px width (horizontal scroll): {det}. '
                        'With correct reflow there is no one-dimensional scroll at 320px (1.4.10).'),
        'reflow_fail_rem': ('Use fluid layouts (flex/grid, max-width instead of fixed width) '
                            'and media queries: content must reflow to 320px without '
                            'horizontal scroll. Exceptions: data tables, maps, charts.'),
        'forced_colors_svg': '{n} SVGs with hardcoded colored fill: under forced-colors (Windows High Contrast) the fill falls back to inherited and the icon can turn invisible.',
        'forced_colors_svg_rem': 'Use fill="currentColor" (inherits text color, which the system already adjusts) or the system keywords (CanvasText).',
        'reduced_motion_ignored': '{n} looping animations still run with prefers-reduced-motion set (before {n}, after {nr}): the user\'s preference is ignored (2.2.2).',
        'reduced_motion_ignored_rem': 'Wrap animations in @media (prefers-reduced-motion: reduce) { animation: none } — or pause via the Animation API. The user asked for less motion; honor it.',
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
        'contrast_review_rem': ('Contrast over a background image could not be measured here: use '
                                'a11y_contrast_image with a screenshot of that region, or '
                                'a11y_contrast_dom to measure it directly from the page.'),
        'contrast_image_fail': ('{n} text areas over an image/gradient with insufficient contrast, '
                                'MEASURED by real pixel sampling: {det}.'),
        'contrast_image_fail_rem': ('Add a semi-transparent scrim over the image, darken it, or move the '
                                    'text to a safe zone. The worst ratio marks the hostile area; if the '
                                    'AA-passing area is not 100%, the real background is not safe.'),
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
        'limits': ('Rendered audit: honest heuristics, no substitute for a screen reader or '
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
  const out = { contrast: {}, contrastReview: 0, contrastZones: [], targets: [], unnamed: [], fields: [],
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
      if (bg.image) {
        out.contrastReview++;
        const fa = (fg.a === undefined) ? 1 : fg.a;
        const pxx = parseFloat(s.fontSize);
        const larg = pxx >= 24 || (parseInt(s.fontWeight || '400', 10) >= 700 && pxx >= 18.66);  // spec bold=700 (600 daba 3:1 a texto normal)
        if (out.contrastZones.length < 12 && fa >= 1 && !el.hasAttribute('data-a11ytxt')) {
          const rr = el.getBoundingClientRect();
          if (rr.width > 2 && rr.height > 2 && rr.width <= 1400 && rr.height <= 400) {
            el.setAttribute('data-a11ytxt', out.contrastZones.length);
            out.contrastZones.push({
              i: out.contrastZones.length, ej: path(el),
              fg: 'rgb(' + Math.round(fg.r) + ',' + Math.round(fg.g) + ',' + Math.round(fg.b) + ')',
              px: pxx, large: larg, x: rr.x, y: rr.y, w: rr.width, h: rr.height });
          }
        }
        continue;
      }
      const px = parseFloat(s.fontSize);
      const bold = parseInt(s.fontWeight || '400', 10) >= 700;
      const large = px >= 24 || (bold && px >= 18.66);
      const over_ = (f, b) => { const a = (f.a === undefined) ? 1 : f.a;
        return { r: Math.round(f.r * a + b.r * (1 - a)),
          g: Math.round(f.g * a + b.g * (1 - a)),
          b: Math.round(f.b * a + b.b * (1 - a)), a: 1 }; };
      const r = ratioOf(over_(fg, bg), bg);  // alfa del TEXTO compuesto sobre el fondo
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
    if (s.textDecorationLine.includes('underline') || parseInt(s.fontWeight || '400', 10) >= 700) continue;  // bold spec=700
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
  let interpRects = null;
  for (const el of deepQ(INTER)) {
    out.elements++;
    if (el.type === 'hidden' || !vis(el)) continue;
    const disp = getComputedStyle(el).display;
    if (el.tagName === 'A' && disp.includes('inline') && el.closest('p, li, dd, dt, td, figcaption, blockquote')) continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 2 || r.height <= 2) continue;   // patrón visualmente oculto (skip link)
    if (el.getAttribute('tabindex') === '-1') continue;
    if (r.width < 24 || r.height < 24) {
      // excepción de espaciado (2.5.8): un objetivo menor de 24px PASA si el
      // más cercano está a ≥24px. Vecinos precomputados (no 121 del DOM
      // arbitrarios) y condena temprana: un solo vecino <24px basta.
      if (!interpRects) {
        interpRects = [];
        for (const otro of deepQ(INTER)) {
          if (otro.type === 'hidden' || !vis(otro)) continue;
          const rr = otro.getBoundingClientRect();
          if (rr.width <= 2 && rr.height <= 2) continue;
          interpRects.push({ el: otro, r: rr });
        }
      }
      let sep = Infinity;
      for (const par of interpRects) {
        if (par.el === el) continue;
        const r2 = par.r;
        const dx = Math.max(r.left - r2.right, r2.left - r.right, 0);
        const dy = Math.max(r.top - r2.bottom, r2.top - r.bottom, 0);
        const d = Math.hypot(dx, dy);
        if (d < sep) sep = d;
        if (sep < 24) break;   // condenado: no hace falta seguir
      }
      if (sep < 24 && out.targets.length < 40) out.targets.push(
        { ej: path(el), w: Math.round(r.width), h: Math.round(r.height),
          inline: disp.includes('inline'), spacing: Math.round(sep) });
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
    const borde = ['Top', 'Right', 'Bottom', 'Left'].some(
      k => parseFloat(s['border' + k + 'Width'] || '0') >= 2
           && s['border' + k + 'Style'] !== 'none');
    if (!outline && !shadow && !borde) out.focus.push(path(el));
    const fgf = parseCol(s.color);
    const bgf = bgOf(el);
    if (fgf && !bgf.image) {
      const fs = parseFloat(s.fontSize) || 16;
      const large = fs >= 24 || (fs >= 18.66 && (parseInt(s.fontWeight) || 400) >= 700);
      const rf2 = ratioOf(over(fgf, bgf), bgf);
      if (rf2 < (large ? 3.0 : 4.5) && out.focusContrast.length < 20)
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


def _add(findings, lang, severidad, code, key, examples=None, **fmt):
    h = {'severity': severidad, 'criterion': CRIT.get(lang, CRIT['es']).get(code, code),
         'signal': key,
         'issue': _t(lang, key).format(**fmt), 'remediation': _t(lang, key + '_rem').format(**fmt)}
    if examples:
        h['examples'] = examples[:MAX_EXAMPLES]
    findings.append(h)


def audit_dom(data, url='(rendered)', lang='en', color_scheme='light'):
    """Agrega los datos JS del DOM en un informe con la misma forma que audit_html."""
    findings = []

    # 1. Contraste real
    failures = data.get('contrast') or []
    if failures:
        det = '; '.join(f"{f['fg']} vs {f['bg']} = {f['ratio']}:1"
                        + (' (grande)' if f['large'] else '') + f" ×{f['n']}"
                        for f in failures[:4])
        _over, _eg = ('sobre', 'p. ej.') if lang == 'es' else ('over', 'e.g.')
        examples = [f"{f['fg']} {_over} {f['bg']} → {f['ratio']}:1 ({_eg} {f['ej']})" for f in failures]
        _add(findings, lang, 'high', '1.4.3', 'contrast_fail',
                examples=examples, n=len(failures), det=det)
    medidos = data.get('contrastMeasured') or []
    if medidos:
        offenders = [m for m in medidos
                 if m['measured']['worst_ratio'] < (3.0 if m.get('large') else 4.5)]
        if offenders:
            det = '; '.join(f"{m['ej']} → worst {m['measured']['worst_ratio']}:1, "
                            f"{m['measured']['area_passes_aa_normal_text_4_5']}% passes AA"
                            for m in offenders[:4])
            _add(findings, lang, 'high', '1.4.3', 'contrast_image_fail',
                    examples=[f"{m['ej']} (worst {m['measured']['worst_ratio']}:1)"
                              for m in offenders],
                    n=len(offenders), det=det)
    # las zonas medidas salen del contador de "revisar" (ya están juzgadas)
    restantes = max(0, data.get('contrastReview', 0) - len(medidos))
    if restantes:
        _add(findings, lang, 'low', '1.4.3', 'contrast_review', n=restantes)

    # 2. Target size 2.5.8 (enlaces inline → baja: la excepción de espaciado
    #    probablemente aplica y no es medible aquí; bloques → media)
    targets = data.get('targets') or []
    if targets:
        all_inline = all(t.get('inline') for t in targets)
        det = ', '.join(f"{t['ej']} ({t['w']}×{t['h']})" for t in targets[:4])
        _add(findings, lang, 'low' if all_inline else 'medium', '2.5.8',
                'target_small',
                examples=[f"{t['ej']} ({t['w']}×{t['h']}px)" for t in targets],
                n=len(targets), det=det)

    # 2.bis Estados focus/hover
    states = list(data.get('focusContrast') or []) + list(data.get('hover') or [])
    if states:
        det = ', '.join(f"{e['ej']} = {e['ratio']}:1" for e in states[:4])
        _add(findings, lang, 'medium', '1.4.3', 'state_contrast',
                examples=[f"{e['ej']} = {e['ratio']}:1" for e in states],
                n=len(states), det=det)

    # 2.ter 2.4.11 foco ocultado por fijos
    if data.get('focusObscured'):
        _add(findings, lang, 'medium', '2.4.11', 'focus_obscured',
                examples=data['focusObscured'], n=len(data['focusObscured']),
                det=', '.join(data['focusObscured'][:3]))

    # v3.12 rendered-only partial signals (review-severity honesty)
    if data.get('colorOnly'):
        _add(findings, lang, 'low', '1.4.1', 'color_only_link',
                examples=data['colorOnly'], n=len(data['colorOnly']))
    if data.get('orderInversions'):
        _add(findings, lang, 'low', '1.3.2', 'dom_visual_order',
                n=data['orderInversions'])
    if data.get('loopingAnims'):
        _add(findings, lang, 'low', '2.2.2', 'motion_moving',
                examples=[], n=data['loopingAnims'],
                ej=f"{data['loopingAnims']} looping CSS animations")
    if data.get('spacingClipped'):
        _add(findings, lang, 'medium', '1.4.12', 'text_spacing_clip',
                examples=data['spacingClipped'], n=len(data['spacingClipped']))

    # 3. Foco
    if data.get('focus'):
        _add(findings, lang, 'medium', '2.4.7', 'focus_invisible',
                examples=data['focus'], n=len(data['focus']),
                det=', '.join(data['focus'][:4]))
    if data.get('focusFail'):
        _add(findings, lang, 'low', '2.4.7', 'focus_not_focusable',
                examples=[f['ej'] for f in data['focusFail']],
                n=len(data['focusFail']), det=', '.join(f['ej'] for f in data['focusFail'][:4]))

    # 4. Resto de señales (renderizadas)
    if data.get('unnamed'):
        _add(findings, lang, 'high', '4.1.2', 'ctrl_name',
                examples=data['unnamed'], n=len(data['unnamed']), tag='control')
    if data.get('fields'):
        _add(findings, lang, 'high', '3.3.2', 'field_label',
                examples=data['fields'], n=len(data['fields']))
    if data.get('imgs'):
        _add(findings, lang, 'high', '1.1.1', 'img_no_alt',
                examples=data['imgs'], n=len(data['imgs']))
    if data.get('ariaHidden'):
        _add(findings, lang, 'high', '4.1.2', 'aria_hidden_focusable',
                n=len(data['ariaHidden']), tag='control')
    if not (data.get('lang') or '').strip():
        _add(findings, lang, 'medium', '3.1.1', 'lang_missing')
    if not (data.get('title') or '').strip():
        _add(findings, lang, 'medium', '2.4.2', 'title_missing')
    if data.get('iframes'):
        _add(findings, lang, 'medium', '4.1.2', 'iframe_title',
                examples=data['iframes'], n=len(data['iframes']))
    videos, subframes = data.get('videos', 0), data.get('videoSubs', 0)
    if videos and subframes < videos:
        _add(findings, lang, 'medium', '1.2.2', 'video_captions', n=videos - subframes)
    vp = data.get('viewport') or ''
    if re.search(r'user-scalable\s*=\s*(no|0)', vp, re.I):
        _add(findings, lang, 'high', '1.4.4', 'zoom_no')
    elif (m := re.search(r'maximum-scale\s*=\s*([\d.]+)', vp, re.I)) and float(m.group(1)) < 2:
        _add(findings, lang, 'medium', '1.4.4', 'zoom_max', v=m.group(1))
    if data.get('refresh'):
        m = re.match(r'\s*(\d+)', str(data['refresh']))
        segs = int(m.group(1)) if m else 0
        _add(findings, lang, 'medium' if segs > 0 else 'low', '2.2.1', 'meta_refresh', v=segs)
    if data.get('tabindex'):
        _add(findings, lang, 'medium', '2.4.3', 'tabindex_pos',
                examples=data['tabindex'], n=len(data['tabindex']))
    if not (data.get('main') or data.get('skip')):
        _add(findings, lang, 'medium', '2.4.1', 'no_bypass')

    levels = [h['lvl'] for h in (data.get('headings') or []) if h['text']]
    h1s = sum(1 for h in data.get('headings') or [] if h['lvl'] == 1 and h['text'])
    vacios = sum(1 for h in data.get('headings') or [] if not h['text'])
    if levels:
        if h1s == 0:
            _add(findings, lang, 'medium', '1.3.1', 'no_h1')
        elif h1s > 1:
            _add(findings, lang, 'low', '1.3.1', 'multi_h1', n=h1s)
        prev, saltos = 0, []
        for n in levels:
            if prev and n > prev + 1:
                saltos.append(f'h{prev}→h{n}')
            prev = n
        if saltos:
            _add(findings, lang, 'low', '1.3.1', 'heading_skips',
                    skips=', '.join(saltos[:5]))
    else:
        _add(findings, lang, 'medium', '1.3.1', 'no_headings')
    if vacios:
        _add(findings, lang, 'low', '1.3.1', 'empty_heading', n=vacios)
    tables, con_th = data.get('tables', 0), data.get('tableTh', 0)
    if tables and con_th < tables:
        _add(findings, lang, 'medium', '1.3.1', 'table_no_th', n=tables - con_th)
    if data.get('blank'):
        _add(findings, lang, 'low', '3.2.5', 'blank_no_warning', n=data['blank'])
    dups = sum(1 for k in (data.get('ids') or {}).values() if k > 1)
    if dups:
        _add(findings, lang, 'low', '4.1.2', 'dup_ids', n=dups)

    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])
    summary = {s: sum(1 for h in findings if h['severity'] == s)
               for s in ('high', 'medium', 'low')}
    return {
        'url': url,
        'mode': 'rendered',
        'color_scheme': color_scheme,
        'nested_iframes': data.get('nested_iframes', 0),
        'shadow_roots': data.get('shadow_roots', 0),
        'score': compute_score(findings),
        'score_note': _t(lang, 'score_note'),
        'interactive_elements': data.get('elements', 0),
        'summary': summary,
        'findings': findings,
        'limits': _t(lang, 'limits'),
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

_JS_FORM_PRE = r'''() => {
  // PRE-submit: la ayuda ordinaria que ya existía (describedby, contexto).
  // Sin esto, "Tu email" contaba como identificación de error y "Use…"
  // como sugerencia — la crítica externa lo destapó: ayuda ≠ error.
  const CAMPOS = 'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]):not([type=image]), select, textarea';
  const pre = {};
  for (const el of document.querySelectorAll(CAMPOS)) {
    if (el.disabled) continue;
    const key = (el.name || el.id || el.type) + '@' + (el.form ? (el.form.id || el.form.action || '') : '');
    let dbTxt = '';
    const db = el.getAttribute('aria-describedby');
    if (db) for (const id of db.split(/\s+/)) {
      const r = document.getElementById(id);
      if (r && (r.innerText || '').trim()) dbTxt += r.innerText.trim() + '\n';
    }
    const cerca = el.closest('div, p, li, td, fieldset');
    pre[key] = { db: dbTxt, ctx: cerca ? (cerca.innerText || '').trim().slice(0, 400) : '' };
  }
  return pre;
}'''

_JS_FORM_STATE = r'''(pre) => {
  // After submit: how were errors identified and announced?
  // Identificación = lo NUEVO tras el envío (aria-invalid, texto cambiado en
  // un nodo referido, semántica de alerta) — la ayuda previa NO cuenta.
  const RX_ERR = /(error|invalid|required|obligatorio|requerido|inv[áa]lido|incorrecto|falta|requerid)/i;
  const RX_SUG = /(format|example|ejemplo|usa |use |dd\/mm|mm\/dd|pattern|como |like |must be|debe)/i;
  pre = pre || {};
  const out = { forms: [], alerts: 0 };
  for (const a of document.querySelectorAll('[role=alert], [aria-live]')) {
    if ((a.innerText || '').trim() && RX_ERR.test(a.innerText)) out.alerts++;
  }
  const CAMPOS = 'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]):not([type=image]), select, textarea';
  for (const f of document.querySelectorAll('form')) {
    const info = { form: f.id || f.action || 'form', fields: 0, identified: 0,
                   suggested: 0, native: 0 };
    for (const el of f.querySelectorAll(CAMPOS)) {
      if (el.disabled) continue;
      info.campos++;
      const key = (el.name || el.id || el.type) + '@' + (f.id || f.action || '');
      const antes = pre[key] || {};
      let identificado = false, sugerido = false;
      if (el.getAttribute('aria-invalid') === 'true') identificado = true;
      const db = el.getAttribute('aria-describedby');
      if (db) for (const id of db.split(/\s+/)) {
        const r = document.getElementById(id);
        if (!r) continue;
        const texto = (r.innerText || '').trim();
        if (!texto) continue;
        const nuevoOCambiado = texto !== (antes.db || '').split('\n').find(t => t === texto)
                               && !(antes.db || '').includes(texto);
        const semanticaError = r.matches('[role=alert],[aria-live],.error,.invalid')
                               || r.hasAttribute('aria-errormessage');
        if (nuevoOCambiado || semanticaError) {
          identificado = true;
          if (RX_SUG.test(texto)) sugerido = true;
        }
      }
      const cerca = el.closest('div, p, li, td, fieldset');
      const ctxAhora = cerca ? (cerca.innerText || '').trim().slice(0, 400) : '';
      if (cerca && RX_ERR.test(ctxAhora) && !RX_ERR.test(antes.ctx || '')) {
        identificado = true;
        const nuevaParte = ctxAhora.replace((antes.ctx || ''), '');
        if (RX_SUG.test(nuevaParte)) sugerido = true;
      }
      // native validation only identifies errors when the form lets it fire
      // (a novalidate form never shows the browser message — the API lying ≠ UX)
      if (!f.noValidate && el.willValidate !== undefined && !el.checkValidity() && el.validationMessage) {
        identificado = true; info.native++;
      }
      if (identificado) info.identified++;
      if (sugerido) info.suggested++;
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
            return {'error': _t(lang, 'fetch_error').format(e=e)}
        url_before = page.url
        pre = page.evaluate(_JS_FORM_PRE)
        tocados = page.evaluate(_JS_FORM_FILL)
        page.wait_for_timeout(900)
        navegado = page.url.split('#')[0] != url_before.split('#')[0]
        state = None if navegado else page.evaluate(_JS_FORM_STATE, pre)
        nav.close()

    findings = []

    def add(sev, code, key, **fmt):
        findings.append({'severity': sev, 'criterion': CRIT.get(lang, CRIT['es']).get(code, code),
                          'signal': key, 'issue': _t(lang, key).format(**fmt),
                          'remediation': _t(lang, key + '_rem').format(**fmt)})

    if navegado:
        add('low', '3.3.1', 'form_navigated', ej=page.url if False else 'submit')
    elif tocados and state is not None:
        unidentified = [f['form'] for f in state['forms']
                           if f['fields'] and f['identified'] == 0 and f['native'] == 0
                           and state['alerts'] == 0]
        if unidentified:
            add('high', '3.3.1', 'form_error_missing', n=len(unidentified))
        error_fields = sum(f['identified'] for f in state['forms'])
        suggested_fields = sum(f['suggested'] for f in state['forms'])
        if error_fields > 0 and suggested_fields == 0:
            add('low', '3.3.3', 'form_error_no_suggestion', n=error_fields)

    from .a11yaudit import compute_score
    return {
        'url': url, 'mode': 'forms',
        'invalid_fields': len(tocados),
        'detail': tocados[:10],
        'score': compute_score(findings),
        'summary': {s_: sum(1 for h in findings if h['severity'] == s_)
                    for s_ in ('high', 'medium', 'low')},
        'findings': findings,
        'limits': _t(lang, 'limits'),
    }


def sr_transcript(url, timeout=45, lang='en', auth_state=None, browser='auto'):
    """Screen reader transcript: what a blind user HEARS on this page.

    Walks the accessibility tree linearly (the order a screen reader reads)
    and outputs the announcement text with roles, names and states — the
    linearized reading experience. This is what `a11y_snapshot` captures as
    structure; this function returns it as prose an agent can READ and
    understand from a blind user's perspective.
    """
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    nav = _get_browser(pw, preferido=browser)
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
        tree = page.locator('body').aria_snapshot()
    except Exception:
        tree = None
    try:
        ctx.close()
    except Exception:
        pass

    if not tree:
        return {'url': url, 'mode': 'sr-transcript',
                'error': 'accessibility tree not available (Playwright >= 1.49 required)'}

    # parse the YAML-like snapshot into linearized announcements
    import re
    announcements = []
    for line in tree.split('\n'):
        stripped = line.strip()
        if not stripped.startswith('- '):
            continue
        # quitar el guion inicial; el resto es el anuncio
        anuncio = stripped[2:].rstrip(':')
        if anuncio:
            announcements.append(anuncio)

    return {
        'url': url,
        'mode': 'sr-transcript',
        'announcements': announcements[:200],  # cap
        'total': len(announcements),
        'arbol_raw': tree[:5000] if len(tree) > 5000 else tree,
        'note': ('Linearized announcement order — what a screen reader user hears. '
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
                # identidad de los tooltips visibles ANTES (por elemento, no
                # por recuento global: otro tooltip podía aparecer a la vez y
                # el contador antiguo enmascaraba un cierre correcto)
                before = page.evaluate(
                    "() => [...document.querySelectorAll("
                    "'[role=tooltip], [class*=tooltip], [class*=popover]')]"
                    ".filter(el => {"
                    "  if (el.checkVisibility) "
                    "    return el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true});"
                    "  const s = getComputedStyle(el);"
                    "  const box = el.getBoundingClientRect();"
                    "  return el.offsetParent !== null && s.visibility !== 'hidden'"
                    "         && parseFloat(s.opacity || '1') > 0.01 && box.width > 0;"
                    "})"
                    ".map(el => el.tagName + '#' + (el.id || '') + '.' + (el.className.toString().slice(0, 30)))")
                if not before:
                    continue  # nada visible → no aplica
                # Escape
                page.keyboard.press('Escape')
                page.wait_for_timeout(300)
                despues = page.evaluate(
                    "() => [...document.querySelectorAll("
                    "'[role=tooltip], [class*=tooltip], [class*=popover]')]"
                    ".filter(el => {"
                    "  if (el.checkVisibility) "
                    "    return el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true});"
                    "  const s = getComputedStyle(el);"
                    "  const box = el.getBoundingClientRect();"
                    "  return el.offsetParent !== null && s.visibility !== 'hidden'"
                    "         && parseFloat(s.opacity || '1') > 0.01 && box.width > 0;"
                    "})"
                    ".map(el => el.tagName + '#' + (el.id || '') + '.' + (el.className.toString().slice(0, 30)))")
                if set(before) <= set(despues):
                    # los mismos (o más) siguen visibles: no se cerró con Escape
                    no_dismissibles.append(f'{c["tag"]}#{c["id"] or "no-id"}')
            except Exception:
                continue
        nav.close()

    findings = []
    if no_dismissibles:
        from .a11yaudit import compute_score
        findings.append({
            'severity': 'low', 'criterion': CRIT.get(lang, CRIT['es']).get('1.4.13', '1.4.13'),
            'signal': 'hover_not_dismissible',
            'issue': _t(lang, 'hover_not_dismissible').format(n=len(no_dismissibles)),
            'remediation': _t(lang, 'hover_not_dismissible_rem'),
            'examples': no_dismissibles[:4]})
        return {'url': url, 'mode': 'hover', 'score': compute_score(findings),
                'summary': {'high': 0, 'medium': 0, 'low': len(findings)},
                'findings': findings}
    return {'url': url, 'mode': 'hover', 'score': 100,
            'summary': {'high': 0, 'medium': 0, 'low': 0}, 'findings': []}


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
_IFRAME_LISTS = ('contrast', 'targets', 'unnamed', 'fields', 'imgs', 'iframes',
                  'headings', 'tabindex', 'ariaHidden')
_CONTADORES_IFRAME = ('blank', 'videos', 'videoSubs', 'tables', 'tableTh',
                      'elements', 'contrastReview')


def _merge_iframes(data):
    """Integra los escaneos de iframes same-origin en el informe principal."""
    subframes = data.pop('iframes_data', [])
    data['nested_iframes'] = len(subframes)
    for sub in subframes:
        pref = 'iframe: '
        for k in _IFRAME_LISTS:
            for item in (sub.get(k) or [])[:12]:
                if isinstance(item, dict):
                    item = dict(item, ej=pref + str(item.get('ej', item)))
                else:
                    item = pref + str(item)
                data.setdefault(k, [])
                if len(data[k]) < 40:
                    data[k].append(item)
        for k in _CONTADORES_IFRAME:
            data[k] = data.get(k, 0) + (sub.get(k) or 0)


_JS_OVERFLOW = r'''() => {
  const vw = document.documentElement.clientWidth;
  const offenders = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.right > vw + 8 && r.width > 8) {
      const s = getComputedStyle(el);
      if (s.position === 'fixed' || s.position === 'absolute') continue;
      if (offenders.length < 8) offenders.push({ el: el.tagName.toLowerCase()
            + (el.id ? '#' + el.id : '')
            + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : ''),
          w: Math.round(r.width) });
    }
  }
  return { vw, scroll: document.documentElement.scrollWidth, offenders };
}'''


def audit_reflow(url, timeout=45, lang='en', auth_state=None, browser='auto'):
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

    findings = []

    def add(sev, code, key, examples, **fmt):
        findings.append({'severity': sev, 'criterion': CRIT.get(lang, CRIT['es']).get(code, code),
                          'signal': key, 'issue': _t(lang, key).format(**fmt),
                          'remediation': _t(lang, key + '_rem').format(**fmt),
                          'examples': examples[:6]})

    ok320 = r320['scroll'] <= r320['vw'] + 1
    if not ok320:
        add('high', '1.4.10', 'reflow_fail',
               [f"{m['el']} ({m['w']}px)" for m in r320['offenders']],
               n=len(r320['offenders']), w=r320['vw'],
               det=', '.join(f"{m['el']} ({m['w']}px)" for m in r320['offenders'][:3]))

    from .a11yaudit import compute_score
    return {
        'url': url,
        'mode': 'reflow',
        'score': compute_score(findings),
        'summary': {s_: sum(1 for h in findings if h['severity'] == s_)
                    for s_ in ('high', 'medium', 'low')},
        'measurements': {'reflow_320': {'scroll': r320['scroll'], 'viewport': r320['vw'],
                                      'ok': ok320}},
        'findings': findings,
        'limits': _t(lang, 'limits'),
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


def audit_keyboard(url, max_steps=60, lang='en', timeout=45, auth_state=None, browser='auto'):
    """Detección de TRAMPAS DE TECLADO (2.1.2) con Tab real.

    Recorre hasta max_pasos tabulaciones reales en Chromium, registra la
    secuencia de paradas, detecta ciclos (el patrón de un modal) y comprueba si
    ESCAPE libera el ciclo. Un modal que cicla y suelta con Escape es correcto;
    uno que no suelta es trampa — hallazgo 'high'.
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
        url_before = page.url
        seq = []
        paths = {}
        for i in range(max_steps):
            page.keyboard.press('Tab')
            try:
                stop = page.evaluate(_JS_STOP, i)
            except Exception:  # noqa: BLE001
                # execution context destroyed = LA NAVEGACIÓN OCURRIÓ al enfocar (3.2.1)
                break
            if stop is None:
                break
            seq.append(stop)
            if stop not in paths:
                paths[stop] = page.evaluate(_STOP_META, stop)
        # detección de ciclo: el final de la secuencia se repite con periodo p
        cycle = None
        for p_ in range(1, min(12, len(seq) // 2) + 1):
            if seq[-p_:] == seq[-2 * p_:-p_] and len(set(seq[-p_:])) >= 1:
                # exige al menos 2 repeticiones completas del periodo
                reps = sum(1 for k in range(len(seq) - p_, 0, -p_)
                           if seq[k:k + p_] == seq[-p_:])
                if reps >= 2:
                    cycle = seq[-p_:]
                    break

        # 3.2.1: ¿el foco provocó navegación? (context destroyed = navegación)
        foco_navego = None
        try:
            if page.url != url_before:
                foco_navego = page.url
        except Exception:
            foco_navego = url_before + ' → (navigated away)'

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

        esc_releases = None
        if cycle and not foco_navego:
            try:
                in_cycle = set(cycle)
                page.keyboard.press('Escape')
                page.wait_for_timeout(150)
                for _ in range(3):
                    page.keyboard.press('Tab')
                    page.wait_for_timeout(80)
                    stop = page.evaluate(_JS_STOP, len(seq))
                    if stop is None or stop not in in_cycle:
                        esc_releases = True
                        break
                else:
                    esc_releases = False
            except Exception:
                esc_releases = None
        try:
            nav.close()
        except Exception:
            pass

    findings = []
    if foco_navego:
        findings.append({
            'severity': 'high', 'criterion': CRIT.get(lang, CRIT['es']).get('3.2.1', '3.2.1'),
            'signal': 'focus_navigates',
            'issue': _t(lang, 'focus_navigates').format(ej='un elemento', url=foco_navego[:60]),
            'remediation': _t(lang, 'focus_navigates_rem')})
    if input_navego:
        findings.append({
            'severity': 'high', 'criterion': CRIT.get(lang, CRIT['es']).get('3.2.2', '3.2.2'),
            'signal': 'input_navigates',
            'issue': _t(lang, 'input_navigates').format(ej=input_elem, url=input_navego[:60]),
            'remediation': _t(lang, 'input_navigates_rem')})
    if cycle and esc_releases is False:
        elems = [paths.get(i, f'tab stop {i}') for i in cycle]
        findings.append({
            'severity': 'high', 'criterion': CRIT.get(lang, CRIT['es']).get('2.1.2', '2.1.2'),
            'signal': 'kbd_trap', 'issue': _t(lang, 'kbd_trap').format(
                n=len(cycle), cycle=' ↔ '.join(elems)),
            'remediation': _t(lang, 'kbd_trap_rem'),
            'examples': elems,
        })
    from .a11yaudit import compute_score
    return {
        'url': url,
        'mode': 'keyboard',
        'score': compute_score(findings),
        'summary': {s_: sum(1 for h in findings if h['severity'] == s_)
                    for s_ in ('high', 'medium', 'low')},
        'steps': len(seq),
        'tab_stops': [paths.get(i, f'tab stop {i}') for i in seq],
        'cycle': {'detected': bool(cycle),
                  'elements': [paths.get(i, f'tab stop {i}') for i in cycle] if cycle else [],
                  'escape_releases': esc_releases},
        'findings': findings,
        'limits': (('Real Tab walk in Chromium (max {n} steps). Focus inside cross-origin '
                    'iframes is not trackable and is marked as such. A cycle that Escape '
                    'releases (a correct modal) is NOT reported as a finding.'
                    ).format(n=max_steps) if lang == 'en' else
                   ('Recorrido con Tab real en Chromium (tope {n} pasos). El foco dentro de '
                    'iframes entre dominios no es rastreable y se marca como tal. Un ciclo '
                    'con Escape operativo (modal correcto) NO se reporta como hallazgo.'
                    ).format(n=max_steps)),
    }


# La captura del FONDO real: el texto se vuelve transparente durante el
# screenshot (los glifos desaparecen y queda el fondo puro, sin bordes de
# antialiasing que sesguen el muestreo); después se restaura. La imagen se
# recorta geométricamente al rect real (Playwright redondea el clip: floor de
# x/y, ceil de ancho/alto — las filas/columnas de "sliver" quedan fuera).
_JS_BACKGROUND = ("el => { el.__a11y_color = el.style.getPropertyValue('color'); "
             "el.__a11y_fill = el.style.getPropertyValue('-webkit-text-fill-color'); "
             "el.style.setProperty('color', 'transparent', 'important'); "
             "el.style.setProperty('-webkit-text-fill-color', 'transparent', 'important'); }")
_JS_RESTORE = ("el => { if (el.__a11y_color !== undefined) { "
                "el.style.setProperty('color', el.__a11y_color); "
                "el.style.removeProperty('-webkit-text-fill-color'); "
                "if (el.__a11y_fill) el.style.setProperty('-webkit-text-fill-color', el.__a11y_fill); } }")


def _fraccion_cubierta(start, tam, p):
    """Fracción del intervalo [p, p+1) cubierta por [ini, ini+tam)."""
    return max(0.0, min(p + 1.0, start + tam) - max(p, start))


def _recorta_rect(rgb, w, h, rect):
    """Descarta las filas/columnas del sliver de redondeo del screenshot.

    rect = {'x', 'y', 'width', 'height'} (coordenadas fraccionales del
    elemento). Devuelve (rw, rh, bytes) o None si no queda nada medible."""
    import math
    x0, y0 = math.floor(rect['x']), math.floor(rect['y'])
    top = 0
    while top < h and _fraccion_cubierta(rect['y'], rect['height'], y0 + top) < 0.5:
        top += 1
    bot = 0
    while bot < h - top and _fraccion_cubierta(rect['y'], rect['height'], y0 + h - 1 - bot) < 0.5:
        bot += 1
    left = 0
    while left < w and _fraccion_cubierta(rect['x'], rect['width'], x0 + left) < 0.5:
        left += 1
    right = 0
    while right < w - left and _fraccion_cubierta(rect['x'], rect['width'], x0 + w - 1 - right) < 0.5:
        right += 1
    rw, rh = w - left - right, h - top - bot
    if rw < 3 or rh < 3:
        return None
    recorte = bytearray(rw * rh * 3)
    for j in range(rh):
        o = ((top + j) * w + left) * 3
        recorte[j * rw * 3:(j + 1) * rw * 3] = rgb[o:o + rw * 3]
    return rw, rh, bytes(recorte)


def _samples_background(loc, rect, c):
    """Captura el fondo real de `loc` (texto transparente) y lo muestrea.

    Devuelve el dict de sample_rgb o None si no hay píxeles medibles."""
    try:
        loc.evaluate(_JS_BACKGROUND)
        png = loc.screenshot()
    finally:
        try:
            loc.evaluate(_JS_RESTORE)
        except Exception:  # noqa: BLE001
            pass
    w, h, rgb = decodificar_png(png)
    recorte = _recorta_rect(rgb, w, h, rect)
    if not recorte:
        return None
    rw, rh, rgb2 = recorte
    return sample_rgb(rw, rh, rgb2, c)


def audit_forced_colors(url, timeout=45, lang='en', auth_state=None, browser='auto'):
    """1.4.3/1.4.12-adjacente — ¿sobrevive el contenido a forced-colors: active?

    Los usuarios de Windows High Contrast Mode (ahora forced-colors CSS) ven
    la paleta del sistema: los colores del autor desaparecen. Lo que se
    rompe: texto pintado con color sobre fondo pintado (los DOS pasan al
    esquema del sistema, el contraste del autor ya no aplica — pero los
    iconos SVG con fill coloreado y las imágenes informativas PNG que
    dependen del color del autor pueden quedar invisibles sobre el fondo
    del sistema), y bordes usados como único indicador visual. Nadie más
    lo automatiza."""
    from playwright.sync_api import sync_playwright
    _JS_FC = r'''() => {
      const invisibles = [];
      let n = 0;
      for (const el of document.querySelectorAll('svg, img, [role=img], canvas')) {
        if (n >= 400) break;
        n++;
        const r = el.getBoundingClientRect();
        if (r.width <= 2 || r.height <= 2) continue;
        const cs = getComputedStyle(el);
        if (cs.visibility === 'hidden' || cs.display === 'none') continue;
        // con forced-colors, fill/stroke coloreados del autor caen a heredado
        // salvo que usen los keywords del sistema; detectar fill coloreado
        // hardcoded en SVG (ni currentColor ni CanvasText)
        if (el.tagName.toLowerCase() === 'svg') {
          const fills = [...el.querySelectorAll('[fill]')].map(x => x.getAttribute('fill'));
          if (el.getAttribute('fill')) fills.push(el.getAttribute('fill'));
          const col = fills.find(f => f && !['currentColor', 'CanvasText', 'Canvas', 'none',
                                          'inherit', 'transparent'].includes(f)
                                  && !f.startsWith('url('));
          if (col) invisibles.push('svg fill=' + col + ' — puede desaparecer en HCM');
        }
      }
      // imágenes informativas sin forced-color-adjust: en HCM Windows las
      // oscurece; si el PNG es oscuro, desaparece. Señal de revisión si hay
      // PNG con clase de icono (heurística humilde)
      const icons = document.querySelectorAll('img[class*=icon i], svg[class*=icon i]').length;
      return { coloredSvgs: invisibles.slice(0, 8), icons };
    }'''
    from .a11yaudit import _t as _t_audit, CRIT, compute_score

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(400)
            normal = page.evaluate(_JS_FC)
            page.emulate_media(forced_colors='active')
            page.wait_for_timeout(400)
            forzado = page.evaluate(_JS_FC)
        except Exception as e:  # noqa: BLE001
            nav.close()
            return {'error': _t_audit(lang, 'fetch_error').format(e=e)}
        nav.close()

    findings = []
    if forzado['coloredSvgs']:
        findings.append({
            'severity': 'low', 'criterion': CRIT.get(lang, CRIT['es']).get('1.4.3', '1.4.3'),
            'signal': 'forced_colors_svg',
            'issue': _t_audit(lang, 'forced_colors_svg').format(n=len(forzado['coloredSvgs'])),
            'remediation': _t_audit(lang, 'forced_colors_svg_rem'),
            'examples': forzado['coloredSvgs']})
    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])
    return {
        'mode': 'forced-colors', 'url': url,
        'normal': normal, 'forced': forzado,
        'score': compute_score(findings),
        'findings': findings,
        'summary': {s2: sum(1 for h in findings if h['severity'] == s2)
                    for s2 in ('high', 'medium', 'low')},
        'limits': ('Heurística de revisión (1.4.3/1.4.11 en HCM): los fills '
                   'coloreados hardcoded en SVG suelen caer al heredado con '
                   'forced-colors. La comprobación definitiva es visual con '
                   'Windows High Contrast — esto la prepara, no la sustituye.'),
    }


def audit_reduced_motion(url, timeout=45, lang='en', auth_state=None, browser='auto'):
    """2.2.2 (2.3.3) — ¿respeta el sitio prefers-reduced-motion?

    Carga la página normal y cuenta animaciones CSS en bucle (>0.15s,
    infinite). Recarga emulando prefers-reduced-motion: reduce y cuenta otra
    vez. Si el número NO baja, el sitio ignora la preferencia del usuario
    (2.2.2: pausa/parada/ocultar; 2.3.3 AAA). Nadie más lo automatiza:
    axe lo deja en revisión manual."""
    from playwright.sync_api import sync_playwright
    _JS_RM = r'''() => {
      let n = 0, examples = [];
      for (const el of document.querySelectorAll('*')) {
        if (n >= 40) break;
        const cs = getComputedStyle(el);
        if (cs.animationIterationCount !== 'infinite' || cs.animationName === 'none') continue;
        const durs = (cs.animationDuration || '0s').split(',').map(
          x => { const v = parseFloat(x) || 0; return x.includes('ms') ? v / 1000 : v; });
        const dur = Math.max(...durs, 0);
        if (dur <= 0.15) continue;
        n++;
        if (examples.length < 6) examples.push(
          el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')
          + '.' + String(el.className).slice(0, 25) + ' (' + cs.animationName.slice(0, 30) + ')');
      }
      const videos = document.querySelectorAll('video[autoplay]').length;
      return { anims: n, examples: examples, videos };
    }'''
    from .a11yaudit import _t as _t_audit, CRIT, compute_score

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(600)
            normal = page.evaluate(_JS_RM)
            page.emulate_media(reduced_motion='reduce')
            page.wait_for_timeout(600)
            reducido = page.evaluate(_JS_RM)
        except Exception as e:  # noqa: BLE001
            nav.close()
            return {'error': _t_audit(lang, 'fetch_error').format(e=e)}
        nav.close()

    respeta = reducido['anims'] < normal['anims']
    findings = []
    if normal['anims'] > 0 and not respeta:
        findings.append({
            'severity': 'medium', 'criterion': CRIT.get(lang, CRIT['es']).get('2.2.2', '2.2.2'),
            'signal': 'reduced_motion_ignored',
            'issue': _t_audit(lang, 'reduced_motion_ignored').format(
                n=normal['anims'], nr=reducido['anims']),
            'remediation': _t_audit(lang, 'reduced_motion_ignored_rem'),
            'examples': normal['examples'][:4]})
    order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: order[h['severity']])
    return {
        'mode': 'reduced-motion', 'url': url,
        'normal': normal, 'reduced': reducido,
        'respects': respeta,
        'score': compute_score(findings),
        'findings': findings,
        'summary': {s2: sum(1 for h in findings if h['severity'] == s2)
                    for s2 in ('high', 'medium', 'low')},
        'limits': ('Mide CSS animations y video[autoplay]. No cubre '
                   'animaciones JS/WebGL ni parallax por scroll — revisión manual.'),
    }


def audit_dom_url(url, timeout=45, lang='en', auth_state=None, browser='auto', color_scheme='light'):
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
        if color_scheme in ('dark', 'light'):
            # contraste por esquema: los temas oscuros fallan donde el claro
            # pasa — nadie audita ambos (axe tampoco)
            page.emulate_media(color_scheme=color_scheme)
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(400)
        except Exception as e:  # noqa: BLE001
            if not page.content() or page.url in ('about:blank', ''):
                nav.close()
                return {'error': f'no se pudo cargar: {e}'}
        try:
            data = page.evaluate(_JS, MAX_EXAMPLES)
            # 1.4.12: inject the WCAG spacing overrides, count clipped texts
            data['spacingClipped'] = page.evaluate(_JS_SPACING)
            # 1.4.3 real: captura + muestreo píxel a píxel de las zonas sobre
            # imagen/degradado que el contraste computado no puede calcular
            # (main frame; los iframes quedan como conteo de "revisar")
            medidos = []
            for z in (data.get('contrastZones') or [])[:8]:
                try:
                    c = parse_color(z['fg'])
                    if not c:
                        continue
                    m = _samples_background(
                        page.locator(f'[data-a11ytxt="{z["i"]}"]'),
                        {'x': z.get('x', 0), 'y': z.get('y', 0),
                         'width': z.get('w', 1400), 'height': z.get('h', 400)}, c)
                    if m:
                        medidos.append({'ej': z['ej'], 'fg': z['fg'],
                                        'large': bool(z.get('large')),
                                        'measured': m})
                except Exception:  # noqa: BLE001
                    continue
            data['contrastMeasured'] = medidos
            # iframes same-origin: mismo colector por frame
            subframes = []
            for fr in page.frames[1:5]:
                try:
                    subframes.append(fr.evaluate(_JS, MAX_EXAMPLES))
                except Exception:  # noqa: BLE001
                    continue  # cross-origin o no escaneable
            data['iframes_data'] = subframes
            # hover real sobre los controles marcados
            hover = []
            for i in range(min(10, int(data.get('marks', 0)))):
                try:
                    page.hover(f'[data-a11yidx="{i}"]', timeout=1000)
                    r = page.evaluate(_JS_HOVER, i)
                    if r and r['ratio'] < 3:
                        hover.append(dict(r, ej=f'hover #{i}'))
                except Exception:  # noqa: BLE001
                    continue
            data['hover'] = hover
        finally:
            try:
                ctx.close()
            except Exception:
                pass
    _merge_iframes(data)
    return audit_dom(data, url, lang=lang, color_scheme=color_scheme)


def contrast_dom(url, selector, text_color=None, sample=4, lang='en', timeout=45,
                 auth_state=None, browser='auto'):
    """Contraste REAL de un elemento contra lo que sea que tenga detrás.

    La versión automatizada de a11y_contrast_image: carga la página, captura el
    elemento que coincide con `selector` con el texto en transparente (queda el
    fondo puro, sin bordes de antialiasing), muestrea sus píxeles y los
    contrasta con el color del texto — computado del elemento cuando no se da.
    Para texto sobre imágenes, degradados, vídeo o cualquier fondo que el
    cálculo CSS no puede resolver. Requiere Playwright.
    """
    from playwright.sync_api import sync_playwright
    from .contrast import T as _TC
    t9 = _TC.get(lang, _TC['es'])
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(storage_state=auth_state) if auth_state else nav
        page = ctx.new_page() if auth_state else nav.new_page()
        try:
            page.goto(url, wait_until='load', timeout=timeout * 1000)
            page.wait_for_timeout(300)
            loc = page.locator(selector).first
            try:
                loc.wait_for(timeout=timeout * 1000)
            except Exception:  # noqa: BLE001
                return {'error': t9['selector_missing'].format(s=selector)}
            if text_color:
                c = parse_color(text_color)
                if not c:
                    return {'error': t9['invalid_color']}
            else:
                comp = loc.evaluate('el => getComputedStyle(el).color')
                c = parse_color(comp)
                if not c:
                    return {'error': f"{t9['invalid_color']} (computed: {comp})"}
            if c.get('a', 1) < 1:
                return {'error': t9['opaque_text']}
            try:
                box = loc.bounding_box()
                if not box or box['width'] < 3 or box['height'] < 3:
                    return {'error': t9['no_box'].format(s=selector)}
                m = _samples_background(loc, box, c)
            except Exception:  # noqa: BLE001
                return {'error': t9['no_box'].format(s=selector)}
            if not m:
                return {'error': t9['no_pixels']}
            out = {'url': url, 'selector': selector, 'text_color': hexs(c),
                   'image': f'{selector} ({round(box["width"])}×{round(box["height"])})',
                   'worst_ratio': m['worst_ratio'],
                   'median_ratio': m['median_ratio'],
                   'p95_ratio': m['p95_ratio'],
                   'area_passes_aa_normal_text_4_5': m['area_passes_aa_normal_text_4_5'],
                   'area_passes_aa_min_3_0': m['area_passes_aa_min_3_0'],
                   'sampled_pixels': m['sampled_pixels'],
                   'interpretation': t9['interp']}
            if 'worst_zone' in m:
                out['worst_zone'] = m['worst_zone']
            return out
        finally:
            try:
                ctx.close()
            except Exception:  # noqa: BLE001
                pass


def contrast_dom_main(argv):
    ap = argparse.ArgumentParser(description='Real text-over-anything contrast: screenshot + pixel sampling (auto-region)')
    ap.add_argument('url')
    ap.add_argument('--selector', required=True, help='CSS selector of the text element')
    ap.add_argument('--text', help='text color (default: computed from the element)')
    ap.add_argument('--sample', type=int, default=4)
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--timeout', type=int, default=45)
    a = ap.parse_args(argv)
    try:
        res = contrast_dom(a.url, a.selector, text_color=a.text, sample=a.sample,
                           lang=a.lang, timeout=a.timeout)
    except ImportError:
        print(json.dumps({'error': 'Playwright not installed'}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


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
    ap.add_argument('--max-steps', type=int, default=60)
    a = ap.parse_args(argv)
    try:
        res = audit_keyboard(a.url, max_steps=a.max_steps, lang=a.lang)
    except ImportError:
        print(json.dumps({'error': 'Playwright no instalado'}))
        return 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
