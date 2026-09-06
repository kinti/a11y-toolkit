#!/usr/bin/env python3
"""Auditoría exprés de accesibilidad sobre HTML (heurísticas WCAG 2.2, cero dependencias).

a11y_audit_url / audit_html revisan señales automáticas de las que derivan
criterios concretos de WCAG 2.2. Cada hallazgo incluye remediación concreta.

Criterios cubiertos (estáticos): 1.1.1, 1.2.2, 1.3.1, 1.4.4, 2.1.1, 2.2.1,
2.4.1, 2.4.2, 2.4.3, 3.1.1, 3.2.5, 3.3.2, 4.1.2.

La automatización cubre ~un tercio de WCAG: la revisión manual sigue siendo
insustituible. Esta herramienta es filtro, no veredicto.

CLI:
  a11yaudit.py --url https://example.com [--lang en]
  a11yaudit.py --file pagina.html
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
gu he hi hr hu hy id is it ja ka kk km kn ko ky lo lt lv mk ml mn mr ms my ne nl no or pa
pl ps pt ro ru rw si sk sl sq sr sv sw ta te tg th ti tk tr uk ur uz vi zh'''.split())

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
        '4.1.2': '4.1.2 Nombre, función, valor',
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
        '4.1.2': '4.1.2 Name, Role, Value',
    },
}

T = {
    'es': {
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
        'zoom_no': 'El viewport bloquea el zoom del usuario (user-scalable=no/0).',
        'zoom_no_rem': 'Elimina user-scalable=no y maximum-scale: el zoom es un derecho del usuario (1.4.4).',
        'zoom_max': 'El viewport limita el zoom (maximum-scale={v}; se recomienda no limitar o ≥2).',
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
        'limites': ('Automatización ≈ un tercio de WCAG: esto es un filtro exprés, no sustituye '
                    'revisión manual (teclado, lector de pantalla, contraste real, refrán de '
                    'auditoría).'),
    },
    'en': {
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
        'zoom_no': 'The viewport blocks user zoom (user-scalable=no/0).',
        'zoom_no_rem': 'Remove user-scalable=no and maximum-scale: zooming is the user\'s right (1.4.4).',
        'zoom_max': 'The viewport limits zoom (maximum-scale={v}; recommend no limit or ≥2).',
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
        self._labels_for = set()
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
            if (a.get('target') or '').lower() == '_blank':
                self.blank_total += 1
                if not _BLANK_HINT.search(texto) and not _BLANK_HINT.search(a.get('aria-label') or '') \
                        and not _BLANK_HINT.search(a.get('title') or ''):
                    self.blank_sin_aviso += 1
            elif (a.get('href') or '').strip().startswith('#') and texto:
                self.hay_skip = True  # ancla interna con texto: candidato a skip link

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
        elif tag == 'meta':
            if a.get('name', '').lower() == 'viewport':
                self.viewport = a.get('content', '')
            elif (a.get('http-equiv') or '').lower() == 'refresh':
                self.meta_refresh = a.get('content', '')
        elif tag == 'img':
            if 'alt' not in a:
                self.imgs_sin_alt.append(a.get('src', '')[:100])
            if self._ctrl and (a.get('alt') or '').strip():
                self._ctrl[-1]['img_interna'] = True
        elif tag == 'iframe':
            if not (a.get('title') or a.get('aria-label')):
                self.iframes_sin_title.append((a.get('src') or '')[:100])
        elif tag in _CONTROLES:
            # Enlace no interactivo (ancla pura sin href): no se audita.
            if tag == 'a' and not (a.get('href') or '').strip():
                pass
            else:
                self._ctrl.append({'tag': tag, 'attrs': a, 'texto': [], 'img_interna': False})
        elif tag == 'input':
            self._nota_campo()
            tipo = (a.get('type') or 'text').lower()
            if tipo == 'image':
                if not (a.get('alt') or a.get('aria-label') or a.get('title')):
                    self.input_img_sin_alt += 1
            elif tipo in ('submit', 'button', 'reset'):
                if not (a.get('value') or a.get('aria-label') or a.get('alt')):
                    self.sitios.setdefault('input:' + tipo, []).append(a)
            elif tipo in _CAMPOS:
                tiene_nombre = a.get('aria-label') or a.get('aria-labelledby') or a.get('title')
                if not tiene_nombre and self._label_depth == 0:
                    self.campos_sin_label.append((tipo, a.get('name', '')[:60], a.get('id')))
        elif tag in ('select', 'textarea'):
            self._nota_campo()
            tiene_nombre = a.get('aria-label') or a.get('aria-labelledby') or a.get('title')
            if not tiene_nombre and self._label_depth == 0:
                self.campos_sin_label.append((tag, a.get('name', '')[:60], a.get('id')))
        elif tag == 'label':
            self._label_depth += 1
            self._labels_stack.append(False)
            if a.get('for'):
                self._labels_for.add(a['for'])
                self._labels_stack[-1] = True
        elif tag == 'video':
            self.videos += 1
            self._en_video = True
        elif tag == 'track':
            if (a.get('kind') or '').lower() in ('captions', 'subtitles'):
                self.videos_con_subs += 1
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
        aria_hidden = (a.get('aria-hidden') or '').lower() == 'true'
        if aria_hidden and (tag in _CONTROLES + ('input', 'select', 'textarea', 'iframe', 'video')
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
        elif tag == 'label':
            self._label_depth = max(0, self._label_depth - 1)
            if self._labels_stack and not self._labels_stack.pop():
                self.labels_huerfanos += 1
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
            self._nivel_h = None

    def handle_data(self, data):
        if self._en_title:
            self.title += data
        else:
            # Un texto puede pertenecer a la vez a un enlace dentro de un
            # encabezado (<h2><a>Guías</a></h2>): alimenta a ambos.
            if self._ctrl:
                self._ctrl[-1]['texto'].append(data)
            if self._nivel_h is not None:
                self._texto_h.append(data)


def audit_html(html_text, url='(html)', lang='es'):
    """Analiza una cadena HTML y devuelve el informe de hallazgos (es/en)."""
    p = _Auditor()
    try:
        p.feed(html_text[:MAX_HTML])
        p.close()
    except Exception as e:  # noqa: BLE001
        return {'error': f'HTML no parseable: {e}'}

    # Campos cuyo id sí tiene un <label for> explícito en otro punto: fuera.
    p.campos_sin_label = [c for c in p.campos_sin_label if c[2] not in p._labels_for]

    hallazgos = []

    def add(severidad, code, key_msg, **fmt):
        h = {'severidad': severidad, 'criterio': _crit(lang, code),
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

    severidad_orden = {'alta': 0, 'media': 1, 'baja': 2}
    hallazgos.sort(key=lambda h: severidad_orden[h['severidad']])
    resumen = {s: sum(1 for h in hallazgos if h['severidad'] == s)
               for s in ('alta', 'media', 'baja')}
    return {
        'url': url,
        'elementos_analizados': p.elementos,
        'resumen': resumen,
        'hallazgos': hallazgos,
        'limites': _t(lang, 'limites'),
    }


def audit_url(url, timeout=30, lang='es'):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; a11y-toolkit/3.0; WCAG audit)',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Encoding': 'gzip',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        datos = r.read(MAX_HTML + 1)
        if len(datos) > MAX_HTML:
            return {'error': f'HTML > {MAX_HTML // 1000000} MB, demasiado grande'}
        if (r.headers.get('Content-Encoding') or '').lower() == 'gzip' or datos[:2] == b'\x1f\x8b':
            import gzip
            datos = gzip.decompress(datos)
        ctype = (r.headers.get('Content-Type') or '').lower()
        if ctype and 'html' not in ctype and 'xml' not in ctype and ctype.split(';')[0].strip():
            return {'error': f'la URL no devuelve HTML (Content-Type: {ctype.split(";")[0]})'}
        charset = 'utf-8'
        m = re.search(rb'charset=["\']?([\w-]+)', datos[:2048])
        if m:
            charset = m.group(1).decode('ascii', 'ignore')
        try:
            html_text = datos.decode(charset, 'replace')
        except LookupError:
            html_text = datos.decode('utf-8', 'replace')
    return audit_html(html_text, url, lang=lang)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--url')
    g.add_argument('--file')
    ap.add_argument('--lang', default='es', choices=['es', 'en'])
    a = ap.parse_args(argv)
    if a.url:
        try:
            res = audit_url(a.url, lang=a.lang)
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
