#!/usr/bin/env python3
"""Express WCAG 2.2 audit over HTML (heuristics, zero dependencies).

a11y_audit_url / audit_html check automatic signals mapped to concrete WCAG
2.2 criteria. Every finding carries concrete remediation.

Criteria covered (static): 1.1.1, 1.2.2, 1.3.1, 1.4.4, 2.1.1, 2.2.1, 2.4.1,
2.4.2, 2.4.3, 3.1.1, 3.2.5, 3.3.2, 4.1.2 (+ 1.3.5, 1.4.2, 2.4.4 and ARIA
value validation since v3.1+).

Automation covers ~one third of WCAG: manual review remains irreplaceable.
This tool is a filter, not a verdict.

CLI:
  a11yaudit.py --url https://example.com [--lang es]
  a11yaudit.py --file page.html
"""

import argparse
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser

MAX_HTML = 3_000_000

# Campos de formulario que necesitan etiqueta visible o nombre accesible
_CAMPOS = {'text', 'email', 'tel', 'url', 'search', 'password', 'number',
           'date', 'time', 'datetime-local', 'month', 'week'}
_CONTROLES = ('a', 'button', 'summary')

# Subetiquetas BCP-47 principales habituales (validación blanda)
_LANG_CODES = set('''af am ar az be bg bn bs ca cs cy da de el en es et eu fa fi fr ga gl
gu he hi hr hu hy id is it ja ka kk km kn ko ky lo lt lv mk ml mn mr ms my ne nl or pa
pl ps pt ro ru rw si sk sl sq sr sv sw ta te tg th ti tk tr uk ur uz vi zh'''.split())

# Roles ARIA concretos (WAI-ARIA 1.2); doc- se admite como prefijo de DPUB
_ROLES_ARIA = set('''alert alertdialog application article banner button caption cell
checkbox code columnheader combobox complementary contentinfo definition deletion dialog
directory document emphasis feed figure form generic grid gridcell group heading img image
input insertion link list listbox listitem log main mark marquee math menu menubar menuitem
menuitemcheckbox menuitemradio meter navigation none note option paragraph presentation
progressbar radio radiogroup region row rowgroup rowheader scrollbar search searchbox
section sectionhead select separator slider spinbutton status strong subscript superscript
switch tab table tablist tabpanel term textbox time timer toolbar tooltip tree treegrid
treeitem'''.split())

# Texto de enlace sin propósito (2.4.4), es + en
_TEXTO_GENERICO = {'more', 'read more', 'learn more', 'click here', 'here', 'this',
                   'this link', 'link', 'details', 'view', 'see more', 'continue',
                   'más', 'leer más', 'saber más', 'pincha aquí', 'aquí', 'ver más',
                   'seguir leyendo', 'detalle', 'detalles', 'enlace', 'continuar', 'ver'}

# 1.3.3: instructions that rely on position/shape alone (es + en, review-only)
_SENSORIAL = re.compile(
    r'(?:el|la|los|las)?\s*(?:bot[oó]n|enlace|icono)\s+(?:de|a|hacia)\s+(?:la\s+)?'
    r'(?:derecha|izquierda|arriba|abajo)|(?:pulsa|haz clic en)\s+(?:el|la)\s+'
    r'(?:redondo|verde|cuadrado)|(?:the\s+)?(?:button|link|icon)\s+(?:on|to)\s+(?:the\s+)?'
    r'(?:right|left|top|bottom)|(?:click|press)\s+(?:the\s+)?(?:round|green|square)', re.I)

# detección extendida de autocomplete (1.3.5)


# Campos que con frecuencia recogen datos personales (1.3.5)
_DATO_PERSONAL = re.compile(
    r'(^|[\W_])(name|nombre|email|correo|phone|telefono|tel|address|direccion|postal|zip|'
    r'city|ciudad|country|pais|organi[sz]ation|company|empresa|street|user|usuario)([\W_]|$)', re.I)

# Validación de VALORES aria-* (estilo axe aria-valid-attr-value)
_ARIA_BOOL = {'aria-hidden', 'aria-expanded', 'aria-selected', 'aria-pressed',
              'aria-checked', 'aria-disabled', 'aria-required', 'aria-readonly',
              'aria-multiline', 'aria-multiselectable', 'aria-modal', 'aria-grabbed'}
_ARIA_INT = {'aria-level', 'aria-posinset', 'aria-setsize', 'aria-colcount',
             'aria-rowcount', 'aria-colindex', 'aria-rowindex', 'aria-colspan',
             'aria-rowspan'}
_ARIA_NUM = {'aria-valuenow', 'aria-valuemin', 'aria-valuemax'}
_ARIA_TOKENS = {
    'aria-sort': {'ascending', 'descending', 'none', 'other'},
    'aria-current': {'page', 'step', 'location', 'date', 'time', 'true', 'false', ''},
    'aria-autocomplete': {'inline', 'list', 'both', 'none', ''},
    'aria-live': {'off', 'polite', 'assertive'},
    'aria-orientation': {'horizontal', 'vertical', 'undefined'},
    'aria-relevant': {'additions', 'removals', 'text', 'all'},
}
_ARIA_IDREFS = {'aria-labelledby', 'aria-describedby', 'aria-controls', 'aria-errormessage'}

CRIT = {
    'es': {
        '1.1.1': '1.1.1 Contenido no textual',
        '1.2.2': '1.2.2 Subtítulos (pregrabado)',
        '1.3.1': '1.3.1 Información y relaciones',
        '1.4.4': '1.4.4 Cambio de tamaño del texto',
        '2.1.1': '2.1.1 Teclado',
        '2.2.1': '2.2.1 Tiempo ajustable',
        '2.4.1': '2.4.1 Evitación de bloques',
        '2.4.2': '2.4.2 Página con título',
        '2.4.3': '2.4.3 Orden del foco',
        '3.1.1': '3.1.1 Idioma de la página',
        '3.2.5': '3.2.5 Cambio a petición',
        '3.3.2': '3.3.2 Etiquetas o instrucciones',
        '1.3.5': '1.3.5 Identificar el propósito de la entrada',
        '2.5.2': '2.5.2 Cancelación del puntero',
        '2.5.3': '2.5.3 Etiqueta en el nombre',
        '3.1.2': '3.1.2 Idioma de las partes',
        '3.3.8': '3.3.8 Autenticación accesible',
        '3.3.1': '3.3.1 Identificación de errores',
        '3.3.4': '3.3.4 Prevención de errores (legal, financiero)',
        '2.4.6': '2.4.6 Encabezados y etiquetas (calidad)',
        '2.1.4': '2.1.4 Atajos de carácter único',
        '2.5.7': '2.5.7 Movimientos de arrastre',
        '3.2.1': '3.2.1 Al recibir foco',
        '3.2.2': '3.2.2 Al recibir entrada',
        '4.1.3': '4.1.3 Mensajes de estado',
        '3.2.6': '3.2.6 Ayuda coherente',
        '1.4.5': '1.4.5 Imágenes de texto',
        '1.4.11': '1.4.11 Contraste no textual',
        '1.4.13': '1.4.13 Contenido al pasar el foco o el puntero',
        '3.3.3': '3.3.3 Sugerencia ante errores',
        '1.4.2': '1.4.2 Control del audio',
        '1.4.3': '1.4.3 Contraste (mínimo)',
        '2.4.4': '2.4.4 Propósito de los enlaces (en contexto)',
        '4.1.2': '4.1.2 Nombre, función, valor',

        # criterios evaluados por el modo renderizado (a11ydom) — explícitos
        # aquí para que el catálogo sea completo sin depender de import colateral
        '2.4.7': '2.4.7 Foco visible',
        '2.2.2': '2.2.2 Poner en pausa, detener, ocultar',
        '2.5.1': '2.5.1 Gestos de puntero',
        '2.5.4': '2.5.4 Activación por movimiento',
        '1.4.1': '1.4.1 Uso del color',
        '1.3.2': '1.3.2 Secuencia significativa',
        '1.3.3': '1.3.3 Características sensoriales',
        '1.3.4': '1.3.4 Orientación',
        '1.2.3': '1.2.3 Audiodescripción o alternativa media',
        '1.2.5': '1.2.5 Audiodescripción (pregrabado)',
        '3.2.3': '3.2.3 Navegación coherente',
        '3.2.4': '3.2.4 Identificación coherente',
        '2.4.5': '2.4.5 Múltiples vías',
        '2.5.8': '2.5.8 Tamaño del objetivo (mínimo)',
        '1.4.10': '1.4.10 Reflujo',
        '2.1.2': '2.1.2 Sin trampa de teclado',
        '2.4.11': '2.4.11 Foco no ocultado (mínimo)',
    },
    'en': {
        '1.1.1': '1.1.1 Non-text Content',
        '1.2.2': '1.2.2 Captions (Prerecorded)',
        '1.3.1': '1.3.1 Info and Relationships',
        '1.4.4': '1.4.4 Resize Text',
        '2.1.1': '2.1.1 Keyboard',
        '2.2.1': '2.2.1 Timing Adjustable',
        '2.4.1': '2.4.1 Bypass Blocks',
        '2.4.2': '2.4.2 Page Titled',
        '2.4.3': '2.4.3 Focus Order',
        '3.1.1': '3.1.1 Language of Page',
        '3.2.5': '3.2.5 Change on Request',
        '3.3.2': '3.3.2 Labels or Instructions',
        '1.3.5': '1.3.5 Identify Input Purpose',
        '2.5.2': '2.5.2 Pointer Cancellation',
        '2.5.3': '2.5.3 Label in Name',
        '3.1.2': '3.1.2 Language of Parts',
        '3.3.8': '3.3.8 Accessible Authentication',
        '3.3.1': '3.3.1 Error Identification',
        '3.3.4': '3.3.4 Error Prevention (Legal, Financial)',
        '2.4.6': '2.4.6 Headings and Labels (quality)',
        '2.1.4': '2.1.4 Character Key Shortcuts',
        '2.5.7': '2.5.7 Dragging Movements',
        '3.2.1': '3.2.1 On Focus',
        '3.2.2': '3.2.2 On Input',
        '4.1.3': '4.1.3 Status Messages',
        '3.2.6': '3.2.6 Consistent Help',
        '1.4.5': '1.4.5 Images of Text',
        '1.4.11': '1.4.11 Non-text Contrast',
        '1.4.13': '1.4.13 Content on Hover or Focus',
        '3.3.3': '3.3.3 Error Suggestion',
        '1.4.2': '1.4.2 Audio Control',
        '1.4.3': '1.4.3 Contrast (Minimum)',
        '2.4.4': '2.4.4 Link Purpose (In Context)',
        '4.1.2': '4.1.2 Name, Role, Value',

        '2.4.7': '2.4.7 Focus Visible',
        '2.2.2': '2.2.2 Pause, Stop, Hide',
        '2.5.1': '2.5.1 Pointer Gestures',
        '2.5.4': '2.5.4 Motion Actuation',
        '1.4.1': '1.4.1 Use of Color',
        '1.3.2': '1.3.2 Meaningful Sequence',
        '1.3.3': '1.3.3 Sensory Characteristics',
        '1.3.4': '1.3.4 Orientation',
        '1.2.3': '1.2.3 Audio Description or Media Alternative',
        '1.2.5': '1.2.5 Audio Description (Prerecorded)',
        '3.2.3': '3.2.3 Consistent Navigation',
        '3.2.4': '3.2.4 Consistent Identification',
        '2.4.5': '2.4.5 Multiple Ways',
        '2.5.8': '2.5.8 Target Size (Minimum)',
        '1.4.10': '1.4.10 Reflow',
        '2.1.2': '2.1.2 No Keyboard Trap',
        '2.4.11': '2.4.11 Focus Not Obscured (Minimum)',
    },
}

T = {
    'es': {
        'descarga_error': 'no se pudo descargar: {e}',
        'imgs_alt': '{n} <img> sin atributo alt (ni siquiera alt="").',
        'imgs_alt_rem': 'Añade alt a cada <img>: texto descriptivo si aporta información, alt="" si es decorativa. En <input type="image"> y <area> es igual de obligatorio.',
        'input_img_alt': '<input type="image"> sin alt (botón gráfico sin nombre).',
        'input_img_alt_rem': 'Añade alt descriptivo al input type="image" (es su nombre accesible), o sustitúyelo por <button> con texto o <input type="submit" value="…">.',
        'ctrl_name': '{n} <{tag}> sin nombre accesible (sin texto, aria-label ni title).',
        'ctrl_name_rem': 'El nombre accesible llega del texto interno, aria-label, title o de una imagen interna con alt. Un control vacío es invisible para lectores de pantalla.',
        'aria_hidden_focusable': '{n} elementos interactivos (<{tag}>) con aria-hidden="true": ocultos al lector pero siguen recibiendo foco.',
        'aria_hidden_focusable_rem': 'Quita aria-hidden del elemento enfocable, o añade tabindex="-1" si debe quedar fuera de la interacción.',
        'field_label': '{n} campos de formulario sin <label> asociado ni nombre accesible.',
        'field_label_rem': 'Asocia <label for="id"> al campo (o envuélvelo), o usa aria-label. Aplica a input, select y textarea.',
        'click_nonfocusable': '{n} elementos no interactivos (<{tag}>) con onclick sin role, tabindex ni manejo de teclado.',
        'click_nonfocusable_rem': 'Usa <button> real; si no es posible, añade role="button", tabindex="0" y manejo de Enter/Espacio (2.1.1).',
        'label_orphan': '{n} <label> sin for y sin campo anidado: no etiquetan nada.',
        'label_orphan_rem': 'Conecta el label con su campo: for="id" del campo, o mueve el campo dentro del label.',
        'iframe_title': '{n} <iframe> sin title accesible.',
        'iframe_title_rem': 'Añade title descriptivo al iframe (lo anuncian los lectores al llegar a él).',
        'video_captions': '{n} <video> sin <track kind="captions">.',
        'video_captions_rem': 'Publica subtítulos para el audio del vídeo (1.2.2). Si es decorativo y sin audio, márcalo como tal.',
        'lang_missing': 'El elemento <html> no declara lang.',
        'lang_missing_rem': 'Añade lang="es" (o el idioma real) a <html>: lectores de pantalla eligen la voz sintética por él.',
        'lang_invalid': 'lang="{lang}" no es un código de idioma válido (BCP-47).',
        'lang_invalid_rem': 'Usa el subtag principal ISO 639 correcto (es, en, pt…).',
        'title_missing': 'La página no tiene <title> con contenido.',
        'title_missing_rem': 'Escribe un <title> único y descriptivo por página (primer anuncio del lector, texto de la pestaña).',
        'heading_quality': '{n} encabezados/labels sospechosamente genéricos o vagos: {ej}. Revisar (2.4.6).',
        'heading_quality_rem': 'Los encabezados deben describir su sección: «Resultados del informe Q3», no «Sección 2» o «Más información» (2.4.6). Nombra las cosas.',
        'char_shortcut': '{n} atajos de teclado de carácter único detectados: {ej}. Revisar (2.1.4).',
        'char_shortcut_rem': 'Los atajos de una tecla deben poder desactivarse o remapearse, o activarse solo con foco (2.1.4): el usuario que dicta por voz dispara cada letra.',
        'drag_no_alt': '{n} manejadores de arrastre sin alternativa visible de clic/botón: {ej}. Revisar (2.5.7).',
        'drag_no_alt_rem': 'Toda acción por arrastre necesita alternativa sin arrastre: botones «arriba/abajo», menú contextual, flechas (2.5.7).',
        'no_status_regions': 'No se detectan regiones de estado (aria-live/status/alert) en la página: los mensajes dinámicos no se anunciarán (4.1.3).',
        'no_status_regions_rem': 'Añade role="status" o aria-live="polite" para toasts, confirmaciones de guardado, resultados de búsqueda (4.1.3).',
        'placeholder_only': '{n} campos con placeholder como única etiqueta (sin <label>): {ej}. El placeholder desaparece al teclear (3.3.2).',
        'placeholder_only_rem': 'El placeholder NO es una etiqueta: añade <label for="id"> visible. El placeholder desaparece al empezar a escribir y los lectores no siempre lo anuncian (3.3.2).',
        'required_no_indication': '{n} campos required sin indicación visible de obligatoriedad: {ej} (3.3.2).',
        'required_no_indication_rem': 'Los campos obligatorios deben indicarlo: asterisco con leyenda, texto "obligatorio" en el label, o aria-required anunciado (3.3.2).',
        'fieldset_missing': '{n} grupos de radio/checkbox sin <fieldset><legend>: los lectores no anuncian la pregunta común (1.3.1).',
        'fieldset_missing_rem': 'Envuelve los grupos en <fieldset><legend>Pregunta común</legend>…</fieldset> (1.3.1): sin esto, cada radio se anuncia suelto sin contexto.',
        'label_vague': '{n} labels sospechosamente vagos: {ej} (2.4.6).',
        'label_vague_rem': 'Los labels deben describir el campo: "Correo electrónico de contacto", no "Campo" o "Texto" (2.4.6).',
        'financial_no_confirm': '{n} formulario(s) financiero(s)/legal(es) sin paso de confirmación detectable (3.3.4).',
        'financial_no_confirm_rem': 'Los envíos con consecuencias legales/financieras deben ser reversibles, verificados o confirmados (3.3.4): checkbox de términos, botón "Revisar y confirmar", o paso de revisión.',
        'zoom_no': 'El viewport bloquea el zoom del usuario (user-scalable=no/0).',
        'zoom_no_rem': 'Elimina user-scalable=no y maximum-scale: el zoom es un derecho del usuario (1.4.4).',
        'zoom_max': 'El viewport limita el zoom (maximum-scale={v}; se recomienda no limitar o ≥2).',
        'zoom_max_rem': 'Elimina maximum-scale del viewport o déjalo en 2 o más, para que se pueda agrandar la letra (1.4.4).',
        'meta_refresh': '<meta http-equiv="refresh"> con recarga/redirección temporizada ({v}s).',
        'meta_refresh_rem': 'Sustituye la recarga automática por navegación iniciada por la persona usuaria (2.2.1). Redirección instantánea mejor en servidor.',
        'tabindex_pos': '{n} elementos con tabindex positivo (modifica el orden natural).',
        'tabindex_pos_rem': 'Usa tabindex="0" o elimina el atributo: el orden de tabulación debe seguir al DOM.',
        'no_bypass': 'Ni <main>/role="main" ni enlace de salto: sin mecanismo para saltar bloques repetidos.',
        'no_bypass_rem': 'Añade <main> (o role="main") y un enlace "Saltar al contenido" como primer foco.',
        'no_headings': 'La página no tiene encabezados (h1–h6).',
        'no_headings_rem': 'Estructura el contenido con encabezados jerárquicos: es el índice de navegación del lector de pantalla.',
        'no_h1': 'No hay ningún <h1> en la página.',
        'no_h1_rem': 'Añade un único h1 que nombre la página.',
        'multi_h1': '{n} <h1> en la página (máximo recomendado: 1).',
        'multi_h1_rem': 'Conserva un solo h1 (título de la página) y baja el resto un nivel.',
        'heading_skips': 'Saltos de nivel en encabezados: {skips}.',
        'heading_skips_rem': 'No saltes niveles (h2→h4): rompe el esquema de navegación. Baja de uno en uno.',
        'empty_heading': '{n} encabezados vacíos (<h*> sin texto).',
        'empty_heading_rem': 'Elimina los encabezados vacíos o dales texto: aparecen como huecos en el índice del lector.',
        'table_no_th': '{n} <table> sin celdas <th>.',
        'table_no_th_rem': 'Marca encabezados de fila/columna con <th> (y scope) para que el lector asocie celdas.',
        'blank_no_warning': '{n} enlaces con target="_blank" sin avisar de que abren ventana nueva.',
        'blank_no_warning_rem': 'Añade aviso en texto (o title/aria-label): «(abre en ventana nueva)», o deja que la persona usuaria decida.',
        'dup_ids': '{n} ids duplicados; pueden romper asociaciones label-for y aria-labelledby.',
        'dup_ids_rem': 'Haz únicos los ids: los <label for> y aria-labelledby apuntan solo al primero.',
        'autocomplete': '{n} campos que recogen datos de la persona usuaria sin atributo autocomplete: {ej}.',
        'autocomplete_rem': 'Añade autocomplete con el token correcto (email, tel, name, postal-code…, 1.3.5): relleno automático y voz de accesibilidad con sobrecoste cero.',
        'aria_ref_missing': '{n} referencias aria-labelledby/describedby apuntan a ids que no existen: {ej}.',
        'aria_ref_missing_rem': 'Corrige o elimina la referencia: un aria-labelledby roto deja el control sin nombre accesible.',
        'help_inconsistent': 'La ayuda (contacto/soporte) aparece en posiciones o formas distintas entre páginas del sitio ({ej}). Revisar (3.2.6).',
        'help_inconsistent_rem': 'Si la ayuda aparece en varias páginas, debe aparecer en el mismo orden relativo y de forma consistente (3.2.6, nuevo en 2.2): mismo menú, misma ubicación.',
        'images_of_text': '{n} imágenes que parecen ser texto renderizado (alt muy largo{ej2}). Revisar (1.4.5).',
        'images_of_text_rem': 'Salvo logotipos, presenta el texto como texto real (1.4.5): se re escala, se re-fluye y se traduce; una imagen no.',
        'label_in_name': '{n} controles cuyo aria-label no contiene el texto visible («{ej}»): quien dicta por voz dice lo que ve (2.5.3).',
        'label_in_name_rem': 'El nombre accesible debe CONTENER la etiqueta visible: «Ofertas de verano (abre en ventana nueva)», no «Más info». Sustituye el aria-label por texto visible + sufijo.',
        'lang_partes': '{n} atributos lang en elementos no válidos (BCP-47): {ej}.',
        'lang_partes_rem': 'Los fragmentos en otro idioma llevan lang con código válido (3.1.2): <blockquote lang="en">…</blockquote>.',
        'down_event': '{n} manejadores en down-event (onmousedown/ontouchstart/onpointerdown): {ej}. Revisar (2.5.2).',
        'down_event_rem': 'Activa en el UP-event (onclick/onmouseup): permite abortar arrastrando fuera — la regla de 2.5.2.',
        'captcha': 'Detectado captcha ({ej}): 3.3.8 exige alternativa sin test cognitivo para el acceso.',
        'captcha_rem': 'Ofrece alternativas: email mágico, OAuth, soporte humano. Un CAPTCHA sin alternativa excluye (3.3.8, nuevo en WCAG 2.2 AA).',
        'motion_moving': '{n} contenidos en movimiento/bucle sin control de pausa visible: {ej}. Revisar (2.2.2).',
        'motion_moving_rem': 'Contenido que se mueve/parpadea >5 s necesita un mecanismo de pausa/parada (2.2.2): <marquee> no tiene ninguno; las animaciones en bucle, tampoco por defecto.',
        'gesture_no_click': '{n} manejadores de gesto/arrastre sin alternativa de clic visible: {ej}. Revisar (2.5.1).',
        'gesture_no_click_rem': 'Toda función por gesto (swipe/arrastre) necesita alternativa sin gesto: botón «anterior/siguiente» o clic simple (2.5.1).',
        'motion_actuation': '{n} manejadores de deviceorientation/devicemotion sin alternativa de UI: {ej}. Revisar (2.5.4).',
        'motion_actuation_rem': 'Lo que se activa moviendo el dispositivo debe poder activarse también con UI (botón) y desactivarse (2.5.4).',
        'color_only_link': 'Enlaces distinguibles solo por color detectados en el pase renderizado (1.4.1).',
        'color_only_link_rem': 'El enlace dentro de texto necesita subrayado u otro distintivo, o contraste ≥3:1 con el texto que lo rodea (1.4.1).',
        'sensory_text': 'Instrucciones que apelan solo a los sentidos: «{ej}». Revisar (1.3.3).',
        'sensory_text_rem': 'No instruyas por posición/forma/color solos («el botón de la derecha»): nombra las cosas (1.3.3).',
        'orientation_lock': 'Bloqueo de orientación detectado: {ej}. Revisar (1.3.4).',
        'orientation_lock_rem': 'El contenido no debe bloquearse a una orientación salvo excepción demostrable (1.3.4): elimina screen.orientation.lock() y los media queries que fuercen una sola orientación.',
        'audio_desc_missing': '{n} <video> sin track de audiodescripción (1.2.3/1.2.5): pendiente de juicio humano.',
        'audio_desc_missing_rem': 'Si el vídeo tiene información visual esencial no narrada, publica audiodescripción (track kind="descriptions" o alternativa) — decide una persona viendo el vídeo.',
        'nav_inconsistent': 'La navegación repetida cambia entre páginas del sitio ({ej}) (3.2.3).',
        'nav_inconsistent_rem': 'Los mecanismos de navegación repetidos deben aparecer en el mismo orden relativo en todas las páginas (3.2.3): plantilla común.',
        'no_multiple_ways': 'Sin vía alternativa para encontrar páginas (sin búsqueda, sin mapa, sin índice) en las páginas muestreadas (2.4.5).',
        'no_multiple_ways_rem': 'Ofrece al menos dos vías: navegación + búsqueda o sitemap (2.4.5).',
        'dom_visual_order': 'Orden DOM distinto del orden visual en {n} bloques de texto: revisar con teclado (1.3.2).',
        'dom_visual_order_rem': 'El orden de lectura programático debe coincidir con el visual: revisa flex order, grid placement y position absolute (1.3.2).',
        'text_spacing_clip': '{n} textos recortados al aplicar los espaciados de 1.4.12 (line-height 1.5, letter 0.12em): revisar.',
        'text_spacing_clip_rem': 'El contenido debe sobrevivir a los overrides de espaciado de texto sin recortarse: sustituye alturas fijas por min-height (1.4.12).',
        'list_structure': '{n} hijos ilegales dentro de <ul>/<ol> (solo <li>, <script> y <template> son válidos).',
        'list_structure_rem': 'Mete el contenido suelto en <li> o usa otro contenedor: los lectores anuncian la lista con su número de ítems y se saltan lo que no es <li>.',
        'aria_value_invalid': '{n} valores de atributos ARIA inválidos: {ej}. Tecnología asistida los ignora.',
        'aria_value_invalid_rem': 'Los aria-* booleanos solo admiten true/false/undefined, los de posición enteros, los de token su lista cerrada (4.1.2). Corrige o elimina el atributo.',
        'role_unknown': '{n} roles ARIA desconocidos: {ej}. Los lectores los ignoran.',
        'role_unknown_rem': 'Usa roles de la especificación ARIA (button, dialog, navigation…) o elimina el atributo y confía en el HTML semántico.',
        'role_required_attr': '{n} controles con role que exige atributos ARIA que faltan: {ej}.',
        'role_required_attr_rem': 'Un slider necesita aria-valuenow (y mejor aria-valuemin/max): sin el estado, el control es inoperante para tecnología asistida (4.1.2).',
        'landmark_dup': '{n} grupos de landmarks duplicados (<nav>, <header>…) sin aria-label que los distinga: {ej}.',
        'landmark_dup_rem': 'Nombra cada landmark repetido (aria-label="Menú principal", aria-label="Menú pie"): si no, la navegación por landmarks es una lotería.',
        'generic_link': '{n} enlaces con texto genérico («más», «aquí», «read more»): {ej}.',
        'generic_link_rem': 'Describe el destino en el texto del enlace (2.4.4): las personas que listan enlaces saltan de uno a otro sin contexto.',
        'same_name_links': '{n} pares de enlaces con idéntico texto y destinos distintos.',
        'same_name_links_rem': 'Diferencia los nombres (o unifica el destino): «Informes» ×3 con tres URLs distintas es un problema para quien navega por lista de enlaces.',
        'accesskey_dup': '{n} teclas accesskey duplicadas: {ej}.',
        'accesskey_dup_rem': 'Accesskey repetidas disparan el control equivocado y chocan con atajos del navegador; elimínalas o hazlas únicas.',
        'multi_label': '{n} campos con más de un <label for> asociado.',
        'multi_label_rem': 'Un campo, una etiqueta: los lectores anuncian los labels concatenados. Agrupa el texto en uno.',
        'video_autoplay': '{n} medios con autoplay (audio >3s sin control para pararlo).',
        'video_autoplay_rem': 'Quita autoplay o añade muted + control visible de pausa/parada (1.4.2): el audio que arranca solo desordena a quien usa lector de pantalla.',
        'score_nota': ('Puntuación ponderada: alta −12, media −6, baja −2 desde 100. Mide solo lo '
                       'automatizable (≈1/3 de WCAG): sirve para seguir tendencias entre versiones, '
                       'no como conformidad.'),
        'limites': ('Automatización ≈ un tercio de WCAG: esto es un filtro exprés, no sustituye '
                    'revisión manual (teclado, lector de pantalla, contraste real, refrán de '
                    'auditoría).'),
    },
    'en': {
        'descarga_error': 'could not download: {e}',
        'imgs_alt': '{n} <img> without an alt attribute (not even alt="").',
        'imgs_alt_rem': 'Add alt to every <img>: descriptive text when it conveys information, alt="" when decorative. Same requirement for <input type="image"> and <area>.',
        'input_img_alt': '<input type="image"> without alt (image button with no name).',
        'input_img_alt_rem': 'Add descriptive alt to the input type="image" (it is its accessible name), or replace it with a <button> with text or <input type="submit" value="…">.',
        'ctrl_name': '{n} <{tag}> with no accessible name (no text, aria-label or title).',
        'ctrl_name_rem': 'The accessible name comes from inner text, aria-label, title, or an inner image with alt. An empty control is invisible to screen readers.',
        'aria_hidden_focusable': '{n} interactive elements (<{tag}>) with aria-hidden="true": hidden from the screen reader yet still focusable.',
        'aria_hidden_focusable_rem': 'Remove aria-hidden from the focusable element, or add tabindex="-1" if it must stay out of interaction.',
        'field_label': '{n} form fields with no associated <label> and no accessible name.',
        'field_label_rem': 'Associate <label for="id"> (or wrap the field), or use aria-label. Applies to input, select and textarea.',
        'click_nonfocusable': '{n} non-interactive elements (<{tag}>) with onclick, no role, no tabindex and no keyboard handling.',
        'click_nonfocusable_rem': 'Use a real <button>; if impossible, add role="button", tabindex="0" and Enter/Space handling (2.1.1).',
        'label_orphan': '{n} <label> without for and without a nested field: they label nothing.',
        'label_orphan_rem': 'Connect the label to its field via for="id", or move the field inside the label.',
        'iframe_title': '{n} <iframe> without an accessible title.',
        'iframe_title_rem': 'Add a descriptive title to the iframe (screen readers announce it on arrival).',
        'video_captions': '{n} <video> without <track kind="captions">.',
        'video_captions_rem': 'Publish captions for the video audio track (1.2.2). If decorative and silent, mark it as such.',
        'lang_missing': 'The <html> element does not declare lang.',
        'lang_missing_rem': 'Add lang="en" (the real language) to <html>: screen readers pick the synthetic voice from it.',
        'lang_invalid': 'lang="{lang}" is not a valid BCP-47 language code.',
        'lang_invalid_rem': 'Use the correct ISO 639 primary subtag (en, es, pt…).',
        'title_missing': 'The page has no <title> with content.',
        'title_missing_rem': 'Write a unique, descriptive <title> per page (screen reader\'s first announcement, tab text).',
        'heading_quality': '{n} suspiciously generic or vague headings/labels: {ej}. Review (2.4.6).',
        'heading_quality_rem': 'Headings should describe their section: "Q3 Report Results", not "Section 2" or "More info" (2.4.6). Name things.',
        'char_shortcut': '{n} single-character keyboard shortcuts detected: {ej}. Review (2.1.4).',
        'char_shortcut_rem': 'Single-key shortcuts must be disablable, remappable, or active only on focus (2.1.4): voice-dictation users trigger every letter.',
        'drag_no_alt': '{n} drag handlers with no visible click/button alternative: {ej}. Review (2.5.7).',
        'drag_no_alt_rem': 'Every drag action needs a non-dragging alternative: up/down buttons, context menu, arrows (2.5.7).',
        'no_status_regions': 'No status regions (aria-live/status/alert) detected on the page: dynamic messages will not be announced (4.1.3).',
        'no_status_regions_rem': 'Add role="status" or aria-live="polite" for toasts, save confirmations, search results (4.1.3).',
        'placeholder_only': '{n} fields using placeholder as their only label (no <label>): {ej}. The placeholder vanishes on input (3.3.2).',
        'placeholder_only_rem': 'Placeholder is NOT a label: add a visible <label for="id">. The placeholder disappears when typing starts and screen readers do not always announce it (3.3.2).',
        'required_no_indication': '{n} required fields with no visible required indication: {ej} (3.3.2).',
        'required_no_indication_rem': 'Required fields must indicate it: asterisk with legend, "required" text in the label, or announced aria-required (3.3.2).',
        'fieldset_missing': '{n} radio/checkbox groups without <fieldset><legend>: screen readers do not announce the common question (1.3.1).',
        'fieldset_missing_rem': 'Wrap groups in <fieldset><legend>Common question</legend>…</fieldset> (1.3.1): without it, each radio is announced without context.',
        'label_vague': '{n} suspiciously vague labels: {ej} (2.4.6).',
        'label_vague_rem': 'Labels should describe the field: "Contact email address", not "Field" or "Text" (2.4.6).',
        'financial_no_confirm': '{n} financial/legal form(s) without a detectable confirmation step (3.3.4).',
        'financial_no_confirm_rem': 'Submissions with legal/financial consequences must be reversible, checked, or confirmed (3.3.4): terms checkbox, "Review and confirm" button, or review step.',
        'zoom_no': 'The viewport blocks user zoom (user-scalable=no/0).',
        'zoom_no_rem': 'Remove user-scalable=no and maximum-scale: zooming is the user\'s right (1.4.4).',
        'zoom_max': 'The viewport limits zoom (maximum-scale={v}; recommend no limit or ≥2).',
        'zoom_max_rem': 'Remove maximum-scale from the viewport, or set it to 2 or higher, so text can be enlarged (1.4.4).',
        'meta_refresh': '<meta http-equiv="refresh"> with a timed reload/redirect ({v}s).',
        'meta_refresh_rem': 'Replace the automatic reload with user-initiated navigation (2.2.1). Instant redirects are better done server-side.',
        'tabindex_pos': '{n} elements with a positive tabindex (overrides natural order).',
        'tabindex_pos_rem': 'Use tabindex="0" or drop the attribute: tab order must follow the DOM.',
        'no_bypass': 'Neither <main>/role="main" nor a skip link: no way to bypass repeated blocks.',
        'no_bypass_rem': 'Add <main> (or role="main") and a "Skip to content" link as the first focus stop.',
        'no_headings': 'The page has no headings (h1–h6).',
        'no_headings_rem': 'Structure content with hierarchical headings: they are the screen reader\'s navigation index.',
        'no_h1': 'There is no <h1> on the page.',
        'no_h1_rem': 'Add a single h1 naming the page.',
        'multi_h1': '{n} <h1> on the page (recommended maximum: 1).',
        'multi_h1_rem': 'Keep a single h1 (page title) and demote the rest one level.',
        'heading_skips': 'Heading level skips: {skips}.',
        'heading_skips_rem': 'Do not skip levels (h2→h4): it breaks the navigation outline. Descend one level at a time.',
        'empty_heading': '{n} empty headings (<h*> with no text).',
        'empty_heading_rem': 'Remove empty headings or give them text: they show up as gaps in the reader\'s index.',
        'table_no_th': '{n} <table> with no <th> cells.',
        'table_no_th_rem': 'Mark row/column headers with <th> (plus scope) so the reader can associate cells.',
        'blank_no_warning': '{n} links with target="_blank" that do not warn they open a new window.',
        'blank_no_warning_rem': 'Add a text hint (or title/aria-label): "(opens in a new window)", or let the user decide.',
        'dup_ids': '{n} duplicated ids; they can break label-for and aria-labelledby associations.',
        'dup_ids_rem': 'Make ids unique: <label for> and aria-labelledby only point at the first match.',
        'autocomplete': '{n} fields collecting user information without an autocomplete attribute: {ej}.',
        'autocomplete_rem': 'Add autocomplete with the right token (email, tel, name, postal-code…, 1.3.5): free accessibility and autofill at zero cost.',
        'aria_ref_missing': '{n} aria-labelledby/describedby references point to ids that do not exist: {ej}.',
        'aria_ref_missing_rem': 'Fix or remove the reference: a broken aria-labelledby leaves the control with no accessible name.',
        'help_inconsistent': 'Help (contact/support) appears in different places or shapes across site pages ({ej}). Review (3.2.6).',
        'help_inconsistent_rem': 'When help appears on multiple pages, it must appear in the same relative order and consistently (3.2.6, new in 2.2): same menu, same place.',
        'images_of_text': '{n} images that appear to be rendered text (very long alt{ej2}). Review (1.4.5).',
        'images_of_text_rem': 'Except for logotypes, present text as real text (1.4.5): it rescales, reflows and translates; an image does not.',
        'label_in_name': '{n} controls whose aria-label does not contain the visible text («{ej}»): voice-input users say what they see (2.5.3).',
        'label_in_name_rem': 'The accessible name must CONTAIN the visible label: "Summer offers (opens in new window)", not "More info". Use visible text + suffix.',
        'lang_partes': '{n} invalid lang attributes on elements (BCP-47): {ej}.',
        'lang_partes_rem': 'Foreign-language fragments carry lang with a valid code (3.1.2): <blockquote lang="en">…</blockquote>.',
        'down_event': '{n} down-event handlers (onmousedown/ontouchstart/onpointerdown): {ej}. Review (2.5.2).',
        'down_event_rem': 'Activate on the UP event (onclick/onmouseup): dragging away can abort — that is rule 2.5.2.',
        'captcha': 'Captcha detected ({ej}): 3.3.8 requires a non-cognitive-test alternative for access.',
        'captcha_rem': 'Offer alternatives: magic links, OAuth, human support. A CAPTCHA without an alternative excludes (3.3.8, new in WCAG 2.2 AA).',
        'motion_moving': '{n} moving/looping contents with no visible pause control: {ej}. Review (2.2.2).',
        'motion_moving_rem': 'Content moving/blinking >5s needs a pause/stop mechanism (2.2.2): <marquee> has none; looping animations do not either by default.',
        'gesture_no_click': '{n} gesture/drag handlers with no visible click alternative: {ej}. Review (2.5.1).',
        'gesture_no_click_rem': 'Every gesture function (swipe/drag) needs a non-gesture alternative: prev/next button or plain click (2.5.1).',
        'motion_actuation': '{n} deviceorientation/devicemotion handlers with no UI alternative: {ej}. Review (2.5.4).',
        'motion_actuation_rem': 'What motion activates must also be activatable via UI (button) and disablable (2.5.4).',
        'color_only_link': 'Links distinguishable only by color detected in the rendered pass (1.4.1).',
        'color_only_link_rem': 'A link inside text needs underline or another cue, or ≥3:1 contrast against surrounding text (1.4.1).',
        'sensory_text': 'Instructions appealing to senses alone: "{ej}". Review (1.3.3).',
        'sensory_text_rem': 'Do not instruct by position/shape/color alone ("the button on the right"): name things (1.3.3).',
        'orientation_lock': 'Orientation lock detected: {ej}. Review (1.3.4).',
        'orientation_lock_rem': 'Content must not be locked to one orientation unless the exception demonstrably applies (1.3.4): remove screen.orientation.lock() and orientation-forcing media queries.',
        'audio_desc_missing': '{n} <video> without audio-description track (1.2.3/1.2.5): pending human judgment.',
        'audio_desc_missing_rem': 'If the video carries essential visual information not narrated, publish audio description (track kind="descriptions" or alternative) — a person watching the video decides.',
        'nav_inconsistent': 'Repeated navigation changes across site pages ({ej}) (3.2.3).',
        'nav_inconsistent_rem': 'Repeated navigation mechanisms must appear in the same relative order on every page (3.2.3): shared template.',
        'no_multiple_ways': 'No alternative way to find pages (no search, no sitemap, no index) across sampled pages (2.4.5).',
        'no_multiple_ways_rem': 'Offer at least two ways: navigation + search or sitemap (2.4.5).',
        'dom_visual_order': 'DOM order differs from visual order in {n} text blocks: review with keyboard (1.3.2).',
        'dom_visual_order_rem': 'Programmatic reading order must match visual order: check flex order, grid placement and position absolute (1.3.2).',
        'text_spacing_clip': '{n} texts clipped when the 1.4.12 spacing overrides apply (line-height 1.5, letter 0.12em): review.',
        'text_spacing_clip_rem': 'Content must survive text-spacing overrides without clipping: replace fixed heights with min-height (1.4.12).',
        'list_structure': '{n} illegal children inside <ul>/<ol> (only <li>, <script> and <template> are valid).',
        'list_structure_rem': 'Wrap loose content in <li> or use another container: screen readers announce the list with its item count and skip non-<li> content.',
        'aria_value_invalid': '{n} invalid ARIA attribute values: {ej}. Assistive tech ignores them.',
        'aria_value_invalid_rem': 'Boolean aria-* only accept true/false/undefined, position ones integers, token ones their closed list (4.1.2). Fix or drop the attribute.',
        'role_unknown': '{n} unknown ARIA roles: {ej}. Screen readers ignore them.',
        'role_unknown_rem': 'Use roles from the ARIA specification (button, dialog, navigation…) or drop the attribute and rely on semantic HTML.',
        'role_required_attr': '{n} widgets whose role requires missing ARIA attributes: {ej}.',
        'role_required_attr_rem': 'A slider needs aria-valuenow (ideally aria-valuemin/max): without the state the widget is inoperative for assistive tech (4.1.2).',
        'landmark_dup': '{n} groups of duplicated landmarks (<nav>, <header>…) without a distinguishing aria-label: {ej}.',
        'landmark_dup_rem': 'Name each repeated landmark (aria-label="Main menu", aria-label="Footer menu"): otherwise landmark navigation is a lottery.',
        'generic_link': '{n} links with generic text ("more", "here", "read more"): {ej}.',
        'generic_link_rem': 'Describe the destination in the link text (2.4.4): people listing links jump between them with no context.',
        'same_name_links': '{n} pairs of links with identical text pointing to different destinations.',
        'same_name_links_rem': 'Differentiate the names (or unify the destination): "Reports" ×3 with three different URLs is a problem for anyone navigating by link list.',
        'accesskey_dup': '{n} duplicated accesskey values: {ej}.',
        'accesskey_dup_rem': 'Duplicated accesskeys trigger the wrong control and clash with browser shortcuts; remove or make unique.',
        'multi_label': '{n} fields with more than one associated <label for>.',
        'multi_label_rem': 'One field, one label: screen readers announce concatenated labels. Merge the text into one.',
        'video_autoplay': '{n} media elements with autoplay (audio >3s with no way to stop it).',
        'video_autoplay_rem': 'Remove autoplay or add muted + a visible pause/stop control (1.4.2): audio that starts on its own disrupts screen-reader users.',
        'score_nota': ('Weighted score: high −12, medium −6, low −2 from 100. It measures only '
                       'what is automatable (≈1/3 of WCAG): use it to track trends between '
                       'releases, not as conformance.'),
        'limites': ('Automation ≈ one third of WCAG: this is an express filter, not a substitute '
                    'for manual review (keyboard, screen reader, real contrast, audit rhyme).'),
    },
}

# Aviso de ventana nueva: texto que lo indica o icono con nombre
_BLANK_HINT = re.compile(r'nueva|nuevo|ventana|pesta|tab\b|window|external|externo|exterior', re.I)


def _t(lang, key):
    return T.get(lang, T['es'])[key]


def _crit(lang, code):
    return CRIT.get(lang, CRIT['es'])[code]


class _Auditor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.imgs_sin_alt = []
        self.sitios = {}          # tag → lista de atributos de controles sin nombre
        self.campos_sin_label = []
        self.iframes_sin_title = []
        self.lang = None
        self.title = ''
        self._en_title = False
        self._en_script = False
        self.headings = []        # (nivel, texto)
        self._nivel_h = None
        self._texto_h = []
        self.tabindex_positivos = []
        self.viewport = None
        self.elementos = 0
        # Pila de controles interactivos (a/button/summary) para recoger su
        # texto interno, que es la fuente más habitual de nombre accesible.
        self._ctrl = []
        self._label_depth = 0
        self._labels_stack = []   # un booleano por <label> abierto: ¿contiene campo?
        self._labels_for = {}     # id → nº de <label for> que lo apuntan
        self.labels_huerfanos = 0
        # Nuevas señales
        self.aria_hidden_focusable = []   # tag de interactivos con aria-hidden
        self.click_sueltos = []           # tags no interactivos con onclick
        self.meta_refresh = None
        self.videos = 0
        self.videos_con_subs = 0
        self._en_video = False
        self.tablas = 0
        self.tablas_con_th = 0
        self._en_tabla = False
        self._th_en_tabla = False
        self.blank_sin_aviso = 0
        self.blank_total = 0
        self.hay_main = False
        self.hay_skip = False
        self.h1s = 0
        self.vacios_h = 0
        self.ids = {}
        self.input_img_sin_alt = 0
        # v3.1: validez ARIA, autocomplete, enlaces, landmarks, accesskey, autoplay
        self.aria_refs = []       # (attr, id) referenciados por aria-labelledby/describedby
        self.aria_valores = []    # valores aria-* inválidos
        self.roles_desconocidos = []
        self.roles_sin_estado = []   # widgets con role que exige aria-valuenow
        self.landmarks = {}       # tipo → [con_etiqueta, total]
        self.accesos = {}         # accesskey → tag
        self.autocomplete_faltan = []
        self.enlaces = {}         # nombre normalizado → set de hrefs
        self.genericos = 0
        self.labels_for_dups = {}  # id → n labels (los >1, varios)
        self.medios_autoplay = 0
        self._lista_prof = 0
        self._li_prof = 0
        self._lista_malos = 0
        self.label_no_name = []     # (texto visible, aria-label) 2.5.3
        self.langs_partes = []      # lang inválidos en elementos no-html
        self.down_events = []       # onmousedown/ontouchstart/onpointerdown
        self.captchas = []          # detección 3.3.8
        self.moviles = []           # marquee/blink/inline infinite animation (2.2.2)
        self.nav_hrefs = set()      # hrefs inside <nav> (site-level 3.2.3 signature)
        self.help_hrefs = set()     # help/contact links (site-level 3.2.6 signature)
        self.imagenes_texto = []
        self.headings_vagos = []
        self.char_shortcuts = []
        self.drag_handlers = []
        self.status_regions = 0
        self.placeholder_only = []     # 3.3.2: placeholder sin label
        self.required_sin_indicio = [] # 3.3.2: required sin * ni "obligatorio"
        self.fieldsets_faltan = 0      # 1.3.1: radio/check groups sin fieldset
        self._radio_group = {}         # name → count (para detectar grupos)
        self.labels_vagos = []         # 2.4.6: label quality
        self.financieros_sin_conf = 0  # 3.3.4: financial form no confirm
        self._form_financiero = False
        self._form_confirma = False    # 1.4.5 suspicion: img inside heading or very long alt
        self._en_nav = 0
        self._en_fieldset = False
        self.tiene_busqueda = False
        self.tiene_sitemap = False
        self.gestos = []            # touchmove/drag handlers (2.5.1)
        self.motions = []           # deviceorientation/devicemotion (2.5.4)
        self.orientation_locks = [] # screen.orientation.lock / orientation MQ (1.3.4)
        self.videos_descriptions = 0   # videos WITH descriptions track
        self.sensory = []           # sensory-only instruction patterns (1.3.3)
        self._skip_labels_pend = []  # labels declarados antes que su campo

    def _cierra_control(self, tag):
        if not self._ctrl:
            return
        c = self._ctrl[-1]
        if c['tag'] != tag:
            return
        self._ctrl.pop()
        a = c['attrs']
        texto = ' '.join(c['texto']).strip()
        if not (texto or a.get('aria-label') or a.get('aria-labelledby')
                or a.get('title') or a.get('alt')):
            # el nombre del control puede venir también de una imagen interna
            if not c.get('img_interna'):
                self.sitios.setdefault(tag, []).append(a)
        if tag == 'a':
            visible = ' '.join(texto.lower().split())
            al = ' '.join((a.get('aria-label') or '').lower().split())
            if visible and al and visible not in al:
                self.label_no_name.append((texto[:40], a.get('aria-label')[:60]))
            if (a.get('target') or '').lower() == '_blank':
                self.blank_total += 1
                if not _BLANK_HINT.search(texto) and not _BLANK_HINT.search(a.get('aria-label') or '') \
                        and not _BLANK_HINT.search(a.get('title') or ''):
                    self.blank_sin_aviso += 1
            elif (a.get('href') or '').strip().startswith('#') and texto:
                self.hay_skip = True  # ancla interna con texto: candidato a skip link
            nombre = (texto or a.get('aria-label') or a.get('title') or '').strip()
            href = (a.get('href') or '').strip()
            if nombre and href:
                clave = ' '.join(nombre.lower().split())[:60]
                self.enlaces.setdefault(clave, set()).add(href)
                if clave in _TEXTO_GENERICO:
                    self.genericos += 1

    def _nota_campo(self):
        """El elemento que acaba de abrirse es un campo: marca su <label> ancestro."""
        if self._labels_stack:
            self._labels_stack[-1] = True

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.elementos += 1
        if a.get('id'):
            self.ids[a['id']] = self.ids.get(a['id'], 0) + 1
        if tag == 'html':
            self.lang = (a.get('lang') or '').strip()
        elif tag == 'title':
            self._en_title = True
        elif tag == 'script':
            self._en_script = True
        elif tag == 'meta':
            if a.get('name', '').lower() == 'viewport':
                self.viewport = a.get('content', '')
            elif (a.get('http-equiv') or '').lower() == 'refresh':
                self.meta_refresh = a.get('content', '')
        elif tag == 'img':
            if 'alt' not in a:
                self.imgs_sin_alt.append(a.get('src', '')[:100])
            alt = (a.get('alt') or '').strip()
            if self._ctrl and alt:
                self._ctrl[-1]['img_interna'] = True
            if self._nivel_h is not None or len(alt) > 120:
                self.imagenes_texto.append('imagen dentro de encabezado' if self._nivel_h is not None
                                           else f'alt de {len(alt)} caracteres')
        elif tag == 'iframe':
            if not (a.get('title') or a.get('aria-label')):
                self.iframes_sin_title.append((a.get('src') or '')[:100])
        elif tag == 'nav':
            self._en_nav += 1
        elif tag in _CONTROLES:
            # Enlace no interactivo (ancla pura sin href): no se audita.
            if tag == 'a' and not (a.get('href') or '').strip():
                pass
            else:
                self._ctrl.append({'tag': tag, 'attrs': a, 'texto': [], 'img_interna': False})
                href = (a.get('href') or '').strip()
                if self._en_nav and href and not href.startswith('#'):
                    self.nav_hrefs.add(href.split('#')[0].rstrip('/'))
                if href and re.search(r'help|contact|support|ayuda|contacto|soporte|asistencia',
                                      href, re.I):
                    self.help_hrefs.add(href.split('#')[0].rstrip('/'))
                if href and re.search(r'sitemap|site-map|mapa-del-sitio|mapa_web|mapaweb', href, re.I):
                    self.tiene_sitemap = True
        elif tag == 'input':
            self._nota_campo()
            tipo = (a.get('type') or 'text').lower()
            if tipo == 'image':
                if not (a.get('alt') or a.get('aria-label') or a.get('title')):
                    self.input_img_sin_alt += 1
            elif tipo in ('submit', 'button', 'reset'):
                if not (a.get('value') or a.get('aria-label') or a.get('alt')):
                    self.sitios.setdefault('input:' + tipo, []).append(a)
            if tipo == 'search' or re.search(r'search|busqueda|b[uú]squeda', (a.get('name') or '') + (a.get('id') or ''), re.I):
                self.tiene_busqueda = True
            elif tipo in _CAMPOS:
                tiene_nombre = a.get('aria-label') or a.get('aria-labelledby') or a.get('title')
                if not tiene_nombre and self._label_depth == 0:
                    self.campos_sin_label.append((tipo, a.get('name', '')[:60], a.get('id')))
                if 'autocomplete' not in a and tipo != 'search' and (
                        tipo in ('email', 'tel')
                        or _DATO_PERSONAL.search((a.get('name') or '') + ' ' + (a.get('id') or ''))):
                    self.autocomplete_faltan.append(f'input type={tipo} name={a.get("name") or "?"}'[:44])
        elif tag in ('select', 'textarea'):
            self._nota_campo()
            tiene_nombre = a.get('aria-label') or a.get('aria-labelledby') or a.get('title')
            if not tiene_nombre and self._label_depth == 0:
                self.campos_sin_label.append((tag, a.get('name', '')[:60], a.get('id')))
        elif tag == 'label':
            self._label_depth += 1
            self._label_texto_actual = []
            self._labels_stack.append(False)
            if a.get('for'):
                self._labels_for[a['for']] = self._labels_for.get(a['for'], 0) + 1
                if self._labels_for[a['for']] > 1:
                    self.labels_for_dups[a['for']] = self._labels_for[a['for']]
                self._labels_stack[-1] = True
        elif tag == 'marquee':
            self.moviles.append('<marquee>')
        elif tag == 'blink':
            self.moviles.append('<blink>')
        elif tag == 'track':
            if (a.get('kind') or '').lower() == 'descriptions':
                self.videos_descriptions += 1
        elif tag in ('video', 'audio'):
            if tag == 'video':
                self.videos += 1
                self._en_video = True
            if 'autoplay' in a:
                self.medios_autoplay += 1
        elif tag == 'track':
            if (a.get('kind') or '').lower() in ('captions', 'subtitles'):
                self.videos_con_subs += 1
        elif tag in ('ul', 'ol'):
            self._lista_prof += 1
        elif tag == 'li':
            self._li_prof += 1
        elif tag == 'table':
            self.tablas += 1
            self._en_tabla = True
            self._th_en_tabla = False
        elif tag == 'th':
            self._th_en_tabla = True
        elif tag == 'main' or (a.get('role') or '').lower() == 'main':
            self.hay_main = True
        elif tag not in _CONTROLES + ('input', 'select', 'textarea', 'label', 'option',
                                      'video', 'audio', 'details', 'summary'):
            if a.get('onclick') and not a.get('role') and 'tabindex' not in a:
                self.click_sueltos.append(tag)
        # v3.9: 3.1.2 idioma de partes (elemento no-html con lang inválido)
        if tag != 'html' and a.get('lang'):
            prim = a['lang'].strip().lower().split('-')[0]
            if prim and prim not in _LANG_CODES:
                self.langs_partes.append(f'{tag} lang="{a["lang"]}"')
        # v3.9: 2.5.2 sospecha de activación en down-event
        for _de in ('onmousedown', 'ontouchstart', 'onpointerdown'):
            if a.get(_de):
                self.down_events.append(f'{tag}[{_de}]')
                break
        # v3.12: 2.2.2 inline looping animation
        estilo = a.get('style') or ''
        if 'animation' in estilo and 'infinite' in estilo:
            self.moviles.append(f'{tag}[style animation…infinite]')
        # v3.12: 2.5.1 gesture without click alternative (attribute-level hint)
        if a.get('ontouchmove') or a.get('ondrag'):
            if not (a.get('onclick') or tag in ('input', 'button', 'a')):
                self.gestos.append(f'{tag}[{list(a)[0] if a else ""}]')
        # forms: placeholder-only, required sin indicio, financial
        if tag == 'form':
            self._form_financiero = False
            self._form_confirma = False
            action = (a.get('action') or '').lower()
            if re.search(r'pay|purchase|checkout|buy|order|contract|legal|billing',
                         action, re.I):
                self._form_financiero = True
        if tag in ('input', 'select', 'textarea'):
            if a.get('placeholder') and not (a.get('aria-label') or a.get('aria-labelledby')):
                if self._label_depth == 0 and not a.get('id'):
                    self.placeholder_only.append(f'{tag}[placeholder="{a.get("placeholder","")[:30]}"]')
            if a.get('required') or a.get('aria-required') == 'true':
                ph = (a.get('placeholder') or '').lower()
                title_ = (a.get('title') or '').lower()
                if not re.search(r'\*|requerid|obligator|required|necesari|precisa', ph + title_):
                    self.required_sin_indicio.append(
                        f'{tag}[name={a.get("name","?")}]')
            if tag == 'input' and a.get('type') == 'radio':
                nm = a.get('name') or '_sin_nombre'
                self._radio_group[nm] = self._radio_group.get(nm, 0) + 1
        if tag == 'fieldset':
            self._en_fieldset = True
        if tag in ('button', 'input'):
            val = (a.get('value') or a.get('data-action') or '').lower()
            if re.search(r'confirm|verificar|review|revisar|accept|aceptar', val):
                self._form_confirma = True
            # checkbox de términos
        if tag == 'input' and a.get('type') == 'checkbox':
            nm = (a.get('name') or '').lower()
            if re.search(r'terms|accept|agree|terminos|aceptar|legal|privacy', nm):
                self._form_confirma = True
        if a.get('draggable') and (a.get('draggable') or '').lower() != 'false':
            if not a.get('onclick') and tag not in ('input', 'button'):
                self.drag_handlers.append(f'{tag}[draggable]')
        if a.get('aria-live') or (a.get('role') or '').lower() in ('status', 'alert', 'log'):
            self.status_regions += 1
        if a.get('accesskey') and len((a.get('accesskey') or '').strip()) == 1:
            self.char_shortcuts.append(f'{tag}[accesskey]')
        # v3.12: 2.5.4 motion actuation handlers
        for _ma in ('ondeviceorientation', 'ondevicemotion'):
            if a.get(_ma):
                self.motions.append(f'{tag}[{_ma}]')
        # v3.12: 1.3.4 orientation lock hints (attribute/inline level)
        if tag == 'meta' and 'orientation' in (a.get('content') or '').lower() \
                and 'lock' in (a.get('content') or '').lower():
            self.orientation_locks.append('meta orientation lock')
        # v3.9: 3.3.8 captcha
        for _v in (a.get('src') or '', a.get('href') or '', a.get('id') or ''):
            if re.search(r'recaptcha|hcaptcha|turnstile|captcha', _v, re.I):
                self.captchas.append(f'{tag} {_v[:50]}')
                break
        if (a.get('name') or '').lower().find('captcha') >= 0:
            self.captchas.append(f'input name={a["name"][:30]}')
        # v3.1/v3.3: validez ARIA (atributos, referencias y VALORES)
        for _ar in _ARIA_IDREFS:
            if a.get(_ar):
                for _ref in a[_ar].split():
                    self.aria_refs.append((_ar, _ref))
        for _ar, _val in a.items():
            if not _ar.startswith('aria-'):
                continue
            _val = (_val or '').strip().lower()
            if _ar in _ARIA_BOOL and _val not in ('true', 'false', 'undefined'):
                self.aria_valores.append({'attr': _ar, 'val': _val, 'tipo': 'bool'})
            elif _ar in _ARIA_INT and not _val.isdigit():
                self.aria_valores.append({'attr': _ar, 'val': _val, 'tipo': 'int'})
            elif _ar in _ARIA_NUM:
                try:
                    float(_val)
                except ValueError:
                    self.aria_valores.append({'attr': _ar, 'val': _val, 'tipo': 'num'})
            elif _ar in _ARIA_TOKENS and _val not in _ARIA_TOKENS[_ar]:
                self.aria_valores.append({'attr': _ar, 'val': _val,
                                          'tipo': 'tokens',
                                          'lista': '/'.join(sorted(v for v in _ARIA_TOKENS[_ar] if v))})
        if a.get('role'):
            rol = a['role'].strip().split()[0].lower()
            if rol not in _ROLES_ARIA and not rol.startswith('doc-'):
                self.roles_desconocidos.append(rol)
            if rol in ('slider', 'spinbutton') and 'aria-valuenow' not in a:
                self.roles_sin_estado.append(f'{tag}[role={rol}]')
        rol_landmark = a.get('role', '').lower() if a.get('role') in (
            'banner', 'contentinfo', 'navigation', 'complementary', 'main', 'form', 'search', 'region') else None
        lm = tag if tag in ('header', 'footer', 'nav', 'aside', 'main', 'search') else rol_landmark
        if lm and not (a.get('aria-label') or a.get('aria-labelledby')):
            t = self.landmarks.setdefault(lm, [0, 0])
            t[0] += 1
            t[1] += 1
        elif lm:
            self.landmarks.setdefault(lm, [0, 0])[1] += 1
        if a.get('accesskey'):
            k = a['accesskey'].strip().lower()
            self.accesos[k] = self.accesos.get(k, 0) + 1
        if self._lista_prof > 0 and self._li_prof == 0 \
                and tag not in ('li', 'script', 'template', 'ul', 'ol'):
            self._lista_malos += 1
        aria_hidden = (a.get('aria-hidden') or '').lower() == 'true'
        ti_raw = (a.get('tabindex') or '').strip()
        if aria_hidden and ti_raw != '-1' and (
                tag in _CONTROLES + ('input', 'select', 'textarea', 'iframe', 'video')
                or a.get('onclick')):
            self.aria_hidden_focusable.append(tag)
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._nivel_h = int(tag[1])
            self._texto_h = []
        ti = a.get('tabindex')
        if ti and ti.isdigit() and int(ti) > 0:
            self.tabindex_positivos.append((tag, int(ti)))

    def handle_endtag(self, tag):
        if tag == 'title':
            self._en_title = False
        elif tag == 'script':
            self._en_script = False
        elif tag == 'label':
            self._label_depth = max(0, self._label_depth - 1)
            if hasattr(self, '_label_texto_actual'):
                txt = ' '.join(self._label_texto_actual).strip()
                bajo = txt.lower()
                if txt and (len(txt) < 2 or re.fullmatch(
                    r'(campo|field|input|texto|text|dato|value|entrada|box|caja)[\s\d]*', bajo)):
                    self.labels_vagos.append(f'"{txt[:30]}"')
            if self._labels_stack and not self._labels_stack.pop():
                self.labels_huerfanos += 1
        elif tag == 'fieldset':
            self._en_fieldset = False
        elif tag == 'form':
            if self._form_financiero and not self._form_confirma:
                self.financieros_sin_conf += 1
        elif tag == 'nav':
            self._en_nav = max(0, self._en_nav - 1)
        elif tag == 'li':
            self._li_prof = max(0, self._li_prof - 1)
        elif tag in ('ul', 'ol'):
            self._lista_prof = max(0, self._lista_prof - 1)
        elif tag in _CONTROLES:
            self._cierra_control(tag)
        elif tag == 'video':
            self._en_video = False
        elif tag == 'table':
            if self._en_tabla:
                if not self._th_en_tabla:
                    pass  # se contabiliza abajo
                else:
                    self.tablas_con_th += 1
            self._en_tabla = False
        elif tag == 'th':
            pass
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6') and self._nivel_h:
            texto = ' '.join(self._texto_h).strip()
            if not texto:
                self.vacios_h += 1
            else:
                self.headings.append((self._nivel_h, texto[:80]))
                if self._nivel_h == 1:
                    self.h1s += 1
                bajo = texto.lower().strip()
                if len(texto) < 4 or len(texto) > 120:
                    self.headings_vagos.append(f'h{self._nivel_h} "{texto[:40]}"')
                elif re.fullmatch(r'(secci[oó]n|section|chapter|cap[ií]tulo|m[aá]s|more|info|informaci[oó]n|information|details|detalle|click|ver|see|leer|read|continue|seguir)[\s\d.]*', bajo):
                    self.headings_vagos.append(f'h{self._nivel_h} "{texto[:40]}"')
                elif re.fullmatch(r'[\d.\s]+', bajo):
                    self.headings_vagos.append(f'h{self._nivel_h} "{texto[:40]}"')
            self._nivel_h = None

    _RE_CHAR_KEY = re.compile(r'key(?:Code)?\s*===?\s*["\']([a-zA-Z0-9])["\']', re.S)

    def handle_script_espera(self, data):
        for m in self._RE_CHAR_KEY.finditer(data):
            if len(self.char_shortcuts) < 5:
                self.char_shortcuts.append(f"key === '{m.group(1)}'")
        if re.search(r'addEventListener\s*\(\s*["\'](?:dragstart|dragover|drop)["\']', data, re.I):
            self.drag_handlers.append('drag listener in script')
        # v3.12: signals that only appear in script bodies
        if 'screen.orientation.lock' in data:
            self.orientation_locks.append('screen.orientation.lock()')
        for _ma in ("addEventListener('deviceorientation'",
                    'addEventListener("deviceorientation"',
                    "addEventListener('devicemotion'", 'addEventListener("devicemotion"'):
            if _ma in data:
                self.motions.append(_ma.split('(')[1].strip('\'"'))

    def handle_data(self, data):
        if self._en_title:
            self.title += data
        elif getattr(self, '_en_script', False):
            self.handle_script_espera(data)
        else:
            # Un texto puede pertenecer a la vez a un enlace dentro de un
            # encabezado (<h2><a>Guías</a></h2>): alimenta a ambos.
            if self._label_depth > 0 and hasattr(self, '_label_texto_actual'):
                self._label_texto_actual.append(data)
            if self._ctrl:
                self._ctrl[-1]['texto'].append(data)
            if self._nivel_h is not None:
                self._texto_h.append(data)
            m = _SENSORIAL.search(data)
            if m and len(self.sensory) < 6:
                self.sensory.append(m.group(0).strip()[:60])


def calcular_score(hallazgos):
    """Puntuación 0-100: penalización ponderada por hallazgo (alta 12, media 6, baja 2)."""
    pesos = {'alta': 12, 'media': 6, 'baja': 2}
    penal = sum(pesos[h['severidad']] for h in hallazgos)
    return max(0, 100 - penal)


def audit_html(html_text, url='(html)', lang='en'):
    """Analiza una cadena HTML y devuelve el informe de hallazgos (es/en)."""
    p = _Auditor()
    try:
        p.feed(html_text[:MAX_HTML])
        p.close()
    except Exception as e:  # noqa: BLE001
        return {'error': f'HTML no parseable: {e}'}

    # 1.3.1: grupos de radio (name compartido, ≥2) sin fieldset
    for nm, count in p._radio_group.items():
        if count >= 2 and not p._en_fieldset:
            p.fieldsets_faltan += 1

    # Campos cuyo id sí tiene un <label for> explícito en otro punto: fuera.
    p.campos_sin_label = [c for c in p.campos_sin_label if c[2] not in p._labels_for]

    hallazgos = []

    def add(severidad, code, key_msg, **fmt):
        h = {'severidad': severidad, 'criterio': _crit(lang, code), 'senal': key_msg,
             'hallazgo': _t(lang, key_msg).format(**fmt)}
        h['remediacion'] = _t(lang, key_msg + '_rem').format(**fmt)
        hallazgos.append(h)

    def add_ej(severidad, code, key_msg, ejemplos, **fmt):
        add(severidad, code, key_msg, **fmt)
        hallazgos[-1]['ejemplos'] = ejemplos[:5]

    if p.imgs_sin_alt:
        add_ej('alta', '1.1.1', 'imgs_alt', p.imgs_sin_alt, n=len(p.imgs_sin_alt))
    if p.input_img_sin_alt:
        add('alta', '1.1.1', 'input_img_alt', n=p.input_img_sin_alt)
    for tag, controles in p.sitios.items():
        add('alta', '4.1.2', 'ctrl_name', n=len(controles), tag=tag)
    if p.aria_hidden_focusable:
        add('alta', '4.1.2', 'aria_hidden_focusable',
            n=len(p.aria_hidden_focusable), tag=p.aria_hidden_focusable[0])
    if p.campos_sin_label:
        add_ej('alta', '3.3.2', 'field_label',
               [f'{t} name={n or "(sin name)"}' for t, n, _i in p.campos_sin_label],
               n=len(p.campos_sin_label))
    if p.click_sueltos:
        add('alta', '2.1.1', 'click_nonfocusable',
            n=len(p.click_sueltos), tag=p.click_sueltos[0])
    if p.labels_huerfanos:
        add('baja', '3.3.2', 'label_orphan', n=p.labels_huerfanos)
    if p._lista_malos:
        add('media', '1.3.1', 'list_structure', n=p._lista_malos)
    if not p.lang:
        add('media', '3.1.1', 'lang_missing')
    elif p.lang.lower().split('-')[0] not in _LANG_CODES:
        add('media', '3.1.1', 'lang_invalid', lang=p.lang)
    if not p.title.strip():
        add('media', '2.4.2', 'title_missing')
    if p.iframes_sin_title:
        add_ej('media', '4.1.2', 'iframe_title', p.iframes_sin_title, n=len(p.iframes_sin_title))
    if p.videos and p.videos_con_subs < p.videos:
        add('media', '1.2.2', 'video_captions', n=p.videos - p.videos_con_subs)
    if p.viewport and re.search(r'user-scalable\s*=\s*(no|0)', p.viewport, re.I):
        add('alta', '1.4.4', 'zoom_no')
    elif p.viewport and (m := re.search(r'maximum-scale\s*=\s*([\d.]+)', p.viewport, re.I)) \
            and float(m.group(1)) < 2:
        add('media', '1.4.4', 'zoom_max', v=m.group(1))
    if p.meta_refresh:
        m = re.match(r'\s*(\d+)', p.meta_refresh)
        segs = int(m.group(1)) if m else 0
        add('media' if segs > 0 else 'baja', '2.2.1', 'meta_refresh', v=segs)
    if p.tabindex_positivos:
        add_ej('media', '2.4.3', 'tabindex_pos',
               [f'{t}[tabindex={i}]' for t, i in p.tabindex_positivos],
               n=len(p.tabindex_positivos))
    if not (p.hay_main or p.hay_skip):
        add('media', '2.4.1', 'no_bypass')

    niveles = [n for n, _ in p.headings]
    if niveles:
        if p.h1s == 0:
            add('media', '1.3.1', 'no_h1')
        elif p.h1s > 1:
            add('baja', '1.3.1', 'multi_h1', n=p.h1s)
        prev = 0
        saltos = []
        for n in niveles:
            if prev and n > prev + 1:
                saltos.append(f'h{prev}→h{n}')
            prev = n
        if saltos:
            add('baja', '1.3.1', 'heading_skips', skips=', '.join(saltos[:5]))
    else:
        add('media', '1.3.1', 'no_headings')
    if p.vacios_h:
        add('baja', '1.3.1', 'empty_heading', n=p.vacios_h)
    if p.tablas and p.tablas_con_th < p.tablas:
        add('media', '1.3.1', 'table_no_th', n=p.tablas - p.tablas_con_th)
    if p.blank_sin_aviso:
        add('baja', '3.2.5', 'blank_no_warning', n=p.blank_sin_aviso)
    dups = sum(1 for _c, k in p.ids.items() if k > 1)
    if dups:
        add('baja', '4.1.2', 'dup_ids', n=dups)

    # --- v3.1: validez ARIA, autocomplete, enlaces, landmarks, accesskey ---
    refs_rotas = [f'{attr}="#{ref}"' for attr, ref in p.aria_refs if ref not in p.ids]
    if refs_rotas:
        add_ej('alta', '4.1.2', 'aria_ref_missing', refs_rotas, n=len(refs_rotas),
               ej=refs_rotas[0])
    if p.aria_valores:
        _eti = {'es': {'bool': 'true/false', 'int': 'entero', 'num': 'número', 'tokens': 'valores'},
                'en': {'bool': 'true/false', 'int': 'integer', 'num': 'number', 'tokens': 'one of'}}
        ejes = [f"{v['attr']}=\"{v['val']}\" ({v['lista'] if v['tipo'] == 'tokens' else _eti[lang][v['tipo']]})"
                for v in p.aria_valores]
        add_ej('media', '4.1.2', 'aria_value_invalid', ejes,
               n=len(p.aria_valores), ej=', '.join(ejes[:4]))
    if p.roles_desconocidos:
        add_ej('media', '4.1.2', 'role_unknown',
               sorted(set(p.roles_desconocidos)), n=len(p.roles_desconocidos),
               ej=', '.join(f'"{r}"' for r in sorted(set(p.roles_desconocidos))[:4]))
    if p.roles_sin_estado:
        add_ej('media', '4.1.2', 'role_required_attr', p.roles_sin_estado,
               n=len(p.roles_sin_estado), ej=', '.join(p.roles_sin_estado[:4]))
    if p.autocomplete_faltan:
        add_ej('media', '1.3.5', 'autocomplete', p.autocomplete_faltan,
               n=len(p.autocomplete_faltan), ej=', '.join(p.autocomplete_faltan[:4]))
    if p.medios_autoplay:
        add('media', '1.4.2', 'video_autoplay', n=p.medios_autoplay)
    if p.label_no_name:
        _ln = p.label_no_name[0]
        add_ej('media', '2.5.3', 'label_in_name',
               [f'«{t}» vs aria-label «{al}»' for t, al in p.label_no_name],
               n=len(p.label_no_name), ej=f'{_ln[0]} ≠ {_ln[1]}')
    if p.langs_partes:
        add_ej('media', '3.1.2', 'lang_partes', p.langs_partes,
               n=len(p.langs_partes), ej=', '.join(p.langs_partes[:4]))
    if p.down_events:
        add_ej('media', '2.5.2', 'down_event', p.down_events,
               n=len(p.down_events), ej=', '.join(p.down_events[:4]))
    # forms deep-dive
    if p.placeholder_only:
        add_ej('alta', '3.3.2', 'placeholder_only', p.placeholder_only,
               n=len(p.placeholder_only), ej=', '.join(p.placeholder_only[:3]))
    if p.required_sin_indicio:
        add_ej('baja', '3.3.2', 'required_no_indication', p.required_sin_indicio,
               n=len(p.required_sin_indicio), ej=', '.join(p.required_sin_indicio[:3]))
    if p.fieldsets_faltan:
        add('media', '1.3.1', 'fieldset_missing', n=p.fieldsets_faltan)
    if p.labels_vagos:
        add_ej('baja', '2.4.6', 'label_vague', p.labels_vagos,
               n=len(p.labels_vagos), ej=', '.join(p.labels_vagos[:3]))
    if p.financieros_sin_conf:
        add('media', '3.3.4', 'financial_no_confirm', n=p.financieros_sin_conf)
    if p.headings_vagos:
        add_ej('baja', '2.4.6', 'heading_quality', p.headings_vagos,
               n=len(p.headings_vagos), ej=', '.join(p.headings_vagos[:3]))
    if p.char_shortcuts:
        add_ej('baja', '2.1.4', 'char_shortcut', p.char_shortcuts,
               n=len(p.char_shortcuts), ej=', '.join(p.char_shortcuts[:3]))
    if p.drag_handlers:
        add_ej('baja', '2.5.7', 'drag_no_alt', p.drag_handlers,
               n=len(p.drag_handlers), ej=', '.join(p.drag_handlers[:3]))
    # 4.1.3: solo si hay evidencia de dinamismo (scripts con eventos, forms, fetch/XHR)
    dinamico = bool(p.click_sueltos or p._en_script or p.char_shortcuts or p.drag_handlers or p.campos_sin_label)
    if dinamico and p.status_regions == 0:
        add('media', '4.1.3', 'no_status_regions')
    if p.imagenes_texto:
        add_ej('baja', '1.4.5', 'images_of_text', p.imagenes_texto,
               n=len(p.imagenes_texto), ej2='')
    if p.captchas:
        add_ej('media', '3.3.8', 'captcha', p.captchas,
               n=len(p.captchas), ej=', '.join(p.captchas[:2]))
    # v3.12: partial signals on previously manual-only criteria
    if p.moviles:
        add_ej('baja', '2.2.2', 'motion_moving', p.moviles,
               n=len(p.moviles), ej=', '.join(p.moviles[:3]))
    if p.gestos:
        add_ej('baja', '2.5.1', 'gesture_no_click', p.gestos,
               n=len(p.gestos), ej=', '.join(p.gestos[:3]))
    if p.motions:
        add_ej('baja', '2.5.4', 'motion_actuation', p.motions,
               n=len(p.motions), ej=', '.join(p.motions[:3]))
    if p.orientation_locks:
        add_ej('baja', '1.3.4', 'orientation_lock', p.orientation_locks,
               n=len(p.orientation_locks), ej=', '.join(p.orientation_locks[:2]))
    if p.videos and p.videos_descriptions < p.videos:
        add('baja', '1.2.3', 'audio_desc_missing', n=p.videos - p.videos_descriptions)
    if p.sensory:
        add('baja', '1.3.3', 'sensory_text', ej='; '.join(p.sensory[:2])[:70])
    lm_dups = [f'{lm} ×{t[1]}' for lm, t in p.landmarks.items()
               if t[1] > 1 and t[0] == t[1]]
    if lm_dups:
        add('baja', '1.3.1', 'landmark_dup', n=len(lm_dups), ej=', '.join(lm_dups[:4]))
    if p.genericos >= 2:   # un enlace genérico único suele desambiguarse por contexto
        gen = [f'«{k}»' for k in p.enlaces if k in _TEXTO_GENERICO][:4]
        add('baja', '2.4.4', 'generic_link', n=p.genericos, ej=', '.join(gen))
    mismos = sum(1 for _k, hrefs in p.enlaces.items() if len(hrefs) > 1)
    if mismos:
        add('baja', '2.4.4', 'same_name_links', n=mismos)
    ak_dups = [f'"{k}" ×{v}' for k, v in p.accesos.items() if v > 1]
    if ak_dups:
        add('baja', '2.1.1', 'accesskey_dup', n=len(ak_dups), ej=', '.join(ak_dups[:4]))
    if p.labels_for_dups:
        add('baja', '3.3.2', 'multi_label', n=len(p.labels_for_dups))

    severidad_orden = {'alta': 0, 'media': 1, 'baja': 2}
    hallazgos.sort(key=lambda h: severidad_orden[h['severidad']])
    resumen = {s: sum(1 for h in hallazgos if h['severidad'] == s)
               for s in ('alta', 'media', 'baja')}
    return {
        'url': url,
        'score': calcular_score(hallazgos),
        'score_nota': _t(lang, 'score_nota'),
        'elementos_analizados': p.elementos,
        'resumen': resumen,
        'hallazgos': hallazgos,
        'limites': _t(lang, 'limites'),
    }


def _descarga(url, timeout=30, truncar_en=None):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; a11y-toolkit/3.2; WCAG audit)',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Encoding': 'gzip',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        techo = truncar_en or MAX_HTML
        datos = r.read(techo + 1)
        if len(datos) > techo and truncar_en is None:
            raise ValueError(f'HTML > {MAX_HTML // 1000000} MB, demasiado grande')
        if (r.headers.get('Content-Encoding') or '').lower() == 'gzip' or datos[:2] == b'\x1f\x8b':
            import gzip
            datos = gzip.decompress(datos)
        ctype = (r.headers.get('Content-Type') or '').lower()
        if ctype and 'html' not in ctype and 'xml' not in ctype and ctype.split(';')[0].strip():
            raise ValueError(f'la URL no devuelve HTML (Content-Type: {ctype.split(";")[0]})')
        charset = 'utf-8'
        m = re.search(rb'charset=["\']?([\w-]+)', datos[:2048])
        if m:
            charset = m.group(1).decode('ascii', 'ignore')
        try:
            return datos.decode(charset, 'replace')
        except LookupError:
            return datos.decode('utf-8', 'replace')


_T_ESQUEMA = {
    'es': 'solo se auditan URLs http/https; para HTML local usa --file / el argumento html',
    'en': 'only http/https URLs can be audited; for local HTML use --file / the html argument',
}


def audit_url(url, timeout=30, lang='en'):
    if url.split(':')[0].lower() not in ('http', 'https'):
        return {'error': _T_ESQUEMA.get(lang, _T_ESQUEMA['es'])}
    try:
        html_text = _descarga(url, timeout=timeout)
    except ValueError as e:
        return {'error': str(e)}
    except Exception as e:  # noqa: BLE001
        return {'error': _t(lang, 'descarga_error').format(e=e)}
    return audit_html(html_text, url, lang=lang)


_LOC = re.compile(r'<loc>\s*([^<\s]+)\s*</loc>', re.I)
_SITEMAP_MAX = 200


def _urls_sitemap(url, timeout=30):
    """Same-domain page URLs from /sitemap.xml (and nested sitemap indexes,
    one level). Zero dependencies, bounded."""
    from urllib.parse import urlsplit, urljoin
    host = urlsplit(url).netloc
    vistos, paginas = set(), []
    cola = [urljoin(url, '/sitemap.xml')]
    while cola and len(paginas) < _SITEMAP_MAX:
        sm = cola.pop(0)
        if sm in vistos:
            continue
        vistos.add(sm)
        try:
            datos = _descarga(sm, timeout=timeout, truncar_en=2_000_000)
        except Exception:  # noqa: BLE001
            continue
        if not datos.lstrip().startswith('<'):
            continue
        for loc in _LOC.findall(datos)[:_SITEMAP_MAX]:
            partes = urlsplit(loc)
            if partes.scheme not in ('http', 'https') or partes.netloc != host:
                continue
            limpio = loc.split('#')[0].rstrip('/')
            if limpio.endswith('.xml'):                     # nested sitemap
                if len(cola) < 8:
                    cola.append(limpio)
                continue
            if _NO_RASTREAR.search(partes.path):
                continue
            if limpio not in paginas:
                paginas.append(limpio)
    return paginas


_HREF = re.compile(r'<a\s[^>]*?href=["\']([^"\']+)["\']', re.I)
_NO_RASTREAR = re.compile(r'\.(pdf|jpg|jpeg|png|gif|webp|svg|zip|mp3|mp4|docx?|xlsx?|pptx?|xml|json|rss)(\?|$)', re.I)


def _enlaces_internos(html_text, base_url, origen):
    from urllib.parse import urljoin, urlsplit
    host = urlsplit(origen).netloc
    out = []
    for href in _HREF.findall(html_text):
        if href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            continue
        absoluta = urljoin(base_url, href.strip()).split('#')[0].rstrip('/')
        partes = urlsplit(absoluta)
        if partes.scheme not in ('http', 'https') or partes.netloc != host:
            continue
        if _NO_RASTREAR.search(partes.path):
            continue
        out.append(absoluta)
    return out


def evaluar_sitio(parsers, lang='en'):
    """Site-level criteria over the crawled parsers: 3.2.3/3.2.4 consistency,
    2.4.5 multiple ways. Pure function so tests need no network."""
    out = []
    if len(parsers) >= 3:
        firmas = [frozenset(p.nav_hrefs) for p in parsers if p.nav_hrefs]
        if len(firmas) >= 3 and len(set(firmas)) > 1:
            out.append({'severidad': 'media', 'criterio': _crit(lang, '3.2.3'),
                        'senal': 'nav_inconsistent',
                        'hallazgo': _t(lang, 'nav_inconsistent').format(
                            ej=f'{len(set(firmas))} distintas en {len(firmas)} páginas'),
                        'remediacion': _t(lang, 'nav_inconsistent_rem')})
    # 3.2.6 Consistent Help (A, new in 2.2): help links stable across pages
    firmas_help = [frozenset(p.help_hrefs) for p in parsers if p.help_hrefs]
    if len(firmas_help) >= 2 and len(parsers) >= 3 and len(set(firmas_help)) > 1:
        out.append({'severidad': 'media', 'criterio': _crit(lang, '3.2.6'),
                    'senal': 'help_inconsistent',
                    'hallazgo': _t(lang, 'help_inconsistent').format(
                        ej=f'{len(set(firmas_help))} variantes en {len(firmas_help)} páginas'),
                    'remediacion': _t(lang, 'help_inconsistent_rem')})
    if parsers and not any(p.tiene_busqueda or p.tiene_sitemap for p in parsers):
        out.append({'severidad': 'media', 'criterio': _crit(lang, '2.4.5'),
                    'senal': 'no_multiple_ways',
                    'hallazgo': _t(lang, 'no_multiple_ways'),
                    'remediacion': _t(lang, 'no_multiple_ways_rem')})
    return out


def audit_site(url, max_pages=5, timeout=30, lang='en', desde_sitemap=True):
    """Audita la URL y hasta max_pages-1 páginas más del mismo dominio
    (descubrimiento por enlaces). Igual de cero-dependencias que el resto."""
    max_pages = max(1, min(20, int(max_pages)))
    try:
        html_text = _descarga(url, timeout=timeout)
    except ValueError as e:
        return {'error': str(e)}
    except Exception as e:  # noqa: BLE001
        return {'error': _t(lang, 'descarga_error').format(e=e)}
    p0 = _Auditor()
    p0.feed(html_text[:MAX_HTML]); p0.close()
    informes = [audit_html(html_text, url, lang=lang)]
    parsers = [p0]
    vistos = {url.split('#')[0].rstrip('/')}
    # discovery: sitemap first (WCAG-EM's own enumeration), links as fallback
    urls_sm = _urls_sitemap(url, timeout=timeout) if desde_sitemap else []
    cola = urls_sm or _enlaces_internos(html_text, url, url)
    while cola and len(informes) < max_pages:
        siguiente = cola.pop(0)
        if siguiente in vistos:
            continue
        vistos.add(siguiente)
        try:
            html_pg = _descarga(siguiente, timeout=timeout)
        except Exception:  # noqa: BLE001
            continue
        informes.append(audit_html(html_pg, siguiente, lang=lang))
        pg = _Auditor()
        pg.feed(html_pg[:MAX_HTML]); pg.close()
        parsers.append(pg)
        if len(informes) < max_pages and not desde_sitemap:
            for nuevo in _enlaces_internos(html_pg, siguiente, url):
                if nuevo not in vistos:
                    cola.append(nuevo)
    hallazgos_sitio = evaluar_sitio(parsers, lang=lang)
    for h in hallazgos_sitio:
        for inf in informes[:1]:
            inf.setdefault('hallazgos', []).append(h)
            inf['score'] = calcular_score(inf['hallazgos'])
    scores = [pg['score'] for pg in informes if 'score' in pg]
    hallazgos_por_senal = {}
    for pg in informes:
        for h in pg.get('hallazgos', []):
            hallazgos_por_senal[h['senal']] = hallazgos_por_senal.get(h['senal'], 0) + 1
    return {
        'url': url,
        'modo': 'site',
        'descubrimiento': 'sitemap' if urls_sm else 'links',
        'paginas': len(informes),
        'score_medio': round(sum(scores) / len(scores)) if scores else None,
        'score_peor': min(scores) if scores else None,
        'senales_recurrentes': sorted(hallazgos_por_senal, key=hallazgos_por_senal.get, reverse=True)[:8],
        'informes': informes,
        'limites': _t(lang, 'limites'),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--url')
    g.add_argument('--file')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--pages', type=int, default=1,
                    help='páginas del mismo dominio a auditar (site crawl ligero)')
    a = ap.parse_args(argv)
    if a.url:
        try:
            res = (audit_site(a.url, max_pages=a.pages, lang=a.lang,
                              desde_sitemap=not a.no_sitemap)
                   if a.pages > 1 else audit_url(a.url, lang=a.lang))
        except Exception as e:  # noqa: BLE001
            print(json.dumps({'error': f'no se pudo descargar: {e}'}))
            return 1
    else:
        with open(a.file, encoding='utf-8', errors='replace') as f:
            res = audit_html(f.read(), a.file, lang=a.lang)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
