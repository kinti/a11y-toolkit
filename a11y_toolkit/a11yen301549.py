#!/usr/bin/env python3
"""EN 301 549 V4.1.1 (2026) — the clause map and the standard metadata.

EN 301 549 is the European harmonized ICT accessibility standard (the EAA's
technical backbone, and — since 2026 — the basis of Canada's ICT
accessibility standard). Its clauses 9 (web), 10 (non-web documents) and
11 (non-web software) each carry the WCAG success criteria under the SAME
numbering: SC 1.4.3 is clause 9.1.4.3 for web, 10.1.4.3 for documents and
11.1.4.3 for software.

That numbering identity was not assumed — it was verified against the
Government of Canada CIO applicability wizard built on EN 301 549 V4.1.1
(2026): all 55 WCAG 2.2 A/AA criteria carry their mirrored clause number in
clauses 9, 10 AND 11 (55/55 each). AAA is NOT claimed: clause 9 carries only
the AAA criteria the standard itself modifies, and A/AA is the conformance
level the toolkit evaluates.

The families beyond the WCAG mirror (5, 6, 7, 8, 12, 13) are real
applicability territory — closed functionality, RTT, hardware, relay — that
no HTML audit can answer. They appear here as honest rows for the scope
engine (a11yscope), never as something this toolkit evaluates. For software
targets the same honesty applies to the EN-only sub-clauses of clause 11
itself (11.5 interoperability with AT, 11.6 documented accessibility usage,
11.7 user preferences): surfaced as human-review rows, never evaluated.

No network, no third parties: this module is pure data.
"""

# Clause prefix per ICT target (EN 301 549 V4.1.1 structure).
_CLAUSE_PREFIX = {'web': '9', 'documents': '10', 'software': '11'}

STANDARD_NAME = 'EN 301 549 V4.1.1 (2026)'

# Targets the toolkit can map findings for. 'web' covers the HTML audits
# (static/rendered), 'documents' the PDF/DOCX screening, 'software' non-web
# UIs audited as HTML prototypes.
TARGETS = tuple(sorted(_CLAUSE_PREFIX))

# Families outside the WCAG mirror. status: machine proposal only where the
# product shape itself decides (a web-only product cannot carry RTT/hardware
# clauses); everything else is a human applicability question. Titles are
# the standard's own chapter titles (verified against the V4.1.1 wizard).
FAMILIES = (
    {'family': '5', 'key': 'generic'},
    {'family': '6', 'key': 'rtt'},
    {'family': '7', 'key': 'video_capabilities'},
    {'family': '8', 'key': 'hardware'},
    {'family': '12', 'key': 'products_info'},
    {'family': '13', 'key': 'relay_emergency'},
)

# EN-only sub-clauses of clause 11 (software) beyond the WCAG mirror
# (11.1-11.4 mirror the SC by principle): 11.5-11.7. Titles are the
# standard's own clause titles (verified against the V4.1.1 table of
# contents). These are applicability rows only — the toolkit does NOT
# evaluate them and never proposes on them (unlike families 6/7/8 for web,
# the product's shape does not decide: a human answers).
SOFTWARE_CLAUSES = ('11.5', '11.6', '11.7')

# Module-level bilingual texts (the families live in locales; these clauses
# postdate them — same pattern as a11yaudit's _labels dicts)
_SOFTWARE_CLAUSE_TEXTS = {
    'en': {
        '11.5': ('Interoperability with assistive technology',
                 'Name, role, value and states exposed through the platform '
                 'accessibility services can only be verified with the software '
                 'running alongside a real assistive technology — human review.'),
        '11.6': ('Documented accessibility usage',
                 'The software must document its accessibility features; a '
                 'documentation question no markup audit answers — human review.'),
        '11.7': ('User preferences',
                 'Respecting the platform user-preference settings requires the '
                 'software running on each platform — human review.'),
    },
    'es': {
        '11.5': ('Interoperabilidad con productos de apoyo',
                 'Exponer nombre, rol, valor y estados vía los servicios de '
                 'accesibilidad de la plataforma solo puede verificarse con el '
                 'software corriendo junto a un producto de apoyo real — '
                 'revisión humana.'),
        '11.6': ('Uso documentado de la accesibilidad',
                 'El software debe documentar sus funciones de accesibilidad; '
                 'una pregunta de documentación que ninguna auditoría de '
                 'marcado responde — revisión humana.'),
        '11.7': ('Preferencias del usuario',
                 'Respetar las preferencias del usuario de la plataforma exige '
                 'el software corriendo en cada plataforma — revisión humana.'),
    },
}


def clause_for(code, target='web'):
    """'1.4.3' + target → '9.1.4.3'. None si el código no es un SC válido.

    Acepta la forma con nombre ('1.4.3 Contrast (Minimum)') que viaja en los
    hallazgos y en la matriz del pack: solo el primer token es el código.
    """
    token = str(code).split(' ')[0] if code is not None else ''
    parts = token.split('.')
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    prefix = _CLAUSE_PREFIX.get(target)
    return f'{prefix}.{token}' if prefix else None


def target_for_mode(mode):
    """Modo del informe → target EN: la web es 9.x, los documentos 10.x."""
    return 'documents' if mode in ('pdf', 'docx') else 'web'


def family_rows(lang='en'):
    """Filas de familias EN para el scope: número, título y nota del estándar
    en el idioma pedido. El ESTADO lo decide el llamador (a11yscope): aquí
    solo vive el texto, no la aplicabilidad."""
    from .a11yi18n import pack
    tx = pack(lang).get('scope', {}).get('families', {}) or {}
    rows = []
    for fam in FAMILIES:
        entry = tx.get(fam['key'], {}) or {}
        row = {'family': fam['family'],
               'title': entry.get('title') or fam['key']}
        if entry.get('note'):
            row['note'] = entry['note']
        rows.append(row)
    return rows


def software_clause_rows(lang='en'):
    """Filas de las cláusulas EN-only de software (11.5-11.7): número, título
    bilingüe y nota honesta. Igual que family_rows: aquí solo vive el texto
    — el estado (revisión humana, no evaluado por este motor) lo pone el
    llamador (a11yscope, target software)."""
    texts = _SOFTWARE_CLAUSE_TEXTS.get(lang) or _SOFTWARE_CLAUSE_TEXTS['en']
    return [{'clause': cl, 'title': texts[cl][0], 'note': texts[cl][1]}
            for cl in SOFTWARE_CLAUSES]


def standard_block(target='web', lang='en'):
    """Bloque 'standard' para informes audit --standard en301549."""
    from .a11yi18n import pack
    tx = pack(lang).get('scope', {}) or {}
    return {
        'name': STANDARD_NAME,
        'target': target,
        'clause_prefix': _CLAUSE_PREFIX[target],
        'mapping_note': tx.get('mapping_note'),
    }
