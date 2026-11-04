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

# elementos vacíos: sin endtag en HTML — no empujan pila de visibilidad ni profundidad
_VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
         'meta', 'param', 'source', 'track', 'wbr'}

# ── kernel de anotación por elemento (a11yannotate) ────────────────────────
# Fuente única de la identidad de elemento: la comparten el auditor (que
# graba rutas mientras parsea) y el localizador de a11yannotate (que vuelve a
# parsear el MISMO html para inyectar marcas). Mismo algoritmo, mismo orden.
VOID_TAGS = _VOID


def path_segment(tag, nth):
    """Segmento de ruta CSS determinista (nth SIEMPRE: los id duplicados no
    pueden romper la identidad)."""
    return f'{tag}:nth-of-type({nth})'

# roles que convierten cualquier elemento en campo etiquetable (e086e5).
# OJO: 'search' NO está — es un LANDMARK (WAI-ARIA 1.2), no un widget: un
# <form role="search"> sin aria-label es un landmark sin etiqueta, no un
# campo sin label (el patrón del tutorial W3C no puede dar HIGH 3.3.2)
_ROLE_FIELDS = {'textbox', 'searchbox', 'spinbutton', 'combobox', 'listbox',
                'checkbox', 'radio', 'switch'}

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
searchfield comment suggestion blockquote
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

# gramática de modificadores (WHATWG §7.5): el modificador exige un campo
# de su familia detrás — "work email" ✓, "work photo" ✗, "shipping" solo ✗
_MOD_CONTACT = {'home', 'work', 'mobile', 'fax', 'pager'}
_MOD_ADDRESS = {'shipping', 'billing'}
# el modificador de contacto solo vale pegado a estos campos (ABNF 73f2c2)
_FIELDS_AFTER_CONTACT = {'email', 'impp', 'tel', 'tel-country-code', 'tel-national',
                         'tel-area-code', 'tel-local', 'tel-extension'}
_FIELDS_AFTER_ADDRMOD = {'street-address', 'address-line1', 'address-line2', 'address-line3',
                         'address-level1', 'address-level2', 'address-level3', 'address-level4',
                         'country', 'country-name', 'postal-code'}
_AUTOFILL_FIELDS = _AUTOFILL_TOKENS - _MOD_CONTACT - _MOD_ADDRESS

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
    'aria-relevant': {'additions', 'removals', 'text', 'all'},   # lista: se valida token a token
}
_ARIA_IDREFS = {'aria-labelledby', 'aria-describedby', 'aria-controls', 'aria-errormessage'}
# atributos cuyo tipo tristate aún incluye 'undefined' en ARIA (casos 6a7281)
_ARIA_BOOL_UNDEFINED = {'aria-expanded', 'aria-selected', 'aria-grabbed'}

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

# Widgets de accesibilidad de terceros ("overlays"): detección por dominio del
# script cargado. NO es un fallo WCAG (ningún criterio dice "no uses overlays";
# la posición pública es comunitaria: overlayfactsheet.com) — se reporta como
# dato del informe para la diligencia de compra. Detección ≠ juicio: la página
# puede seguir teniendo fallos reales, y esto no toca score ni findings.
_OVERLAY_WIDGETS = (
    ('accessiBe', ('accessibe.com', 'acsbapp.com')),
    ('UserWay', ('userway.org',)),
    ('AudioEye', ('audioeye.com',)),
    ('EqualWeb', ('equalweb.com',)),
    ("FACIL'ITI", ('facil-iti.com', 'facil-iti.org')),
)

# texto de un skip link (es/en/pt/fr — el vocabulario del patrón 3e12e1)
_SKIP_TEXT = re.compile(
    r'skip|jump to|saltar|ir al contenido|ir para o conte[uú]do|passer au contenu', re.I)

# encabezados cortos legítimos (acrónimos y términos técnicos): «FAQ», «API»…
_SHORT_HEADINGS = {'FAQ', 'API', 'CSS', 'APP', 'MAP', 'EN', 'DE', 'ES', 'PT', 'FR',
                   'IT', 'UI', 'UX', 'ID', 'TV', 'HR', 'PR', 'AI', 'PC', 'OK', '3D',
                   'IOS', 'OS', 'GB', 'MB', 'KB', 'PDF', 'RSS', 'URL', 'WWW', 'XML',
                   'HTTP', 'FAQS', 'BLOG', 'HOME', 'INICIO', 'NOTAS', 'AGENDA'}


def _t(lang, key, n=None):
    """Message by key; `{"one","other"}` entries resolve via the locale's
    CLDR plural rule when the caller passes the count."""
    value = T.get(lang, T['en']).get(key, key)
    return a11yi18n.plural_entry(value, lang, n) if n is not None else value


def _crit(lang, code):
    return CRIT.get(lang, CRIT['es'])[code]


class _Auditor(HTMLParser):
    # rasgos contados para el scope (evidencia positiva de aplicabilidad)
    FEATURE_TAGS = ('video', 'audio', 'track', 'embed', 'object', 'iframe',
                    'form', 'input', 'select', 'textarea', 'table')

    def __init__(self):
        # ── anotación por elemento (kernel a11yannotate) ──────────────────
        # identidad determinista: cada elemento del parseo recibe su ruta
        # CSS (tag:nth-of-type(n) desde la raíz). id(attrs) es estable dentro
        # del parseo (cada attrs es un dict nuevo) → los recolectores pueden
        # resolver la ruta de LO QUE COGIERON sin cambiar sus tuplas.
        self._path_stack = []      # [(tag, path, {tag: nth})] del elemento abierto
        self._elem_paths = {}      # id(attrs) → ruta del elemento
        super().__init__(convert_charrefs=True)
        self.imgs_no_alt = []
        # elementos (attrs) detrás de cada ejemplo, para el kernel de anotación
        self.imgs_no_alt_elems = []
        self.canvas_no_layer = []        # canvas sin capa accesible (1.1.1)
        self.canvas_no_layer_elems = []
        self.iframes_no_title_elems = []
        self.placeholder_only_elems = []
        self.autocomplete_elems = []
        self.controls_by_kind = {}          # tag → lista de atributos de controles sin nombre
        self.fields_no_label = []
        self.iframes_no_title = []
        self.lang = None
        self.lang_region_invalid = None
        self.title = ''
        self._in_title = False
        self._in_script = False
        self._script_srcs = []   # src de cada <script>: huella de overlays de terceros
        self._in_style = False
        self.headings = []        # (nivel, texto)
        self._heading_level = None
        self._heading_text = []
        self._visible_text = []
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
        self.aria_hidden_focusable_elems = []
        self.stray_clicks = []           # tags no interactivos con onclick
        self.stray_click_elems = []      # attrs de cada uno (paths del kernel)
        self._stray_pend = []            # (tag, attrs, frame) hasta cerrar: se
        # confirma salvo que el subárbol contenga un control nativo (delegación)
        self.role_no_tabindex = []       # [role=button/link] sin tabindex (2.1.1)
        self.role_no_tabindex_elems = []
        self.meta_refresh = None
        self.meta_refreshes = []   # todos los meta refresh: gana el 1º parseable (spec HTML)
        self.saw_html = False
        self.saw_body = False
        self.root_tag = None
        self._in_template = 0
        self._title_buf = []
        self._titles_in_order = []
        # svg: <title> DENTRO de <svg> es el nombre del svg (accname), no el
        # título del documento — se rastrea por profundidad de svg abiertos
        self._svg_depth = 0
        self._in_svg_title = False
        self._svg_title_buf = []
        self._svg_titles = {}          # id(attrs del svg) → texto de su <title>
        # accname (ola de precisión ACT): visibilidad HEREDADA (aria-hidden con
        # re-activación por false, attr hidden, display:none/visibility:hidden)
        # y registro id→texto para resolver aria-labelledby a un salto — los ids
        # referenciados pueden declararse DESPUÉS del elemento, así que la
        # decisión de nombre se toma post-parse, no en streaming
        self._hidden_stack = [(False, False)]   # (hidden_cualquiera, hidden_aria)
        self._css_hidden_stack = [False]        # hidden por hidden/display:none/visibility:hidden
        self._ah_true_stack = []    # un bool por elemento abierto: ¿él mismo aria-hidden=true?
        self._ah_true_depth = 0     # ancestros abiertos con aria-hidden=true (6cfa84)
        self._id_texts = {}
        self._id_text_parts = {}
        self._open_ids = []
        self._depth = 0
        self._scripts_text = ''    # contenido de <script>: ids de centinelos de foco
        self._styles_text = ''     # contenido de <style>: clases ocultas y fuentes-icono
        self._styles_cached_src = None
        self._style_rules = []
        self._icon_links = []
        self._ahf_deferred = []    # (tag, id) off-screen: decidir post-parse con los scripts completos
        self._el_stack = []        # (tag, attrs, [texto directo]) — texto propio del elemento
        self._role_field_ids = set()   # ids de campos por rol: su texto directo es su nombre
        self._field_buffers = {}       # id → texto directo (rescatado al cerrar)
        self._role_field_text = []     # (attrs, texto directo) de campos por rol, con o sin id
        self._nav_ids = set()      # ids de <nav>: bloque repetido abatible por botón (3e12e1)
        self._toggle_onclicks = []
        # candidatos en cruto para las decisiones de nombre post-parse
        self.imgs_all = []       # (attrs, hidden)
        self.inputs_image = []   # (attrs, hidden)
        self.iframes_all = []    # (attrs, hidden)
        self.controls_raw = []   # (kind, attrs, texto, [nombres imgs internas], hidden)
        self.headings_raw = []   # (nivel, attrs, texto, hidden)
        self.fields_raw = []     # (tag, kind, attrs, dentro_de_label, hidden)
        self._heading_attrs = {}
        self.videos = 0
        self.videos_with_captions = 0
        self._in_video = False
        self._video_caps_stack = []     # [attrs, tiene_captions] por <video> abierto
        self.videos_no_caps_elems = []
        self.media_autoplay_elems = []
        self.tables = 0
        self.tables_with_th = 0
        self._in_table = False
        self._th_in_table = False
        self._table_stack = []          # (th_había, attrs) por <table> abierta
        self.tables_no_th_elems = []
        self.blank_no_warning = 0
        self.blank_total = 0
        self.hay_main = False
        self.hay_skip = False
        self.h1s = 0
        self.empty_h = 0
        self.ids = {}
        self.input_img_no_alt = 0
        self.canvases = []        # [(attrs, texto_interno, hidden)] — capa accesible del canvas
        self.canvas_hidden = {}   # id(attrs) → hidden, del starttag al endtag
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
        self._label_for_stack = []   # valor `for` de cada <label> abierto (None = envolvente)
        self._label_text_for = {}    # id del for → texto del label (decisión post-parse)
        self.media_autoplay = 0
        self._list_depth = 0
        self._li_depth = 0
        self._bad_list = 0
        self.label_no_name = []     # (texto visible, aria-label) 2.5.3
        self.lang_parts_invalid = []      # lang inválidos en elementos no-html
        self.down_events = []       # onmousedown/ontouchstart/onpointerdown
        self.captchas = []          # detección 3.3.8 — SOLO en contexto de autenticación
        self._form_captchas = []    # candidatos del <form> abierto (3.3.8 aplica a auth)
        self._form_auth = False     # form actual: acción de login o input password
        self._required_pend = []    # (tag, attrs) required: decide post-parse con el label
        self.mobiles = []           # marquee/blink/inline infinite animation (2.2.2)
        self._landmark_ids = set()  # ids de landmarks: objetivos válidos de skip link
        self.nav_hrefs = set()      # hrefs inside <nav> (site-level 3.2.3 signature)
        self.help_hrefs = set()     # help/contact links (site-level 3.2.6 signature)
        self.images_of_text = []
        self.vague_headings = []
        self.char_shortcuts = []
        self.drag_handlers = []
        self.status_regions = 0
        self.placeholder_only = []     # 3.3.2: placeholder sin label (decisión post-parse)
        self._placeholder_candidates = []
        self.required_no_indication = [] # 3.3.2: required sin * ni "obligatorio"
        self.missing_fieldsets = 0      # 1.3.1: radio/check groups sin fieldset
        self._radio_group = {}
        self._radio_in_fieldset = {}         # name → count (para detectar grupos)
        self._radio_in_group = {}             # name → dentro de role=group con nombre
        self.vague_labels = []         # 2.4.6: label quality
        self.financial_no_confirm = 0  # 3.3.4: financial form no confirm
        self._financial_form = False
        self._confirm_form = False    # 3.3.4: pista de confirmación en form financiero
        self._in_nav = 0
        self._in_fieldset = False
        self._group_role_depth = 0    # <div role=group/radiogroup> abierto (con nombre)
        self.has_search = False
        self.has_sitemap = False
        self.gestures = []            # touchmove/drag handlers (2.5.1)
        self.features = {}            # tag → n (rasgos de aplicabilidad)
        self.motions = []           # deviceorientation/devicemotion (2.5.4)
        self.orientation_locks = [] # screen.orientation.lock / orientation MQ (1.3.4)
        self.videos_descriptions = 0   # videos WITH descriptions track
        self.sensory = []           # sensory-only instruction patterns (1.3.3)

    def _close_control(self, tag):
        if not self._ctrl:
            return
        c = self._ctrl[-1]
        if c['tag'] != tag:
            return
        self._ctrl.pop()
        a = c['attrs']
        text = ' '.join(c['text']).strip()
        # decisión de nombre POST-parse: los ids de un aria-labelledby pueden
        # declararse después del control; se registra todo en crudo
        self.controls_raw.append((c.get('kind') or tag, a, text, c.get('img_attrs', []),
                                  c.get('hidden', False)))
        # 2.5.3 label in name — algoritmo de WCAG Understanding 2.5.3: sin el
        # contenido entre paréntesis, minúsculas, sin puntuación, y la
        # etiqueta visible contenida POR PALABRAS en el nombre («just ice» ≠
        # «justice»; «Discover It» falla contra «Discover Italy»). Una
        # etiqueta visible de un solo carácter/símbolo (X, emoji) es texto no
        # verbal: exenta. La etiqueta es la que se VEE (la oculta por CSS no)
        # concatenación DOM fiel: sin espacios artificiales — los del DOM ya
        # vienen en los propios nodos de texto (2ee8b8: «W C A G» ≠ «ACT»)
        _vis = ''.join(c.get('text_visible', [])).strip()
        _al = (a.get('aria-label') or '').strip()
        # página con fuente-icono declarada (Material Icons, Font Awesome…):
        # el «texto» de un botón puede ser un glifo no verbal — exento
        _icon_font = bool(re.search(
            r"font-family\s*:[^;}]*?(Material[+ ]Icons|Font Awesome|glyphicon|icomoon|feather)"
            r"|@font-face[^}]*?(Material[+ ]Icons|Font Awesome|glyphicon|icomoon|feather)",
            self._styles_text, re.I)) or bool(re.search(
            r'fonts\.googleapis\.com/icon|/material-icons|font-?awesome|/icomoon',
            ' '.join(getattr(self, '_icon_links', [])), re.I))
        # página con fuente-icono: el «texto» del control puede ser un glifo
        # no verbal (ligadura Material «shopping_cart») — exento en CUALQUIER
        # control (enlaces-icono incluidos), no solo <button>
        if not _icon_font and _vis and _al:
            def _lin_words(txt):
                txt = re.sub(r'\([^)]*\)', ' ', txt)
                # la puntuación se ELIMINA sin partir palabras («11×3=33» →
                # «1133»: una sola palabra) — algoritmo 2.5.3
                return [w for w in re.sub(r'[^\w\s]|_', '', txt.lower()).split() if w]
            _vp, _ap2 = _lin_words(_vis), _lin_words(_al)
            _mismatch = False
            if _vp and _ap2:
                if len(_vp) == 1 and len(_vp[0]) <= 2 and _vp[0].isalpha():
                    _mismatch = False   # letra-símbolo única (X): texto no verbal
                else:
                    # RODAJA CONTIGUA EXACTA: «discover it» no cabe en
                    # «discover italy» (it ≠ italy); «download specification»
                    # no cabe en «download the specification»; «you how are»
                    # no en «how are you» aunque estén todas las palabras
                    _mismatch = not any(_ap2[i:i + len(_vp)] == _vp
                                     for i in range(len(_ap2) - len(_vp) + 1))
            if _mismatch:
                self.label_no_name.append((_vis[:40], _al[:60]))
        if tag == 'a' and not c.get('hidden'):
            if (a.get('target') or '').lower() == '_blank':
                self.blank_total += 1
                _img_alts = ' '.join((ia.get('alt') or '')
                                     for ia in c.get('img_attrs', []))
                if not _BLANK_HINT.search(text) and not _BLANK_HINT.search(a.get('aria-label') or '') \
                        and not _BLANK_HINT.search(a.get('title') or '') \
                        and not _BLANK_HINT.search(_img_alts):
                    self.blank_no_warning += 1
            elif (a.get('href') or '').strip().startswith('#') \
                    and len((a.get('href') or '').strip()) > 1 and text:
                # skip link REAL: ancla interna cuyo objetivo es un landmark o
                # cuyo texto lo dice — un TOC/footnote no abate bloques (3e12e1)
                if (a.get('href') or '').strip()[1:] in self._landmark_ids \
                        or _SKIP_TEXT.search(text):
                    self.hay_skip = True
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

    def _wrap_labels(self, a):
        """¿Un <label> ABIERTO etiqueta ESTE campo? El label envolvente solo
        asocia cuando NO tiene `for` (o su `for` apunta al propio campo):
        <label for=email>…<input id=pw>> NO etiqueta a pw (el for manda)."""
        if not self._label_for_stack:
            return False
        _fid = a.get('id')
        return any(_f is None or (_fid and _f == _fid)
                   for _f in self._label_for_stack)

    def handle_starttag(self, tag, attrs):
        # atributos DUPLICADOS: gana el PRIMERO (spec HTML: los repetidos se
        # descartan) — dict(attrs) dejaría ganar al último y <img alt="x" alt="">
        # pasaría por decorativa
        a = {}
        for _k, _v in attrs:
            if _k not in a:
                a[_k] = _v
        self.elements += 1
        # delegación de eventos: un control interactivo DENTRO de un candidato
        # a «click no enfocable» lo exime (wrapper de analytics/React sobre un
        # <button> real — el teclado lo opera desde el descendiente)
        if self._stray_pend:
            _ti_mark = (a.get('tabindex') or '').strip()
            if tag in ('a', 'button', 'input', 'select', 'textarea', 'summary') \
                    or (a.get('role') or '').strip().lower() in ('button', 'link') \
                    or (_ti_mark.isdigit() and int(_ti_mark) >= 0):
                for _sp in self._stray_pend:
                    _sp[3] = True
        # ruta determinista del elemento (kernel de anotación): nth-of-type
        # SIEMPRE (los id duplicados no pueden romper la ruta) y los void no
        # abren pila (no tienen handle_endtag)
        if self._path_stack:
            _parent = self._path_stack[-1]
            _parent[2][tag] = _parent[2].get(tag, 0) + 1
            _seg = path_segment(tag, _parent[2][tag])
            _path = _parent[1] + '>' + _seg
        else:
            _path = path_segment(tag, 1)
        self._elem_paths[id(a)] = _path
        if tag not in VOID_TAGS:
            self._path_stack.append((tag, _path, {}))
        # rasgos estructurales para el scope de aplicabilidad (a11yscope):
        # evidencia POSITIVA — cero <video> habilita proponer 1.2.x como no
        # aplicable; la ausencia de señal jamás cuenta como ausencia de
        # contenido. input type=hidden no es un campo visible.
        if tag in self.FEATURE_TAGS:
            if tag == 'input' and (a.get('type') or '').strip().lower() == 'hidden':
                pass
            else:
                self.features[tag] = self.features.get(tag, 0) + 1
        if a.get('id'):
            self.ids[a['id']] = self.ids.get(a['id'], 0) + 1
        if self.root_tag is None:
            self.root_tag = tag
        # visibilidad heredada para accname y enfocabilidad: aria-hidden se
        # hereda y aria-hidden="false" RE-ACTIVA el subárbol; hidden y
        # display:none/visibility:hidden ocultan sin re-activación
        _style = (a.get('style') or '').replace(' ', '').lower()
        _inh, _inh_aria = self._hidden_stack[-1]
        _ah_val = (a.get('aria-hidden') or '').strip().lower()
        _hidden_aria = _inh_aria
        if _ah_val == 'true':
            _hidden_aria = True
        elif _ah_val == 'false':
            _hidden_aria = False
        _hidden = _inh or 'hidden' in a or 'display:none' in _style \
            or 'visibility:hidden' in _style or _hidden_aria
        # <template> es contenido INERTE (spec HTML): no renderiza, no recibe
        # foco, sus ids no existen — se audita como oculto y los colectores
        # que no consultan _hidden llevan guardia explícita
        if self._in_template:
            _hidden = True
        if tag not in _VOID:
            self._depth += 1
            self._hidden_stack.append((_hidden, _hidden_aria))
            self._css_hidden_stack.append('hidden' in a or 'display:none' in _style
                                          or 'visibility:hidden' in _style
                                          or self._css_hidden_stack[-1])
            self._ah_true_stack.append(_ah_val == 'true')
            if _ah_val == 'true':
                self._ah_true_depth += 1
            if a.get('id'):
                self._open_ids.append((a['id'], self._depth))
            self._el_stack.append((tag, a, []))
            if tag == 'nav' and a.get('id'):
                self._nav_ids.add(a['id'])
            if a.get('onclick'):
                self._toggle_onclicks.append(a['onclick'])
        if tag == 'template':
            self._in_template += 1
        elif tag == 'svg':
            self._svg_depth += 1
        elif tag == 'html':
            self.saw_html = True
            self.lang = (a.get('lang') or '').strip()
            parts = self.lang.split('-')
            if len(parts) == 2 and parts[1] and parts[1].isalpha() \
                    and parts[1].lower() not in _REGIONS:
                self.lang_region_invalid = self.lang
        elif tag == 'body':
            self.saw_body = True
        elif tag == 'title' and not self._in_template and self._svg_depth == 0:
            # TODOS los <title> se acumulan en orden de documento: decide el
            # PRIMERO (modelo de ACT 2779a5: head vacío + body con texto falla;
            # title solo en body pasa; los de <template> son inertes). El
            # <title> de un <svg> es el NOMBRE del svg (accname): otra vía.
            self._in_title = True
        elif tag == 'title' and self._svg_depth > 0 and not self._in_template:
            self._in_svg_title = True
            self._svg_title_buf = []
        elif tag == 'script':
            self._in_script = True
            if a.get('src'):
                self._script_srcs.append(a['src'])
        elif tag == 'style':
            self._in_style = True
        elif tag == 'link':
            if (a.get('rel') or '').lower() == 'stylesheet' and a.get('href'):
                self._icon_links.append(a['href'])
        elif tag == 'canvas':
            # attrs ahora; el texto de reserva se recoge en el endtag (pop)
            self.canvas_hidden[id(a)] = _hidden
        elif tag == 'meta':
            if (a.get('name') or '').lower() == 'viewport':
                self.viewport = (a.get('content') or '')
            elif (a.get('http-equiv') or '').lower() == 'refresh':
                self.meta_refresh = (a.get('content') or '')
                self.meta_refreshes.append((a.get('content') or ''))
        elif tag == 'img':
            # la decisión de nombre es POST-parse (nombre accesible = alt u
            # otras fuentes; presentación/none y hiddens quedan fuera)
            self.imgs_all.append((a, _hidden))
            alt = (a.get('alt') or '').strip()
            if self._ctrl:
                # la imagen interna aporta SU nombre completo al control
                # (alt, aria-label, title, labelledby — resuelto post-parse)
                self._ctrl[-1]['img_attrs'].append(a)
            if a.get('id') and alt and not self._in_template:
                # el alt de una img ES su nombre accesible: un aria-labelledby
                # que apunte a esta img resuelve al alt (accname), no a ''
                self._id_text_parts.setdefault(a['id'], []).append(alt)
            if alt and not _hidden:
                # el alt SE LEE: cuenta como texto bajo el lang de su
                # contexto (de46e4 — una img con alt es contenido textual)
                self._effective_lang_check()
            if self._heading_level is not None and not _hidden \
                    and (a.get('role') or '').strip().lower() not in ('presentation', 'none'):
                # nombre de la imagen (alt u otras fuentes) alimenta al
                # encabezado — salvo presentación/none u oculta (ffd0e9).
                # NOTA: una img DENTRO de un heading no es evidencia de
                # «imagen de texto» (1.4.5 exime logotipos; un gráfico de
                # datos no es texto) — solo el alt kilométrico sigue siendo
                # señal de revisión
                _nom_img = alt or (a.get('aria-label') or '').strip() \
                    or (a.get('title') or '').strip()
                if _nom_img:
                    self._heading_text.append(_nom_img)
            if len(alt) > 120:
                self.images_of_text.append(f'alt de {len(alt)} caracteres')
        elif tag == 'iframe':
            self.iframes_all.append((a, _hidden))
        elif tag == 'nav':
            self._in_nav += 1
        elif tag in _CONTROLS:
            # Enlace no interactivo (ancla pura sin href): no se audita.
            if tag == 'a' and not (a.get('href') or '').strip():
                pass
            else:
                self._ctrl.append({'tag': tag, 'attrs': a, 'text': [], 'text_visible': [],
                                   'inner_img': False,
                                   'img_attrs': [], 'hidden': _hidden})
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
            if kind == 'password':
                self._form_auth = True   # 3.3.8: form con password = autenticación
            if kind == 'image':
                self.inputs_image.append((a, _hidden))
            elif kind in ('submit', 'button', 'reset'):
                # decisión de nombre post-parse: los input botones tienen valor
                # por defecto del navegador ("Submit"/"Reset") — nunca sin nombre
                self.controls_raw.append((f'input:{kind}', a, '', [], _hidden))
            if kind == 'search' or re.search(r'search|busqueda|b[uú]squeda', (a.get('name') or '') + (a.get('id') or ''), re.I):
                self.has_search = True
            if kind in _FIELDS:
                self.fields_raw.append((tag, kind, a, self._wrap_labels(a), _hidden))
                if 'autocomplete' not in a and kind != 'search' and (
                        kind in ('email', 'tel')
                        or _PERSONAL_DATA.search((a.get('name') or '') + ' ' + (a.get('id') or ''))):
                    self.missing_autocomplete.append(f'input type={kind} name={a.get("name") or "?"}'[:44])
                    self.autocomplete_elems.append(a)
        if tag == 'input' and 'autocomplete' in a and 'disabled' not in a \
                and (a.get('aria-disabled') or '').strip().lower() != 'true' and not _hidden:
            # ABNF exacta de la regla ACT 73f2c2 (HTML autofill): [section-*]?
            # [shipping|billing]? [home|work|mobile|fax|pager — solo si el
            # siguiente es email/impp/tel/tel-*]? campo [webauthn]? — los
            # campos disabled u hiddens quedan fuera (aplicabilidad)
            _toks = [t.lower() for t in (a['autocomplete'] or '').split()]
            _mal = None
            if not (_toks == ['on'] or _toks == ['off']):
                _i = 0
                if _toks and _SECTION.match(_toks[0]):
                    _i = 1
                if len(_toks) > _i and _toks[_i] in _MOD_ADDRESS:
                    _i += 1
                if len(_toks) > _i and _toks[_i] in _MOD_CONTACT:
                    if len(_toks) > _i + 1 and _toks[_i + 1].split(':')[-1] in _FIELDS_AFTER_CONTACT:
                        _i += 1
                    else:
                        _mal = _toks[_i]      # «work photo»: contacto exige su campo pegado
                if _mal is None:
                    _remainder = _toks[_i:]
                    if not _remainder or _remainder[0].split(':')[-1] not in _AUTOFILL_FIELDS:
                        _mal = _remainder[0] if _remainder else (_toks or [None])[0]
                    elif len(_remainder) == 2 and _remainder[1] != 'webauthn':
                        _mal = _remainder[1]
                    elif len(_remainder) > 2:
                        _mal = _remainder[1]
            if _mal:
                self.autocomplete_invalid.append(
                    f'{_mal} (input name={a.get("name") or "?"})'[:60])
        elif tag in ('select', 'textarea'):
            self._field_note()
            self.fields_raw.append((tag, tag, a, self._wrap_labels(a), _hidden))
        elif tag == 'label':
            self._label_depth += 1
            self._label_text_current = []
            self._labels_stack.append(False)
            self._label_for_stack.append(a.get('for') or None)
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
            # sin kind (o kind vacío/None), el valor por defecto del spec HTML
            # es «subtitles» — cuenta como captions (no exigir el atributo)
            kind = (a.get('kind') or 'subtitles').lower()
            if kind == 'descriptions':
                self.videos_descriptions += 1
            elif kind in ('captions', 'subtitles'):
                self.videos_with_captions += 1
                if self._video_caps_stack:
                    self._video_caps_stack[-1][1] = True
        elif tag in ('video', 'audio'):
            if tag == 'video' and 'muted' not in a:
                # muted = el hero de fondo sin pista audible: 1.2.2/1.2.3
                # aplican a vídeo CON audio — no se exige track a lo inaudible
                self.videos += 1
                self._in_video = True
                self._video_caps_stack.append([a, False])
            # 1.4.2 aplica a audio QUE SUENA sin control: muted = nada audible;
            # controls = el usuario puede pararlo — ambos pasan (el hero-video
            # muted de toda landing no es un fallo de Audio Control)
            if 'autoplay' in a and 'muted' not in a and 'controls' not in a \
                    and not self._in_template:
                self.media_autoplay += 1
                self.media_autoplay_elems.append(a)
        elif tag in ('ul', 'ol'):
            self._list_depth += 1
        elif tag == 'li':
            self._li_depth += 1
        elif tag == 'table':
            # role=presentation/none la declara de MAQUETACIÓN: no se exige th
            # (el mail HTML y las grids legacy viven aquí) — y el contenido de
            # <template> es inerte
            if (a.get('role') or '').strip().lower() in ('presentation', 'none') \
                    or self._in_template:
                pass
            else:
                self.tables += 1
                self._in_table = True
                # pila por tabla anidada: la interna no borra el th de la externa
                self._table_stack.append((self._th_in_table, a))
                self._th_in_table = False
        elif tag == 'th':
            self._th_in_table = True
        elif tag == 'main' or (a.get('role') or '').lower() == 'main':
            self.hay_main = True
            if a.get('id'):
                self._landmark_ids.add(a['id'])
        elif tag not in _CONTROLS + ('input', 'select', 'textarea', 'label', 'option',
                                      'video', 'audio', 'details', 'summary'):
            _role_v = (a.get('role') or '').strip().lower()
            if _role_v in ('group', 'radiogroup') and not self._in_template:
                # grupo con nombre accesible = alternativa legítima al fieldset
                # (técnica ARIA de H71): se computa al abrir, se cierra en endtag
                if a.get('aria-label') or a.get('aria-labelledby'):
                    self._group_role_depth += 1
            if _role_v in _ROLE_FIELDS and _role_v not in ('none', 'presentation'):
                if a.get('id'):
                    self._role_field_ids.add(a['id'])
                # campos por rol (textbox, searchbox…): mismos requisitos de
                # nombre — pero un <label> envolvente NO los etiqueta: el
                # label solo asocia con elementos LABELABLE (input, select,
                # textarea…), un div con role no lo es (e086e5)
                self._field_note()
                self.fields_raw.append((tag, 'role:' + _role_v, a, False, _hidden))
            elif _role_v in ('button', 'link'):
                # controles por rol: también necesitan nombre (97a4e1) — entran
                # en la pila de controles para recoger su texto interno
                self._ctrl.append({'tag': tag, 'attrs': a, 'text': [], 'text_visible': [],
                                   'inner_img': False,
                                   'img_attrs': [], 'hidden': _hidden, 'depth': self._depth,
                                   'kind': 'role:' + _role_v})
                # 2.1.1: un rol interactivo en tag NO enfocable de nacimiento
                # exige tabindex — sin él el control es inalcanzable por
                # teclado (el JS podría añadirlo en runtime: señal de revisión,
                # el pase rendered confirma). Los <template> son inertes.
                if 'tabindex' not in a and not _hidden:
                    self.role_no_tabindex.append(f'{tag}[role={_role_v}]')
                    self.role_no_tabindex_elems.append(a)
            elif _role_v == 'img' and tag != 'img':
                # div[role=img] con imagen de fondo: también necesita nombre (23a2a8)
                self.imgs_all.append((a, _hidden))
            if a.get('onclick') and not _role_v and 'tabindex' not in a \
                    and not self._in_template:
                # candidato a «click no enfocable»: se CONFIRMA al cerrar salvo
                # que el subárbol contenga un control nativo (delegación de
                # eventos / wrappers de analytics sobre un <button> real)
                if tag in _VOID:
                    self.stray_clicks.append(tag)
                    self.stray_click_elems.append(a)
                else:
                    self._stray_pend.append([tag, a, self._depth, False])
        # v3.9: 2.5.2 sospecha de activación en down-event — PERO solo si el
        # elemento no completa en up (onclick/onpointerup/onmouseup presentes):
        # un mousedown de arrastre/selección con click normal NO es down-event
        if not self._in_template:
            for _de in ('onmousedown', 'ontouchstart', 'onpointerdown'):
                if a.get(_de):
                    if not (a.get('onclick') or a.get('onpointerup') or a.get('onmouseup')):
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
            self._form_captchas = []
            action = (a.get('action') or '').lower() + (a.get('id') or '').lower()
            if re.search(r'pay|purchase|checkout|buy|order|contract|legal|billing',
                         action, re.I):
                self._financial_form = True
            if re.search(r'login|log-in|signin|sign-in|auth|session|sso|register|'
                         r'registro|acces|password', action, re.I):
                self._form_auth = True
        if tag in ('input', 'textarea') and a.get('placeholder') \
                and not (a.get('aria-label') or a.get('aria-labelledby')):
            # candidato a placeholder-only: se confirma POST-parse (un
            # <label for> con su id le da nombre real y lo retira)
            self._placeholder_candidates.append((tag, a, self._wrap_labels(a), _hidden))
            if a.get('required') is not None or 'required' in a or a.get('aria-required') == 'true':
                # required sin indicación: la decisión es POST-parse — el «*»
                # puede vivir en el texto del <label for> (declarado después)
                self._required_pend.append((tag, a))
            if tag == 'input' and a.get('type') == 'radio':
                nm = a.get('name') or '(no name)'
                self._radio_group[nm] = self._radio_group.get(nm, 0) + 1
                self._radio_in_fieldset[nm] = self._in_fieldset
                self._radio_in_group[nm] = self._group_role_depth > 0
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
            if not self._in_template:
                self.status_regions += 1
        # v3.12: 2.5.4 motion actuation handlers
        for _ma in ('ondeviceorientation', 'ondevicemotion'):
            if a.get(_ma):
                self.motions.append(f'{tag}[{_ma}]')
        # v3.12: 1.3.4 orientation lock hints (attribute/inline level)
        if tag == 'meta' and 'orientation' in (a.get('content') or '').lower() \
                and 'lock' in (a.get('content') or '').lower():
            self.orientation_locks.append('meta orientation lock')
        # v3.9: 3.3.8 captcha — SOLO dentro de un form de autenticación (la
        # decisión es del endtag del form: ahí se sabe si hubo password/login)
        if not self._in_template:
            for _v in (a.get('src') or '', a.get('href') or '', a.get('id') or ''):
                if re.search(r'recaptcha|hcaptcha|turnstile|captcha', _v, re.I):
                    self._form_captchas.append(f'{tag} {_v[:50]}')
                    break
            if (a.get('name') or '').lower().find('captcha') >= 0:
                self._form_captchas.append(f'input name={a["name"][:30]}')
        # v3.1/v3.3: validez ARIA (atributos, referencias y VALORES) — el
        # contenido de <template> es inerte: sus aria-* no existen en el DOM
        for _ar in _ARIA_IDREFS if not self._in_template else ():
            if a.get(_ar):
                for _ref in a[_ar].split():
                    self.aria_refs.append((_ar, _ref))
        for _ar, _val in a.items() if not self._in_template else ():
            if not _ar.startswith('aria-'):
                continue
            _val = (_val or '').strip().lower()
            if not _val:
                continue    # atributo sin valor: nada que validar (6a7281)
            if _ar in _ARIA_BOOL and _val not in ('true', 'false') \
                    and not (_val == 'mixed' and _ar in ('aria-pressed', 'aria-checked')) \
                    and not (_val == 'undefined' and _ar in _ARIA_BOOL_UNDEFINED):
                self.aria_values.append({'attr': _ar, 'val': _val, 'type': 'bool'})
            elif _ar in _ARIA_INT and not _val.isdigit() \
                    and not (_val == '-1' and _ar in ('aria-rowcount', 'aria-colcount',
                                                       'aria-setsize')):
                # -1 en rowcount/colcount/setsize es OBLIGATORIO cuando el
                # total es desconocido (ARIA 1.2) — grids virtualizadas
                self.aria_values.append({'attr': _ar, 'val': _val, 'type': 'int'})
            elif _ar in _ARIA_NUM:
                try:
                    float(_val)
                except ValueError:
                    self.aria_values.append({'attr': _ar, 'val': _val, 'type': 'num'})
            elif _ar == 'aria-relevant':
                # es una LISTA: cada token debe ser válido; una lista entera
                # válida nunca llega al caso genérico
                if any(_tk not in _ARIA_TOKENS['aria-relevant'] for _tk in _val.split()):
                    self.aria_values.append({'attr': _ar, 'val': _val, 'type': 'tokens',
                                              'valid_tokens': '/'.join(sorted(_ARIA_TOKENS['aria-relevant']))})
            elif _ar in _ARIA_TOKENS and _val not in _ARIA_TOKENS[_ar]:
                self.aria_values.append({'attr': _ar, 'val': _val,
                                          'type': 'tokens',
                                          'valid_tokens': '/'.join(sorted(v for v in _ARIA_TOKENS[_ar] if v))})
        if a.get('role') and not self._in_template:
            # role admite LISTA de tokens separados por espacios (con
            # fallback): TODOS deben ser roles válidos, no solo el primero
            for role in a['role'].strip().lower().split():
                if role not in _ROLES_ARIA and not role.startswith('doc-'):
                    self.unknown_roles.append(role)
            if any(r in ('slider', 'spinbutton') for r in a['role'].strip().lower().split()) \
                    and 'aria-valuenow' not in a:
                self.roles_without_state.append(f'{tag}[role={a["role"].split()[0]}]')
        landmark_role = a.get('role', '').lower() if a.get('role') in (
            'banner', 'contentinfo', 'navigation', 'complementary', 'main', 'form', 'search', 'region') else None
        lm = tag if tag in ('header', 'footer', 'nav', 'aside', 'main', 'search') else landmark_role
        if lm and not self._in_template:
            if a.get('id'):
                self._landmark_ids.add(a['id'])
            if lm == 'search':
                # un landmark search ES un mecanismo de búsqueda (2.4.5)
                self.has_search = True
            if not (a.get('aria-label') or a.get('aria-labelledby')):
                t = self.landmarks.setdefault(lm, [0, 0])
                t[0] += 1
                t[1] += 1
            else:
                self.landmarks.setdefault(lm, [0, 0])[1] += 1
        if a.get('accesskey') and not self._in_template:
            k = (a.get('accesskey') or '').strip().lower()
            if k:
                self.accesskeys[k] = self.accesskeys.get(k, 0) + 1
        if self._list_depth > 0 and self._li_depth == 0 \
                and tag not in ('li', 'script', 'template', 'ul', 'ol'):
            self._bad_list += 1
        # 4.1.2/2.1.2: enfocable dentro de un subárbol aria-hidden=true — el
        # aria-hidden=false anidado NO exime (ACT 6cfa84). No es enfocable:
        # hidden por CSS/hidden (fuera de la navegación por tab — INCLUIDO el
        # display:none POR CLASE, el patrón hamburguesa .menu{display:none}),
        # tabindex negativo (cualquiera, no solo -1), o disabled.
        _ti_raw = (a.get('tabindex') or '').strip()
        _ti_num = None
        if _ti_raw and (_ti_raw.isdigit() or _ti_raw[1:].isdigit()):
            _ti_num = int(_ti_raw)
        _css_hidden = 'hidden' in a or 'display:none' in _style or 'visibility:hidden' in _style \
            or self._css_hidden_stack[-1] or self._focus_hidden_class()
        _native = (tag in ('button', 'summary', 'select', 'textarea', 'iframe')
                   or (tag in ('a', 'area') and (a.get('href') or '').strip())
                   or (tag == 'input' and (a.get('type') or 'text').lower() != 'hidden')
                   or (tag in ('video', 'audio') and 'controls' in a))
        _enfocable = ((_native and 'disabled' not in a)
                      or (_ti_num is not None and _ti_num >= 0))
        if (_ti_num is not None and _ti_num < 0) or _css_hidden:
            _enfocable = False
        # centinela de foco off-screen (patrón modal): un link fuera de vista
        # cuyo id aparece en los scripts (el wiring de focus) NO cuenta — la
        # regla lo define así (mueve el foco al recibirlo). El <script> suele
        # llegar DESPUÉS del link: la decisión se difiere a post-parse
        if (_hidden_aria or self._ah_true_depth > 0) and _enfocable:
            if re.search(r'(top|left)\s*:\s*-\d{3,}', a.get('style') or '', re.I):
                self._ahf_deferred.append((tag, a, a.get('id')))
            else:
                self.aria_hidden_focusable.append(tag)
                self.aria_hidden_focusable_elems.append(a)
        if tag == 'area' and (a.get('href') or '').strip():
            # <area> es void: sin pila de control — se registra directo (el
            # nombre le llega del alt)
            self.controls_raw.append(('area', a, '', [], _hidden))
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            # role=none/presentation APAGA la semántica del encabezado; un
            # aria-level válido la SOBRESCRIBE (accname: h3[aria-level=4] ES 4)
            if (a.get('role') or '').strip().lower() in ('none', 'presentation') \
                    or self._in_template:
                pass
            else:
                self._heading_level = int(tag[1])
                _alv = re.match(r'\d+', str(a.get('aria-level') or ''))
                if _alv:
                    self._heading_level = int(_alv.group())
                self._heading_text = []
                self._heading_attrs = a
                self._heading_route = self._elem_paths.get(id(a))
                self._heading_hidden = _hidden
                self._heading_tag = tag
        elif (a.get('role') or '').lower() == 'heading' and not self._in_template:
            # role=heading cuenta como encabezado para el nombre (ffd0e9); sin
            # aria-level el nivel por defecto de ARIA es 2 — y un aria-level
            # basura JAMÁS tira el parse (int guardado)
            _alv = re.match(r'\d+', str(a.get('aria-level') or ''))
            self._heading_level = int(_alv.group()) if _alv else 2
            self._heading_text = []
            self._heading_attrs = a
            self._heading_route = self._elem_paths.get(id(a))
            self._heading_hidden = _hidden
            self._heading_tag = tag
        ti = a.get('tabindex')
        if ti and ti.isdigit() and int(ti) > 0 and not self._in_template:
            self.positive_tabindices.append((tag, int(ti)))

    def handle_endtag(self, tag):
        # pila de rutas del kernel: pop normal si casa; si hay anidamiento
        # malformado, se descarta hasta el que casa; suelto, se ignora
        if self._path_stack:
            if self._path_stack[-1][0] == tag:
                self._path_stack.pop()
            else:
                for _i in range(len(self._path_stack) - 1, -1, -1):
                    if self._path_stack[_i][0] == tag:
                        del self._path_stack[_i:]
                        break
        if tag not in _VOID:
            # LAS PILAS SE SINCRONIZAN como _path_stack: buscar el frame que
            # casa y descartar hasta él (un </span> suelto ya no arrastra el
            # elemento abierto de verdad — el texto no se malatribuye)
            _idx = None
            for _i in range(len(self._el_stack) - 1, -1, -1):
                if self._el_stack[_i][0] == tag:
                    _idx = _i
                    break
            if _idx is None:
                return   # endtag suelto: ignorar, nada se desincroniza
            _nframes = len(self._el_stack) - _idx
            for _ in range(_nframes):
                if not self._el_stack:
                    break
                _etag, _eattrs, _ebuf = self._el_stack.pop()
                if _etag == 'canvas':
                    self.canvases.append((_eattrs, ' '.join(_ebuf).strip(),
                                          self.canvas_hidden.pop(id(_eattrs), False)))
                if _eattrs.get('id') and _eattrs['id'] in self._role_field_ids:
                    self._field_buffers[_eattrs['id']] = _ebuf
                elif (_eattrs.get('role') or '').strip().lower() in _ROLE_FIELDS:
                    self._role_field_text.append((_eattrs, ' '.join(_ebuf).strip()))
                if (_eattrs.get('role') or '').strip().lower() in ('group', 'radiogroup') \
                        and self._group_role_depth > 0:
                    self._group_role_depth -= 1
                # candidato stray-click que cierra: confirmar salvo delegación
                for _sp in self._stray_pend[:]:
                    if _sp[1] is _eattrs:
                        self._stray_pend.remove(_sp)
                        if not _sp[3]:
                            self.stray_clicks.append(_sp[0])
                            self.stray_click_elems.append(_sp[1])
                if len(self._hidden_stack) > 1:
                    self._hidden_stack.pop()
                    self._css_hidden_stack.pop()
                if self._ah_true_stack and self._ah_true_stack.pop():
                    self._ah_true_depth = max(0, self._ah_true_depth - 1)
            self._depth = max(0, self._depth - _nframes)
            self._open_ids = [(i, d) for (i, d) in self._open_ids if d <= self._depth]
        # controles cierran con SU etiqueta Y a SU profundidad — un <div>
        # anidado dentro de un div[role=button] no cierra el control (React)
        if self._ctrl and self._ctrl[-1]['tag'] == tag \
                and self._depth == self._ctrl[-1].get('depth', 0) - 1:
            self._close_control(tag)
        if tag == 'template':
            self._in_template = max(0, self._in_template - 1)
        if tag == 'svg':
            self._svg_depth = max(0, self._svg_depth - 1)
        if tag == 'title':
            if self._in_svg_title:
                # <title> de svg: nombre del svg — alimenta al control abierto
                # (name-from-content: el botón-icono del W3C) y al registro
                # id→texto (labelledby al svg resuelve a su título)
                _svgtxt = ' '.join(self._svg_title_buf).strip()
                if _svgtxt:
                    if self._ctrl:
                        self._ctrl[-1]['text'].append(_svgtxt)
                        self._ctrl[-1]['text_visible'].append(_svgtxt)
                    for _fr in reversed(self._el_stack):
                        if _fr[0] == 'svg':
                            self._svg_titles[id(_fr[1])] = _svgtxt
                            if _fr[1].get('id'):
                                self._id_text_parts.setdefault(_fr[1]['id'], []).append(_svgtxt)
                            break
                self._in_svg_title = False
                self._svg_title_buf = []
            else:
                self._in_title = False
                self._titles_in_order.append(' '.join(self._title_buf))
                self._title_buf = []
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
                # texto del label POR SU for: el «*» del required puede vivir aquí
                if self._label_for_stack:
                    _lfor = self._label_for_stack.pop()
                    if _lfor and txt:
                        self._label_text_for[_lfor] = txt
            if self._labels_stack and not self._labels_stack.pop():
                self.orphan_labels += 1
        elif tag == 'fieldset':
            self._in_fieldset = False
        elif tag == 'form':
            if self._financial_form and not self._confirm_form:
                self.financial_no_confirm += 1
            # 3.3.8 Accessible Authentication: SOLO en proceso de autenticación
            # (form con password o acción de login) — un captcha en un form de
            # contacto no es un fallo de 3.3.8
            if self._form_auth:
                self.captchas.extend(self._form_captchas)
            self._form_captchas = []
            self._form_auth = False
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
            if self._video_caps_stack:
                _vattrs, _vcaps = self._video_caps_stack.pop()
                if not _vcaps:
                    self.videos_no_caps_elems.append(_vattrs)
        elif tag == 'table':
            if self._table_stack:
                _th_saved, _tattrs = self._table_stack.pop()
                # el estado th de ESTA tabla decide; el guardado restaura al
                # padre (el <th> de una tabla interna no satisface a la externa)
                if self._th_in_table:
                    self.tables_with_th += 1
                else:
                    self.tables_no_th_elems.append(_tattrs)
                self._th_in_table = _th_saved
            self._in_table = bool(self._table_stack)
        elif tag == 'th':
            pass
        elif self._heading_level and tag == getattr(self, '_heading_tag', None):
            # el veredicto de nombre vacío es POST-parse (labelledby resuelto,
            # aria-label tras strip, nombres de imgs internas)
            self.headings_raw.append((self._heading_level, dict(self._heading_attrs or {}),
                                      ' '.join(self._heading_text).strip(),
                                      getattr(self, '_heading_hidden', False),
                                      getattr(self, '_heading_route', None)))
            self._heading_level = None

    _RE_CHAR_KEY = re.compile(r'key(?:Code)?\s*===?\s*["\']([a-zA-Z0-9])["\']', re.S)

    def handle_script_wait(self, data):
        self._scripts_text += ' ' + data
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

    def handle_style_wait(self, data):
        self._styles_text += ' ' + data

    def _effective_lang_check(self):
        """El texto recién encontrado hereda el lang del ancestro (o propio)
        más cercano CON lang; si ese lang es inválido, el texto se lee mal.
        Un lang VACÍO no declara idioma: no acusa (de46e4)."""
        for _k in range(len(self._el_stack) - 1, -1, -1):
            _lang_v = self._el_stack[_k][1].get('lang')
            if _lang_v is None:
                continue
            _lang_eff = _lang_v.strip()
            _tag_eff = self._el_stack[_k][0]
            if _tag_eff == 'html' or _lang_v == '':
                return   # "" no declara idioma; html es 3.1.1, no 3.1.2
            _prim = _lang_eff.lower().split('-')[0]
            if _prim not in _LANG_CODES:
                _mark = f'{_tag_eff} lang="{_lang_eff}"'
                if _mark not in self.lang_parts_invalid:
                    self.lang_parts_invalid.append(_mark)
            return

    _RE_RULE = re.compile(r'\.([\w-]+)\s*\{([^}]*)\}')
    _RE_HIDDEN_STYLE = re.compile(r'clip-path|display\s*:\s*none|visibility\s*:\s*hidden'
                            r'|height\s*:\s*1px|width\s*:\s*1px|opacity\s*:\s*0')
    # subconjunto ESTRICTO para focuseabilidad: solo lo que saca del tab
    _RE_RULE_DISPLAY = re.compile(r'display\s*:\s*none|visibility\s*:\s*hidden')

    def _hidden_class_style(self):
        """¿Algún ancestro abierto del control tiene una clase que el
        <style> de la página declara como oculta (clip-path, position
        absolute + 1px, display none, visibility hidden)? Las reglas se
        cachean: reparsear TODO el css por nodo de texto era cuadrático."""
        return self._class_hides('hidden')

    def _focus_hidden_class(self):
        """Clase que saca el elemento del TAB (display:none/visibility:hidden
        por <style>) — MÁS ESTRICTA que _hidden_class_style: un
        .visually-hidden (clip/1px) SIGUE enfocable (el skip link vive ahí)."""
        return self._class_hides('focus')

    def _class_hides(self, mode):
        if self._styles_text is not self._styles_cached_src:
            self._styles_cached_src = self._styles_text
            self._style_rules = self._RE_RULE.findall(self._styles_text)
        _rx = self._RE_HIDDEN_STYLE if mode == 'hidden' else self._RE_RULE_DISPLAY
        _open_classes = [c.get('attrs', {}).get('class') for c in self._ctrl]
        _open_classes += (_fr[1].get('class') for _fr in self._el_stack)
        for _cls in filter(None, _open_classes):
            for _nom in _cls.split():
                for _selector, _body in self._style_rules:
                    if _nom == _selector and _rx.search(_body):
                        return True
        return False

    def handle_data(self, data):
        in_code = getattr(self, '_in_script', False) or getattr(self, '_in_style', False)
        if not in_code and not self._in_template:
            # registro para resolver aria-labelledby a un salto: todo texto
            # dentro de un elemento con id alimenta su entrada (los ids dentro
            # de <template> no existen en el DOM)
            for _id, _d in self._open_ids:
                # lista por id + join único post-parse: la concatenación por
                # nodo era cuadrática en páginas con wrappers id grandes
                self._id_text_parts.setdefault(_id, []).append(data)
        if data.strip() and not in_code and not self._in_title:
            self._visible_text.append(data)  # prosa visible: ni JS, ni CSS, ni título
        if self._in_title:
            self._title_buf.append(data)
        elif self._in_svg_title:
            self._svg_title_buf.append(data)
        elif getattr(self, '_in_script', False):
            self.handle_script_wait(data)
        elif getattr(self, '_in_style', False):
            self.handle_style_wait(data)
        else:
            # Un texto puede pertenecer a la vez a un enlace dentro de un
            # encabezado (<h2><a>Guías</a></h2>): alimenta a ambos. El texto
            # dentro de un subárbol aria-hidden NO es nombre de nada (accname).
            _hidden_ah = self._hidden_stack[-1][1]
            if self._el_stack:
                self._el_stack[-1][2].append(data)
                if data.strip() and not self._css_hidden_stack[-1] \
                        and not self._hidden_class_style():
                    self._effective_lang_check()
            if self._label_depth > 0 and hasattr(self, '_label_text_current'):
                self._label_text_current.append(data)
            if self._ctrl and not _hidden_ah:
                self._ctrl[-1]['text'].append(data)
            if self._ctrl and not self._css_hidden_stack[-1] \
                    and not self._hidden_class_style():
                # el texto VISIBLE es el renderizado: aria-hidden se ve,
                # display:none / .visually-hidden (por <style>) no
                self._ctrl[-1]['text_visible'].append(data)
            if self._heading_level is not None and not _hidden_ah:
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
    reason_txt = (T.get(lang, T['es'])).get('rendered_reason') or T['es']['rendered_reason']
    return [{
        'criterion': f"{c} {_C[c][1]['en'][0]}",
        'reason': reason_txt,
    } for c in sorted(RENDERED_ONLY)]


def audit_html(html_text, url='(html)', lang='en', standard=None, target=None):
    """Analiza una cadena HTML y devuelve el informe de hallazgos (es/en)."""
    p = _Auditor()
    try:
        p.feed(html_text[:MAX_HTML])
        p.close()
    except Exception as e:  # noqa: BLE001
        # un atributo hostil NO puede tirar la auditoría de 3 MB de página
        # válida: el mensaje viaja por el catálogo (es/en), como todo lo visible
        return {'error': _t(lang, 'err_unparseable').format(e=str(e)[:120])}

    # 1.3.1: grupos de radio (name compartido, ≥2) sin fieldset NI grupo ARIA
    # con nombre (role=group/radiogroup + aria-label: la otra técnica de H71)
    for nm, count in p._radio_group.items():
        if count >= 2 and not p._radio_in_fieldset.get(nm, False) \
                and not p._radio_in_group.get(nm, False):
            p.missing_fieldsets += 1
    # 3.3.2: required sin indicación — la marca («*», «obligatorio») puede
    # vivir en el TEXTO del <label for> que el parser vio después del campo
    for tag, a in p._required_pend:
        ph = (a.get('placeholder') or '').lower()
        title_ = (a.get('title') or '').lower()
        _lbl = p._label_text_for.get(a.get('id') or '', '').lower()
        if not re.search(r'\*|requerid|obligator|required|necesari|precisa',
                         ph + title_ + _lbl):
            p.required_no_indication.append(f'{tag}[name={a.get("name","?")}]')

    # id→texto resuelto de una vez (partes acumuladas en streaming)
    for _id, _parts in p._id_text_parts.items():
        p._id_texts[_id] = ' '.join(_parts).strip()

    # centinela off-screen: decidir con los scripts YA completos (el <script>
    # llega después del link en el documento) — sin id o sin wiring = fallo
    for _tag, _tattrs, _tid in p._ahf_deferred:
        if not _tid or _tid not in p._scripts_text:
            p.aria_hidden_focusable.append(_tag)
            p.aria_hidden_focusable_elems.append(_tattrs)
    # candidatos stray-click que nunca cerraron (HTML truncado): sin
    # interactivo dentro registrado, cuentan igual — el documento está roto
    for _sp in p._stray_pend:
        if not _sp[3]:
            p.stray_clicks.append(_sp[0])
            p.stray_click_elems.append(_sp[1])

    # ── decisiones de nombre POST-parse ─────────────────────────────────────
    # Los ids de un aria-labelledby pueden declararse DESPUÉS del elemento que
    # lo referencia: la resolución se hace con el registro completo id→texto.
    # Nombre accesible práctico (orden accname): aria-label (no vacío tras
    # strip) → aria-labelledby resuelto → texto/alt → title.
    def _name_sources(a):
        lb = ' '.join((p._id_texts.get(i, '') or '').strip()
                      for i in (a.get('aria-labelledby') or '').split()).strip()
        return lb, (a.get('aria-label') or '').strip(), (a.get('title') or '').strip()

    for a, hidden in p.imgs_all:
        # presentación/none = decorativo declarado; hidden (aria-hidden, hidden,
        # display:none) queda fuera de 23a2a8; alt="" exacto = decorativo.
        # PERO un img presentacional ENFOCABLE (tabindex ≥ 0) sigue necesitando
        # nombre: sigue en la navegación por tab (ACT 23a2a8)
        _ti = (a.get('tabindex') or '').strip()
        _enfocable_img = _ti.isdigit() and int(_ti) >= 0
        if hidden or ((a.get('role') or '').strip().lower() in ('presentation', 'none')
                      and not _enfocable_img):
            continue
        if 'alt' in a and (a['alt'] or '').strip():
            continue
        if 'alt' in a and (a['alt'] or '') == '':
            continue
        lb, al, ti = _name_sources(a)
        # <svg role=img> con <title> hijo: el título ES su nombre (accname)
        # — la vía recomendada por el W3C para gráficos accesibles
        _svgt = p._svg_titles.get(id(a), '')
        if not (al or lb or ti or _svgt):
            p.imgs_no_alt.append((a.get('src') or a.get('aria-label') or '(role=img)')[:100])
            p.imgs_no_alt_elems.append(a)
    for a, hidden in p.inputs_image:
        if hidden:
            continue
        lb, al, ti = _name_sources(a)
        if not ((a.get('alt') or '').strip() or al or lb or ti):
            p.input_img_no_alt += 1
    for a, fallback, hidden in p.canvases:
        # canvas: la capa accesible suele inyectarla JS al renderizar el
        # gráfico — la señal estática es FILTRO (media); el pase rendered
        # juzga el nombre computado. Conservador: oculto/decorativo no acusa;
        # con texto de reserva no acusa (fallback content)
        if hidden or (a.get('role') or '').strip().lower() in ('presentation', 'none'):
            continue
        lb, al, ti = _name_sources(a)
        if al or lb or ti or fallback:
            continue
        p.canvas_no_layer.append(a)
        p.canvas_no_layer_elems.append(a)
    for a, hidden in p.iframes_all:
        # tabindex=-1 saca el iframe del orden de tab: la regla lo excluye;
        # role=none/presentation le quita la semántica de iframe (ACT cae760)
        if hidden or (a.get('tabindex') or '').strip() == '-1' \
                or (a.get('role') or '').strip().lower() in ('none', 'presentation'):
            continue
        lb, al, ti = _name_sources(a)
        if not ((a.get('title') or '').strip() or al or lb):
            p.iframes_no_title.append((a.get('src') or '')[:100])
            p.iframes_no_title_elems.append(a)
    for kind, a, text, img_attrs, hidden in p.controls_raw:
        # input submit/reset/button llevan valor por defecto del navegador;
        # disabled/hidden quedan fuera. El value de un <button> NO es su
        # nombre (solo lo es en inputs) ni role=none exime (ACT 97a4e1)
        if hidden or 'disabled' in a or kind.startswith('input:'):
            continue
        lb, al, ti = _name_sources(a)
        _img_names = []
        for ia in img_attrs:
            ilb, ial, iti = _name_sources(ia)
            _img_names.append((ia.get('alt') or '').strip() or ial or ilb or iti)
        if not (text.strip() or al or lb or ti
                or ' '.join(x for x in _img_names if x).strip()
                or (a.get('alt') or '').strip()):
            p.controls_by_kind.setdefault(kind, []).append(a)
    for level, a, text, hidden, _hroute in p.headings_raw:
        if hidden:
            continue
        lb, al, _ti = _name_sources(a)
        heading_name = text.strip() or al or lb
        if not heading_name:
            p.empty_h += 1
        else:
            p.headings.append((level, heading_name[:80]))
            if level == 1:
                p.h1s += 1
            lowered = heading_name.lower().strip()
            # encabezado corto: solo SOSPECHOSO si no es un acrónimo/término
            # técnico conocido («FAQ», «API», «CSS»…) — len<4 en solitario
            # no prueba vaguedad
            _short_ok = heading_name.upper().replace(' ', '') in _SHORT_HEADINGS
            if (len(heading_name) < 4 and not _short_ok) or len(heading_name) > 120:
                p.vague_headings.append(f'h{level} "{heading_name[:40]}"')
            elif re.fullmatch(r'(secci[oó]n|section|chapter|cap[ií]tulo|m[aá]s|more|info|informaci[oó]n|information|details|detalle|click|ver|see|leer|read|continue|seguir)[\s\d.]*', lowered):
                p.vague_headings.append(f'h{level} "{heading_name[:40]}"')
            elif re.fullmatch(r'[\d.\s]+', lowered):
                p.vague_headings.append(f'h{level} "{heading_name[:40]}"')
    # texto directo de campos por rol (name-from-content): buffer salvado al
    # cerrar el elemento, recuperado por id
    _direct_text = {}
    for _tid, _buf in p._field_buffers.items():
        _direct_text[_tid] = ' '.join(_buf).strip()
    for tag, kind, a, en_label, hidden in p.fields_raw:
        if hidden or (a.get('role') or '').strip().lower() in ('none', 'presentation'):
            continue
        lb, al, ti = _name_sources(a)
        _is_labelable = tag in ('input', 'select', 'textarea', 'meter', 'progress', 'output')
        # name-from-content SOLO aplica a los roles que toman nombre del
        # contenido (checkbox, radio, switch, option…): un textbox NO — su
        # contenido no es su etiqueta (e086e5)
        _NAME_FROM_CONTENT = {'checkbox', 'radio', 'switch', 'option', 'menuitem',
                              'menuitemcheckbox', 'menuitemradio', 'tab', 'treeitem'}
        _content_name = ''
        if kind.startswith('role:') and kind.split(':', 1)[1] in _NAME_FROM_CONTENT:
            _content_name = _direct_text.get(a.get('id'), '') or next(
                (_txt for _fa, _txt in p._role_field_text
                 if _fa.get('role') == a.get('role') and not a.get('id') and not _fa.get('id')),
                '')
        _placeholder = (a.get('placeholder') or '').strip() if tag != 'select' else ''
        _has_real_name = bool(al or lb or ti
                or (en_label and _is_labelable)
                or (_is_labelable and a.get('id') and a['id'] in p._labels_for)
                or _content_name)
        if not (_has_real_name or _placeholder):
            p.fields_no_label.append((kind or tag, (a.get('name') or '')[:60], a.get('id')))
    for tag, a, en_label, hidden in p._placeholder_candidates:
        # placeholder como ÚNICO nombre: revisión 3.3.2 (el accname del
        # navegador lo cuenta, pero como etiqueta es débil — se declara)
        if hidden:
            continue
        lb, al, ti = _name_sources(a)
        if not (lb or al or ti or en_label
                or (a.get('id') and a['id'] in p._labels_for)):
            p.placeholder_only.append(f'{tag}[placeholder="{(a.get("placeholder") or "")[:30]}"]')
            p.placeholder_only_elems.append(a)

    findings = []

    def add(severity, code, key_msg, **fmt):
        h = {'severity': severity, 'criterion': _crit(lang, code), 'signal': key_msg,
             'issue': _t(lang, key_msg, n=fmt.get('n')).format(**fmt)}
        h['remediation'] = _t(lang, key_msg + '_rem').format(**fmt)
        paths = fmt.pop('paths', None)
        if paths:
            h['paths'] = paths[:5]
        findings.append(h)

    def add_ej(severity, code, key_msg, examples, **fmt):
        add(severity, code, key_msg, **fmt)
        findings[-1]['examples'] = examples[:5]

    if p.imgs_no_alt:
        _p_img = [p._elem_paths[id(_a)] for _a in p.imgs_no_alt_elems
                  if id(_a) in p._elem_paths][:5]
        add_ej('high', '1.1.1', 'img_no_alt', p.imgs_no_alt,
               n=len(p.imgs_no_alt), paths=_p_img)
    if p.input_img_no_alt:
        add('high', '1.1.1', 'input_img_alt', n=p.input_img_no_alt)
    if p.canvas_no_layer:
        _p_canvas = [p._elem_paths[id(_a)] for _a in p.canvas_no_layer_elems
                     if id(_a) in p._elem_paths][:5]
        add_ej('medium', '1.1.1', 'canvas_no_accessible_layer', p.canvas_no_layer,
               n=len(p.canvas_no_layer), paths=_p_canvas)
    for tag, controls in p.controls_by_kind.items():
        add('high', '4.1.2', 'ctrl_name', n=len(controls), tag=tag,
            paths=[p._elem_paths[id(_a)] for _a in controls
                   if id(_a) in p._elem_paths][:5])
    if p.aria_hidden_focusable:
        add('high', '4.1.2', 'aria_hidden_focusable',
            n=len(p.aria_hidden_focusable), tag=p.aria_hidden_focusable[0],
            paths=[p._elem_paths[id(_a)] for _a in p.aria_hidden_focusable_elems
                   if id(_a) in p._elem_paths][:5])
    if p.fields_no_label:
        add_ej('high', '3.3.2', 'field_label',
               [f'{t} name={n or "(no name)"}' for t, n, _i in p.fields_no_label],
               n=len(p.fields_no_label))
    if p.stray_clicks:
        add('high', '2.1.1', 'click_nonfocusable',
            n=len(p.stray_clicks), tag=p.stray_clicks[0],
            paths=[p._elem_paths[id(_a)] for _a in p.stray_click_elems
                   if id(_a) in p._elem_paths][:5])
    if p.role_no_tabindex:
        add_ej('low', '2.1.1', 'role_no_tabindex', p.role_no_tabindex,
               n=len(p.role_no_tabindex), example=', '.join(p.role_no_tabindex[:3]),
               paths=[p._elem_paths[id(_a)] for _a in p.role_no_tabindex_elems
                      if id(_a) in p._elem_paths][:5])
    if p.orphan_labels:
        add('low', '3.3.2', 'label_orphan', n=p.orphan_labels)
    if p._bad_list:
        add('medium', '1.3.1', 'list_structure', n=p._bad_list)
    if p.root_tag in ('svg', 'math'):
        # documento no-HTML (svg/math como raíz): las señales de página
        # (idioma, título, bypass, encabezados) no aplican (ACT b5c3f8/3e12e1)
        pass
    elif not p.lang:
        add('medium', '3.1.1', 'lang_missing',
            paths=[path_segment('html', 1)])
    elif p.lang.lower().split('-')[0] not in _LANG_CODES:
        add('medium', '3.1.1', 'lang_invalid', lang=p.lang)
    elif p.lang_region_invalid:
        add('low', '3.1.1', 'lang_region_invalid', l=p.lang_region_invalid)
    # el PRIMER <title> del documento decide (modelo ACT 2779a5)
    p.title = p._titles_in_order[0] if p._titles_in_order else ''
    t_clean = (p.title or '').strip().lower()
    if not t_clean:
        add('medium', '2.4.2', 'title_missing')
    elif t_clean in ('untitled', 'documento', 'documento sin título', 'sin título',
                      'home', 'inicio', 'page 1', 'new page', 'página 1',
                      'untitled document', 'sin nombre', 'document'):
        add('low', '2.4.2', 'title_generic', t=t_clean)
    if p.iframes_no_title:
        add_ej('medium', '4.1.2', 'iframe_title', p.iframes_no_title,
               n=len(p.iframes_no_title),
               paths=[p._elem_paths[id(_a)] for _a in p.iframes_no_title_elems
                      if id(_a) in p._elem_paths][:5])
    if p.videos and p.videos_with_captions < p.videos:
        add('medium', '1.2.2', 'video_captions', n=p.videos - p.videos_with_captions,
            paths=[p._elem_paths[id(_a)] for _a in p.videos_no_caps_elems
                   if id(_a) in p._elem_paths][:5])
    if p.viewport:
        # valores inválidos también blocksn (ACT b4f0c3): user-scalable ha de
        # ser yes/true o numérico ≥ 1; maximum-scale numérico — si no parsea,
        # el zoom queda sin garantía y se acusa
        m_us = re.search(r'user-scalable\s*=\s*([\w.-]+)', p.viewport, re.I)
        if m_us:
            v = m_us.group(1).lower()
            try:
                allows = float(v) >= 1
            except ValueError:
                allows = v in ('yes', 'true')
            if not allows:
                add('high', '1.4.4', 'zoom_no')
        m_ms = re.search(r'maximum-scale\s*=\s*([\w.-]+)', p.viewport, re.I)
        if m_ms:
            _v_ms = m_ms.group(1)
            try:
                blocks = 0 <= float(_v_ms) < 2   # negativo: ignorado por el parser
            except ValueError:
                # basura blocks (ACT), salvo las palabras clave del viewport
                blocks = _v_ms.lower() not in ('device-width', 'device-height',
                                                'initial-scale', 'width', 'height')
            if blocks:
                # mismo daño que user-scalable=no (bloquea el zoom del usuario):
                # misma severidad — ACT b4f0c3 no las distingue
                add('high', '1.4.4', 'zoom_max', v=_v_ms)
    # meta refresh (2.2.1/ACT bc659a): gana el PRIMER meta que parsea según
    # los pasos del HTML (dígitos + ; o , o fin — un «0: url» con dos puntos
    # NO parsea y se salta); 0 segundos = redirección inmediata y > 72000
    # (20 h) quedan EXENTOS
    _mr = None
    for _content in p.meta_refreshes or ([p.meta_refresh] if p.meta_refresh else []):
        _m = re.match(r'\s*(\d+)\s*(?:[;,]|$)', _content or '')
        if _m:
            _mr = int(_m.group(1))
            break
    if _mr is not None and 0 < _mr <= 72000:
        add('medium', '2.2.1', 'meta_refresh', v=_mr)
    if p.positive_tabindices:
        add_ej('medium', '2.4.3', 'tabindex_pos',
               [f'{t}[tabindex={i}]' for t, i in p.positive_tabindices],
               n=len(p.positive_tabindices))
    # un toggle cuenta como mecanismo de abatido SOLO si la función que
    # invoca colapsa de verdad (su cuerpo, en el script de la página, toca
    # `display`): mover off-screen o aria-hidden no colapsa el bloque (3e12e1)
    _nav_collapsible = False
    for _oc in p._toggle_onclicks:
        for _nid in p._nav_ids:
            if _nid not in _oc:
                continue
            _m = re.match(r'\s*(\w+)\s*\(', _oc)
            if not _m:
                continue
            if _nav_collapsible:
                break
            _fn = re.search(r'function\s+' + _m.group(1) + r'\s*\([^)]*\)\s*\{(.{0,180})',
                            p._scripts_text, re.S)
            if _fn:
                _nav_collapsible = 'display' in _fn.group(1)
            else:
                # función en JS externo (no descargable): el NOMBRE decide —
                # hide/collapse/display colapsan; visibility/aria no (3e12e1)
                _nom = _m.group(1).lower()
                _nav_collapsible = not re.search(r'visib|aria', _nom) \
                    and bool(re.search(r'hide|hidden|collapse|display', _nom))
    if p.root_tag not in ('svg', 'math') and not (p.hay_main or p.hay_skip or _nav_collapsible):
        # revisión (best-practice al nivel de axe «bypass»): 2.4.1 aplica a
        # bloques REPETIDOS — en estático no se puede saber si se repiten
        add('low', '2.4.1', 'no_bypass')

    levels = [n for n, _ in p.headings]
    if levels:
        if p.h1s == 0:
            # best-practice (axe page-has-heading-one), no fallo 1.3.1: WCAG
            # no exige h1 — y en SPAs el h1 suele llegar del render del cliente
            add('low', '1.3.1', 'no_h1')
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
    elif p.root_tag not in ('svg', 'math'):
        add('low', '1.3.1', 'no_headings')
    if p.empty_h:
        add('low', '1.3.1', 'empty_heading', n=p.empty_h)
    if p.tables and p.tables_with_th < p.tables:
        add('medium', '1.3.1', 'table_no_th', n=p.tables - p.tables_with_th,
            paths=[p._elem_paths[id(_a)] for _a in p.tables_no_th_elems
                   if id(_a) in p._elem_paths][:5])
    if p.blank_no_warning:
        add('low', '3.2.5', 'blank_no_warning', n=p.blank_no_warning)
    dups = sum(1 for _c, k in p.ids.items() if k > 1)
    if dups:
        add_ej('low', '4.1.2', 'dup_ids',
               [f'"{_c}" ×{_k}' for _c, _k in list(p.ids.items()) if _k > 1],
               n=dups)

    # --- v3.1: validez ARIA, autocomplete, enlaces, landmarks, accesskey ---
    broken_refs = [f'{attr}="#{ref}"' for attr, ref in p.aria_refs if ref not in p.ids]
    if broken_refs:
        add_ej('high', '4.1.2', 'aria_ref_missing', broken_refs, n=len(broken_refs),
               example=broken_refs[0])
    if p.aria_values:
        _labels = {'es': {'bool': 'true/false', 'int': 'entero', 'num': 'número', 'tokens': 'valores'},
                'en': {'bool': 'true/false', 'int': 'integer', 'num': 'number', 'tokens': 'one of'}}
        axes = [f"{v['attr']}=\"{v['val']}\" ({v['valid_tokens'] if v['type'] == 'tokens' else _labels[lang][v['type']]})"
                for v in p.aria_values]
        add_ej('medium', '4.1.2', 'aria_value_invalid', axes,
               n=len(p.aria_values), example=', '.join(axes[:4]))
    if p.unknown_roles:
        add_ej('medium', '4.1.2', 'role_unknown',
               sorted(set(p.unknown_roles)), n=len(p.unknown_roles),
               example=', '.join(f'"{r}"' for r in sorted(set(p.unknown_roles))[:4]))
    if p.roles_without_state:
        add_ej('medium', '4.1.2', 'role_required_attr', p.roles_without_state,
               n=len(p.roles_without_state), example=', '.join(p.roles_without_state[:4]))
    if p.missing_autocomplete:
        add_ej('medium', '1.3.5', 'autocomplete', p.missing_autocomplete,
               n=len(p.missing_autocomplete), example=', '.join(p.missing_autocomplete[:4]),
               paths=[p._elem_paths[id(_a)] for _a in p.autocomplete_elems
                      if id(_a) in p._elem_paths][:5])
    if p.autocomplete_invalid:
        add_ej('medium', '1.3.5', 'autocomplete_invalid', p.autocomplete_invalid,
               n=len(p.autocomplete_invalid), example=', '.join(p.autocomplete_invalid[:4]))
    if p.media_autoplay:
        add('medium', '1.4.2', 'video_autoplay', n=p.media_autoplay,
            paths=[p._elem_paths[id(_a)] for _a in p.media_autoplay_elems
                   if id(_a) in p._elem_paths][:5])
    if p.label_no_name:
        _ln = p.label_no_name[0]
        add_ej('medium', '2.5.3', 'label_in_name',
               [f'«{t}» vs aria-label «{al}»' for t, al in p.label_no_name],
               n=len(p.label_no_name), example=f'{_ln[0]} ≠ {_ln[1]}')
    if p.lang_parts_invalid:
        add_ej('medium', '3.1.2', 'element_lang_invalid', p.lang_parts_invalid,
               n=len(p.lang_parts_invalid), example=', '.join(p.lang_parts_invalid[:4]))
    if p.down_events:
        add_ej('medium', '2.5.2', 'down_event', p.down_events,
               n=len(p.down_events), example=', '.join(p.down_events[:4]))
    # forms deep-dive
    if p.placeholder_only:
        add_ej('high', '3.3.2', 'placeholder_only', p.placeholder_only,
               n=len(p.placeholder_only), example=', '.join(p.placeholder_only[:3]),
               paths=[p._elem_paths[id(_a)] for _a in p.placeholder_only_elems
                      if id(_a) in p._elem_paths][:5])
    if p.required_no_indication:
        add_ej('low', '3.3.2', 'required_no_indication', p.required_no_indication,
               n=len(p.required_no_indication), example=', '.join(p.required_no_indication[:3]))
    if p.missing_fieldsets:
        add('medium', '1.3.1', 'fieldset_missing', n=p.missing_fieldsets)
    if p.vague_labels:
        add_ej('low', '2.4.6', 'label_vague', p.vague_labels,
               n=len(p.vague_labels), example=', '.join(p.vague_labels[:3]))
    if p.financial_no_confirm:
        add('medium', '3.3.4', 'financial_no_confirm', n=p.financial_no_confirm)
    if p.vague_headings:
        add_ej('low', '2.4.6', 'heading_quality', p.vague_headings,
               n=len(p.vague_headings), example=', '.join(p.vague_headings[:3]))
    if p.char_shortcuts:
        add_ej('low', '2.1.4', 'char_shortcut', p.char_shortcuts,
               n=len(p.char_shortcuts), example=', '.join(p.char_shortcuts[:3]))
    if p.drag_handlers:
        add_ej('low', '2.5.7', 'drag_no_alt', p.drag_handlers,
               n=len(p.drag_handlers), example=', '.join(p.drag_handlers[:3]))
    # 4.1.3: señal de REVISIÓN y solo con evidencia fuerte de interactividad
    # propia (handlers de arrastre/clicks huérfanos/atajos) — un <script>
    # cualquiera (analytics, JSON-LD) o un campo sin label NO crean mensajes
    # de estado: 4.1.3 solo aplica cuando EXISTEN mensajes que anunciar
    dynamic = bool(p.stray_clicks or p.char_shortcuts or p.drag_handlers)
    if dynamic and p.status_regions == 0:
        add('low', '4.1.3', 'no_status_regions')
    if p.images_of_text:
        add_ej('low', '1.4.5', 'images_of_text', p.images_of_text,
               n=len(p.images_of_text), ej2='')
    if p.captchas:
        add_ej('medium', '3.3.8', 'captcha', p.captchas,
               n=len(p.captchas), example=', '.join(p.captchas[:2]))
    # v3.12: partial signals on previously manual-only criteria
    if p.mobiles:
        add_ej('low', '2.2.2', 'motion_moving', p.mobiles,
               n=len(p.mobiles), example=', '.join(p.mobiles[:3]))
    if p.gestures:
        add_ej('low', '2.5.1', 'gesture_no_click', p.gestures,
               n=len(p.gestures), example=', '.join(p.gestures[:3]))
    if p.motions:
        add_ej('low', '2.5.4', 'motion_actuation', p.motions,
               n=len(p.motions), example=', '.join(p.motions[:3]))
    if p.orientation_locks:
        add_ej('low', '1.3.4', 'orientation_lock', p.orientation_locks,
               n=len(p.orientation_locks), example=', '.join(p.orientation_locks[:2]))
    if p.videos and p.videos_descriptions < p.videos:
        add('low', '1.2.3', 'audio_desc_missing', n=p.videos - p.videos_descriptions)
    if p.sensory:
        add('low', '1.3.3', 'sensory_text', example='; '.join(p.sensory[:2])[:70])
    lm_dups = [f'{lm} ×{t[1]}' for lm, t in p.landmarks.items()
               if t[1] > 1 and t[0] == t[1]]
    if lm_dups:
        add('low', '1.3.1', 'landmark_dup', n=len(lm_dups), example=', '.join(lm_dups[:4]))
    if p.generics >= 2:   # un enlace genérico único suele desambiguarse por contexto
        gen = [f'«{k}»' for k in p.links if k in _GENERIC_TEXT][:4]
        add('low', '2.4.4', 'generic_link', n=p.generics, example=', '.join(gen))
    same = sum(1 for _k, hrefs in p.links.items() if len(hrefs) > 1)
    if same:
        add('low', '2.4.4', 'same_name_links', n=same)
    ak_dups = [f'"{k}" ×{v}' for k, v in p.accesskeys.items() if v > 1]
    if ak_dups:
        add('low', '2.1.1', 'accesskey_dup', n=len(ak_dups), example=', '.join(ak_dups[:4]))
    if p.labels_for_dups:
        add('low', '3.3.2', 'multi_label', n=len(p.labels_for_dups))

    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda h: severity_order[h['severity']])
    summary = {s: sum(1 for h in findings if h['severity'] == s)
               for s in ('high', 'medium', 'low')}
    page_lang = (p.lang or '').split('-')[0].lower() if getattr(p, 'lang', None) else ''
    reading = _reading_level(' '.join(p._visible_text),
                             page_lang if page_lang in ('es', 'en') else lang)

    import hashlib as _hl
    res = {
        'mode': 'static',
        'url': url,
        'source_sha256': _hl.sha256(html_text.encode('utf-8', 'replace')).hexdigest(),
        'reading_level': reading,
        'score': compute_score(findings),
        'score_note': _t(lang, 'score_note'),
        'not_measured': _not_measured(lang),
        'elements_scanned': p.elements,
        'summary': summary,
        'findings': findings,
        'limits': _t(lang, 'limits'),
    }
    # rasgos de aplicabilidad (evidencia positiva para a11yscope): cuentan
    # lo que el parser VIO, no lo que dejó de señalar. Va SIEMPRE (vacío es
    # evidencia: el parser corrió y no vio ninguno) — un informe sin bloque
    # es un informe viejo y a11yscope no propone nada sobre él.
    res['features'] = dict(sorted(p.features.items()))
    # --standard en301549: cláusula EN por hallazgo + bloque del estándar
    if standard == 'en301549':
        from . import a11yen301549 as _enstd
        _tgt = target or _enstd.target_for_mode('static')
        res['standard'] = _enstd.standard_block(_tgt, lang)
        for h in findings:
            _cl = _enstd.clause_for(h['criterion'].split(' ')[0], _tgt)
            if _cl:
                h['clause'] = _cl
    elif standard == 'rgaa':
        from . import a11yrgaa as _rg
        res['standard'] = _rg.standard_block(lang)
        for h in findings:
            _rgaa = _rg.rgaa_for_sc(h['criterion'].split(' ')[0])
            if _rgaa:
                h['rgaa'] = _rgaa
    # overlays detectados: dato del informe (diligencia de compra), nunca un
    # hallazgo — no hay criterio WCAG que anclar y el score no se toca
    overlays, _seen = [], set()
    for _src in p._script_srcs:
        _low = _src.lower()
        for _vendor, _pats in _OVERLAY_WIDGETS:
            if _vendor not in _seen and any(_p in _low for _p in _pats):
                _seen.add(_vendor)
                overlays.append({'vendor': _vendor, 'evidence': _src[:180]})
    if overlays:
        res['overlay_widgets'] = overlays
        res['overlay_widgets_note'] = _t(lang, 'overlay_widgets_note')
    return res


# ── redirect policy hook ───────────────────────────────────────────────────
# urlopen follows 3xx (up to 10 hops) to ANY host without asking: every hop
# is a NEW destination nobody validated. DEFAULT: every redirect hop is
# resolved and rejected if it lands on a private network (loopback, RFC1918,
# link-local incl. cloud metadata 169.254.169.254…) — the classic SSRF pivot
# (public URL → internal hop). The URL the USER typed is explicit intent and
# is never blocked; only implicit hops are. Callers can inject their own
# validator (callable(url) -> bool) or pass True to allow everything.
validate_redirect = None   # inyectable: callable(url) -> bool


def _redirect_to_private(url):
    """True si la URL resuelve a una IP no pública (fail-closed)."""
    import ipaddress
    import socket
    from urllib.parse import urlsplit
    try:
        host = urlsplit(url).hostname or ''
        infos = socket.getaddrinfo(host, None)
    except (OSError, ValueError):
        return True   # no resuelve: cerrar, no seguir
    for _fam, _ty, _pr, _ad, sa in infos:
        try:
            ip = ipaddress.ip_address(sa[0])
        except ValueError:
            return True
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved \
                or ip.is_multicast or ip.is_unspecified:
            return True
    return False


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _guard = validate_redirect
        if _guard is None:
            _guard = (lambda _u: not _redirect_to_private(_u))
        if _guard is not True and not _guard(newurl):
            raise ValueError(f'redirect to a disallowed destination: {newurl[:96]}')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_CheckedRedirect)


class _FetchError(ValueError):
    """Error de descarga CON CLAVE de catálogo (es/en): el mensaje visible
    viaja por locales, no hardcodeado — invariante bilingüe del repo."""
    def __init__(self, key, **fmt):
        super().__init__(key)
        self.key, self.fmt = key, fmt


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
            raise _FetchError('err_too_big', mb=MAX_HTML // 1000000)
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
            raise _FetchError('err_not_html', ct=base)
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


def audit_url(url, timeout=30, lang='en', standard=None, target=None):
    if url.split(':')[0].lower() not in ('http', 'https'):
        return {'error': _T_SCHEME.get(lang, _T_SCHEME['es'])}
    try:
        html_text = _fetch(url, timeout=timeout)
    except _FetchError as e:
        return {'error': _t(lang, e.key).format(**e.fmt)}
    except ValueError as e:
        return {'error': str(e)}
    except Exception as e:  # noqa: BLE001
        return {'error': _t(lang, 'fetch_error').format(e=e)}
    return audit_html(html_text, url, lang=lang, standard=standard, target=target)


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
                            example=f'{len(set(signatures))} distintas en {len(signatures)} páginas'),
                        'remediation': _t(lang, 'nav_inconsistent_rem')})
    # 3.2.6 Consistent Help (A, new in 2.2): help links stable across pages
    signatures_help = [frozenset(p.help_hrefs) for p in parsers if p.help_hrefs]
    if len(signatures_help) >= 2 and len(parsers) >= 3 and len(set(signatures_help)) > 1:
        out.append({'severity': 'medium', 'criterion': _crit(lang, '3.2.6'),
                    'signal': 'help_inconsistent',
                    'issue': _t(lang, 'help_inconsistent').format(
                        example=f'{len(set(signatures_help))} variantes en {len(signatures_help)} páginas'),
                    'remediation': _t(lang, 'help_inconsistent_rem')})
    # 2.4.5 exige múltiples formas de encontrar PÁGINAS: con una muestra de
    # una sola página no hay proceso multi-página que reclamarlo (FP en
    # sitios de una página — la excepción del propio criterio)
    if len(parsers) >= 2 and not any(p.has_search or p.has_sitemap for p in parsers):
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
    except _FetchError as e:
        return {'error': _t(lang, e.key).format(**e.fmt)}
    except ValueError as e:
        return {'error': str(e)}
    except Exception as e:  # noqa: BLE001
        return {'error': _t(lang, 'fetch_error').format(e=e)}
    # el parser jamás tira el crawl entero: una página hostil → informe de
    # error de ESA página y se sigue con la cola
    def _parse_page(html_txt, page_url):
        pg = _Auditor()
        try:
            pg.feed(html_txt[:MAX_HTML])
            pg.close()
        except Exception as e:  # noqa: BLE001
            return pg, {'url': page_url, 'error': _t(lang, 'err_unparseable').format(e=str(e)[:120])}
        return pg, None
    p0, p0_err = _parse_page(html_text, url)
    if p0_err:
        return p0_err
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
        pg, pg_err = _parse_page(html_pg, next)
        if pg_err is not None:
            continue   # página rota: no cuenta, el crawl sigue
        reports.append(audit_html(html_pg, next, lang=lang))
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
            # el summary también: un score recalculado con summary viejo miente
            inf['summary'] = {s: sum(1 for f2 in inf['findings'] if f2['severity'] == s)
                              for s in ('high', 'medium', 'low')}
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


def _apply_standard(res, standard, target, lang):
    """ Enriquecimiento post-hoc EN 301 549 (site crawl, --changed): añade
    bloque standard y cláusula por hallazgo. standard=None → res intacto."""
    if standard != 'en301549' or not isinstance(res, dict) or 'error' in res:
        return res
    from . import a11yen301549 as _enstd
    _tgt = target or _enstd.target_for_mode(res.get('mode', 'static'))
    res['standard'] = _enstd.standard_block(_tgt, lang)
    for _pg in res.get('reports', [res]):
        for h in _pg.get('findings', []):
            _cl = _enstd.clause_for(h.get('criterion'), _tgt)
            if _cl:
                h['clause'] = _cl
    return res


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
    ap.add_argument('--standard', choices=['en301549', 'rgaa'], default=None,
                    help='añade a cada hallazgo su cláusula EN 301 549 V4.1.1 '
                         '(9.x web por defecto)')
    ap.add_argument('--target', choices=['web', 'documents', 'software'],
                    default=None, help='target EN: web=9.x, documents=10.x, '
                    'software=11.x (default: según el modo)')
    a = ap.parse_args(argv)
    if a.changed:
        res = audit_changed(base=a.base, lang=a.lang)
        if 'error' in res:
            print(json.dumps(res))
            return 1
        res = _apply_standard(res, a.standard, a.target, a.lang)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 2 if res.get('blocking') else 0
    if a.url:
        try:
            res = (audit_site(a.url, max_pages=a.pages, lang=a.lang,
                              from_sitemap=not a.no_sitemap)
                   if a.pages > 1 else audit_url(a.url, lang=a.lang,
                                                 standard=a.standard,
                                                 target=a.target))
        except Exception as e:  # noqa: BLE001
            print(json.dumps({'error': _t(a.lang, 'fetch_error').format(e=e)}))
            return 1
    else:
        with open(a.file, encoding='utf-8', errors='replace') as f:
            res = audit_html(f.read(), a.file, lang=a.lang,
                             standard=a.standard, target=a.target)
    # site/changed no pasan por audit_html: enriquecer post-hoc para que
    # --standard nunca se descarte en silencio en NINGUNA ruta del CLI
    res = _apply_standard(res, a.standard, a.target, a.lang)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
