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
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from . import a11yi18n

MAX_HTML = 3_000_000

# Campos de formulario que necesitan etiqueta visible o nombre accesible
_FIELDS = {'text', 'email', 'tel', 'url', 'search', 'password', 'number',
           'date', 'time', 'datetime-local', 'month', 'week', 'checkbox',
           'radio', 'file', 'range', 'color'}
_CONTROLS = ('a', 'button', 'summary')

# Subetiquetas BCP-47 principales habituales (validación blanda)
_LANG_CODES = set('''af am ar az be bg bn bs ca cs cy da de el en es et eu fa fi fr ga gl
gu he hi hr hu hy id is it ja ka kk km kn ko ky lo lt lv mk ml mn mr ms my ne nl or pa
pl ps pt ro ru rw si sk sl sq sr sv sw ta te tg th ti tk tr uk ur uz vi zh'''.split())

_REGIONS = set('''af ax al dz as ad ao ai aq ag ar am aw au at az bs bh bd bb by be bz
bm bt bo bq ba bw bv io br io bn bg bf bi cv kh cm ca ky cf td cl cn cx cc co km cg cd
ck cr ci hr cu cw cy cz dj dk dm do ec eg sv gq er ee et fk fo fj fi fr gf pf tf ga gm
ge de gh gi gr gl gd gp gu gt gn gw gy ht hm hn hk hu is in id ir iq ie im il it jm je
jo kz ke ki kp kr kw kg la lv lb ls lr ly li lt lu mo mg mw my mv ml mt mh mq mr mu yt
mx fm md mc mn me ms ma mz mm na nr np nl nc nz ni ne ng nu nf mp no om pk pw ps pa pg
py pe ph pn pl pr qa re ro ru rw bl sh kn lc mf pm vc ws sm st sa sn rs sc sl sx sb so
za gs ss es lk sd sr sj sz se ch sy tw tj tz th tl tg tk to tt tn tr tm tc tv ug ua ae
gb us um uy uz vu ve vn vg vi wf eh ye zm zw'''.split())

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
_GENERIC_TEXT = {'more', 'read more', 'learn more', 'click here', 'here', 'this',
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
_PERSONAL_DATA = re.compile(
    r'(^|[\W_])(name|nombre|email|correo|phone|telefono|tel|address|direccion|postal|zip|'
    r'city|ciudad|country|pais|organi[sz]ation|company|empresa|street|user|usuario)([\W_]|$)', re.I)

# Tokens autofill válidos (HTML §7.5 — subconjunto práctico del estándar;
# one-time-code incluido: los campos OTP lo exigen y los lectores lo usan)
_AUTOFILL_TOKENS = {
    'name', 'honorific-prefix', 'given-name', 'additional-name', 'family-name',
    'nickname', 'username', 'new-password', 'current-password', 'one-time-code',
    'organization', 'street-address', 'address-line1', 'address-line2',
    'address-line3', 'address-level4', 'address-level3', 'address-level2',
    'address-level1', 'country', 'country-name', 'postal-code', 'cc-name',
    'cc-given-name', 'cc-family-name', 'cc-number', 'cc-exp', 'cc-exp-month',
    'cc-exp-year', 'cc-csc', 'cc-type', 'transaction-currency',
    'transaction-amount', 'language', 'bday', 'bday-day', 'bday-month',
    'bday-year', 'sex', 'url', 'photo',
    'tel', 'tel-country-code', 'tel-national', 'tel-area-code', 'tel-local',
    'email', 'impp',
    # esquemas de contacto (WHATWG §7.5: «work email», «mobile tel»…)
    'home', 'work', 'mobile', 'fax', 'pager',
    # nombres de campo que faltaban
    'cc-additional-name', 'tel-extension', 'webauthn',
}
# sección-*: comodín del estándar (section-main, section-top…)
_SECTION = __import__('re').compile(r'^section-[a-z0-9-]+$')

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

T = a11yi18n.pair('audit')  # locales/<lang>.json — community-editable

# Aviso de ventana nueva: texto que lo indica o icono con nombre
_BLANK_HINT = re.compile(r'nueva|nuevo|ventana|pesta|tab\b|window|external|externo|exterior', re.I)


def _t(lang, key, n=None):
    """Message by key; `{"one","other"}` entries resolve via the locale's
    CLDR plural rule when the caller passes the count."""
    value = T.get(lang, T['en']).get(key, key)
    return a11yi18n.plural_entry(value, lang, n) if n is not None else value


def _crit(lang, code):
    return CRIT.get(lang, CRIT['es'])[code]


class _Auditor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.imgs_no_alt = []
        self.controls_by_kind = {}          # tag → lista de atributos de controles sin nombre
        self.fields_no_label = []
        self.iframes_no_title = []
        self.lang = None
        self.lang_region_invalid = None
        self.title = ''
        self._in_title = False
        self._in_script = False
        self._in_style = False
        self.headings = []        # (nivel, texto)
        self._heading_level = None
        self._heading_text = []
        self._visible_text = []
        self._heading_text = []
        self.positive_tabindices = []
        self.viewport = None
        self.elements = 0
        # Pila de controles interactivos (a/button/summary) para recoger su
        # texto interno, que es la fuente más habitual de nombre accesible.
        self._ctrl = []
        self._label_depth = 0
        self._labels_stack = []   # un booleano por <label> abierto: ¿contiene campo?
        self._labels_for = {}     # id → nº de <label for> que lo apuntan
        self.orphan_labels = 0
        # Nuevas señales
        self.aria_hidden_focusable = []   # tag de interactivos con aria-hidden
        self.stray_clicks = []           # tags no interactivos con onclick
        self.meta_refresh = None
        self.videos = 0
        self.videos_with_captions = 0
        self._in_video = False
        self.tables = 0
        self.tables_with_th = 0
        self._in_table = False
        self._th_in_table = False
        self.blank_no_warning = 0
        self.blank_total = 0
        self.hay_main = False
        self.hay_skip = False
        self.h1s = 0
        self.empty_h = 0
        self.ids = {}
        self.input_img_no_alt = 0
        # v3.1: validez ARIA, autocomplete, enlaces, landmarks, accesskey, autoplay
        self.aria_refs = []       # (attr, id) referenciados por aria-labelledby/describedby
        self.aria_values = []    # valores aria-* inválidos
        self.unknown_roles = []
        self.roles_without_state = []   # widgets con role que exige aria-valuenow
        self.landmarks = {}       # tipo → [con_etiqueta, total]
        self.accesskeys = {}         # accesskey → tag
        self.missing_autocomplete = []
        self.autocomplete_invalid = []
        self.links = {}         # nombre normalizado → set de hrefs
        self.generics = 0
        self.labels_for_dups = {}  # id → n labels (los >1, varios)
        self.media_autoplay = 0
        self._list_depth = 0
        self._li_depth = 0
        self._bad_list = 0
        self.label_no_name = []     # (texto visible, aria-label) 2.5.3
        self.lang_parts_invalid = []      # lang inválidos en elementos no-html
        self.down_events = []       # onmousedown/ontouchstart/onpointerdown
        self.captchas = []          # detección 3.3.8
        self.mobiles = []           # marquee/blink/inline infinite animation (2.2.2)
        self.nav_hrefs = set()      # hrefs inside <nav> (site-level 3.2.3 signature)
        self.help_hrefs = set()     # help/contact links (site-level 3.2.6 signature)
        self.images_of_text = []
        self.vague_headings = []
        self.char_shortcuts = []
        self.drag_handlers = []
        self.status_regions = 0
        self.placeholder_only = []     # 3.3.2: placeholder sin label
        self.required_no_indication = [] # 3.3.2: required sin * ni "obligatorio"
        self.missing_fieldsets = 0      # 1.3.1: radio/check groups sin fieldset
        self._radio_group = {}
        self._radio_in_fieldset = {}         # name → count (para detectar grupos)
        self.vague_labels = []         # 2.4.6: label quality
        self.financial_no_confirm = 0  # 3.3.4: financial form no confirm
        self._financial_form = False
        self._confirm_form = False    # 1.4.5 suspicion: img inside heading or very long alt
        self._in_nav = 0
        self._in_fieldset = False
        self.has_search = False
        self.has_sitemap = False
        self.gestures = []            # touchmove/drag handlers (2.5.1)
        self.motions = []           # deviceorientation/devicemotion (2.5.4)
        self.orientation_locks = [] # screen.orientation.lock / orientation MQ (1.3.4)
        self.videos_descriptions = 0   # videos WITH descriptions track
        self.sensory = []           # sensory-only instruction patterns (1.3.3)
        self._skip_labels_pend = []  # labels declarados antes que su campo

    def _close_control(self, tag):
        if not self._ctrl:
            return
        c = self._ctrl[-1]
        if c['tag'] != tag:
            return
        self._ctrl.pop()
        a = c['attrs']
        text = ' '.join(c['text']).strip()
        if not (text or a.get('aria-label') or a.get('aria-labelledby')
                or a.get('title') or a.get('alt')):
            # el nombre del control puede venir también de una imagen interna
            if not c.get('img_interna'):
                self.controls_by_kind.setdefault(tag, []).append(a)
        if tag == 'a':
            visible = ' '.join(text.lower().split())
            al = ' '.join((a.get('aria-label') or '').lower().split())
            if visible and al and visible not in al:
                self.label_no_name.append((text[:40], a.get('aria-label')[:60]))
            if (a.get('target') or '').lower() == '_blank':
                self.blank_total += 1
                if not _BLANK_HINT.search(text) and not _BLANK_HINT.search(a.get('aria-label') or '') \
                        and not _BLANK_HINT.search(a.get('title') or ''):
                    self.blank_no_warning += 1
            elif (a.get('href') or '').strip().startswith('#') and text:
                self.hay_skip = True  # ancla interna con texto: candidato a skip link
            name = (text or a.get('aria-label') or a.get('title') or '').strip()
            href = (a.get('href') or '').strip()
            if name and href:
                entry_key = ' '.join(name.lower().split())[:60]
                self.links.setdefault(entry_key, set()).add(href)
                if entry_key in _GENERIC_TEXT:
                    self.generics += 1

    def _field_note(self):
        """El elemento que acaba de abrirse es un campo: marca su <label> ancestro."""
        if self._labels_stack:
            self._labels_stack[-1] = True

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.elements += 1
        if a.get('id'):
            self.ids[a['id']] = self.ids.get(a['id'], 0) + 1
        if tag == 'html':
            self.lang = (a.get('lang') or '').strip()
            parts = self.lang.split('-')
            if len(parts) == 2 and parts[1] and parts[1].isalpha() \
                    and parts[1].lower() not in _REGIONS:
                self.lang_region_invalid = self.lang
        elif tag == 'title':
            self._in_title = True
        elif tag == 'script':
            self._in_script = True
        elif tag == 'style':
            self._in_style = True
        elif tag == 'meta':
            if a.get('name', '').lower() == 'viewport':
                self.viewport = a.get('content', '')
            elif (a.get('http-equiv') or '').lower() == 'refresh':
                self.meta_refresh = a.get('content', '')
        elif tag == 'img':
            if 'alt' not in a:
                self.imgs_no_alt.append(a.get('src', '')[:100])
            alt = (a.get('alt') or '').strip()
            if self._ctrl and alt:
                self._ctrl[-1]['img_interna'] = True
            if self._heading_level is not None or len(alt) > 120:
                self.images_of_text.append('imagen dentro de encabezado' if self._heading_level is not None
                                           else f'alt de {len(alt)} caracteres')
        elif tag == 'iframe':
            if not (a.get('title') or a.get('aria-label')):
                self.iframes_no_title.append((a.get('src') or '')[:100])
        elif tag == 'nav':
            self._in_nav += 1
        elif tag in _CONTROLS:
            # Enlace no interactivo (ancla pura sin href): no se audita.
            if tag == 'a' and not (a.get('href') or '').strip():
                pass
            else:
                self._ctrl.append({'tag': tag, 'attrs': a, 'text': [], 'inner_img': False})
                href = (a.get('href') or '').strip()
                if self._in_nav and href and not href.startswith('#'):
                    self.nav_hrefs.add(href.split('#')[0].rstrip('/'))
                if href and re.search(r'help|contact|support|ayuda|contacto|soporte|asistencia',
                                      href, re.I):
                    self.help_hrefs.add(href.split('#')[0].rstrip('/'))
                if href and re.search(r'sitemap|site-map|mapa-del-sitio|mapa_web|mapaweb', href, re.I):
                    self.has_sitemap = True
        elif tag == 'input':
            self._field_note()
            kind = (a.get('type') or 'text').lower()
            if kind == 'image':
                if not (a.get('alt') or a.get('aria-label') or a.get('title')):
                    self.input_img_no_alt += 1
            elif kind in ('submit', 'button', 'reset'):
                if not (a.get('value') or a.get('aria-label') or a.get('alt')):
                    self.controls_by_kind.setdefault('input:' + kind, []).append(a)
            if kind == 'search' or re.search(r'search|busqueda|b[uú]squeda', (a.get('name') or '') + (a.get('id') or ''), re.I):
                self.has_search = True
            elif kind in _FIELDS:
                has_name = a.get('aria-label') or a.get('aria-labelledby') or a.get('title')
                if not has_name and self._label_depth == 0:
                    self.fields_no_label.append((kind, a.get('name', '')[:60], a.get('id')))
                if 'autocomplete' not in a and kind != 'search' and (
                        kind in ('email', 'tel')
                        or _PERSONAL_DATA.search((a.get('name') or '') + ' ' + (a.get('id') or ''))):
                    self.missing_autocomplete.append(f'input type={kind} name={a.get("name") or "?"}'[:44])
        if tag == 'input' and 'autocomplete' in a:
            for tok in (a['autocomplete'] or '').split():
                if tok and tok not in ('on', 'off') and tok.split(':')[-1] not in _AUTOFILL_TOKENS \
                        and tok not in ('shipping', 'billing') and not _SECTION.match(tok):
                    self.autocomplete_invalid.append(
                        f'{tok} (input name={a.get("name") or "?"})'[:60])
        elif tag in ('select', 'textarea'):
            self._field_note()
            has_name = a.get('aria-label') or a.get('aria-labelledby') or a.get('title')
            if not has_name and self._label_depth == 0:
                self.fields_no_label.append((tag, a.get('name', '')[:60], a.get('id')))
        elif tag == 'label':
            self._label_depth += 1
            self._label_text_current = []
            self._labels_stack.append(False)
            if a.get('for'):
                self._labels_for[a['for']] = self._labels_for.get(a['for'], 0) + 1
                if self._labels_for[a['for']] > 1:
                    self.labels_for_dups[a['for']] = self._labels_for[a['for']]
                self._labels_stack[-1] = True
        elif tag == 'marquee':
            self.mobiles.append('<marquee>')
        elif tag == 'blink':
            self.mobiles.append('<blink>')
        elif tag == 'track':
            kind = (a.get('kind') or '').lower()
            if kind == 'descriptions':
                self.videos_descriptions += 1
            elif kind in ('captions', 'subtitles'):
                self.videos_with_captions += 1
        elif tag in ('video', 'audio'):
            if tag == 'video':
                self.videos += 1
                self._in_video = True
            if 'autoplay' in a:
                self.media_autoplay += 1
        elif tag in ('ul', 'ol'):
            self._list_depth += 1
        elif tag == 'li':
            self._li_depth += 1
        elif tag == 'table':
            self.tables += 1
            self._in_table = True
            self._th_in_table = False
        elif tag == 'th':
            self._th_in_table = True
        elif tag == 'main' or (a.get('role') or '').lower() == 'main':
            self.hay_main = True
        elif tag not in _CONTROLS + ('input', 'select', 'textarea', 'label', 'option',
                                      'video', 'audio', 'details', 'summary'):
            if a.get('onclick') and not a.get('role') and 'tabindex' not in a:
                self.stray_clicks.append(tag)
        # v3.9: 3.1.2 idioma de partes (elemento no-html con lang inválido)
        if tag != 'html' and a.get('lang'):
            prim = a['lang'].strip().lower().split('-')[0]
            if prim and prim not in _LANG_CODES:
                self.lang_parts_invalid.append(f'{tag} lang="{a["lang"]}"')
        # v3.9: 2.5.2 sospecha de activación en down-event
        for _de in ('onmousedown', 'ontouchstart', 'onpointerdown'):
            if a.get(_de):
                self.down_events.append(f'{tag}[{_de}]')
                break
        # v3.12: 2.2.2 inline looping animation
        style = a.get('style') or ''
        if 'animation' in style and 'infinite' in style:
            self.mobiles.append(f'{tag}[style animation…infinite]')
        # v3.12: 2.5.1 gesture without click alternative (attribute-level hint)
        if a.get('ontouchmove') or a.get('ondrag'):
            if not (a.get('onclick') or tag in ('input', 'button', 'a')):
                self.gestures.append(f'{tag}[{list(a)[0] if a else ""}]')
        # forms: placeholder-only, required sin indicio, financial
        if tag == 'form':
            self._financial_form = False
            self._confirm_form = False
            action = (a.get('action') or '').lower()
            if re.search(r'pay|purchase|checkout|buy|order|contract|legal|billing',
                         action, re.I):
                self._financial_form = True
        if tag in ('input', 'select', 'textarea'):
            if a.get('placeholder') and not (a.get('aria-label') or a.get('aria-labelledby')):
                if self._label_depth == 0 and not a.get('id'):
                    self.placeholder_only.append(f'{tag}[placeholder="{a.get("placeholder","")[:30]}"]')
            if a.get('required') is not None or 'required' in a or a.get('aria-required') == 'true':
                ph = (a.get('placeholder') or '').lower()
                title_ = (a.get('title') or '').lower()
                if not re.search(r'\*|requerid|obligator|required|necesari|precisa', ph + title_):
                    self.required_no_indication.append(
                        f'{tag}[name={a.get("name","?")}]')
            if tag == 'input' and a.get('type') == 'radio':
                nm = a.get('name') or '_sin_nombre'
                self._radio_group[nm] = self._radio_group.get(nm, 0) + 1
                self._radio_in_fieldset[nm] = self._in_fieldset
        if tag == 'fieldset':
            self._in_fieldset = True
        if tag in ('button', 'input'):
            val = (a.get('value') or a.get('data-action') or '').lower()
            if re.search(r'confirm|verificar|review|revisar|accept|aceptar', val):
                self._confirm_form = True
            # checkbox de términos
        if tag == 'input' and a.get('type') == 'checkbox':
            nm = (a.get('name') or '').lower()
            if re.search(r'terms|accept|agree|terminos|aceptar|legal|privacy', nm):
                self._confirm_form = True
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
                self.aria_values.append({'attr': _ar, 'val': _val, 'type': 'bool'})
            elif _ar in _ARIA_INT and not _val.isdigit():
                self.aria_values.append({'attr': _ar, 'val': _val, 'type': 'int'})
            elif _ar in _ARIA_NUM:
                try:
                    float(_val)
                except ValueError:
                    self.aria_values.append({'attr': _ar, 'val': _val, 'type': 'num'})
            elif _ar in _ARIA_TOKENS and _val not in _ARIA_TOKENS[_ar]:
                self.aria_values.append({'attr': _ar, 'val': _val,
                                          'type': 'tokens',
                                          'valid_tokens': '/'.join(sorted(v for v in _ARIA_TOKENS[_ar] if v))})
        if a.get('role'):
            role = a['role'].strip().split()[0].lower()
            if role not in _ROLES_ARIA and not role.startswith('doc-'):
                self.unknown_roles.append(role)
            if role in ('slider', 'spinbutton') and 'aria-valuenow' not in a:
                self.roles_without_state.append(f'{tag}[role={role}]')
        landmark_role = a.get('role', '').lower() if a.get('role') in (
            'banner', 'contentinfo', 'navigation', 'complementary', 'main', 'form', 'search', 'region') else None
        lm = tag if tag in ('header', 'footer', 'nav', 'aside', 'main', 'search') else landmark_role
        if lm and not (a.get('aria-label') or a.get('aria-labelledby')):
            t = self.landmarks.setdefault(lm, [0, 0])
            t[0] += 1
            t[1] += 1
        elif lm:
            self.landmarks.setdefault(lm, [0, 0])[1] += 1
        if a.get('accesskey'):
            k = a['accesskey'].strip().lower()
            self.accesskeys[k] = self.accesskeys.get(k, 0) + 1
        if self._list_depth > 0 and self._li_depth == 0 \
                and tag not in ('li', 'script', 'template', 'ul', 'ol'):
            self._bad_list += 1
        aria_hidden = (a.get('aria-hidden') or '').lower() == 'true'
        ti_raw = (a.get('tabindex') or '').strip()
        if aria_hidden and ti_raw != '-1' and (
                tag in _CONTROLS + ('input', 'select', 'textarea', 'iframe', 'video')
                or a.get('onclick')):
            self.aria_hidden_focusable.append(tag)
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._heading_level = int(tag[1])
            self._heading_text = []
        ti = a.get('tabindex')
        if ti and ti.isdigit() and int(ti) > 0:
            self.positive_tabindices.append((tag, int(ti)))

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False
        elif tag == 'script':
            self._in_script = False
        elif tag == 'style':
            self._in_style = False
        elif tag == 'label':
            self._label_depth = max(0, self._label_depth - 1)
            if hasattr(self, '_label_text_current'):
                txt = ' '.join(self._label_text_current).strip()
                lowered = txt.lower()
                if txt and (len(txt) < 2 or re.fullmatch(
                    r'(campo|field|input|texto|text|dato|value|entrada|box|caja)[\s\d]*', lowered)):
                    self.vague_labels.append(f'"{txt[:30]}"')
            if self._labels_stack and not self._labels_stack.pop():
                self.orphan_labels += 1
        elif tag == 'fieldset':
            self._in_fieldset = False
        elif tag == 'form':
            if self._financial_form and not self._confirm_form:
                self.financial_no_confirm += 1
        elif tag == 'nav':
            self._in_nav = max(0, self._in_nav - 1)
        elif tag == 'li':
            self._li_depth = max(0, self._li_depth - 1)
        elif tag in ('ul', 'ol'):
            self._list_depth = max(0, self._list_depth - 1)
        elif tag in _CONTROLS:
            self._close_control(tag)
        elif tag == 'video':
            self._in_video = False
        elif tag == 'table':
            if self._in_table:
                if not self._th_in_table:
                    pass  # se contabiliza abajo
                else:
                    self.tables_with_th += 1
            self._in_table = False
        elif tag == 'th':
            pass
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6') and self._heading_level:
            text = ' '.join(self._heading_text).strip()
            if not text:
                self.empty_h += 1
            else:
                self.headings.append((self._heading_level, text[:80]))
                if self._heading_level == 1:
                    self.h1s += 1
                lowered = text.lower().strip()
                if len(text) < 4 or len(text) > 120:
                    self.vague_headings.append(f'h{self._heading_level} "{text[:40]}"')
                elif re.fullmatch(r'(secci[oó]n|section|chapter|cap[ií]tulo|m[aá]s|more|info|informaci[oó]n|information|details|detalle|click|ver|see|leer|read|continue|seguir)[\s\d.]*', lowered):
                    self.vague_headings.append(f'h{self._heading_level} "{text[:40]}"')
                elif re.fullmatch(r'[\d.\s]+', lowered):
                    self.vague_headings.append(f'h{self._heading_level} "{text[:40]}"')
            self._heading_level = None

    _RE_CHAR_KEY = re.compile(r'key(?:Code)?\s*===?\s*["\']([a-zA-Z0-9])["\']', re.S)

    def handle_script_wait(self, data):
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
        in_code = getattr(self, '_in_script', False) or getattr(self, '_in_style', False)
        if data.strip() and not in_code and not self._in_title:
            self._visible_text.append(data)  # prosa visible: ni JS, ni CSS, ni título
        if self._in_title:
            self.title += data
        elif getattr(self, '_in_script', False):
            self.handle_script_wait(data)
        else:
            # Un texto puede pertenecer a la vez a un enlace dentro de un
            # encabezado (<h2><a>Guías</a></h2>): alimenta a ambos.
            if self._label_depth > 0 and hasattr(self, '_label_text_current'):
                self._label_text_current.append(data)
            if self._ctrl:
                self._ctrl[-1]['text'].append(data)
            if self._heading_level is not None:
                self._heading_text.append(data)
            m = _SENSORIAL.search(data)
            if m and len(self.sensory) < 6:
                self.sensory.append(m.group(0).strip()[:60])



# Señales renombradas en 5.11.0 (superficie pública 100% inglesa).
# Los informes y ledgers guardados antes del rename siguen siendo válidos:
# toda ingesta pasa por normalize_signal().
SIGNAL_ALIASES = {
    'imgs_alt': 'img_no_alt',
    'descarga_error': 'fetch_error',
    'lang_partes': 'element_lang_invalid',
    'lang_region_invalida': 'lang_region_invalid',
    'docx_falsos_encabezados': 'docx_fake_headings',
    'docx_sin_idioma': 'docx_no_lang',
    'docx_sin_tabla_header': 'docx_table_no_header',
}


def normalize_signal(signal):
    """Nombre canónico de una señal (acepta las formas españolas previas a 5.11.0)."""
    return SIGNAL_ALIASES.get(signal, signal)


def normalize_report(report):
    """Informe con señales normalizadas (no muta el original)."""
    if not isinstance(report, dict):
        return report
    findings = report.get('findings')
    if not findings:
        return report
    out = dict(report)
    out['findings'] = [dict(h, signal=normalize_signal(h.get('signal', '')))
                       for h in findings]
    return out


def compute_score(findings):
    """Puntuación 0-100: penalización ponderada por hallazgo (alta 12, media 6, baja 2)."""
    weights = {'high': 12, 'medium': 6, 'low': 2}
    penal = sum(weights[h['severity']] for h in findings)
    return max(0, 100 - penal)


_VOCAL = re.compile(r'[aeiouyáéíóúàèìòùäëïöü]+', re.I)


def _syllables(word):
    """Heurística de sílabas por grupos vocálicos (suficiente para índices)."""
    return max(1, len(_VOCAL.findall(word)))


def _reading_level(text, lang='en'):
    """Flesch Reading Ease (en) / Fernández-Huerta (es) — 3.1.5 cognitivo.

    Informativo (AAA): se reporta, no penaliza el score. 100 = muy fácil;
    <50 = difícil (nivel universitario)."""
    clean = re.sub(r'<[^>]+>', ' ', text)
    words = re.findall(r"[\wáéíóúñü'-]{2,}", clean, re.UNICODE)
    phrases = [f for f in re.split(r'[.!?;:]+', clean) if f.strip()]
    if len(words) < 40 or not phrases:
        return None  # muestra insuficiente: no inventar un índice
    sil = sum(_syllables(w) for w in words)
    ppf = len(words) / len(phrases)   # palabras por frase
    spf = sil / len(words) * 100     # sílabas por 100 palabras
    if lang == 'es':
        # Fernández-Huerta: L = 206.84 − 0.60·P − 1.02·F
        # (P = sílabas por 100 palabras, F = palabras por frase)
        index = 206.84 - 0.60 * spf - 1.02 * ppf
        scale = ('muy fácil', 'fácil', 'estándar', 'difícil', 'muy difícil')
    else:
        index = 206.835 - 1.015 * ppf - 84.6 * (sil / len(words))
        scale = ('very easy', 'easy', 'standard', 'difficult', 'very difficult')
    index = round(max(0, min(100, index)), 1)
    level = scale[0] if index >= 90 else scale[1] if index >= 70 else \
        scale[2] if index >= 50 else scale[3] if index >= 30 else scale[4]
    return {'index': index, 'level': level, 'scale': 'fernandez-huerta' if lang == 'es' else 'flesch-reading-ease',
            'words': len(words), 'sentences': len(phrases),
            'note': 'informational (3.1.5 is level AAA): reported, never scored'}


def _not_measured(lang='en'):
    """Criterios que el pase estático NO mide: renderizado obligatorio.

    Honradez del informe: un 100 estático nunca debe leerse como
    "contraste bien" (la limitación que la crítica externa destapó:
    .btn-primary{background:var(--x)} es invisible para el HTML puro)."""
    from .a11ycrit import RENDERED_ONLY, _C
    return [{
        'criterion': f"{c} {_C[c][1]['en'][0]}",
        'reason': ('requires the rendered audit (a11y_audit_dom / a11ytoolkit dom): '
                   'computed styles, cascade, var(), real layout'
                   if lang == 'en' else
                   'requiere la auditoría renderizada (a11y_audit_dom / a11ytoolkit dom): '
                   'estilos computados, cascada, var(), layout real'),
    } for c in sorted(RENDERED_ONLY)]


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
        if count >= 2 and not p._radio_in_fieldset.get(nm, False):
            p.missing_fieldsets += 1

    # Campos cuyo id sí tiene un <label for> explícito en otro punto: fuera.
    p.fields_no_label = [c for c in p.fields_no_label if c[2] not in p._labels_for]

    findings = []

    def add(severity, code, key_msg, **fmt):
        h = {'severity': severity, 'criterion': _crit(lang, code), 'signal': key_msg,
             'issue': _t(lang, key_msg, n=fmt.get('n')).format(**fmt)}
        h['remediation'] = _t(lang, key_msg + '_rem').format(**fmt)
        findings.append(h)

    def add_ej(severity, code, key_msg, examples, **fmt):
        add(severity, code, key_msg, **fmt)
        findings[-1]['examples'] = examples[:5]

    if p.imgs_no_alt:
        add_ej('high', '1.1.1', 'img_no_alt', p.imgs_no_alt, n=len(p.imgs_no_alt))
    if p.input_img_no_alt:
        add('high', '1.1.1', 'input_img_alt', n=p.input_img_no_alt)
    for tag, controls in p.controls_by_kind.items():
        add('high', '4.1.2', 'ctrl_name', n=len(controls), tag=tag)
    if p.aria_hidden_focusable:
        add('high', '4.1.2', 'aria_hidden_focusable',
            n=len(p.aria_hidden_focusable), tag=p.aria_hidden_focusable[0])
    if p.fields_no_label:
        add_ej('high', '3.3.2', 'field_label',
               [f'{t} name={n or "(sin name)"}' for t, n, _i in p.fields_no_label],
               n=len(p.fields_no_label))
    if p.stray_clicks:
        add('high', '2.1.1', 'click_nonfocusable',
            n=len(p.stray_clicks), tag=p.stray_clicks[0])
    if p.orphan_labels:
        add('low', '3.3.2', 'label_orphan', n=p.orphan_labels)
    if p._bad_list:
        add('medium', '1.3.1', 'list_structure', n=p._bad_list)
    if not p.lang:
        add('medium', '3.1.1', 'lang_missing')
    elif p.lang.lower().split('-')[0] not in _LANG_CODES:
        add('medium', '3.1.1', 'lang_invalid', lang=p.lang)
    elif p.lang_region_invalid:
        add('low', '3.1.1', 'lang_region_invalid', l=p.lang_region_invalid)
    t_clean = (p.title or '').strip().lower()
    if not t_clean:
        add('medium', '2.4.2', 'title_missing')
    elif t_clean in ('untitled', 'documento', 'documento sin título', 'sin título',
                      'home', 'inicio', 'page 1', 'new page', 'página 1',
                      'untitled document', 'sin nombre', 'document'):
        add('low', '2.4.2', 'title_generic', t=t_clean)
    if p.iframes_no_title:
        add_ej('medium', '4.1.2', 'iframe_title', p.iframes_no_title, n=len(p.iframes_no_title))
    if p.videos and p.videos_with_captions < p.videos:
        add('medium', '1.2.2', 'video_captions', n=p.videos - p.videos_with_captions)
    if p.viewport and re.search(r'user-scalable\s*=\s*(no|0)', p.viewport, re.I):
        add('high', '1.4.4', 'zoom_no')
    elif p.viewport and (m := re.search(r'maximum-scale\s*=\s*([\d.]+)', p.viewport, re.I)) \
            and float(m.group(1)) < 2:
        add('medium', '1.4.4', 'zoom_max', v=m.group(1))
    if p.meta_refresh:
        m = re.match(r'\s*(\d+)', p.meta_refresh)
        segs = int(m.group(1)) if m else 0
        add('medium' if segs > 0 else 'low', '2.2.1', 'meta_refresh', v=segs)
    if p.positive_tabindices:
        add_ej('medium', '2.4.3', 'tabindex_pos',
               [f'{t}[tabindex={i}]' for t, i in p.positive_tabindices],
               n=len(p.positive_tabindices))
    if not (p.hay_main or p.hay_skip):
        add('medium', '2.4.1', 'no_bypass')

    levels = [n for n, _ in p.headings]
    if levels:
        if p.h1s == 0:
            add('medium', '1.3.1', 'no_h1')
        elif p.h1s > 1:
            add('low', '1.3.1', 'multi_h1', n=p.h1s)
        prev = 0
        jumps = []
        for n in levels:
            if prev and n > prev + 1:
                jumps.append(f'h{prev}→h{n}')
            prev = n
        if jumps:
            add('low', '1.3.1', 'heading_skips', skips=', '.join(jumps[:5]))
    else:
        add('medium', '1.3.1', 'no_headings')
    if p.empty_h:
        add('low', '1.3.1', 'empty_heading', n=p.empty_h)
    if p.tables and p.tables_with_th < p.tables:
        add('medium', '1.3.1', 'table_no_th', n=p.tables - p.tables_with_th)
    if p.blank_no_warning:
        add('low', '3.2.5', 'blank_no_warning', n=p.blank_no_warning)
    dups = sum(1 for _c, k in p.ids.items() if k > 1)
    if dups:
        add('low', '4.1.2', 'dup_ids', n=dups)

    # --- v3.1: validez ARIA, autocomplete, enlaces, landmarks, accesskey ---
    broken_refs = [f'{attr}="#{ref}"' for attr, ref in p.aria_refs if ref not in p.ids]
    if broken_refs:
        add_ej('high', '4.1.2', 'aria_ref_missing', broken_refs, n=len(broken_refs),
               ej=broken_refs[0])
    if p.aria_values:
        _labels = {'es': {'bool': 'true/false', 'int': 'entero', 'num': 'número', 'tokens': 'valores'},
                'en': {'bool': 'true/false', 'int': 'integer', 'num': 'number', 'tokens': 'one of'}}
        axes = [f"{v['attr']}=\"{v['val']}\" ({v['valid_tokens'] if v['type'] == 'tokens' else _labels[lang][v['type']]})"
                for v in p.aria_values]
        add_ej('medium', '4.1.2', 'aria_value_invalid', axes,
               n=len(p.aria_values), ej=', '.join(axes[:4]))
    if p.unknown_roles:
        add_ej('medium', '4.1.2', 'role_unknown',
               sorted(set(p.unknown_roles)), n=len(p.unknown_roles),
               ej=', '.join(f'"{r}"' for r in sorted(set(p.unknown_roles))[:4]))
    if p.roles_without_state:
        add_ej('medium', '4.1.2', 'role_required_attr', p.roles_without_state,
               n=len(p.roles_without_state), ej=', '.join(p.roles_without_state[:4]))
    if p.missing_autocomplete:
        add_ej('medium', '1.3.5', 'autocomplete', p.missing_autocomplete,
               n=len(p.missing_autocomplete), ej=', '.join(p.missing_autocomplete[:4]))
    if p.autocomplete_invalid:
        add_ej('medium', '1.3.5', 'autocomplete_invalid', p.autocomplete_invalid,
               n=len(p.autocomplete_invalid), ej=', '.join(p.autocomplete_invalid[:4]))
    if p.media_autoplay:
        add('medium', '1.4.2', 'video_autoplay', n=p.media_autoplay)
    if p.label_no_name:
        _ln = p.label_no_name[0]
        add_ej('medium', '2.5.3', 'label_in_name',
               [f'«{t}» vs aria-label «{al}»' for t, al in p.label_no_name],
               n=len(p.label_no_name), ej=f'{_ln[0]} ≠ {_ln[1]}')
    if p.lang_parts_invalid:
        add_ej('medium', '3.1.2', 'element_lang_invalid', p.lang_parts_invalid,
               n=len(p.lang_parts_invalid), ej=', '.join(p.lang_parts_invalid[:4]))
    if p.down_events:
        add_ej('medium', '2.5.2', 'down_event', p.down_events,
               n=len(p.down_events), ej=', '.join(p.down_events[:4]))
    # forms deep-dive
    if p.placeholder_only:
        add_ej('high', '3.3.2', 'placeholder_only', p.placeholder_only,
               n=len(p.placeholder_only), ej=', '.join(p.placeholder_only[:3]))
    if p.required_no_indication:
        add_ej('low', '3.3.2', 'required_no_indication', p.required_no_indication,
               n=len(p.required_no_indication), ej=', '.join(p.required_no_indication[:3]))
    if p.missing_fieldsets:
        add('medium', '1.3.1', 'fieldset_missing', n=p.missing_fieldsets)
    if p.vague_labels:
        add_ej('low', '2.4.6', 'label_vague', p.vague_labels,
               n=len(p.vague_labels), ej=', '.join(p.vague_labels[:3]))
    if p.financial_no_confirm:
        add('medium', '3.3.4', 'financial_no_confirm', n=p.financial_no_confirm)
    if p.vague_headings:
        add_ej('low', '2.4.6', 'heading_quality', p.vague_headings,
               n=len(p.vague_headings), ej=', '.join(p.vague_headings[:3]))
    if p.char_shortcuts:
        add_ej('low', '2.1.4', 'char_shortcut', p.char_shortcuts,
               n=len(p.char_shortcuts), ej=', '.join(p.char_shortcuts[:3]))
    if p.drag_handlers:
        add_ej('low', '2.5.7', 'drag_no_alt', p.drag_handlers,
               n=len(p.drag_handlers), ej=', '.join(p.drag_handlers[:3]))
    # 4.1.3: solo si hay evidencia de dinamismo (scripts con eventos, forms, fetch/XHR)
    dynamic = bool(p.stray_clicks or p._in_script or p.char_shortcuts or p.drag_handlers or p.fields_no_label)
    if dynamic and p.status_regions == 0:
        add('medium', '4.1.3', 'no_status_regions')
    if p.images_of_text:
        add_ej('low', '1.4.5', 'images_of_text', p.images_of_text,
               n=len(p.images_of_text), ej2='')
    if p.captchas:
        add_ej('medium', '3.3.8', 'captcha', p.captchas,
               n=len(p.captchas), ej=', '.join(p.captchas[:2]))
    # v3.12: partial signals on previously manual-only criteria
    if p.mobiles:
        add_ej('low', '2.2.2', 'motion_moving', p.mobiles,
               n=len(p.mobiles), ej=', '.join(p.mobiles[:3]))
    if p.gestures:
        add_ej('low', '2.5.1', 'gesture_no_click', p.gestures,
               n=len(p.gestures), ej=', '.join(p.gestures[:3]))
    if p.motions:
        add_ej('low', '2.5.4', 'motion_actuation', p.motions,
               n=len(p.motions), ej=', '.join(p.motions[:3]))
    if p.orientation_locks:
        add_ej('low', '1.3.4', 'orientation_lock', p.orientation_locks,
               n=len(p.orientation_locks), ej=', '.join(p.orientation_locks[:2]))
    if p.videos and p.videos_descriptions < p.videos:
        add('low', '1.2.3', 'audio_desc_missing', n=p.videos - p.videos_descriptions)
    if p.sensory:
        add('low', '1.3.3', 'sensory_text', ej='; '.join(p.sensory[:2])[:70])
    lm_dups = [f'{lm} ×{t[1]}' for lm, t in p.landmarks.items()
               if t[1] > 1 and t[0] == t[1]]
    if lm_dups:
        add('low', '1.3.1', 'landmark_dup', n=len(lm_dups), ej=', '.join(lm_dups[:4]))
    if p.generics >= 2:   # un enlace genérico único suele desambiguarse por contexto
        gen = [f'«{k}»' for k in p.links if k in _GENERIC_TEXT][:4]
        add('low', '2.4.4', 'generic_link', n=p.generics, ej=', '.join(gen))
    same = sum(1 for _k, hrefs in p.links.items() if len(hrefs) > 1)
    if same:
        add('low', '2.4.4', 'same_name_links', n=same)
    ak_dups = [f'"{k}" ×{v}' for k, v in p.accesskeys.items() if v > 1]
    if ak_dups:
        add('low', '2.1.1', 'accesskey_dup', n=len(ak_dups), ej=', '.join(ak_dups[:4]))
    if p.labels_for_dups:
        add('low', '3.3.2', 'multi_label', n=len(p.labels_for_dups))

    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: severity_order[h['severity']])
    summary = {s: sum(1 for h in findings if h['severity'] == s)
               for s in ('high', 'medium', 'low')}
    page_lang = (p.lang or '').split('-')[0].lower() if getattr(p, 'lang', None) else ''
    reading = _reading_level(' '.join(p._visible_text),
                             page_lang if page_lang in ('es', 'en') else lang)

    return {
        'mode': 'static',
        'url': url,
        'reading_level': reading,
        'score': compute_score(findings),
        'score_note': _t(lang, 'score_note'),
        'not_measured': _not_measured(lang),
        'elements_scanned': p.elements,
        'summary': summary,
        'findings': findings,
        'limits': _t(lang, 'limits'),
    }


# ── redirect policy hook ───────────────────────────────────────────────────
# urlopen follows 3xx (up to 10 hops) to ANY host without asking: every hop
# is a NEW destination nobody validated. Callers that audit untrusted URLs
# can inject a per-hop validator here (returns False → the redirect is not
# followed). Without injection, behavior is unchanged.
validate_redirect = None   # callable(url) -> bool


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if validate_redirect is not None and not validate_redirect(newurl):
            raise ValueError(f'redirect to a disallowed destination: {newurl[:96]}')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_CheckedRedirect)


def _fetch(url, timeout=30, truncate_at=None, accept_ct=()):
    scheme = url.split(':', 1)[0].lower() if ':' in url else ''
    if scheme not in ('http', 'https'):
        # política única para TODAS las rutas de descarga (audit_url la
        # comprobaba; audit_site y el crawl pasaban por aquí sin frontera)
        return {'error': f'scheme not allowed: {scheme or url[:24]!r} (http/https only)'}
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; a11y-toolkit/3.2; WCAG audit)',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Encoding': 'gzip',
    })
    with _OPENER.open(req, timeout=timeout) as r:
        ceiling = truncate_at or MAX_HTML
        # TOTAL-CLOCK reading: the socket timeout is per-operation and a server
        # dribbling one byte per operation reset it forever. Read in chunks
        # with a global deadline: what arrived is enough to audit (partial).
        import time
        read_deadline = time.monotonic() + max(timeout, 5)
        try:
            r.fp.raw._sock.settimeout(min(timeout, 5))
        except (AttributeError, OSError):
            pass
        data = b''
        while len(data) < ceiling + 1:
            if time.monotonic() >= read_deadline:
                break          # partial: what arrived suffices to audit
            chunk = r.read(min(65536, ceiling + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > ceiling and truncate_at is None:
            raise ValueError(f'HTML > {MAX_HTML // 1000000} MB, demasiado grande')
        if (r.headers.get('Content-Encoding') or '').lower() == 'gzip' or data[:2] == b'\x1f\x8b':
            import zlib
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            data = d.decompress(data, ceiling)   # techo duro también al descomprimir
            if d.unconsumed_tail:
                data = data[:ceiling]            # bomba gzip: truncado, no OOM
        ctype = (r.headers.get('Content-Type') or '').lower()
        base = ctype.split(';')[0].strip()
        extra_ok = any(base == p or base.startswith(p + '/') for p in accept_ct)
        if ctype and not extra_ok and 'html' not in ctype and 'xml' not in ctype and base:
            raise ValueError(f'la URL no devuelve HTML (Content-Type: {base})')
        # the HEADER charset wins over body sniffing (HTTP has priority over
        # <meta>): a server declaring iso-8859-1 without a meta tag otherwise
        # produces U+FFFD inside findings
        charset = None
        m_ct = re.search(r'charset=["\']?([\w-]+)', (r.headers.get('Content-Type') or '').lower(), re.I)
        if m_ct:
            charset = m_ct.group(1)
        if not charset:
            m = re.search(rb'charset=["\']?([\w-]+)', data[:2048])
            if m:
                charset = m.group(1).decode('ascii', 'ignore')
        try:
            return data.decode(charset or 'utf-8', 'replace')
        except LookupError:
            return data.decode('utf-8', 'replace')


_T_SCHEME = {
    'es': 'solo se auditan URLs http/https; para HTML local usa --file / el argumento html',
    'en': 'only http/https URLs can be audited; for local HTML use --file / the html argument',
}


def audit_url(url, timeout=30, lang='en'):
    if url.split(':')[0].lower() not in ('http', 'https'):
        return {'error': _T_SCHEME.get(lang, _T_SCHEME['es'])}
    try:
        html_text = _fetch(url, timeout=timeout)
    except ValueError as e:
        return {'error': str(e)}
    except Exception as e:  # noqa: BLE001
        return {'error': _t(lang, 'fetch_error').format(e=e)}
    return audit_html(html_text, url, lang=lang)


_LOC = re.compile(r'<loc>\s*([^<\s]+)\s*</loc>', re.I)
_SITEMAP_MAX = 200


def _urls_sitemap(url, timeout=30):
    """Same-domain page URLs from /sitemap.xml (and nested sitemap indexes,
    one level). Zero dependencies, bounded."""
    from urllib.parse import urlsplit, urljoin
    host = urlsplit(url).netloc
    seen, pages = set(), []
    queue = [urljoin(url, '/sitemap.xml')]
    while queue and len(pages) < _SITEMAP_MAX:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        try:
            data = _fetch(sm, timeout=timeout, truncate_at=2_000_000)
        except Exception:  # noqa: BLE001
            continue
        if not data.lstrip().startswith('<'):
            continue
        for loc in _LOC.findall(data)[:_SITEMAP_MAX]:
            parts = urlsplit(loc)
            if parts.scheme not in ('http', 'https') or parts.netloc != host:
                continue
            clean = loc.split('#')[0].rstrip('/')
            if clean.endswith('.xml'):                     # nested sitemap
                if len(queue) < 8:
                    queue.append(clean)
                continue
            if _DO_NOT_TRACK.search(parts.path):
                continue
            if clean not in pages:
                pages.append(clean)
    return pages


_HREF = re.compile(r'<a\s[^>]*?href=["\']([^"\']+)["\']', re.I)
_DO_NOT_TRACK = re.compile(r'\.(pdf|jpg|jpeg|png|gif|webp|svg|zip|mp3|mp4|docx?|xlsx?|pptx?|xml|json|rss)(\?|$)', re.I)


def _internal_links(html_text, base_url, origin):
    from urllib.parse import urljoin, urlsplit
    host = urlsplit(origin).netloc
    out = []
    for href in _HREF.findall(html_text):
        if href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            continue
        absolute = urljoin(base_url, href.strip()).split('#')[0].rstrip('/')
        parts = urlsplit(absolute)
        if parts.scheme not in ('http', 'https') or parts.netloc != host:
            continue
        if _DO_NOT_TRACK.search(parts.path):
            continue
        out.append(absolute)
    return out


def evaluate_site(parsers, lang='en'):
    """Site-level criteria over the crawled parsers: 3.2.3/3.2.4 consistency,
    2.4.5 multiple ways. Pure function so tests need no network."""
    out = []
    if len(parsers) >= 3:
        signatures = [frozenset(p.nav_hrefs) for p in parsers if p.nav_hrefs]
        if len(signatures) >= 3 and len(set(signatures)) > 1:
            out.append({'severity': 'medium', 'criterion': _crit(lang, '3.2.3'),
                        'signal': 'nav_inconsistent',
                        'issue': _t(lang, 'nav_inconsistent').format(
                            ej=f'{len(set(signatures))} distintas en {len(signatures)} páginas'),
                        'remediation': _t(lang, 'nav_inconsistent_rem')})
    # 3.2.6 Consistent Help (A, new in 2.2): help links stable across pages
    signatures_help = [frozenset(p.help_hrefs) for p in parsers if p.help_hrefs]
    if len(signatures_help) >= 2 and len(parsers) >= 3 and len(set(signatures_help)) > 1:
        out.append({'severity': 'medium', 'criterion': _crit(lang, '3.2.6'),
                    'signal': 'help_inconsistent',
                    'issue': _t(lang, 'help_inconsistent').format(
                        ej=f'{len(set(signatures_help))} variantes en {len(signatures_help)} páginas'),
                    'remediation': _t(lang, 'help_inconsistent_rem')})
    if parsers and not any(p.has_search or p.has_sitemap for p in parsers):
        out.append({'severity': 'medium', 'criterion': _crit(lang, '2.4.5'),
                    'signal': 'no_multiple_ways',
                    'issue': _t(lang, 'no_multiple_ways'),
                    'remediation': _t(lang, 'no_multiple_ways_rem')})
    return out


def audit_site(url, max_pages=5, timeout=30, lang='en', from_sitemap=True,
               budget=None):
    """Audita la URL y hasta max_pages-1 páginas más del mismo dominio
    (descubrimiento por enlaces). Igual de cero-dependencias que el resto."""
    max_pages = max(1, min(20, int(max_pages)))
    import time
    deadline = (time.monotonic() + budget) if budget else None
    try:
        html_text = _fetch(url, timeout=timeout)
    except ValueError as e:
        return {'error': str(e)}
    except Exception as e:  # noqa: BLE001
        return {'error': _t(lang, 'fetch_error').format(e=e)}
    p0 = _Auditor()
    p0.feed(html_text[:MAX_HTML]); p0.close()
    reports = [audit_html(html_text, url, lang=lang)]
    parsers = [p0]
    seen = {url.split('#')[0].rstrip('/')}
    # discovery: sitemap first (WCAG-EM's own enumeration), links as fallback
    urls_sm = _urls_sitemap(url, timeout=timeout) if from_sitemap else []
    queue = urls_sm or _internal_links(html_text, url, url)
    while queue and len(reports) < max_pages:
        if deadline is not None and time.monotonic() >= deadline:
            break          # budget exhausted: partial, not eternal
        next = queue.pop(0)
        if next in seen:
            continue
        seen.add(next)
        try:
            html_pg = _fetch(next, timeout=timeout)
        except Exception:  # noqa: BLE001
            continue
        reports.append(audit_html(html_pg, next, lang=lang))
        pg = _Auditor()
        pg.feed(html_pg[:MAX_HTML]); pg.close()
        parsers.append(pg)
        if len(reports) < max_pages and not from_sitemap:
            for new in _internal_links(html_pg, next, url):
                if new not in seen:
                    queue.append(new)
    site_findings = evaluate_site(parsers, lang=lang)
    for h in site_findings:
        for inf in reports[:1]:
            inf.setdefault('findings', []).append(h)
            inf['score'] = compute_score(inf['findings'])
    scores = [pg['score'] for pg in reports if 'score' in pg]
    findings_by_signal = {}
    for pg in reports:
        for h in pg.get('findings', []):
            findings_by_signal[h['signal']] = findings_by_signal.get(h['signal'], 0) + 1
    return {
        'url': url,
        'mode': 'site',
        'budget_exhausted': bool(deadline is not None and time.monotonic() >= deadline),
        'not_measured': _not_measured(lang),
        'discovery': 'sitemap' if urls_sm else 'links',
        'pages': len(reports),
        'mean_score': round(sum(scores) / len(scores)) if scores else None,
        'worst_score': min(scores) if scores else None,
        'recurring_signals': sorted(findings_by_signal, key=findings_by_signal.get, reverse=True)[:8],
        'reports': reports,
        'limits': _t(lang, 'limits'),
    }


# extensiones que no son HTML auditable pero sí "web tocado" — se listan, no se audita
_WEB_TOUCHED = {'.css', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.astro',
                '.php', '.erb', '.twig', '.liquid', '.hbs', '.ejs', '.md', '.svg'}
_AUDITABLE = {'.html', '.htm'}


def audit_changed(base='HEAD', lang='en', cwd='.'):
    """Audit ONLY what changed since `base` — the CI gate.

    HEAD (default) covers staged+unstaged work; a ref like origin/main covers
    a branch (three-dot diff). HTML files are audited; other web-touched files
    are listed as not auditable (the honest boundary: without the build there
    is no HTML to audit). Deleted files are skipped.
    """
    import subprocess
    spec = ['git', 'diff', '--name-only', '--diff-filter=d',
            base if base == 'HEAD' else f'{base}...HEAD']
    try:
        out = subprocess.run(spec, cwd=cwd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return {'error': 'git not available'}
    if out.returncode != 0:
        return {'error': f'git diff failed: {out.stderr.strip()[:200]}'}
    changed = [f for f in out.stdout.splitlines() if f.strip()]
    # los NUEVOS sin trackear no salen en git diff — entran también:
    # una página recién creada no puede escaparse del gate local
    untracked = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'],
                               cwd=cwd, capture_output=True, text=True, timeout=30)
    if untracked.returncode == 0:
        changed += [f for f in untracked.stdout.splitlines() if f.strip() and f not in changed]
    auditables, web_touched = [], []
    for f in changed:
        ext = os.path.splitext(f)[1].lower()
        if ext in _AUDITABLE:
            auditables.append(f)
        elif ext in _WEB_TOUCHED:
            web_touched.append(f)

    reports = []
    for f in auditables:
        filepath = os.path.join(cwd, f)
        if not os.path.exists(filepath):
            continue  # renombrado/eliminado entre el diff y ahora
        with open(filepath, encoding='utf-8', errors='replace') as fh:
            reports.append(audit_html(fh.read(), f, lang=lang))

    findings = [h for r in reports for h in r.get('findings', [])]
    scores = [r['score'] for r in reports if r.get('score') is not None]
    blocking = sum(1 for h in findings if h['severity'] in ('high', 'medium'))
    return {
        'mode': 'changed', 'base': base, 'lang': lang,
        'files': {'changed': len(changed), 'audited': len(reports),
                  'web_touched_not_auditable': sorted(web_touched)},
        'reports': reports,
        'score': round(sum(scores) / len(scores)) if scores else None,
        'worst_score': min(scores) if scores else None,
        'summary': {sev: sum(1 for h in findings if h['severity'] == sev)
                    for sev in ('high', 'medium', 'low')},
        'blocking': blocking,
        'note': ('exit code 2 = high/medium findings in changed files (CI gate; '
                 'untracked new files included); web-touched non-HTML files are '
                 'listed, not audited — audit the built/deployed output for those.'
                 if lang == 'en' else
                 'código de salida 2 = hallazgos high/medium en lo tocado (gate CI; '
                 'los nuevos sin trackear también entran); los ficheros web no-HTML '
                 'se listan sin auditar — audita la salida compilada/desplegada '
                 'para esos.'),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--url')
    g.add_argument('--file')
    g.add_argument('--changed', action='store_true',
                   help='audit ONLY files changed since --base (default HEAD) — CI gate')
    ap.add_argument('--base', default='HEAD',
                    help='git ref for --changed (default HEAD; e.g. origin/main)')
    ap.add_argument('--lang', default='en', choices=['en', 'es'])
    ap.add_argument('--pages', type=int, default=1,
                    help='crawl ligero mismo dominio (1 = solo la página)')
    ap.add_argument('--no-sitemap', action='store_true',
                    help='descubre por enlaces, sin leer el sitemap')
    a = ap.parse_args(argv)
    if a.changed:
        res = audit_changed(base=a.base, lang=a.lang)
        if 'error' in res:
            print(json.dumps(res))
            return 1
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 2 if res.get('blocking') else 0
    if a.url:
        try:
            res = (audit_site(a.url, max_pages=a.pages, lang=a.lang,
                              from_sitemap=not a.no_sitemap)
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
