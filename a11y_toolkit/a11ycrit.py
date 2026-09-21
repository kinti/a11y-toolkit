#!/usr/bin/env python3
"""WCAG 2.2 criterion knowledge (es/en) — the "what it is" behind the auditor.

a11y_criterion(code) returns, for every criterion the toolkit evaluates: the
official name, level, what it requires, typical failures, how to verify it
manually and with which toolkit tool. It is the bridge between an automated
finding and actually understanding the criterion.

CLI:
  a11ycrit.py 2.5.8 [--lang es]
  a11ycrit.py --list
"""

import argparse
import json
import sys

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
        'es': ('Imágenes de texto', 'Salvo logotipos, el texto se presenta como texto real, no como imagen.', 'Headings or paragraphs rendered as PNG/JPG; banner text baked into hero images.', 'a11y_audit_url flags images inside headings and book-length alts (review signal); you judg'),
        'en': ('Images of Text', 'Except for logotypes, text is presented as real text, not images of text.', 'Headings or paragraphs rendered as PNG/JPG; banner text baked into hero images.', 'a11y_audit_url flags images inside headings and book-length alts (review signal); you judg'),
    }),
    '1.4.11': ('AA', {
        'es': ('Contraste no textual', 'Componentes UI y objetos gráficos tienen al menos 3:1 contra colores adyacentes.', 'Icon buttons barely visible against their background; focus indicators too faint to see.', 'a11y_contrast_pair with target 3.0 for UI elements; the rendered audit checks focus-indica'),
        'en': ('Non-text Contrast', 'UI components and graphical objects have at least 3:1 contrast against adjacent colors.', 'Icon buttons barely visible against their background; focus indicators too faint to see.', 'a11y_contrast_pair with target 3.0 for UI elements; the rendered audit checks focus-indica'),
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
               'a11y_audit_url / a11y_audit_dom (detection); you verify a pause control actually exists an'),
        'en': ('Pause, Stop, Hide',
               'Moving, blinking or auto-updating content that starts automatically and lasts >5s can be paused, stopped or hi',
               '<marquee>, looping CSS animations, auto-updating tickers with no pause control.',
               'a11y_audit_url / a11y_audit_dom (detection); you verify a pause control actually exists an'),
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
               'a11y_audit_url (devicemotion/orientation handler suspicion); you verify the UI alternative'),
        'en': ('Motion Actuation',
               'Functions triggered by device motion can also be triggered by UI, and the motion trigger can be disabled.',
               'Shake-to-undo, tilt-to-scroll with no button alternative.',
               'a11y_audit_url (devicemotion/orientation handler suspicion); you verify the UI alternative'),
    }),
    '1.4.1': ('A', {
        'es': ('Uso del color',
               'El color nunca es el único medio visual de transmitir información.',
               'Links inside prose distinguished only by a slightly different color; "fields in red are re',
               'a11y_audit_dom (link-in-text-block color/underline check); you scan the page for color-onl'),
        'en': ('Use of Color',
               'Color is never the only visual means of conveying information.',
               'Links inside prose distinguished only by a slightly different color; "fields in red are re',
               'a11y_audit_dom (link-in-text-block color/underline check); you scan the page for color-onl'),
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
               'a11y_audit_url (track absence); a human watching the video decides if description is neede'),
        'en': ('Audio Description or Media Alternative',
               'Prerecorded video has audio description or a media alternative.',
               'Videos with essential visual information and no descriptions track.',
               'a11y_audit_url (track absence); a human watching the video decides if description is neede'),
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
               'Manual (frame-by-frame review); automated flash counting is not implemented anywhere hones'),
        'en': ('Three Flashes or Below Threshold',
               'Nothing flashes more than 3 times per second.',
               'Videos, animations or GIFs with rapid strobe sections.',
               'Manual (frame-by-frame review); automated flash counting is not implemented anywhere hones'),
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
               'a11y_aria_live_snippet (observe announcements); the scroll auditor checks feed loading ann'),
        'en': ('Status Messages',
               'Status messages are announced without moving focus.',
               'Toasts, "saved" confirmations with no aria-live.',
               'a11y_aria_live_snippet (observe announcements); the scroll auditor checks feed loading ann'),
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
}

_NIVEL = {'A': 'A', 'AA': 'AA', 'AAA': 'AAA'}

# Human-effort class for every A/AA criterion — what the HUMAN still does after
# the machine's best signal. Used for review pricing (Countersignatory interlock)
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


def criterio(code, lang='en'):
    code = code.strip()
    if code not in _C:
        return {'error': f'criterio desconocido: {code}',
                'disponibles': sorted(_C)}
    nivel, idiomas = _C[code]
    nombre, exige, fallos, prueba = idiomas.get(lang) or idiomas['es']
    return {
        'criterio': f'{code} {nombre}',
        'nivel': _NIVEL[nivel],
        'exige': exige,
        'fallos_habituales': fallos,
        'como_comprobar': prueba,
        'nota': ('Esto resume el criterio, no sustituye su texto oficial en '
                 'https://www.w3.org/TR/WCAG22/#' if lang == 'es' else
                 'This summarizes the criterion; the official text at '
                 'https://www.w3.org/TR/WCAG22/# governs.'),
    }


def effort(code):
    """Human-effort class for an A/AA criterion: {clase, porque, minutos} or None."""
    if code not in _EFFORT:
        return None
    clase, why = _EFFORT[code]
    return {'clase': clase, 'porque': why, 'minutos': list(_EFFORT_MINUTES[clase])}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('code', nargs='?')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args(argv)
    if a.list or not a.code:
        print(json.dumps({'criterios_disponibles': sorted(_C)}, indent=1))
        return 0
    print(json.dumps(criterio(a.code, a.lang), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
