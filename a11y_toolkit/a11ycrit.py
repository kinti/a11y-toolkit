#!/usr/bin/env python3
"""WCAG 2.2 criterion knowledge (es/en) — the "what it is" behind the auditor.

a11y_criterion(code) returns, for every criterion the toolkit evaluates: the
official name, level, what it requires, typical failures, how to verify it
manually and with which toolkit tool. It is the bridge between an automated
finding and actually understanding the criterion.

CLI:
  a11ycrit.py 2.5.8 [--lang es]
  a11ycrit.py --signal kbd_trap [--lang en]
  a11ycrit.py --list
"""

import argparse
import json
import sys


# Enlace oficial Understanding WCAG 2.2 por criterio (w3.org, índice 2026-10).
# Fuente: https://www.w3.org/WAI/WCAG22/Understanding/ — los 86 criterios.
_UNDERSTANDING = {
    '1.1.1': 'non-text-content',
    '1.2.1': 'audio-only-and-video-only-prerecorded',
    '1.2.2': 'captions-prerecorded',
    '1.2.3': 'audio-description-or-media-alternative-prerecorded',
    '1.2.4': 'captions-live',
    '1.2.5': 'audio-description-prerecorded',
    '1.2.6': 'sign-language-prerecorded',
    '1.2.7': 'extended-audio-description-prerecorded',
    '1.2.8': 'media-alternative-prerecorded',
    '1.2.9': 'audio-only-live',
    '1.3.1': 'info-and-relationships',
    '1.3.2': 'meaningful-sequence',
    '1.3.3': 'sensory-characteristics',
    '1.3.4': 'orientation',
    '1.3.5': 'identify-input-purpose',
    '1.3.6': 'identify-purpose',
    '1.4.1': 'use-of-color',
    '1.4.2': 'audio-control',
    '1.4.3': 'contrast-minimum',
    '1.4.4': 'resize-text',
    '1.4.5': 'images-of-text',
    '1.4.6': 'contrast-enhanced',
    '1.4.7': 'low-or-no-background-audio',
    '1.4.8': 'visual-presentation',
    '1.4.9': 'images-of-text-no-exception',
    '1.4.10': 'reflow',
    '1.4.11': 'non-text-contrast',
    '1.4.12': 'text-spacing',
    '1.4.13': 'content-on-hover-or-focus',
    '2.1.1': 'keyboard',
    '2.1.2': 'no-keyboard-trap',
    '2.1.3': 'keyboard-no-exception',
    '2.1.4': 'character-key-shortcuts',
    '2.2.1': 'timing-adjustable',
    '2.2.2': 'pause-stop-hide',
    '2.2.3': 'no-timing',
    '2.2.4': 'interruptions',
    '2.2.5': 're-authenticating',
    '2.2.6': 'timeouts',
    '2.3.1': 'three-flashes-or-below-threshold',
    '2.3.2': 'three-flashes',
    '2.3.3': 'animation-from-interactions',
    '2.4.1': 'bypass-blocks',
    '2.4.2': 'page-titled',
    '2.4.3': 'focus-order',
    '2.4.4': 'link-purpose-in-context',
    '2.4.5': 'multiple-ways',
    '2.4.6': 'headings-and-labels',
    '2.4.7': 'focus-visible',
    '2.4.8': 'location',
    '2.4.9': 'link-purpose-link-only',
    '2.4.10': 'section-headings',
    '2.4.11': 'focus-not-obscured-minimum',
    '2.4.12': 'focus-not-obscured-enhanced',
    '2.4.13': 'focus-appearance',
    '2.5.1': 'pointer-gestures',
    '2.5.2': 'pointer-cancellation',
    '2.5.3': 'label-in-name',
    '2.5.4': 'motion-actuation',
    '2.5.5': 'target-size-enhanced',
    '2.5.6': 'concurrent-input-mechanisms',
    '2.5.7': 'dragging-movements',
    '2.5.8': 'target-size-minimum',
    '3.1.1': 'language-of-page',
    '3.1.2': 'language-of-parts',
    '3.1.3': 'unusual-words',
    '3.1.4': 'abbreviations',
    '3.1.5': 'reading-level',
    '3.1.6': 'pronunciation',
    '3.2.1': 'on-focus',
    '3.2.2': 'on-input',
    '3.2.3': 'consistent-navigation',
    '3.2.4': 'consistent-identification',
    '3.2.5': 'change-on-request',
    '3.2.6': 'consistent-help',
    '3.3.1': 'error-identification',
    '3.3.2': 'labels-or-instructions',
    '3.3.3': 'error-suggestion',
    '3.3.4': 'error-prevention-legal-financial-data',
    '3.3.5': 'help',
    '3.3.6': 'error-prevention-all',
    '3.3.7': 'redundant-entry',
    '3.3.8': 'accessible-authentication-minimum',
    '3.3.9': 'accessible-authentication-enhanced',
    '4.1.1': 'parsing',
    '4.1.2': 'name-role-value',
    '4.1.3': 'status-messages'
}

# code → (nivel, {es: (nombre, exige, fallos, prueba)}, {en: ...})
_C = {
    '1.2.1': ('A', {
        'es': ('Solo audio y solo vídeo (pregrabado)', 'El audio tiene transcripción; el vídeo sin audio, alternativa textual.', 'Podcasts without transcripts; silent demonstration videos without text description.', 'Manual: play the media and check an alternative exists.'),
        'en': ('Audio-only and Video-only (Prerecorded)', 'Audio-only content has a transcript; video-only has a text or audio alternative.', 'Podcasts without transcripts; silent demonstration videos without text description.', 'Manual: play the media and check an alternative exists.'),
    }),
    '1.4.10': ('AA', {
        'es': ('Reflujo', 'El contenido refluye a 320px CSS sin scroll bidimensional.', 'Fixed-width layouts that force horizontal scrolling on phones.', 'a11y_reflow (320px viewport, real overflow measurement + offenders).'),
        'en': ('Reflow', 'Content reflows to 320 CSS px without two-dimensional scroll.', 'Fixed-width layouts that force horizontal scrolling on phones.', 'a11y_reflow (320px viewport, real overflow measurement + offenders).'),
    }),
    '1.4.12': ('AA', {
        'es': ('Espaciado de texto', 'Sin pérdida de contenido con los overrides de espaciado oficiales.', 'Cards with fixed heights that clip their text when spacing grows.', 'a11y_audit_dom (injects the official override set and counts clipped texts).'),
        'en': ('Text Spacing', 'No loss of content when users apply the documented spacing overrides (line-height 1.5, letter-spacing 0.12em…)', 'Cards with fixed heights that clip their text when spacing grows.', 'a11y_audit_dom (injects the official override set and counts clipped texts).'),
    }),
    '1.4.13': ('AA', {
        'es': ('Contenido al pasar el foco o el puntero', 'El contenido emergente se puede cerrar, alcanzar y persiste.', 'Tooltips that vanish when you move toward them; hovers you cannot dismiss with Esc.', 'Manual: hover/focus each trigger, try Esc, try moving to the tooltip.'),
        'en': ('Content on Hover or Focus', 'Hover/focus-triggered content is dismissible, hoverable and persistent.', 'Tooltips that vanish when you move toward them; hovers you cannot dismiss with Esc.', 'Manual: hover/focus each trigger, try Esc, try moving to the tooltip.'),
    }),
    '2.1.2': ('A', {
        'es': ('Sin trampa de teclado', 'El foco siempre puede salir solo con teclado.', 'Modals whose focus cycles forever with no Escape release.', 'a11y_keyboard (real Tab walk, cycle detection, Escape-release test).'),
        'en': ('No Keyboard Trap', 'Focus can always leave a component with the keyboard alone.', 'Modals whose focus cycles forever with no Escape release.', 'a11y_keyboard (real Tab walk, cycle detection, Escape-release test).'),
    }),
    '2.5.7': ('AA', {
        'es': ('Movimientos de arrastre', 'Toda acción de arrastre tiene alternativa sin arrastre.', 'Sliders you can only drag; kanban cards you can only drag-and-drop.', 'Manual: try every action with click/tap only; a11y_audit_url flags drag-handler suspicion.'),
        'en': ('Dragging Movements', 'Dragging operations have a non-dragging alternative.', 'Sliders you can only drag; kanban cards you can only drag-and-drop.', 'Manual: try every action with click/tap only; a11y_audit_url flags drag-handler suspicion.'),
    }),
    '1.4.5': ('AA', {
        'es': ('Imágenes de texto', 'Salvo logotipos, el texto se presenta como texto real, no como imagen.', 'Headings or paragraphs rendered as PNG/JPG; banner text baked into hero images.', 'a11y_audit_url flags images inside headings and book-length alts (review signal); you judge whether each image of text is justified (logo exception).'),
        'en': ('Images of Text', 'Except for logotypes, text is presented as real text, not images of text.', 'Headings or paragraphs rendered as PNG/JPG; banner text baked into hero images.', 'a11y_audit_url flags images inside headings and book-length alts (review signal); you judge whether each image of text is justified (logo exception).'),
    }),
    '1.4.11': ('AA', {
        'es': ('Contraste no textual', 'Componentes UI y objetos gráficos tienen al menos 3:1 contra colores adyacentes.', 'Icon buttons barely visible against their background; focus indicators too faint to see.', 'a11y_contrast_pair with target 3.0 for UI elements; the rendered audit checks focus-indicator contrast; you verify visually.'),
        'en': ('Non-text Contrast', 'UI components and graphical objects have at least 3:1 contrast against adjacent colors.', 'Icon buttons barely visible against their background; focus indicators too faint to see.', 'a11y_contrast_pair with target 3.0 for UI elements; the rendered audit checks focus-indicator contrast; you verify visually.'),
    }),
    '3.2.6': ('A', {
        'es': ('Ayuda coherente — NUEVO en 2.2', 'Si hay ayuda en varias páginas, aparece en el mismo orden relativo.', 'A "Contact us" link in the header on some pages and the footer on others.', 'a11ytoolkit audit --pages N (site-level help-link drift detection across the crawl).'),
        'en': ('Consistent Help — NEW in WCAG 2.2', 'If help is available on multiple pages, it appears in the same relative order.', 'A "Contact us" link in the header on some pages and the footer on others.', 'a11ytoolkit audit --pages N (site-level help-link drift detection across the crawl).'),
    }),
    '1.1.1': ('A', {
        'es': ('Contenido no textual',
               'Toda imagen funcional o informativa tiene alternativa textual equivalente; las decorativas se ocultan (alt="").',
               '<img> sin alt, botones-imagen sin nombre, mapas sin texto alternativo, canvas/svg sin nombre accesible.',
               'a11y_audit_url / a11y_audit_dom (faltantes); tú valoras si el texto describe el contenido.'),
        'en': ('Non-text Content',
               'Every functional or informative image has an equivalent text alternative; decorative ones are hidden (alt="").',
               '<img> without alt, image buttons with no name, maps without text alternative, canvas/svg with no accessible name.',
               'a11y_audit_url / a11y_audit_dom (missing ones); you judge whether the text describes the content.'),
    }),
    '1.2.2': ('A', {
        'es': ('Subtítulos (pregrabado)',
               'Los vídeos con audio pregrabado publican subtítulos sincronizados.',
               'Vídeos de marketing, demos o tutoriales sin <track kind="captions">.',
               'a11y_audit_url / a11y_audit_dom (detección); tú validas la calidad de los subtítulos.'),
        'en': ('Captions (Prerecorded)',
               'Videos with prerecorded audio publish synchronized captions.',
               'Marketing, demo or tutorial videos without <track kind="captions">.',
               'a11y_audit_url / a11y_audit_dom (detection); you validate caption quality.'),
    }),
    '1.3.1': ('A', {
        'es': ('Información y relaciones',
               'La estructura visual es programática: encabezados jerárquicos, tablas con th/scope, landmarks, labels asociados.',
               'Saltos de nivel de encabezados, tablas sin th, encabezados vacíos, múltiples h1, landmarks duplicados sin nombre.',
               'a11y_audit_url / a11y_audit_dom (estructura); tú juzgas si el esquema tiene sentido.'),
        'en': ('Info and Relationships',
               'The visual structure is programmatic: hierarchical headings, tables with th/scope, landmarks, associated labels.',
               'Heading level skips, tables without th, empty headings, multiple h1, duplicated unnamed landmarks.',
               'a11y_audit_url / a11y_audit_dom (structure); you judge whether the outline makes sense.'),
    }),
    '1.3.5': ('AA', {
        'es': ('Identificar el propósito de la entrada',
               'Los campos que recogen datos de la persona usuaria declaran su propósito con autocomplete (email, tel, name…).',
               'Campos de contacto/registro sin atributo autocomplete.',
               'a11y_audit_url / a11y_audit_dom (detección de campos sin autocomplete).'),
        'en': ('Identify Input Purpose',
               'Fields collecting user information declare their purpose via autocomplete (email, tel, name…).',
               'Contact/signup fields without the autocomplete attribute.',
               'a11y_audit_url / a11y_audit_dom (detection of fields without autocomplete).'),
    }),
    '1.4.2': ('A', {
        'es': ('Control del audio',
               'El audio que suena solo más de 3 segundos se puede pausar/parar o ajustar su volumen sin bajar el global.',
               '<video>/<audio> con autoplay y sonido.',
               'a11y_audit_url / a11y_audit_dom (detección de autoplay); tú compruebas que el control exista y funcione.'),
        'en': ('Audio Control',
               'Audio playing automatically for more than 3 seconds can be paused/stopped or volume-controlled without lowering the global volume.',
               '<video>/<audio> with autoplay and sound.',
               'a11y_audit_url / a11y_audit_dom (autoplay detection); you verify a working control exists.'),
    }),
    '1.4.3': ('AA', {
        'es': ('Contraste (mínimo)',
               'Texto normal ≥4.5:1, texto grande (≥24px o ≥18.66px negrita) ≥3:1 contra su fondo efectivo.',
               'Colores corporativos claros sobre blanco, texto sobre fotos y degradados, placeholders grises.',
               'a11y_contrast_pair (pares), a11y_contrast_image (sobre imagen), a11y_audit_dom (computado en toda la página).'),
        'en': ('Contrast (Minimum)',
               'Normal text ≥4.5:1, large text (≥24px or ≥18.66px bold) ≥3:1 against its effective background.',
               'Light brand colors on white, text over photos and gradients, gray placeholders.',
               'a11y_contrast_pair (pairs), a11y_contrast_image (over images), a11y_audit_dom (computed page-wide).'),
    }),
    '1.4.4': ('AA', {
        'es': ('Cambio de tamaño del texto',
               'El texto se puede ampliar al 200% sin pérdida de contenido o funcionalidad.',
               'viewport con user-scalable=no o maximum-scale<2, textos en píxeles fijos dentro de contenedores rígidos.',
               'a11y_audit_url / a11y_audit_dom (viewport); tú haces zoom 200% y compruebas reflujo.'),
        'en': ('Resize Text',
               'Text can be resized up to 200% without loss of content or functionality.',
               'viewport with user-scalable=no or maximum-scale<2, fixed-px text inside rigid containers.',
               'a11y_audit_url / a11y_audit_dom (viewport); you zoom to 200% and check reflow.'),
    }),
    '2.1.1': ('A', {
        'es': ('Teclado',
               'Toda funcionalidad es operable solo con teclado.',
               'onclick en div/span sin focus, menús y carruseles sin manejo de teclas, atajos accesskey duplicados.',
               'a11y_audit_url (onclick suelto, accesskey); tú recorres la página entera con Tab/Enter/Esc.'),
        'en': ('Keyboard',
               'All functionality is operable through a keyboard interface.',
               'onclick on div/span without focus handling, menus/carousels without key handling, duplicated accesskeys.',
               'a11y_audit_url (loose onclick, accesskey); you walk the whole page with Tab/Enter/Esc.'),
    }),
    '2.2.1': ('A', {
        'es': ('Tiempo ajustable',
               'Los límites de tiempo se pueden ampliar, desactivar o extender; nada se recarga sin petición.',
               '<meta http-equiv="refresh"> temporizado, sesiones que caducan sin avisar.',
               'a11y_audit_url / a11y_audit_dom (meta refresh).'),
        'en': ('Timing Adjustable',
               'Time limits can be turned off, adjusted or extended; nothing reloads unless requested.',
               'Timed <meta http-equiv="refresh">, sessions expiring without warning.',
               'a11y_audit_url / a11y_audit_dom (meta refresh).'),
    }),
    '2.4.1': ('A', {
        'es': ('Evitación de bloques',
               'Hay mecanismo para saltar bloques de contenido que se repiten (skip link, landmarks).',
               'Sin <main>/role="main" ni enlace "saltar al contenido".',
               'a11y_audit_url / a11y_audit_dom (detección).'),
        'en': ('Bypass Blocks',
               'A mechanism exists to skip blocks of repeated content (skip link, landmarks).',
               'No <main>/role="main" and no "skip to content" link.',
               'a11y_audit_url / a11y_audit_dom (detection).'),
    }),
    '2.4.2': ('A', {
        'es': ('Página con título',
               'Cada página tiene un <title> descriptivo y único.',
               'Title vacío o genérico ("Inicio" en todas las páginas).',
               'a11y_audit_url / a11y_audit_dom (detección); tú valoras si describe la página.'),
        'en': ('Page Titled',
               'Every page has a descriptive, unique <title>.',
               'Empty or generic titles ("Home" everywhere).',
               'a11y_audit_url / a11y_audit_dom (detection); you judge whether it describes the page.'),
    }),
    '2.4.3': ('A', {
        'es': ('Orden del foco',
               'El orden de tabulación sigue el orden lógico de lectura y uso.',
               'tabindex positivos, DOM reordenado con CSS que rompe la secuencia.',
               'a11y_snapshot (orden REAL de tabulación) + a11y_diff entre builds; tabindex en el auditor estático.'),
        'en': ('Focus Order',
               'Focus order follows the logical reading and usage sequence.',
               'Positive tabindex, CSS-reordered DOM breaking the sequence.',
               'a11y_snapshot (REAL tab order) + a11y_diff between builds; tabindex in the static auditor.'),
    }),
    '2.4.4': ('A', {
        'es': ('Propósito de los enlaces (en contexto)',
               'El destino de cada enlace es comprensible por su texto (o su contexto programático).',
               '«Más», «aquí», «leer más» repetidos; enlaces distintos con idéntico texto.',
               'a11y_audit_url (texto genérico y colisiones de nombre).'),
        'en': ('Link Purpose (In Context)',
               'Each link\'s destination is clear from its text (or programmatic context).',
               '"More", "here", "read more" repeated; different links with identical text.',
               'a11y_audit_url (generic text and name collisions).'),
    }),
    '2.4.7': ('AA', {
        'es': ('Foco visible',
               'El indicador de foco del teclado es visible en todos los elementos enfocables.',
               'outline:none sin sustituto, indicadores con contraste insuficiente.',
               'a11y_audit_dom (heurística outline/box-shadow); tú confirmas visualmente cada parada de Tab.'),
        'en': ('Focus Visible',
               'The keyboard focus indicator is visible on every focusable element.',
               'outline:none with no replacement, indicators with insufficient contrast.',
               'a11y_audit_dom (outline/box-shadow heuristic); you visually confirm each Tab stop.'),
    }),
    '2.5.8': ('AA', {
        'es': ('Tamaño del objetivo (mínimo) — NUEVO en WCAG 2.2',
               'Los objetivos de puntero (botones, enlaces) miden al menos 24×24 px CSS, o tienen espaciado suficiente.',
               'Iconos-boton de 16px, enlaces apretados en menús de pie de página.',
               'a11y_audit_dom (getBoundingClientRect, con excepciones: enlaces inline equivalentes).'),
        'en': ('Target Size (Minimum) — NEW in WCAG 2.2',
               'Pointer targets (buttons, links) are at least 24×24 CSS px, or have sufficient spacing.',
               '16px icon buttons, cramped footer-menu links.',
               'a11y_audit_dom (getBoundingClientRect, with exceptions: equivalent inline links).'),
    }),
    '3.1.1': ('A', {
        'es': ('Idioma de la página',
               '<html> declara el idioma real de la página (código BCP-47).',
               'lang ausente o inválido ("xx"); lectores eligen la voz sintética equivocada.',
               'a11y_audit_url / a11y_audit_dom (detección + validez).'),
        'en': ('Language of Page',
               '<html> declares the page\'s real language (BCP-47 code).',
               'Missing or invalid lang ("xx"); screen readers pick the wrong synthetic voice.',
               'a11y_audit_url / a11y_audit_dom (detection + validity).'),
    }),
    '3.2.5': ('AAA', {
        'es': ('Cambio a petición',
               'No hay cambios de contexto (ventanas nuevas, recargas) sin aviso o petición de la persona usuaria.',
               'target="_blank" sin avisar, redirecciones automáticas.',
               'a11y_audit_url (target=_blank sin aviso, meta refresh).'),
        'en': ('Change on Request',
               'No context changes (new windows, reloads) without notice or user request.',
               'target="_blank" without warning, automatic redirects.',
               'a11y_audit_url (target=_blank without warning, meta refresh).'),
    }),
    '3.3.2': ('A', {
        'es': ('Etiquetas o instrucciones',
               'Los campos tienen etiqueta visible o nombre accesible; las instrucciones están disponibles.',
               'input/select/textarea sin label ni aria-label, labels huérfanos, doble etiqueta.',
               'a11y_audit_url / a11y_audit_dom (detección).'),
        'en': ('Labels or Instructions',
               'Fields have visible labels or accessible names; instructions are available.',
               'input/select/textarea without label or aria-label, orphan labels, double labels.',
               'a11y_audit_url / a11y_audit_dom (detection).'),
    }),
    '2.5.2': ('A', {
        'es': ('Cancelación del puntero',
               'La activación se produce en el UP-event (o se puede abortar antes de completar).',
               'Lógica de activación en onmousedown/ontouchstart/onpointerdown: arrastrar el dedo fuera no cancela.',
               'a11y_audit_url (sospecha: manejadores en down-event); tú verificas el comportamiento.'),
        'en': ('Pointer Cancellation',
               'Activation happens on the up-event (or can be aborted before completion).',
               'Activation logic in onmousedown/ontouchstart/onpointerdown: dragging away does not abort.',
               'a11y_audit_url (suspicion: down-event handlers); you verify the behavior.'),
    }),
    '2.5.3': ('A', {
        'es': ('Etiqueta en el nombre',
               'El nombre accesible CONTIENE el texto de la etiqueta visible.',
               'aria-label que no incluye el texto visible: quien dicta por voz dice «Ver ofertas» y el control se llama «Más información».',
               'a11y_audit_url / a11y_audit_dom (detección).'),
        'en': ('Label in Name',
               'The accessible name CONTAINS the visible label text.',
               'aria-label that excludes the visible text: voice users say "View offers" but the control is named "More information".',
               'a11y_audit_url / a11y_audit_dom (detection).'),
    }),
    '3.1.2': ('AA', {
        'es': ('Idioma de las partes',
               'Pasajes en otro idioma llevan lang con código BCP-47 válido.',
               'Citas o términos extranjeros sin lang, o con código inválido.',
               'a11y_audit_url (validez de los lang de elementos).'),
        'en': ('Language of Parts',
               'Passages in another language carry lang with a valid BCP-47 code.',
               'Foreign quotes or terms without lang, or with invalid codes.',
               'a11y_audit_url (element lang validity).'),
    }),
    '3.3.8': ('AA', {
        'es': ('Autenticación accesible — NUEVO en WCAG 2.2',
               'El acceso no exige test cognitivo (recordar, resolver puzles): hay alternativa.',
               'CAPTCHA (reCAPTCHA, hCaptcha, Turnstile) sin alternativa: email mágico, OAuth, soporte.',
               'a11y_audit_url (detección de captcha); la alternativa se verifica a mano.'),
        'en': ('Accessible Authentication — NEW in WCAG 2.2',
               'Access does not require a cognitive test (remembering, puzzles): an alternative exists.',
               'CAPTCHA (reCAPTCHA, hCaptcha, Turnstile) with no alternative: magic links, OAuth, support.',
               'a11y_audit_url (captcha detection); the alternative is verified manually.'),
    }),
    '2.4.11': ('AA', {
        'es': ('Foco no ocultado (mínimo) — NUEVO en WCAG 2.2',
               'El elemento con foco no queda tapado por contenido del propio autor (cabeceras fijas, banners).',
               'Header sticky sin scroll-padding-top: anclajes y saltos de foco aterrizan bajo él.',
               'a11y_audit_dom (causa raíz: altura del fijo vs scroll-padding-top).'),
        'en': ('Focus Not Obscured (Minimum) — NEW in WCAG 2.2',
               'The focused element is not hidden by author content (sticky headers, banners).',
               'Sticky header without scroll-padding-top: anchors and focus jumps land beneath it.',
               'a11y_audit_dom (root cause: fixed height vs scroll-padding-top).'),
    }),
    '2.2.2': ('A', {
        'es': ('Poner en pausa, detener, ocultar',
               'El contenido en movimiento >5s se puede pausar, detener u ocultar.',
               '<marquee>, looping CSS animations, auto-updating tickers with no pause control.',
               'a11y_audit_url / a11y_audit_dom (detection); you verify a pause control actually exists and works.'),
        'en': ('Pause, Stop, Hide',
               'Moving, blinking or auto-updating content that starts automatically and lasts >5s can be paused, stopped or hidden',
               '<marquee>, looping CSS animations, auto-updating tickers with no pause control.',
               'a11y_audit_url / a11y_audit_dom (detection); you verify a pause control actually exists and works.'),
    }),
    '2.5.1': ('A', {
        'es': ('Gestos de puntero',
               'Todo gesto complejo tiene alternativa de clic/toque simple.',
               'Swipe carousels with no prev/next buttons; drag-to-reorder with no menu alternative.',
               'a11y_audit_url (touch/drag handler suspicion); you test with single clicks only.'),
        'en': ('Pointer Gestures',
               'Multipoint or path-based gestures have a single-pointer alternative (tap/click).',
               'Swipe carousels with no prev/next buttons; drag-to-reorder with no menu alternative.',
               'a11y_audit_url (touch/drag handler suspicion); you test with single clicks only.'),
    }),
    '2.5.4': ('A', {
        'es': ('Activación por movimiento',
               'Lo que activa el movimiento del dispositivo se activa también con UI y se puede desactivar.',
               'Shake-to-undo, tilt-to-scroll with no button alternative.',
               'a11y_audit_url (devicemotion/orientation handler suspicion); you verify the UI alternative actually works.'),
        'en': ('Motion Actuation',
               'Functions triggered by device motion can also be triggered by UI, and the motion trigger can be disabled.',
               'Shake-to-undo, tilt-to-scroll with no button alternative.',
               'a11y_audit_url (devicemotion/orientation handler suspicion); you verify the UI alternative actually works.'),
    }),
    '1.4.1': ('A', {
        'es': ('Uso del color',
               'El color nunca es el único medio visual de transmitir información.',
               'Links inside prose distinguished only by a slightly different color; "fields in red are required" alone fails the criterion.',
               'a11y_audit_dom (link-in-text-block color/underline check); you scan the page for color-only links by eye.'),
        'en': ('Use of Color',
               'Color is never the only visual means of conveying information.',
               'Links inside prose distinguished only by a slightly different color; "fields in red are required" alone fails the criterion.',
               'a11y_audit_dom (link-in-text-block color/underline check); you scan the page for color-only links by eye.'),
    }),
    '1.3.2': ('A', {
        'es': ('Secuencia significativa',
               'El orden de lectura del código coincide con el visual.',
               'CSS flex/grid order or absolute positioning that contradicts DOM order.',
               'a11y_audit_dom (DOM-vs-visual inversion heuristic); you confirm with a Tab walk.'),
        'en': ('Meaningful Sequence',
               'The reading order in code matches the visual presentation order.',
               'CSS flex/grid order or absolute positioning that contradicts DOM order.',
               'a11y_audit_dom (DOM-vs-visual inversion heuristic); you confirm with a Tab walk.'),
    }),
    '1.3.3': ('A', {
        'es': ('Características sensoriales',
               'Las instrucciones no dependen solo de forma/posición/tamaño.',
               '"Click the round button on the right"; "see the instructions above".',
               'a11y_audit_url (text pattern review); you judge whether the reference is unambiguous.'),
        'en': ('Sensory Characteristics',
               'Instructions do not rely on shape, size, position or orientation alone.',
               '"Click the round button on the right"; "see the instructions above".',
               'a11y_audit_url (text pattern review); you judge whether the reference is unambiguous.'),
    }),
    '1.3.4': ('AA', {
        'es': ('Orientación',
               'El contenido no se limita a una sola orientación salvo excepción.',
               'screen.orientation.lock() calls; orientation-forcing media queries.',
               'a11y_audit_url (lock detection); you test portrait and landscape.'),
        'en': ('Orientation',
               'Content does not restrict operation to a single orientation unless essential.',
               'screen.orientation.lock() calls; orientation-forcing media queries.',
               'a11y_audit_url (lock detection); you test portrait and landscape.'),
    }),
    '1.2.3': ('A', {
        'es': ('Audiodescripción o alternativa media',
               'El vídeo pregrabado tiene audiodescripción o alternativa.',
               'Videos with essential visual information and no descriptions track.',
               'a11y_audit_url (track absence); a human watching the video decides if description is needed.'),
        'en': ('Audio Description or Media Alternative',
               'Prerecorded video has audio description or a media alternative.',
               'Videos with essential visual information and no descriptions track.',
               'a11y_audit_url (track absence); a human watching the video decides if description is needed.'),
    }),
    '1.2.5': ('AA', {
        'es': ('Audiodescripción (pregrabado)',
               'El vídeo pregrabado lleva audiodescripción sincronizada.',
               'Same as 1.2.3 at AA level.',
               'a11y_audit_url (track kind="descriptions" absence); human judgment required.'),
        'en': ('Audio Description (Prerecorded)',
               'Prerecorded video carries synchronized audio description.',
               'Same as 1.2.3 at AA level.',
               'a11y_audit_url (track kind="descriptions" absence); human judgment required.'),
    }),
    '3.2.3': ('AA', {
        'es': ('Navegación coherente',
               'La navegación repetida mantiene el mismo orden relativo en todas las páginas.',
               'Menu items reordered or renamed between sections of the same site.',
               'a11ytoolkit audit --pages N (site-level nav-signature comparison); you review the diff.'),
        'en': ('Consistent Navigation',
               'Repeated navigation appears in the same relative order across pages.',
               'Menu items reordered or renamed between sections of the same site.',
               'a11ytoolkit audit --pages N (site-level nav-signature comparison); you review the diff.'),
    }),
    '3.2.4': ('AA', {
        'es': ('Identificación coherente',
               'Lo que funciona igual se identifica igual en todo el sitio.',
               'A search icon labelled "Search" on one page and "Find" on another.',
               'Site-level pass (same crawl); you compare accessible names across pages.'),
        'en': ('Consistent Identification',
               'Components with the same functionality are identified consistently.',
               'A search icon labelled "Search" on one page and "Find" on another.',
               'Site-level pass (same crawl); you compare accessible names across pages.'),
    }),
    '2.4.5': ('AA', {
        'es': ('Múltiples vías',
               'Hay al menos dos formas de encontrar cada página.',
               'Sites where the only path to content is one deep menu.',
               'a11ytoolkit audit --pages N (search input / sitemap link detection across the crawl).'),
        'en': ('Multiple Ways',
               'At least two ways exist to find any page (nav + search/sitemap).',
               'Sites where the only path to content is one deep menu.',
               'a11ytoolkit audit --pages N (search input / sitemap link detection across the crawl).'),
    }),
    '1.2.4': ('AA', {
        'es': ('Subtítulos (directo)',
               'El audio en directo tiene subtítulos sincronizados.',
               'Live streams, webinars with no CART/captioning.',
               'Manual: attend the live session and verify captions exist.'),
        'en': ('Captions (Live)',
               'Live audio content has synchronized captions.',
               'Live streams, webinars with no CART/captioning.',
               'Manual: attend the live session and verify captions exist.'),
    }),
    '2.1.4': ('A', {
        'es': ('Atajos de carácter único',
               'Los atajos de una tecla se pueden desactivar o remapear.',
               'Pressing "s" anywhere triggers search while typing in a field.',
               'Manual: type single letters with focus inside inputs and outside.'),
        'en': ('Character Key Shortcuts',
               'Single-character shortcuts can be turned off, remapped, or active only on focus.',
               'Pressing "s" anywhere triggers search while typing in a field.',
               'Manual: type single letters with focus inside inputs and outside.'),
    }),
    '2.3.1': ('A', {
        'es': ('Tres destellos o menos',
               'Nada parpadea más de 3 veces por segundo.',
               'Videos, animations or GIFs with rapid strobe sections.',
               'Manual (frame-by-frame review); automated flash counting is not implemented anywhere honestly.'),
        'en': ('Three Flashes or Below Threshold',
               'Nothing flashes more than 3 times per second.',
               'Videos, animations or GIFs with rapid strobe sections.',
               'Manual (frame-by-frame review); automated flash counting is not implemented anywhere honestly.'),
    }),
    '2.4.6': ('AA', {
        'es': ('Encabezados y etiquetas',
               'Encabezados y etiquetas describen su tema o propósito.',
               'A heading that says "Section 2"; a form label that says "Field 1".',
               'a11ytoolkit checks structure (empty/skips); descriptiveness is human/agent judgment.'),
        'en': ('Headings and Labels',
               'Headings and labels describe their topic or purpose.',
               'A heading that says "Section 2"; a form label that says "Field 1".',
               'a11ytoolkit checks structure (empty/skips); descriptiveness is human/agent judgment.'),
    }),
    '3.2.1': ('A', {
        'es': ('Al recibir foco',
               'Recibir foco nunca cambia el contexto.',
               'Focus moving to a menu item navigates immediately.',
               'Manual: Tab through the page and watch for unexpected changes.'),
        'en': ('On Focus',
               'Receiving focus never triggers a context change (navigation, form submission).',
               'Focus moving to a menu item navigates immediately.',
               'Manual: Tab through the page and watch for unexpected changes.'),
    }),
    '3.2.2': ('A', {
        'es': ('Al recibir entrada',
               'Cambiar un ajuste nunca cambia el contexto automáticamente.',
               'Selecting from a select navigates without a Submit.',
               'Manual: interact with every control and watch for surprises.'),
        'en': ('On Input',
               'Changing a setting never changes context automatically.',
               'Selecting from a select navigates without a Submit.',
               'Manual: interact with every control and watch for surprises.'),
    }),
    '3.3.1': ('A', {
        'es': ('Identificación de errores',
               'Los errores se identifican y describen en texto.',
               'Forms that just border fields in red with no message.',
               'Manual/agent: submit invalid data and check the announced error.'),
        'en': ('Error Identification',
               'Input errors are identified in text, and described to the user.',
               'Forms that just border fields in red with no message.',
               'Manual/agent: submit invalid data and check the announced error.'),
    }),
    '3.3.3': ('AA', {
        'es': ('Sugerencia ante errores',
               'Los mensajes de error sugieren la corrección cuando se conoce.',
               '"Invalid date" instead of "Use DD/MM/YYYY".',
               'Manual/agent: trigger errors and read the messages.'),
        'en': ('Error Suggestion',
               'Error messages suggest a correction when known.',
               '"Invalid date" instead of "Use DD/MM/YYYY".',
               'Manual/agent: trigger errors and read the messages.'),
    }),
    '3.3.4': ('AA', {
        'es': ('Prevención de errores',
               'Envíos con consecuencias son reversibles, verificados o confirmados.',
               'Purchase buttons with no review step.',
               'Manual: walk the full transaction flow.'),
        'en': ('Error Prevention (Legal, Financial, Data)',
               'Submissions with legal/financial consequences are reversible, checked or confirmed.',
               'Purchase buttons with no review step.',
               'Manual: walk the full transaction flow.'),
    }),
    '3.3.7': ('A', {
        'es': ('Entrada redundante',
               'No se pide reescribir información ya dada.',
               'Multi-step forms asking for the email again.',
               'Manual/agent: walk multi-step flows.'),
        'en': ('Redundant Entry',
               'Information asked before is auto-filled or selectable, not retyped.',
               'Multi-step forms asking for the email again.',
               'Manual/agent: walk multi-step flows.'),
    }),
    '4.1.3': ('AA', {
        'es': ('Mensajes de estado',
               'Los mensajes de estado se anuncian sin mover el foco.',
               'Toasts, "saved" confirmations with no aria-live.',
               'a11y_aria_live_snippet (observe announcements); the scroll auditor checks feed loading announcements.'),
        'en': ('Status Messages',
               'Status messages are announced without moving focus.',
               'Toasts, "saved" confirmations with no aria-live.',
               'a11y_aria_live_snippet (observe announcements); the scroll auditor checks feed loading announcements.'),
    }),
    '4.1.2': ('A', {
        'es': ('Nombre, función, valor',
               'Controles y widgets exponen nombre, función y estado a tecnología asistida.',
               'Botones sin nombre, roles ARIA desconocidos, aria-labelledby roto, slider sin aria-valuenow, aria-hidden en enfocables.',
               'a11y_audit_url / a11y_audit_dom (detección); a11y_snapshot muestra los nombres reales.'),
        'en': ('Name, Role, Value',
               'Controls and widgets expose name, role and state to assistive technology.',
               'Buttons with no name, unknown ARIA roles, broken aria-labelledby, slider without aria-valuenow, aria-hidden on focusables.',
               'a11y_audit_url / a11y_audit_dom (detection); a11y_snapshot shows the real names.'),
    }),

    # ── AAA: la biblia completa (ingesta w3c/wcag 2026-10) ──────────────────
    '1.2.6': ('AAA', {
        'es': ('Lengua de señas (pregrabado)', 'El vídeo pregrabado ofrece interpretación en lengua de señas.', 'Vídeos con subtítulos pero sin interpretación en señas.', 'Manual: verificar que existe la pista o ventana de lengua de señas.'),
        'en': ('Sign Language (Prerecorded)', 'Prerecorded video provides sign language interpretation.', 'Videos with captions but no sign language interpretation.', 'Manual: verify a sign language track or window exists.'),
    }),
    '1.2.7': ('AAA', {
        'es': ('Audiodescripción extendida (pregrabado)', 'La audiodescripción extendida pausa el vídeo cuando hace falta más tiempo.', 'Audiodescripción que se corta porque el vídeo no hace pausas.', 'Manual: reproducir y comprobar que la descripción completa cabe.'),
        'en': ('Extended Audio Description (Prerecorded)', 'Extended audio description pauses the video when more time is needed.', 'Audio description cut off because the video never pauses.', 'Manual: play and check the full description fits.'),
    }),
    '1.2.8': ('AAA', {
        'es': ('Alternativa medial (pregrabado)', 'Toda película pregrabada tiene transcripción textual completa que describe la acción.', 'Vídeos largos sin transcripción descriptiva.', 'Manual: verificar la transcripción y que describe lo esencial visual.'),
        'en': ('Media Alternative (Prerecorded)', 'Every prerecorded movie has a full text transcript describing the action.', 'Long videos without a descriptive transcript.', 'Manual: verify the transcript describes the essential visuals.'),
    }),
    '1.2.9': ('AAA', {
        'es': ('Solo audio (en directo)', 'La transmisión de audio en directo tiene transcripción o equivalente textual.', 'Directos y webinars sin subtítulos ni transcripción en vivo.', 'Manual: verificar la transcripción en vivo o su equivalente.'),
        'en': ('Audio-only (Live)', 'Live audio streams provide a transcript or text alternative.', 'Live events and webinars without live captions or transcript.', 'Manual: verify live transcription or its equivalent.'),
    }),
    '1.3.6': ('AAA', {
        'es': ('Identificar el propósito', 'El propósito de los controles comunes se puede determinar programáticamente (personalización).', 'Controles sin semántica que impiden la personalización por el usuario.', 'a11y_audit_url (roles/estructura) + manual: contrastar con los purposes de WCAG.'),
        'en': ('Identify Purpose', 'The purpose of common controls is programmatically determinable (personalization).', 'Controls without semantics blocking user-side customization.', 'a11y_audit_url (roles/structure) + manual: compare against WCAG purposes.'),
    }),
    '1.4.6': ('AAA', {
        'es': ('Contraste (mejorado)', 'Texto con ratio ≥ 7:1 (≥ 4,5:1 el grande).', 'Gris claro sobre blanco, textos de marca al límite.', 'a11y_contrast_pair con objetivo 7.0; a11y_contrast_dom / a11y_contrast_image en contexto real.'),
        'en': ('Contrast (Enhanced)', 'Text at ≥ 7:1 (≥ 4.5:1 large).', 'Light gray on white, brand colors at the edge.', 'a11y_contrast_pair with 7.0 target; a11y_contrast_dom / a11y_contrast_image in real context.'),
    }),
    '1.4.7': ('AAA', {
        'es': ('Audio de fondo bajo o nulo', 'El audio hablado tiene fondo ≤ 20 dB por debajo de la voz, o se puede apagar.', 'Música alta bajo una locución que no se puede silenciar.', 'Manual: medir o verificar el control de audio de fondo.'),
        'en': ('Low or No Background Audio', 'Speech audio has background ≥ 20 dB below the voice, or it can be turned off.', 'Loud music under narration with no way to mute it.', 'Manual: measure or verify the background-audio control.'),
    }),
    '1.4.8': ('AAA', {
        'es': ('Presentación visual', 'Bloques de texto: selección de colores, 80 columnas, reflujo, justificado no forzado, interlineado/espaciado ajustables.', 'Textos justificados a fuerza de hyphens, sin opciones de espaciado, columnas kilométricas.', 'Manual: probar el reflujo a 320px (a11y_reflow ayuda) y las preferencias de usuario.'),
        'en': ('Visual Presentation', 'Text blocks: color selectable, 80 columns, reflow, no forced justification, adjustable leading/spacing.', 'Force-justified text, no spacing options, kilometer-wide columns.', 'Manual: test reflow at 320px (a11y_reflow helps) and user preferences.'),
    }),
    '1.4.9': ('AAA', {
        'es': ('Imágenes de texto (sin excepción)', 'Texto como texto siempre — salvo esencial (logos) o decorativo.', 'Citas o párrafos enteros renderizados como imagen.', 'a11y_audit_url (images_of_text) + revisión visual de excepciones esenciales.'),
        'en': ('Images of Text (No Exception)', 'Text as text always — except essential (logos) or decorative.', 'Whole quotes or paragraphs rendered as images.', 'a11y_audit_url (images_of_text) + visual review of essential exceptions.'),
    }),
    '2.1.3': ('AAA', {
        'es': ('Teclado (sin excepción)', 'TODA la funcionalidad es operable por teclado, sin excepción de plataforma.', 'Widget que solo funciona con puntero en alguna plataforma.', 'a11y_keyboard (trampas) + recorrido manual completo por teclado.'),
        'en': ('Keyboard (No Exception)', 'ALL functionality is keyboard operable, with no platform exception.', 'A widget that only works with pointer on some platform.', 'a11y_keyboard (traps) + full manual keyboard walk.'),
    }),
    '2.2.3': ('AAA', {
        'es': ('Sin tiempos', 'Ni la interacción ni los eventos tienen límite de tiempo — ni siquiera ajustable.', 'Carrousels que avanzan solos sin control de pausa.', 'Manual: buscar todo avance/timeout automático; a11y_reduced_motion ayuda con animaciones.'),
        'en': ('No Timing', 'No interaction or event has a time limit — not even an adjustable one.', 'Carousels that auto-advance with no pause control.', 'Manual: hunt every auto-advance/timeout; a11y_reduced_motion helps with animation.'),
    }),
    '2.2.4': ('AAA', {
        'es': ('Interrupciones', 'Las interrupciones (avisos, actualizaciones) se pueden aplazar o suprimir.', 'Popups de chat que saltan sobre la tarea y no se silencian.', 'Manual: probar notificaciones y actualizaciones en contexto.'),
        'en': ('Interruptions', 'Interruptions (alerts, updates) can be postponed or suppressed.', 'Chat popups jumping over the task with no way to silence.', 'Manual: test notifications and updates in context.'),
    }),
    '2.2.5': ('AAA', {
        'es': ('Re-autenticación', 'Al re-autenticar tras expirar la sesión, no se pierde el estado ni los datos de la actividad.', 'Formularios que se vacían cuando caduca la sesión a mitad.', 'Manual: dejar caducar la sesión con un formulario a medias.'),
        'en': ('Re-authenticating', 'Re-authenticating after session expiry loses no activity data or state.', 'Forms wiped when the session expires mid-way.', 'Manual: let a half-filled form session expire.'),
    }),
    '2.2.6': ('AAA', {
        'es': ('Tiempos de espera', 'Se avisa de la duración de la inactividad que provoca pérdida de datos (salvo seguridad esencial).', 'Sesiones que caducan sin decir cuánto ni avisar.', 'Manual: revisar avisos de expiración y su antelación.'),
        'en': ('Timeouts', 'Users are warned of the inactivity duration that causes data loss (unless security-essential).', 'Sessions expiring with no duration info or warning.', 'Manual: review expiry notices and their lead time.'),
    }),
    '2.3.2': ('AAA', {
        'es': ('Tres destellos', 'Nada destella más de tres veces por segundo (umbral más estricto que 2.3.1).', 'Animaciones parpadeantes agresivas aunque "justo" bajo el umbral de 2.3.1.', 'Manual + análisis de la frecuencia de parpadeo del contenido.'),
        'en': ('Three Flashes', 'Nothing flashes more than three times per second (stricter threshold than 2.3.1).', 'Aggressive flashing animations "just" under the 2.3.1 threshold.', 'Manual + flash-frequency analysis of the content.'),
    }),
    '2.3.3': ('AAA', {
        'es': ('Animación por interacciones', 'La animación por interacción se puede desactivar (salvo esencial).', 'Parallax y efectos que siguen al scroll/puntero sin off.', 'a11y_reduced_motion (¿respeta prefers-reduced-motion?) + manual de la pausa.'),
        'en': ('Animation from Interactions', 'Motion from interaction can be disabled (unless essential).', 'Parallax and effects tracking scroll/pointer with no off switch.', 'a11y_reduced_motion (honors prefers-reduced-motion?) + manual pause check.'),
    }),
    '2.4.8': ('AAA', {
        'es': ('Ubicación', 'Hay información de la ubicación dentro del conjunto de páginas (breadcrumb o mapa).', 'Páginas profundas sin rastro de dónde estás.', 'Manual: verificar breadcrumb/mapa; a11y_audit_url detecta sitemap/enlaces de ayuda.'),
        'en': ('Location', 'Information about location within the page set exists (breadcrumb or sitemap).', 'Deep pages with no trace of where you are.', 'Manual: verify breadcrumb/sitemap; a11y_audit_url detects sitemap/help links.'),
    }),
    '2.4.9': ('AAA', {
        'es': ('Propósito del enlace (solo enlace)', 'El propósito se entiende SOLO con el texto del enlace, sin contexto.', '"Más", "aquí" como única pista incluso con contexto.', 'a11y_audit_url (generic_link / same_name_links) + revisión editorial.'),
        'en': ('Link Purpose (Link Only)', 'The purpose is understandable from the link text ALONE, no context.', '"More", "here" as the only hint even with context.', 'a11y_audit_url (generic_link / same_name_links) + editorial review.'),
    }),
    '2.4.10': ('AAA', {
        'es': ('Encabezados de sección', 'Las secciones van encabezadas (cuando la estructura lo permite).', 'Muros de texto sin encabezados por sección.', 'a11y_audit_url (heading_skips / no_headings) + revisión de estructura.'),
        'en': ('Section Headings', 'Sections begin with headings (where structure allows).', 'Walls of text with no per-section headings.', 'a11y_audit_url (heading_skips / no_headings) + structure review.'),
    }),
    '2.4.12': ('AAA', {
        'es': ('Foco no oscurecido (mejorado)', 'El foco nunca queda oculto por nada (umbral estricto del 2.4.11).', 'Banners/cookies que tapan el elemento enfocado.', 'a11y_audit_dom (focus_obscured 2.4.11) + recorrido manual estricto.'),
        'en': ('Focus Not Obscured (Enhanced)', 'Focus is never obscured by anything (strict version of 2.4.11).', 'Banners/cookies covering the focused element.', 'a11y_audit_dom (focus_obscured 2.4.11) + strict manual walk.'),
    }),
    '2.4.13': ('AAA', {
        'es': ('Apariencia del foco', 'El indicador de foco: ≥ 2px de perímetro, ≥ 3:1 de contraste, sin que el tamaño del encierre baje.', 'Focos de 1px casi invisibles o con cambio de color únicamente.', 'a11y_audit_dom (focus indicator) + medición manual fina.'),
        'en': ('Focus Appearance', 'Focus indicator: ≥ 2px perimeter, ≥ 3:1 contrast, no enclosure size drop.', '1px near-invisible focus or color-only change.', 'a11y_audit_dom (focus indicator) + fine manual measurement.'),
    }),
    '2.5.5': ('AAA', {
        'es': ('Tamaño del objetivo (mejorado)', 'Objetivos de puntero ≥ 44×44 CSS (con las excepciones del estándar).', 'Iconos de 16px pegados unos a otros.', 'a11y_audit_dom (target_small, umbral AA 24 — el AAA exige 44).'),
        'en': ('Target Size (Enhanced)', 'Pointer targets ≥ 44×44 CSS (with the standard exceptions).', '16px icons crammed together.', 'a11y_audit_dom (target_small, AA threshold 24 — AAA requires 44).'),
    }),
    '2.5.6': ('AAA', {
        'es': ('Mecanismos de entrada concurrentes', 'No restringir el uso de los mecanismos de entrada disponibles (salvo esencial).', 'Forzar a pantalla táctil cuando hay teclado/pointer.', 'Manual: probar entrada alternativa en cada plataforma.'),
        'en': ('Concurrent Input Mechanisms', 'Do not restrict use of available input mechanisms (unless essential).', 'Forcing touch when keyboard/pointer exist.', 'Manual: try an alternative input on each platform.'),
    }),
    '3.1.3': ('AAA', {
        'es': ('Palabras inusuales', 'Las palabras raras, jerga o idioms tienen explicación (glosario o en línea).', 'Jerga de sector sin glosario en una web pública.', 'Manual + revisión editorial; reading_level da el nivel de lectura del texto.'),
        'en': ('Unusual Words', 'Rare words, jargon or idioms are explained (glossary or inline).', 'Industry jargon with no glossary on a public site.', 'Manual + editorial review; reading_level gives the text reading level.'),
    }),
    '3.1.4': ('AAA', {
        'es': ('Abreviaturas', 'Las abreviaturas tienen expansión en su primera aparición (o un glosario).', 'Siglas internas sin expandir jamás.', 'Manual + revisión editorial de primeras apariciones.'),
        'en': ('Abbreviations', 'Abbreviations have an expansion at first use (or a glossary).', 'Internal acronyms never expanded.', 'Manual + editorial review of first occurrences.'),
    }),
    '3.1.5': ('AAA', {
        'es': ('Nivel de lectura', 'Suplementos de comprensión para contenido que exige nivel de lectura superior al inferior de secundaria.', 'Textos legales densos sin resumen en lenguaje claro.', 'reading_level (Fernández-Huerta/Flesch por página) para detectar densidad + redacción de suplementos.'),
        'en': ('Reading Level', 'Comprehension supplements when reading level exceeds lower secondary education.', 'Dense legal text with no plain-language summary.', 'reading_level (Fernández-Huerta/Flesch per page) to spot density + write supplements.'),
    }),
    '3.1.6': ('AAA', {
        'es': ('Pronunciación', 'Cuando el significado depende de la pronunciación, esta se determina programáticamente o por contexto.', 'Homógrafos chinos o puntuación hebrea sin marca de pronunciación.', 'Manual específico del idioma (idiomas con ambigüedad de pronunciación).'),
        'en': ('Pronunciation', 'Where meaning depends on pronunciation, it is programmatically or contextually determinable.', 'Chinese heteronyms or Hebrew punctuation without pronunciation marks.', 'Manual, language-specific (languages with pronunciation ambiguity).'),
    }),
    '3.3.5': ('AAA', {
        'es': ('Ayuda', 'Hay ayuda sensible al contexto para cada paso de un proceso.', 'Formularios complejos sin pista contextual en cada campo difícil.', 'Manual: revisar hints/contexto por paso; a11y_audit_url (help_inconsistent 3.2.6 relacionado).'),
        'en': ('Help', 'Context-sensitive help exists for each step of a process.', 'Complex forms with no contextual hint on each hard field.', 'Manual: review per-step hints; a11y_audit_url (related 3.2.6 help_inconsistent).'),
    }),
    '3.3.6': ('AAA', {
        'es': ('Prevención de errores (todos)', 'Toda sumisión reversible/verificable/corregible — para TODOS los formularios, no solo legales.', 'Cualquier formulario que confirma a ciegas.', 'Manual: recorrer todos los flujos de envío.'),
        'en': ('Error Prevention (All)', 'Every submission reversible/verifiable/correctable — for ALL forms, not just legal ones.', 'Any form that confirms blindly.', 'Manual: walk every submission flow.'),
    }),
    '3.3.9': ('AAA', {
        'es': ('Autenticación accesible (mejorado)', 'Sin prueba de función cognitiva NINGUNA en la autenticación (ni con alternativa: ninguna).', 'Captcha como único paso, sin excepción.', 'Manual del flujo de autenticación completo (registro, login, recuperación).'),
        'en': ('Accessible Authentication (Enhanced)', 'NO cognitive function test at all in authentication (no alternative-based exception either).', 'A captcha as the only step, no exception.', 'Manual review of the full authentication flow (signup, login, recovery).'),
    }),
}

_LEVEL = {'A': 'A', 'AA': 'AA', 'AAA': 'AAA'}

# Human-effort class for every A/AA criterion — what the HUMAN still does after
# the machine's best signal. Used for review-marketplace pricing interlocks
# and emitted in the evidence pack matrix.
#   MIN (1-3 min):  the agent verified with a measured signal; the human reads and confirms.
#   MED (5-10 min): the agent prepares context; the human verifies in the browser.
#   MAX (15-30 min): real interaction, real judgment, real tooling.
# A not-flagged on a partially-covered criterion never earns a lower class:
# "the machine looked and found nothing" is weaker than a confirmation.
_EFFORT = {
    '1.1.1': ('MIN', 'alt presence is measured; scan for the image the heuristic missed.'),
    '1.2.2': ('MIN', 'caption track presence detected; confirm the captions are real.'),
    '1.3.3': ('MIN', 'sensory-instruction phrases detected; read the instructions once.'),
    '1.3.4': ('MIN', 'orientation-lock CSS/JS detected; confirm on a device.'),
    '1.3.5': ('MIN', 'autocomplete token per input measured; confirm.'),
    '1.4.2': ('MIN', 'autoplay-with-audio detected; confirm.'),
    '1.4.4': ('MIN', 'viewport zoom block measured; confirm.'),
    '2.2.1': ('MIN', 'meta refresh and timing scripts detected; confirm.'),
    '2.4.1': ('MIN', 'missing main/skip detected; confirm.'),
    '2.4.2': ('MIN', 'missing or empty title detected; confirm.'),
    '2.4.3': ('MIN', 'positive tabindex detected; confirm.'),
    '2.4.4': ('MIN', 'generic link text detected; read the links in context.'),
    '2.5.2': ('MIN', 'down-event-only handlers detected; confirm.'),
    '2.5.3': ('MIN', 'label-in-name mismatch computed; confirm.'),
    '2.5.4': ('MIN', 'motion actuation without UI detected; confirm.'),
    '3.1.1': ('MIN', 'page lang missing or invalid, measured; confirm.'),
    '3.1.2': ('MIN', 'part lang invalid, measured; confirm.'),
    '3.2.1': ('MIN', 'focus-triggered navigation detected; confirm.'),
    '3.2.2': ('MIN', 'select-triggered navigation detected; confirm.'),
    '3.2.6': ('MIN', 'help presence compared across crawled pages; confirm.'),
    '3.3.2': ('MIN', 'placeholder-only and unlabeled required fields measured; read each label.'),
    '3.3.8': ('MIN', 'captcha detected; confirm an alternative exists.'),
    '4.1.2': ('MIN', 'invalid roles, broken refs and missing state measured; confirm.'),
    '1.2.1': ('MED', 'media tags detected; play the media and judge the alternative.'),
    '1.3.1': ('MED', 'semantic structure signals (fieldsets, heading skips, lists); navigate with a screen reader.'),
    '1.3.2': ('MED', 'DOM vs visual order from snapshot and tab walk; spot-check layout exceptions.'),
    '1.4.1': ('MED', 'link-vs-text color ratio computed; verify visually.'),
    '1.4.5': ('MED', 'images-of-text candidates detected; judge logo and text exceptions.'),
    '1.4.10': ('MED', '320px reflow measured with real overflow; navigate the reflowed content.'),
    '1.4.11': ('MED', 'focus-indicator contrast computed; verify visually.'),
    '1.4.12': ('MED', 'text-spacing overrides injected, clipping counted; verify.'),
    '1.4.13': ('MED', 'hover + Escape dismissibility tested; verify.'),
    '2.1.1': ('MED', 'click handlers on non-interactive elements detected; Tab the page.'),
    '2.2.2': ('MED', 'looping animations computed; verify the pause control.'),
    '2.4.5': ('MED', 'nav/sitemap/search presence from the crawl; confirm.'),
    '2.4.6': ('MED', 'vague headings detected; read them in context.'),
    '2.4.11': ('MED', 'sticky header vs scroll-padding measured; Tab the page.'),
    '2.5.1': ('MED', 'gesture listeners without alternatives detected; try the gesture.'),
    '2.5.7': ('MED', 'drag listeners detected; try the click path.'),
    '2.5.8': ('MED', 'target rects measured; check the inline/equivalent exceptions.'),
    '3.2.3': ('MED', 'nav consistency compared across crawled pages; confirm the order.'),
    '3.2.4': ('MED', 'consistent identification compared across pages; confirm the icons.'),
    '1.2.3': ('MAX', 'watch the media and judge whether an alternative covers essential visuals.'),
    '1.2.4': ('MAX', 'live captions must be watched and judged; no honest signal.'),
    '1.2.5': ('MAX', 'audio description requires watching and judging the video.'),
    '1.4.3': ('MAX', 'computed ratios are evidence, not verdicts; gradients, images and hover states still need review.'),
    '2.1.2': ('MAX', 'real Tab walk plus Escape test per modal and iframe.'),
    '2.1.4': ('MAX', 'single-character shortcuts tested by typing in every field.'),
    '2.3.1': ('MAX', 'flash threshold needs frame-by-frame analysis; no honest signal.'),
    '2.4.7': ('MAX', 'focus visibility measured per stop; Tab the whole site.'),
    '3.3.1': ('MAX', 'invalid submissions fired and the DOM judged; verify with a screen reader.'),
    '3.3.3': ('MAX', 'read and judge each correction suggestion.'),
    '3.3.4': ('MAX', 'reversible-transaction check requires walking the flow.'),
    '3.3.7': ('MAX', 'redundant entry requires a remembered multi-step walk.'),
    '4.1.3': ('MAX', 'fire each status message and listen for the announcement.'),
}

_EFFORT_MINUTES = {'MIN': (1, 3), 'MED': (5, 10), 'MAX': (15, 30)}

# Criterios A/AA que SOLO el modo renderizado puede medir (a11y_audit_dom):
# contraste computado, espaciado, tamaño de objetivo, foco, formularios vivos…
# El informe estático los declara en `not_measured` — un 100 estático jamás
# debe leerse como "contraste bien" (la limitación que la crítica externa
# destapó: .btn-primary{background:var(--x)} es invisible para el HTML puro).
RENDERED_ONLY = frozenset({
    '1.3.2', '1.4.1', '1.4.3', '1.4.10', '1.4.11', '1.4.12', '1.4.13',
    '2.1.2', '2.2.2', '2.4.7', '2.4.11', '2.5.8', '3.2.1', '3.2.2',
    '3.3.1', '3.3.3', '4.1.3',
})



# Señal del motor → criterio WCAG que alimenta. Derivado empíricamente de los
# puntos de emisión (add/_add/_agrega y dicts _CRIT) — el test de invariantes
# re-deriva este mapa del código y compara: una señal nueva sin entrada falla.
_SIGNAL_CRIT = {
    # — emisiones no derivables por regex (llamada multi-línea / clave variable) —
    'target_small': '2.5.8',
    'vtt_malformed': '1.2.2', 'vtt_no_cues': '1.2.2', 'vtt_empty_cue': '1.2.2',
    'vtt_overlap': '1.2.2', 'vtt_too_fast': '1.2.2', 'vtt_coverage': '1.2.2',
    'accesskey_dup': '2.1.1',
    'aria_hidden_focusable': '4.1.2',
    'aria_ref_missing': '4.1.2',
    'aria_value_invalid': '4.1.2',
    'audio_desc_missing': '1.2.3',
    'autocomplete': '1.3.5',
    'autocomplete_invalid': '1.3.5',
    'blank_no_warning': '3.2.5',
    'captcha': '3.3.8',
    'char_shortcut': '2.1.4',
    'click_nonfocusable': '2.1.1',
    'color_only_link': '1.4.1',
    'contrast_fail': '1.4.3',
    'contrast_image_fail': '1.4.3',
    'contrast_review': '1.4.3',
    'ctrl_name': '4.1.2',
    'docx_fake_headings': '1.3.1',
    'docx_no_alt': '1.1.1',
    'docx_no_lang': '3.1.1',
    'docx_table_no_header': '1.3.1',
    'dom_visual_order': '1.3.2',
    'down_event': '2.5.2',
    'drag_no_alt': '2.5.7',
    'dup_ids': '4.1.2',
    'element_lang_invalid': '3.1.2',
    'empty_heading': '1.3.1',
    'field_label': '3.3.2',
    'fieldset_missing': '1.3.1',
    'financial_no_confirm': '3.3.4',
    'focus_invisible': '2.4.7',
    'focus_navigates': '3.2.1',
    'focus_not_focusable': '2.4.7',
    'focus_obscured': '2.4.11',
    'forced_colors_svg': '1.4.3',
    'form_error_missing': '3.3.1',
    'form_error_no_suggestion': '3.3.3',
    'form_navigated': '3.3.1',
    'generic_link': '2.4.4',
    'gesture_no_click': '2.5.1',
    'heading_quality': '2.4.6',
    'heading_skips': '1.3.1',
    'help_inconsistent': '3.2.6',
    'hover_not_dismissible': '1.4.13',
    'iframe_title': '4.1.2',
    'images_of_text': '1.4.5',
    'img_no_alt': '1.1.1',
    'input_img_alt': '1.1.1',
    'input_navigates': '3.2.2',
    'journey_dialog_trap': '2.1.2',
    'journey_duplicate_targets': '4.1.2',
    'journey_dynamic_stale': '4.1.3',
    'journey_error_silent': '3.3.1',
    'journey_focus_lost': '2.4.3',
    'journey_generic_link': '2.4.4',
    'journey_heading_nav_broken': '2.4.6',
    'journey_hidden_in_tree': '1.3.1',
    'journey_landmark_missing': '2.4.1',
    'journey_mode_confusion': '4.1.2',
    'journey_no_instruction': '3.3.2',
    'journey_reach_fail': '2.1.1',
    'journey_status_silent': '4.1.3',
    'journey_timeout_confusion': '2.2.1',
    'journey_unnamed_control': '4.1.2',
    'kbd_trap': '2.1.2',
    'label_in_name': '2.5.3',
    'label_orphan': '3.3.2',
    'label_vague': '2.4.6',
    'landmark_dup': '1.3.1',
    'lang_invalid': '3.1.1',
    'lang_missing': '3.1.1',
    'lang_region_invalid': '3.1.1',
    'list_structure': '1.3.1',
    'meta_refresh': '2.2.1',
    'motion_actuation': '2.5.4',
    'motion_moving': '2.2.2',
    'multi_h1': '1.3.1',
    'multi_label': '3.3.2',
    'nav_inconsistent': '3.2.3',
    'no_bypass': '2.4.1',
    'no_h1': '1.3.1',
    'no_headings': '1.3.1',
    'no_multiple_ways': '2.4.5',
    'no_status_regions': '4.1.3',
    'orientation_lock': '1.3.4',
    'pdf_encrypted': '1.1.1',
    'pdf_fake_link': '2.4.4',
    'pdf_form_no_label': '3.3.2',
    'pdf_button_no_name': '4.1.2',
    'pdf_low_contrast': '1.4.3',
    'pdf_no_alt': '1.1.1',
    'pdf_no_lang': '3.1.1',
    'pdf_no_outline': '1.3.1',
    'pdf_no_title': '2.4.2',
    'pdf_scanned': '1.1.1',
    'pdf_untagged': '1.3.1',
    'placeholder_only': '3.3.2',
    'reduced_motion_ignored': '2.2.2',
    'reflow_fail': '1.4.10',
    'required_no_indication': '3.3.2',
    'role_required_attr': '4.1.2',
    'role_unknown': '4.1.2',
    'same_name_links': '2.4.4',
    'scroll_focus': '2.4.3',
    'scroll_no_announce': '4.1.3',
    'scroll_no_end': '2.2.2',
    'scroll_no_feed': '1.3.1',
    'sensory_text': '1.3.3',
    'state_contrast': '1.4.3',
    'tabindex_pos': '2.4.3',
    'table_no_th': '1.3.1',
    'text_spacing_clip': '1.4.12',
    'title_generic': '2.4.2',
    'title_missing': '2.4.2',
    'video_autoplay': '1.4.2',
    'video_captions': '1.2.2',
    'zoom_max': '1.4.4',
    'zoom_no': '1.4.4'
}

def criterion(code=None, lang='en', signal=None):
    from .a11yact import act_rules_for
    if signal:
        from .a11yaudit import normalize_signal
        signal = normalize_signal(signal.strip())
        if signal in _SIGNAL_CRIT:
            code = _SIGNAL_CRIT[signal]
        else:
            return {'error': f'señal desconocida: {signal}',
                    'known_signals': len(_SIGNAL_CRIT),
                    'hint': 'signal ids appear in every audit finding'}
    code = code.strip()
    if code not in _C:
        return {'error': f'criterio desconocido: {code}',
                'available': sorted(_C)}
    level, languages = _C[code]
    name, requires, failures, how_to_check = languages.get(lang) or languages['es']
    out = {
        'criterion': f'{code} {name}',
        'level': _LEVEL[level],
        'understanding': (f'https://www.w3.org/WAI/WCAG22/Understanding/'
                          f'{_UNDERSTANDING[code]}.html') if code in _UNDERSTANDING else None,
        'toolkit_signals': sorted(s for s, c in _SIGNAL_CRIT.items() if c == code),
    }
    if signal:
        out['signal'] = signal
        out['act_rules'] = act_rules_for(signal)
        return out
    out.update({
        'requires': requires,
        'typical_failures': failures,
        'how_to_check': how_to_check,
        'note': ('Esto resume el criterio, no sustituye su texto oficial en '
                 'https://www.w3.org/TR/WCAG22/#' if lang == 'es' else
                 'This summarizes the criterion; the official text at '
                 'https://www.w3.org/TR/WCAG22/# governs.'),
    })
    return out


def effort(code):
    """Human-effort class for an A/AA criterion: {clase, porque, minutos} or None."""
    if code not in _EFFORT:
        return None
    grade, why = _EFFORT[code]
    return {'class': grade, 'why': why, 'minutes': list(_EFFORT_MINUTES[grade])}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('code', nargs='?')
    ap.add_argument('--signal', help='engine signal id (e.g. kbd_trap) instead of a criterion code')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args(argv)
    if a.list or not (a.code or a.signal):
        print(json.dumps({'available_criteria': sorted(_C)}, indent=1))
        return 0
    print(json.dumps(criterion(a.code, a.lang, signal=a.signal), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
