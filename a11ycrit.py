#!/usr/bin/env python3
"""Conocimiento de criterios WCAG 2.2 (es/en) — el «qué es» detrás del auditor.

a11y_criterion(code) devuelve, para cada criterio que el toolkit evalúa: nombre
oficial, nivel, qué exige, fallos habituales, cómo comprobarlo a mano y con qué
herramienta del toolkit. Es el puente entre un hallazgo automático y la
comprensión real del criterio (lo que otros servidores MCP resuelven con un
servidor de conocimiento aparte).

CLI:
  a11ycrit.py 2.5.8 [--lang en]
  a11ycrit.py --list
"""

import argparse
import json
import sys

# code → (nivel, {es: (nombre, exige, fallos, prueba)}, {en: ...})
_C = {
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
    '2.4.4': ('AA', {
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


def criterio(code, lang='es'):
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


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('code', nargs='?')
    ap.add_argument('--lang', default='es', choices=['es', 'en'])
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args(argv)
    if a.list or not a.code:
        print(json.dumps({'criterios_disponibles': sorted(_C)}, indent=1))
        return 0
    print(json.dumps(criterio(a.code, a.lang), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
