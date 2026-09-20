#!/usr/bin/env python3
"""a11y-toolkit MCP v3 · stdio MCP server (JSON-RPC, zero dependencies).

The accessibility layer for AI coding agents: audit → fix → document → watch.

Tools:
  - a11y_audit_url(url | html, lang?, timeout?)   express static WCAG audit
  - a11y_audit_dom(url, lang?, timeout?)          rendered audit (Playwright):
                                                  real contrast, target size 2.5.8,
                                                  focus indicator
  - a11y_contrast_pair(fg, bg, lang?)             ratio + AA/AAA verdicts + fix
  - a11y_contrast_image(path, text_color, ...)    text over image, pixel sampling
  - a11y_suggest_color(fg, bg, target?)           nearest passing color
  - a11y_generate_declaration(...)                legal statement RD 1112/2018 / EAA
  - a11y_snapshot(url)                            interactive elements + tab order
  - a11y_diff(a, b)                               regression diff between snapshots
  - a11y_diff_urls(url_a, url_b)                  staging vs production in one call
  - a11y_aria_live_snippet(lang?)                 injectable live-region monitor
  - a11y_criterion(code, lang?)                   WCAG 2.2 criterion explained
  - a11y_badge(score, lang?, fecha?)              honest SVG badge (score+date+scope)
  - a11y_autofix(html, lang?, title?)             deterministic safe fixes
  - a11y_reflow(url, …)                           320px reflow check (1.4.10)
  - a11y_keyboard(url, …)                         keyboard-trap detection (2.1.2)
  - a11y_scroll(url, …)                           infinite-scroll audit
  - a11y_forms(url, …)                            form errors 3.3.1/3.3.3 (fill+submit)
  - a11y_hover(url, …)                             tooltip Escape dismissibility (1.4.13)
  - a11y_sr_transcript(url, …)                     what a blind user hears, linearized
  - a11y_disprove(url, informe?, …)                re-verify findings → confirmed/rejected
  - a11y_ledger(action, url?, informe?, …)          persistent coverage ledger
  - a11y_html_validate(url|html, …)                W3C Nu parser view
  - a11y_evidence(informes, …)                   countersignature-ready evidence pack

Prompts: audit-page, fix-contrast, pre-deploy-check, declaration-eaa.

Register in an MCP client (no clone needed):

  { "mcpServers": { "a11y-toolkit": {
      "command": "uvx", "args": ["--from", "a11y-toolkit", "a11y-toolkit-mcp"] } } }
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

from contrast import pair as pair_fn, image_contrast, sugerir, parse_color  # noqa: E402
from declaracion import generar as declaracion_fn  # noqa: E402
from a11yaudit import audit_url as audit_url_fn, audit_html as audit_html_fn  # noqa: E402
from a11ydom import audit_dom_url, audit_reflow, audit_keyboard, audit_forms, audit_hover, sr_transcript  # noqa: E402
from a11yfix import autofix as autofix_fn  # noqa: E402
from a11yscroll import audit_scroll  # noqa: E402
from a11yvalidate import validar_url, validar_html  # noqa: E402
from a11yevidence import empaquetar as empaquetar_fn  # noqa: E402
from a11ydiff import snapshot as snapshot_fn, diff as diff_fn  # noqa: E402
from a11ycrit import criterio as criterio_fn  # noqa: E402
from a11ydisprove import disprove as disprove_fn  # noqa: E402
from a11yledger import record as ledger_record, gaps as ledger_gaps, summary as ledger_summary  # noqa: E402
from a11ybadge import badge as badge_fn  # noqa: E402
from a11yaudit import audit_site as audit_site_fn  # noqa: E402

try:
    from arialive_js import ARIALIVE_JS  # installed as a module (pip)
except ImportError:
    ARIALIVE_JS = None  # repo checkout: read the file

VERSION = '3.20.0'

INSTRUCTIONS = (
    'Accessibility toolkit (WCAG 2.2), multilanguage es/en. '
    'Loop: AUDIT (a11y_audit_url for a fast static pass with a 0-100 score; '
    'a11y_audit_dom for a rendered audit with real computed contrast, 2.5.8 target '
    'size and focus indicator — needs local Playwright) → FIX (a11y_contrast_pair, '
    'a11y_contrast_image, a11y_suggest_color) → DOCUMENT (a11y_generate_declaration: '
    'RD 1112/2018 or European Accessibility Act wording) → WATCH (a11y_snapshot — '
    'includes the computed accessibility tree — + a11y_diff across deploys). '
    'Site sampling reads /sitemap.xml first (WCAG-EM enumeration, links as fallback); '
    'rendered tools accept auth_state (Playwright storage_state) to audit behind login; '
    'a11y_forms submits invalid data and judges error announcement (3.3.1/3.3.3). '
         'a11y_evidence records verificados codes as agent-verified (automated-fail stays fail). '
    'a11y_criterion explains what any criterion means. Every tool returns es/en '
    'findings with concrete remediation. '
    'Automation covers about one third of WCAG: pair audits with the manual checklist '
    'in the audit-page prompt (keyboard, screen reader, zoom).'
)

TOOLS = [
    {
        'name': 'a11y_audit_url',
        'description': ('Express WCAG 2.2 audit of a URL or an HTML string: 20+ automated '
                        'signals with a weighted 0-100 score — images without alt (1.1.1), '
                        'controls without accessible names (4.1.2), form fields without labels '
                        '(3.3.2), missing autocomplete on user-data fields (1.3.5), click '
                        'handlers on non-interactive elements (2.1.1), unknown ARIA roles and '
                        'broken aria-labelledby (4.1.2), duplicated unnamed landmarks, timed '
                        'meta refresh (2.2.1), missing skip mechanism (2.4.1), lang/title '
                        '(3.1.1, 2.4.2), heading structure (1.3.1), blocked zoom (1.4.4), '
                        'captions (1.2.2), autoplay audio (1.4.2), generic/duplicated link text '
                        '(2.4.4), target=_blank without warning (3.2.5), positive tabindex '
                        '(2.4.3), aria-hidden on focusable elements, tables without th, '
                        'duplicate ids, duplicate accesskeys. Each finding includes concrete '
                        'remediation. Filter, not verdict: automation covers ~1/3 of WCAG; '
                        'query a11y_criterion for what a criterion means.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string', 'description': 'URL to fetch and audit'},
            'html': {'type': 'string', 'description': 'raw HTML to audit directly (overrides url)'},
            'pages': {'type': 'integer', 'description': 'light same-domain crawl: audit up to N pages, aggregated by score and recurring signals (default 1, max 20)'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'output language (en default)'},
            'timeout': {'type': 'number', 'description': 'fetch timeout seconds (30 default)'},
        }},
    },
    {
        'name': 'a11y_audit_dom',
        'description': ('Deep RENDERED WCAG audit via local Playwright/Chromium: real computed '
                        'text contrast against effective backgrounds with alpha compositing '
                        '(1.4.3), minimum target size 24×24 (2.5.8, new in WCAG 2.2), visible '
                        'focus indicator heuristic (2.4.7), plus rendered versions of the '
                        'static checks (alt, accessible names, labels, headings, lang/title, '
                        'tabindex, aria-hidden, captions, tables). Findings include remediation. '
                        'Requires playwright: pip install playwright && playwright install '
                        'chromium.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
            'timeout': {'type': 'number', 'description': 'page load timeout seconds (45 default)'},
            'auth_state': {'type': 'string', 'description': 'Path to a Playwright storage_state JSON (exported session) to audit behind login — local file, never uploaded'},
        },             'browser': {'type': 'string', 'enum': ['auto', 'chromium', 'firefox', 'webkit', 'chrome', 'msedge'], 'description': 'Browser engine (auto = detect the first available)'},
'required': ['url']},
    },
    {
        'name': 'a11y_contrast_pair',
        'description': ('Exact WCAG contrast ratio for a color pair: per-criterion verdicts '
                        '1.4.3 (AA), 1.4.6 (AAA), 1.4.11 (non-text). Accepts #hex, rgb(), '
                        'hsl(), CSS color names; rgba/hsl with alpha is composited over the '
                        'background. If AA fails, suggests the nearest passing color.'),
        'inputSchema': {'type': 'object', 'properties': {
            'fg': {'type': 'string'}, 'bg': {'type': 'string'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'output language (en default)'},
        }, 'required': ['fg', 'bg']},
    },
    {
        'name': 'a11y_contrast_image',
        'description': ('TEXT OVER IMAGE contrast: pixel-level sampling of the real background '
                        'behind the text box → worst/median/p95 ratio, % of area passing AA, '
                        'and automatic hostile-zone detection on a 3×3 grid (zona_peor). What '
                        'pair-only checkers cannot do. region="x,y,w,h" recommended.'),
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string'}, 'text_color': {'type': 'string'},
            'region': {'type': 'string'},
            'sample': {'type': 'integer'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['path', 'text_color']},
    },
    {
        'name': 'a11y_suggest_color',
        'description': ('Nearest opaque color (RGB distance) to fg that reaches the target '
                        'ratio against bg (4.5 default). Returns the color, its ratio and '
                        'whether it lightens or darkens.'),
        'inputSchema': {'type': 'object', 'properties': {
            'fg': {'type': 'string'}, 'bg': {'type': 'string'},
            'target': {'type': 'number'},
        }, 'required': ['fg', 'bg']},
    },
    {
        'name': 'a11y_generate_declaration',
        'description': ('Generates an Accessibility Statement in HTML: art. 10 RD 1112/2018 '
                        '(Spanish public sector, marco="rd1112") or European Accessibility Act '
                        'wording (Directive (EU) 2019/882 / Ley 11/2023, marco="eaa"; EN output '
                        'uses Directive (EU) 2016/2102 / EAA wording). The generated document '
                        'is itself accessible. Saves to output_path when given.'),
        'inputSchema': {'type': 'object', 'properties': {
            'entidad': {'type': 'string'}, 'url': {'type': 'string'},
            'estado': {'type': 'string', 'enum': ['plena', 'parcial', 'no_conforme']},
            'contenido_no_accesible': {'type': 'array', 'items': {'type': 'string'}},
            'metodo': {'type': 'string'},
            'fecha_evaluacion': {'type': 'string'},
            'fecha_revision': {'type': 'string'},
            'feedback': {'type': 'string'},
            'reclamacion': {'type': 'string'},
            'marco': {'type': 'string', 'enum': ['rd1112', 'eaa']},
            'disponibilidad_alternativa': {'type': 'string'},
            'output_path': {'type': 'string', 'description': 'save the HTML here (optional)'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['entidad', 'url', 'estado']},
    },
    {
        'name': 'a11y_snapshot',
        'description': ('Accessibility snapshot of a URL: interactive elements (tag, role, '
                        'accessible name, href) in DOM order, the REAL tab focus order, and '
                        'when Playwright ≥1.49 is available the computed ACCESSIBILITY TREE '
                        '(aria snapshot — what a screen reader announces). Save it before a '
                        'deploy and compare after with a11y_diff. Requires local Playwright.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string', 'description': 'Page URL to snapshot (http/https or file://)'},
            'auth_state': {'type': 'string', 'description': 'Path to a Playwright storage_state JSON (exported session) to snapshot behind login'},
        }, 'required': ['url']},
    },
    {
        'name': 'a11y_diff',
        'description': ('Regression diff between two accessibility snapshots (before/after a '
                        'deploy): added/removed/renamed interactives and focus-order changes. '
                        'ok=false means a regression to review. Accepts inline JSON (starting '
                        'with "{") or file paths.'),
        'inputSchema': {'type': 'object', 'properties': {
            'a': {'type': 'string', 'description': 'BEFORE snapshot (inline JSON or path)'},
            'b': {'type': 'string', 'description': 'AFTER snapshot (inline JSON or path)'},
        }, 'required': ['a', 'b']},
    },
    {
        'name': 'a11y_diff_urls',
        'description': ('Snapshot two URLs and diff them in a single call (e.g. staging vs '
                        'production). Requires local Playwright.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url_a': {'type': 'string'}, 'url_b': {'type': 'string'},
        }, 'required': ['url_a', 'url_b']},
    },
    {
        'name': 'a11y_aria_live_snippet',
        'description': ('Returns injectable JavaScript for an aria-live announcement monitor '
                        '(bookmarklet or page.evaluate): logs every dynamic-region '
                        'announcement with time, politeness, role and text — what a screen '
                        'reader would say, visible on screen.'),
        'inputSchema': {'type': 'object', 'properties': {
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'monitor panel language (en default)'},
        }},
    },
    {
        'name': 'a11y_badge',
        'description': ('Returns an HONEST accessibility badge as accessible SVG: score, '
                        'date and scope (automated screening ≈ 1/3 of WCAG), color-coded '
                        'by score. Deliberately does NOT say "conformant" — the honest '
                        'seal. Embed it in audited sites or statements.'),
        'inputSchema': {'type': 'object', 'properties': {
            'score': {'type': 'number', 'description': '0-100 (from an audit result)'},
            'fecha': {'type': 'string', 'description': 'ISO date (today by default)'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['score']},
    },
    {
        'name': 'a11y_autofix',
        'description': ('DETERMINISTIC safe auto-fixes applied to HTML — the honest '
                        'anti-overlay: a short closed list of fixes where the correct '
                        'answer is unique (unblock viewport zoom 1.4.4, add the exact '
                        'autocomplete token 1.3.5, fill missing html lang and empty title '
                        'when provided). Everything requiring judgment (alt text, '
                        'contrast, accessible names) is NOT touched — it returns '
                        'no_aplicados with the reason and remediation instead. Returns '
                        'fixed_html + aplicados + no_aplicados.'),
        'inputSchema': {'type': 'object', 'properties': {
            'html': {'type': 'string', 'description': 'raw HTML to fix'},
            'lang': {'type': 'string', 'description': 'only if provided and <html> lacks lang'},
            'title': {'type': 'string', 'description': 'only if provided and <title> is empty'},
        }, 'required': ['html']},
    },
    {
        'name': 'a11y_reflow',
        'description': ('Reflow check at 320px — criterion 1.4.10 (AA), the check axe and '
                        'Lighthouse do not automate. Loads the URL at 1280px, then at '
                        '320px, and reports real horizontal scroll + the overflowing '
                        'elements. Method note: browser zoom RE-LAYS OUT at 320 CSS px '
                        '(that is the standard\'s own equivalence: 1280 @ 400% zoom = 320px), '
                        'so the correct measurement is a 320px viewport. Requires local '
                        'Playwright.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
            'timeout': {'type': 'number'},
            'auth_state': {'type': 'string', 'description': 'Path to a Playwright storage_state JSON (exported session) to test behind login'},
        },             'browser': {'type': 'string', 'enum': ['auto', 'chromium', 'firefox', 'webkit', 'chrome', 'msedge'], 'description': 'Browser engine (auto = detect the first available)'},
'required': ['url']},
    },
    {
        'name': 'a11y_keyboard',
        'description': ('Keyboard-trap detection (2.1.2) with REAL Tab walking in Chromium: '
                        'up to 60 real tab stops, cycle detection (the modal pattern), then '
                        'the decisive test — does ESCAPE release the cycle? A modal that '
                        'cycles and releases on Escape is correct and NOT reported; a cycle '
                        'Escape cannot leave is a trap (high severity). Returns the full tab '
                        'stop list too. Requires local Playwright.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
            'max_pasos': {'type': 'integer', 'description': 'max real Tab presses (60 default)'},
            'auth_state': {'type': 'string', 'description': 'Path to a Playwright storage_state JSON (exported session) to Tab-walk behind login'},
        },             'browser': {'type': 'string', 'enum': ['auto', 'chromium', 'firefox', 'webkit', 'chrome', 'msedge'], 'description': 'Browser engine (auto = detect the first available)'},
'required': ['url']},
    },
    {
        'name': 'a11y_scroll',
        'description': ('Infinite-scroll accessibility audit — the documented disaster nobody '
                        'automates (Deque guidance + ARIA APG Feed pattern; criteria 2.4.3, '
                        '4.1.3, 2.2.2). Real scrolling batches in Chromium with a live-region '
                        'observer: does the focused element SURVIVE each batch (re-render '
                        'destroys it — the documented failure)? Is new content ANNOUNCED '
                        '(aria-live/status receives text, role=feed)? Does the feed END or '
                        'offer a load-more alternative (footer reachability)? APG feed pattern '
                        'as positive signal. Honest guard: if no standard items are detected '
                        '(login walls, non-standard markup) the unfounded signals are skipped '
                        'with a note. Requires local Playwright.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
            'max_tandas': {'type': 'integer', 'description': 'scroll batches (5 default)'},
            'auth_state': {'type': 'string', 'description': 'Path to a Playwright storage_state JSON (exported session) to audit an authenticated feed'},
        },             'browser': {'type': 'string', 'enum': ['auto', 'chromium', 'firefox', 'webkit', 'chrome', 'msedge'], 'description': 'Browser engine (auto = detect the first available)'},
'required': ['url']},
    },
    {
        'name': 'a11y_evidence',
        'description': ('Builds the COUNTERSIGNATURE-READY evidence pack: the machine→human '
                        'handoff object for WCAG conformance work. Takes one or more audit '
                        'reports (any mode — static, rendered, reflow, keyboard, scroll) and '
                        'returns: a full criteria matrix (automated-fail / automated-review / '
                        'not-flagged — NOT pass / manual-only), the list of A/AA criteria with '
                        'no automated signal anywhere (the human reviewer homework list), every '
                        'artifact SHA-256-hashed with timestamps, an empty signature block '
                        '(name, credential, date) whose statement must reference the pack\'s '
                        'own sha256, and the tamper-evidence rule stated. Vendor-neutral: any '
                        'qualified human can countersign it. Evidence, never conformance.'),
        'inputSchema': {'type': 'object', 'properties': {
            'informes': {'type': 'array', 'items': {'type': 'object'},
                         'description': 'audit report objects (any mode)'},
            'snapshot': {'type': 'object', 'description': 'a11y_snapshot output (optional)'},
            'evaluador': {'type': 'object', 'description': '{"nombre":…, "credencial":…, "fecha_revision":…} to prefill the signature block'},
            'verificados': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Criterion codes an agent/human verified against this sample (manual checklist protocol) — they become agent-verified in the matrix; automated-fail stays fail'},
        }, 'required': ['informes']},
    },
    {
        'name': 'a11y_forms',
        'description': ('Form error testing (3.3.1 Error Identification, 3.3.3 Error Suggestion) — '
                        'the guided flow no competitor automates: fills every validatable field '
                        'with INVALID data, really submits, and judges the post-submit DOM — are '
                        'errors identified in text and associated with the field (aria-invalid + '
                        'aria-describedby, error summary, role=alert), or does the form swallow '
                        'them? Native browser validation counts as identification (unless the '
                        'form has novalidate); forms that navigate on submit are honestly noted '
                        'as not measurable in-page. Requires local Playwright.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string', 'description': 'Page URL with the form(s) to test'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'Output language (en default)'},
            'timeout': {'type': 'number', 'description': 'Page load timeout seconds (45 default)'},
            'auth_state': {'type': 'string', 'description': 'Path to a Playwright storage_state JSON to test forms behind login'},
        },             'browser': {'type': 'string', 'enum': ['auto', 'chromium', 'firefox', 'webkit', 'chrome', 'msedge'], 'description': 'Browser engine (auto = detect the first available)'},
'required': ['url']},
    },
    {
        'name': 'a11y_html_validate',
        'description': ('The W3C\'s own parser as a toolkit mode: checks a URL or raw HTML '
                        'against the Nu Html Checker (validator.w3.org/nu) — doctype, encoding, '
                        'structural validity, plus alt/lang/role issues from the authoritative '
                        'source, mapped to WCAG criteria where they overlap. PRIVACY: html mode '
                        'POSTs the document to the W3C service (url mode shares only the URL, '
                        'like a11y_audit_url); self-hosted vnu instances supported via base_url '
                        'for sensitive content.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string', 'description': 'Page URL to validate (shares the URL with the W3C service)'},
            'html': {'type': 'string', 'description': 'Raw HTML to validate — POSTs the content to validator.w3.org/nu; use url or a self-hosted instance for sensitive pages'},
            'base_url': {'type': 'string', 'description': 'Base URL of a self-hosted vnu instance (docker ghcr.io/validator/validator) instead of the public W3C service'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'Output language (en default)'},
        }},
    },
    {
        'name': 'a11y_hover',
        'description': ('Content on Hover or Focus (1.4.13): finds tooltip/overlay '
                        'candidates, hovers each, and tests whether Escape dismisses '
                        'the result — tooltips that do not dismiss are flagged. '
                        'Requires local Playwright. — Scope: tooltips only; full audit '
                        'is a11y_audit_dom, keyboard traps are a11y_keyboard.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string', 'description': 'Page URL to test'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'Output language (en default)'},
            'timeout': {'type': 'number', 'description': 'Page load timeout (45 default)'},
        }, 'required': ['url']},
    },
    {
        'name': 'a11y_sr_transcript',
        'description': ('Screen reader TRANSCRIPT: what a blind user HEARS on this page. '
                        'Walks the accessibility tree linearly and returns the announcement '
                        'text with roles, names and states — the linearized reading '
                        'experience, as prose an agent can READ to understand the page '
                        'from a blind user\'s perspective. — Read-only: for structure '
                        'use a11y_snapshot, for keyboard traps use a11y_keyboard. '
                        'Requires Playwright.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string', 'description': 'Page URL to transcribe'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'Output language (en default)'},
            'timeout': {'type': 'number', 'description': 'Page load timeout (45 default)'},
        }, 'required': ['url']},
    },
    {
        'name': 'a11y_disprove',
        'description': ('Disprover pattern (from Cloudflare\'s security-audit-skill): '
                        're-runs the audit against the live page and marks each finding '
                        'confirmed or rejected — findings that don\'t reproduce are '
                        'rejected with the reason. Catches false positives, race '
                        'conditions, and page changes between audit and report. Returns '
                        'a fresh score over confirmed findings only. — Run this before '
                        'acting on any audit report.'),
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string', 'description': 'URL to re-verify against'},
            'informe': {'type': 'object', 'description': 'existing audit report (optional; if absent, audits first)'},
            'lang': {'type': 'string', 'enum': ['es', 'en'], 'description': 'Output language (en default)'},
            'timeout': {'type': 'number', 'description': 'Timeout seconds (30 default)'},
        }, 'required': ['url']},
    },
    {
        'name': 'a11y_ledger',
        'description': ('Coverage ledger (from Cloudflare\'s security-audit-skill): '
                        'persistent record of what has been audited, when, and with what '
                        'result. Actions: record (add audit result), gaps (what has never '
                        'been checked on a URL), summary (portfolio overview). Accumulates '
                        'across runs — second audits show resolved findings.'),
        'inputSchema': {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['record', 'gaps', 'summary'],
                       'description': 'What to do'},
            'url': {'type': 'string', 'description': 'URL (for record/gaps)'},
            'informe': {'type': 'object', 'description': 'audit report object (for record)'},
            'ledger_path': {'type': 'string', 'description': 'ledger file path (default: a11y-ledger.json)'},
        }, 'required': ['action']},
    },
    {
        'name': 'a11y_criterion',
        'description': ('Explains a WCAG 2.2 success criterion in plain language (es/en): '
                        'what it requires, typical failures, and how to verify it with this '
                        'toolkit (which tool automates which part). Codes like "1.4.3", '
                        '"2.5.8", "4.1.2". Use it whenever you need to explain WHY a finding '
                        'matters or what the criterion actually says.'),
        'inputSchema': {'type': 'object', 'properties': {
            'code': {'type': 'string', 'description': 'criterion number, e.g. 1.4.3'},
            'lang': {'type': 'string', 'enum': ['es', 'en']},
        }, 'required': ['code']},
    },
]

_PROMPTS = [
    {
        'name': 'audit-page',
        'description': 'Full accessibility audit workflow for a URL: automated tools + what to verify manually (keyboard, screen reader, zoom).',
        'arguments': [
            {'name': 'url', 'description': 'page to audit', 'required': True},
            {'name': 'language', 'description': 'es or en (default: match the user)', 'required': False},
        ],
    },
    {
        'name': 'fix-contrast',
        'description': 'Guided contrast fix: verify the pair (or the text-over-image region), get the nearest passing color, apply it to the code.',
        'arguments': [
            {'name': 'fg', 'description': 'foreground/text color', 'required': True},
            {'name': 'bg', 'description': 'background color', 'required': True},
            {'name': 'context', 'description': 'file(s) or component where the colors live', 'required': False},
        ],
    },
    {
        'name': 'pre-deploy-check',
        'description': 'Pre-deploy regression check: express audit of the URL plus snapshot diff against a baseline snapshot.',
        'arguments': [
            {'name': 'url', 'description': 'staging URL to check', 'required': True},
            {'name': 'baseline', 'description': 'path or URL of the before snapshot', 'required': False},
        ],
    },
    {
        'name': 'declaration-eaa',
        'description': 'Generate a European Accessibility Act / RD 1112/2018 accessibility statement, collecting any missing legal fields from the user.',
        'arguments': [
            {'name': 'entidad', 'description': 'organization name', 'required': True},
            {'name': 'url', 'description': 'website URL', 'required': True},
            {'name': 'estado', 'description': 'plena | parcial | no_conforme', 'required': False},
        ],
    },
    {
        'name': 'conformance-wcagem',
        'description': 'Guided WCAG-EM conformance ladder for a site: express screening → agent-verified guided evaluation on a representative sample → conformance report inputs.',
        'arguments': [
            {'name': 'url', 'description': 'site root to evaluate', 'required': True},
            {'name': 'tier', 'description': 'express | guided | conformance (default: express)', 'required': False},
            {'name': 'language', 'description': 'es or en', 'required': False},
        ],
    },
]


def _prompt(nombre, args):
    L = (args.get('language') or 'en').lower()
    if L not in ('es', 'en'):
        L = 'en'
    t = {
        'audit-page': {
            'en': f"Run a full accessibility audit of {args.get('url','the URL')} and report in the user's language:\n"
                  "1. Call a11y_audit_url (static express pass). If Playwright is available, also call a11y_audit_dom for real computed contrast, 2.5.8 target size and focus indicator.\n"
                  "2. Group findings by severity; for each, cite the WCAG criterion, the evidence, and the remediation the tool returned.\n"
                  "3. State clearly what automation CANNOT check, and verify what you can: keyboard operability (Tab/Shift+Tab/Enter/Esc, focus visible), heading landmarks, form flow, 200% zoom reflow.\n"
                  "4. End with a prioritized fix list (high/medium/low) and the honest scope note: automation ≈ 1/3 of WCAG; recommend screen-reader testing for the rest.",
            'es': f"Ejecuta una auditoría de accesibilidad completa de {args.get('url','la URL')} e informa en el idioma de la persona usuaria:\n"
                  "1. Llama a a11y_audit_url (pase estático exprés). Si hay Playwright, llama también a a11y_audit_dom para contraste real computado, tamaño de objetivo 2.5.8 e indicador de foco.\n"
                  "2. Agrupa por severidad; para cada hallazgo cita el criterio WCAG, la evidencia y la remediación devuelta por la herramienta.\n"
                  "3. Deja claro lo que la automatización NO puede revisar y verifica lo que puedas: operabilidad por teclado (Tab/Shift+Tab/Enter/Esc, foco visible), landmarks, flujo de formularios, reflujo al 200%.\n"
                  "4. Cierra con una lista priorizada de arreglo (alta/media/baja) y la nota honesta: automatización ≈ 1/3 de WCAG; recomienda prueba con lector de pantalla para el resto.",
        },
        'fix-contrast': {
            'en': f"Fix the contrast of {args.get('fg','fg')} on {args.get('bg','bg')}"
                  + (f" in {args.get('context','')}" if args.get('context') else '') + ":\n"
                  "1. Call a11y_contrast_pair to get the exact ratio and per-criterion verdicts.\n"
                  "2. If AA fails, take sugerencia_aa (or call a11y_suggest_color with the needed level: 4.5 normal text, 3.0 large text, 3.0 UI components).\n"
                  "3. Locate the color in the code" + (f" ({args.get('context','')})" if args.get('context') else '')
                  + ", replace it with the suggested value, and re-verify with a11y_contrast_pair.\n"
                  "4. If the text sits over an image or gradient, use a11y_contrast_image with a screenshot region instead — pixel sampling is the only honest check there.",
            'es': f"Corrige el contraste de {args.get('fg','fg')} sobre {args.get('bg','bg')}"
                  + (f" en {args.get('context','')}" if args.get('context') else '') + ":\n"
                  "1. Llama a a11y_contrast_pair para el ratio exacto y los veredictos por criterio.\n"
                  "2. Si no pasa AA, toma sugerencia_aa (o llama a a11y_suggest_color con el nivel necesario: 4.5 texto normal, 3.0 texto grande, 3.0 componentes UI).\n"
                  "3. Localiza el color en el código" + (f" ({args.get('context','')})" if args.get('context') else '')
                  + ", sustitúyelo por el valor sugerido y reverifica con a11y_contrast_pair.\n"
                  "4. Si el texto va sobre imagen o degradado, usa a11y_contrast_image con la región de una captura — el muestreo píxel a píxel es la única verificación honesta ahí.",
        },
        'pre-deploy-check': {
            'en': f"Pre-deploy accessibility regression check for {args.get('url','the URL')}:\n"
                  "1. Call a11y_audit_url on the staging URL (and a11y_audit_dom if Playwright is available).\n"
                  + (f"2. Compare against baseline {args.get('baseline','')} with a11y_diff (if the baseline is a URL, snapshot it first with a11y_snapshot).\n"
                     if args.get('baseline') else
                     "2. If a baseline snapshot exists, diff it with a11y_diff; if not, create one with a11y_snapshot for the next deploy.\n")
                  + "3. Report: new findings (blockers), resolved findings (good news), interactive elements added/removed/renamed, focus-order changes.\n"
                  "4. Verdict: GO (no new high findings and no focus regressions) / NO-GO (otherwise) with the evidence.",
            'es': f"Comprobación de regresión de accesibilidad antes de desplegar {args.get('url','la URL')}:\n"
                  "1. Llama a a11y_audit_url sobre la URL de staging (y a11y_audit_dom si hay Playwright).\n"
                  + (f"2. Compara con la referencia {args.get('baseline','')} mediante a11y_diff (si la referencia es una URL, captúrala antes con a11y_snapshot).\n"
                     if args.get('baseline') else
                     "2. Si existe un snapshot de referencia, compara con a11y_diff; si no, créalo con a11y_snapshot para el próximo despliegue.\n")
                  + "3. Informa: hallazgos nuevos (bloqueantes), hallazgos resueltos (buenas noticias), interactivos añadidos/eliminados/renombrados, cambios de orden de foco.\n"
                  "4. Veredicto: GO (sin hallazgos altos nuevos ni regresiones de foco) / NO-GO (en caso contrario) con la evidencia.",
        },
        'conformance-wcagem': {
            'en': f"Run the WCAG-EM conformance ladder for {args.get('url','the site')} (tier: {args.get('tier','express')}):\n"
                  "1. EXPRESS (always): a11y_audit_url on the root and the 4-5 key pages (use pages parameter / crawl). Report scores and findings by severity.\n"
                  "2. GUIDED: pick a WCAG-EM sample — structured pages (home, contact, login, a content page, a form flow) plus a random pick from the crawl. On each sample page, run a11y_audit_dom if Playwright is available, then verify the manual checklist yourself (keyboard walk, focus visibility, zoom 200%, error announcement on one form). Mark each item verified-by-agent vs automated-only.\n"
                  "3. CONFORMANCE: only with a human in the loop — compile the evidence (sample, pages, results, dates) into WCAG-EM report structure, state the scope honestly (sample-based evaluation, not a certification), and feed contenido_no_accesible into a11y_generate_declaration.\n"
                  "Escalate one tier at a time; never present tier 1 or 2 as conformance.",
            'es': f"Ejecuta la escalera de conformidad WCAG-EM para {args.get('url','el sitio')} (nivel: {args.get('tier','express')})\u003a\n"
                  "1. EXPRESS (siempre): a11y_audit_url en la raíz y las 4-5 páginas clave (parámetro pages). Informa puntuaciones y hallazgos por severidad.\n"
                  "2. GUIDED: elige una muestra WCAG-EM — páginas estructurales (inicio, contacto, login, una de contenido, un flujo de formulario) más una aleatoria del rastreo. En cada una, a11y_audit_dom si hay Playwright, y verifica tú el checklist manual (recorrido de teclado, foco visible, zoom 200%, anuncio de errores en un formulario). Marca cada punto como verificado-por-agente o solo-automático.\n"
                  "3. CONFORMANCE: solo con humana en el bucle — recopila la evidencia (muestra, páginas, resultados, fechas) en la estructura del informe WCAG-EM, declara el alcance con honestidad (evaluación por muestreo, no certificación) y alimenta contenido_no_accesible en a11y_generate_declaration.\n"
                  "Escala un nivel cada vez; nunca presentes el nivel 1 o 2 como conformidad.",
        },
        'declaration-eaa': {
            'en': f"Generate an accessibility statement for {args.get('entidad','the entity')} ({args.get('url','URL')}):\n"
                  "1. Establish the compliance state with a11y_audit_url (parcial is the honest default when findings exist).\n"
                  f"2. Current estado argument: {args.get('estado','(missing)')}. If missing, infer from the audit and confirm with the user.\n"
                  "3. Collect what is missing: feedback contact, claim procedure (reclamación), evaluation method and dates. Ask the user only for what you cannot infer.\n"
                  "4. List contenido_no_accesible from the audit findings with reasons and alternatives.\n"
                  "5. Call a11y_generate_declaration (marco='eaa' for private sector / EAA; 'rd1112' for Spanish public sector), lang matching the site, and save with output_path.\n"
                  "6. Remind: the statement must be linked from every page (typically the footer) and reviewed after significant changes.",
            'es': f"Genera la declaración de accesibilidad de {args.get('entidad','la entidad')} ({args.get('url','URL')}):\n"
                  "1. Establece el estado de conformidad con a11y_audit_url (parcial es lo honesto por defecto si hay hallazgos).\n"
                  f"2. Argumento estado actual: {args.get('estado','(falta)')}. Si falta, infiérelo de la auditoría y confírmalo con la persona usuaria.\n"
                  "3. Recoge lo que falte: contacto de feedback, procedimiento de reclamación, método y fechas de evaluación. Pregunta solo lo que no puedas inferir.\n"
                  "4. Enumera contenido_no_accesible a partir de los hallazgos, con razón y alternativa.\n"
                  "5. Llama a a11y_generate_declaration (marco='eaa' para sector privado / EAA; 'rd1112' para sector público español), lang del sitio, y guarda con output_path.\n"
                  "6. Recuerda: la declaración debe enlazarse desde todas las páginas (típico en el pie) y revisarse tras cambios significativos.",
        },
    }
    txt = t[nombre][L]
    return {'description': next(p['description'] for p in _PROMPTS if p['name'] == nombre),
            'messages': [{'role': 'user', 'content': {'type': 'text', 'text': txt}}]}


# ── Parameter documentation (100% coverage, pinned by test_solido) ──────────
# TDQS/Glama's top penalty was undocumented params; this table is the single
# source, injected at import time so the literals above stay readable.
_PARAM_DOCS = {
 ('a11y_audit_url', 'url'): 'Page URL to fetch and audit (http/https only; local HTML goes in the html argument)',
 ('a11y_audit_url', 'html'): 'Raw HTML string to audit directly (overrides url — use for pages you already fetched or local files)',
 ('a11y_audit_url', 'pages'): 'Light same-domain crawl: audit up to N pages discovered by links, aggregated by mean/worst score and recurring signals (1 = single page)',
 ('a11y_audit_url', 'timeout'): 'Fetch timeout in seconds per page (default 30)',
 ('a11y_audit_dom', 'url'): 'Page URL to load in Chromium (http/https or file:// for local fixtures)',
 ('a11y_audit_dom', 'timeout'): 'Page load timeout in seconds (default 45)',
 ('a11y_audit_url', 'lang'): 'Output language for findings and remediation (default en)',
 ('a11y_audit_dom', 'lang'): 'Output language for findings and remediation (default en)',
 ('a11y_reflow', 'url'): 'Page URL to test at 320px (http/https or file://)',
 ('a11y_forms', 'url'): 'Page URL containing the form(s) to fill and submit with invalid data',
 ('a11y_hover', 'url'): 'Page URL to test tooltip dismissibility on',
 ('a11y_hover', 'timeout'): 'Page load timeout in seconds (default 45)',
 ('a11y_hover', 'browser'): 'Browser engine (auto = detect the first available)',
 ('a11y_sr_transcript', 'browser'): 'Browser engine (auto = detect the first available)',
 ('a11y_audit_dom', 'browser'): 'Browser engine (auto = detect the first available)',
 ('a11y_reflow', 'browser'): 'Browser engine (auto = detect the first available)',
 ('a11y_keyboard', 'browser'): 'Browser engine (auto = detect the first available)',
 ('a11y_scroll', 'browser'): 'Browser engine (auto = detect the first available)',
 ('a11y_forms', 'browser'): 'Browser engine (auto = detect the first available)',
 ('a11y_sr_transcript', 'url'): 'Page URL to get the screen reader announcement transcript',
 ('a11y_sr_transcript', 'timeout'): 'Page load timeout in seconds (default 45)',
 ('a11y_disprove', 'url'): 'URL to re-verify findings against',
 ('a11y_disprove', 'informe'): 'Existing audit report to verify (optional; audits first if absent)',
 ('a11y_disprove', 'timeout'): 'Fetch timeout seconds (default 30)',
 ('a11y_ledger', 'action'): 'record (add audit), gaps (what is missing), or summary (overview)',
 ('a11y_ledger', 'url'): 'URL being audited (for record/gaps)',
 ('a11y_ledger', 'informe'): 'Audit report object (for record action)',
 ('a11y_ledger', 'ledger_path'): 'Path to the ledger JSON file (default: a11y-ledger.json)',


 ('a11y_autofix', 'form_errors'): 'Inject the accessible error layer into forms without their own handling (default true)',
 ('a11y_forms', 'timeout'): 'Page load timeout in seconds (default 45)',
 ('a11y_html_validate', 'url'): 'Page URL to validate via the W3C Nu service',
 ('a11y_html_validate', 'html'): 'Raw HTML — its CONTENT is sent to validator.w3.org/nu',
 ('a11y_html_validate', 'base_url'): 'Self-hosted vnu instance base URL for sensitive content',


 ('a11y_reflow', 'timeout'): 'Page load timeout in seconds (default 45)',
 ('a11y_reflow', 'lang'): 'Output language (default en)',
 ('a11y_keyboard', 'url'): 'Page URL to Tab-walk (http/https or file://)',
 ('a11y_keyboard', 'lang'): 'Output language (default en)',
 ('a11y_keyboard', 'max_pasos'): 'Maximum real Tab presses before giving up (default 60)',
 ('a11y_scroll', 'url'): 'Feed URL to audit (best on feeds you own or can authenticate into)',
 ('a11y_scroll', 'lang'): 'Output language (default en)',
 ('a11y_scroll', 'max_tandas'): 'Scroll batches to load and evaluate (default 5)',
 ('a11y_contrast_pair', 'fg'): 'Foreground/text color: #hex, rgb(), hsl() or a CSS color name; alpha composites over bg',
 ('a11y_contrast_pair', 'bg'): 'Background color: same formats; alpha composites over white',
 ('a11y_contrast_image', 'path'): 'Local path to the screenshot/image the text sits on (PNG/JPG/PPM)',
 ('a11y_contrast_image', 'text_color'): 'The text color as rendered over the image (must be opaque)',
 ('a11y_contrast_image', 'region'): 'Text bounding box as "x,y,width,height" in pixels (strongly recommended: defines what to sample)',
 ('a11y_contrast_image', 'sample'): 'Pixel step: 4 samples every 4px (auto-raised for huge regions)',
 ('a11y_contrast_image', 'lang'): 'Output language (default en)',
 ('a11y_suggest_color', 'fg'): 'The failing foreground color to fix',
 ('a11y_suggest_color', 'bg'): 'The background it must pass against',
 ('a11y_suggest_color', 'target'): 'Ratio to reach: 4.5 normal text, 3.0 large text/UI, 7.0 AAA (default 4.5)',
 ('a11y_generate_declaration', 'entidad'): 'Legal entity name as it should appear in the statement (company, body…)',
 ('a11y_generate_declaration', 'url'): 'Website URL the statement covers',
 ('a11y_generate_declaration', 'estado'): 'Compliance state: plena | parcial | no_conforme (parcial is the honest default when findings exist)',
 ('a11y_generate_declaration', 'contenido_no_accesible'): 'Non-accessible content list: one string per item, ideally criterion + reason + alternative',
 ('a11y_generate_declaration', 'metodo'): 'How conformance was evaluated (e.g. "self-evaluation: a11y-toolkit screening + manual review")',
 ('a11y_generate_declaration', 'fecha_evaluacion'): 'ISO date of the last evaluation (YYYY-MM-DD)',
 ('a11y_generate_declaration', 'fecha_revision'): 'ISO date of the next scheduled review',
 ('a11y_generate_declaration', 'feedback'): 'Contact channel for accessibility feedback (email or URL)',
 ('a11y_generate_declaration', 'reclamacion'): 'Claim/complaint procedure URL or address (legally required in several jurisdictions)',
 ('a11y_generate_declaration', 'marco'): 'Legal framework: rd1112 (Spanish public sector, art. 10) or eaa (European Accessibility Act / private sector)',
 ('a11y_generate_declaration', 'disponibilidad_alternativa'): 'Where to get the content in an alternative accessible format',
 ('a11y_generate_declaration', 'output_path'): 'Local path to save the statement HTML (omit to receive it inline)',
 ('a11y_generate_declaration', 'lang'): 'Statement language (default en; es uses the Spanish legal wording)',
 ('a11y_snapshot', 'url'): 'Page URL to snapshot (http/https or file://)',
 ('a11y_diff', 'a'): 'BEFORE snapshot: inline JSON (starts with {) or path to the snapshot file',
 ('a11y_diff', 'b'): 'AFTER snapshot: inline JSON or file path',
 ('a11y_diff_urls', 'url_a'): 'First URL (usually staging)',
 ('a11y_diff_urls', 'url_b'): 'Second URL (usually production)',
 ('a11y_autofix', 'html'): 'Raw HTML to apply the closed allowlist of deterministic fixes to',
 ('a11y_autofix', 'lang'): 'BCP-47 language to set on <html> ONLY if it is missing (e.g. "es")',
 ('a11y_autofix', 'title'): 'Page title to set ONLY if <title> is empty',
 ('a11y_badge', 'score'): '0-100 score from an audit result (int/float)',
 ('a11y_badge', 'fecha'): 'ISO date shown on the badge (today by default)',
 ('a11y_badge', 'lang'): 'Badge language (default en)',
 ('a11y_criterion', 'code'): 'WCAG criterion number, e.g. "1.4.3", "2.5.8"',
 ('a11y_criterion', 'lang'): 'Explanation language (default en)',
 ('a11y_evidence', 'informes'): 'Audit report objects to bundle (any mode: static, rendered, reflow, keyboard, scroll)',
 ('a11y_evidence', 'snapshot'): 'Optional a11y_snapshot output to include as an artifact',
 ('a11y_evidence', 'evaluador'): 'Optional prefill for the signature block: {"nombre":…, "credencial":…, "fecha_revision":…}',
 ('a11y_aria_live_snippet', 'lang'): 'Monitor panel language (default en)',
}

# Routing guidance: one "prefer sibling X" sentence per tool (TDQS dimension).
_ROUTING = {
 'a11y_audit_url': 'Prefer a11y_audit_dom when JS renders the content or contrast/2.5.8/focus matter; use pages for light multi-page sampling.',
 'a11y_audit_dom': 'Use instead of a11y_audit_url on JS-heavy pages; needs local Playwright.',
 'a11y_reflow': 'Scope: 320px reflow only (1.4.10); for the full rendered pass use a11y_audit_dom.',
 'a11y_keyboard': 'Scope: keyboard traps (2.1.2); focus visibility is part of a11y_audit_dom.',
 'a11y_scroll': 'For paginated feeds only; general page audit is a11y_audit_url/dom.',
 'a11y_contrast_pair': 'For flat pairs; text over images needs a11y_contrast_image.',
 'a11y_contrast_image': 'Use instead of a11y_contrast_pair whenever the background is a photo/gradient.',
 'a11y_suggest_color': 'The fixer companion to a11y_contrast_pair failures.',
 'a11y_snapshot': 'Capture half of the watch loop; compare with a11y_diff (or a11y_diff_urls for two live URLs).',
 'a11y_diff': 'Compares two existing snapshots; a11y_diff_urls snapshots both for you.',
 'a11y_diff_urls': 'Convenience for staging-vs-production; manual control is snapshot + a11y_diff.',
 'a11y_autofix': 'Only the closed allowlist of provably safe fixes; judgment fixes come back as no_aplicados with remediation.',
 'a11y_badge': 'Scope: the honest SVG seal for audited sites; the machine-readable bundle is a11y_evidence.',
 'a11y_criterion': 'Knowledge lookup; does not fetch or audit anything.',
 'a11y_evidence': 'The tier-3 handoff object; feed it every audit report you have.',
 'a11y_aria_live_snippet': 'Diagnostics aid to inject in a browser; not an audit by itself.',
 'a11y_generate_declaration': 'Legal statement generator; drive contenido_no_accesible from audit findings and a11y_evidence.',
}

for _t in TOOLS:
    _props = _t['inputSchema'].get('properties', {})
    for _p, _desc in _PARAM_DOCS.items():
        if _p[0] == _t['name'] and _p[1] in _props:
            _props[_p[1]].setdefault('description', _desc)
    if _t['name'] in _ROUTING and _ROUTING[_t['name']] not in _t['description']:
        _t['description'] += ' — ' + _ROUTING[_t['name']]

# Títulos UI + annotations (MCP spec 2025-11-25): los clientes pueden aprobar
# automáticamente las tools de solo lectura → menos fricción en cada uso.
_ANN = {
    'a11y_audit_url':        ('Express WCAG audit', True, True),
    'a11y_audit_dom':        ('Rendered WCAG audit', True, True),
    'a11y_reflow':           ('320px reflow check', True, True),
    'a11y_keyboard':         ('Keyboard-trap detector', True, True),
    'a11y_html_validate':    ('W3C Nu validation', True, True),
    'a11y_forms':            ('Form error testing', True, True),
    'a11y_scroll':           ('Infinite-scroll audit', True, True),
    'a11y_snapshot':         ('A11y snapshot + tab order', True, True),
    'a11y_diff':             ('Snapshot regression diff', True, False),
    'a11y_diff_urls':        ('Staging vs production diff', True, True),
    'a11y_contrast_pair':    ('Contrast ratio + verdicts', True, False),
    'a11y_contrast_image':   ('Text-over-image contrast', True, False),
    'a11y_suggest_color':    ('Nearest passing color', True, False),
    'a11y_generate_declaration': ('Accessibility statement (EAA/RD 1112)', False, False),
    'a11y_autofix':          ('Deterministic safe auto-fixes', True, False),
    'a11y_aria_live_snippet': ('aria-live monitor snippet', True, False),
    'a11y_badge':            ('Honest SVG badge', True, False),
    'a11y_evidence':         ('Evidence pack (countersignature-ready)', True, False),
    'a11y_hover':            ('Hover dismissibility (1.4.13)', True, True),
    'a11y_sr_transcript':    ('Screen reader transcript', True, True),
    'a11y_disprove':         ('Disprover: re-verify findings', True, True),
    'a11y_ledger':           ('Coverage ledger (persistent)', True, False),
    'a11y_criterion':        ('WCAG criterion explained', True, False),
}
for _t in TOOLS:
    _titulo, _ro, _ow = _ANN[_t['name']]
    _t['title'] = 'a11y-toolkit: ' + _titulo
    _t['annotations'] = {'readOnlyHint': _ro, 'destructiveHint': not _ro,
                         'idempotentHint': True, 'openWorldHint': _ow}


def _texto(obj):
    r = {'content': [{'type': 'text', 'text': json.dumps(obj, ensure_ascii=False, indent=1)}]}
    if isinstance(obj, dict) and 'error' in obj:
        r['isError'] = True
    return r


def llamar(nombre, args):
    if nombre == 'a11y_contrast_pair':
        return _texto(pair_fn(args['fg'], args['bg'], lang=args.get('lang', 'en')))
    if nombre == 'a11y_contrast_image':
        return _texto(image_contrast(args['path'], args['text_color'],
                                     region=args.get('region'), sample=args.get('sample', 4), lang=args.get('lang', 'en')))
    if nombre == 'a11y_suggest_color':
        fg, bg = parse_color(args['fg']), parse_color(args['bg'])
        if not fg or not bg:
            return _texto({'error': 'invalid color'})
        return _texto(sugerir(fg, bg, float(args.get('target', 4.5)), args.get('lang', 'en')) or {'resultado': None})
    if nombre == 'a11y_generate_declaration':
        res = declaracion_fn(
            args['entidad'], args['url'], args['estado'],
            contenido_no_accesible=args.get('contenido_no_accesible'),
            metodo=args.get('metodo'), fecha_evaluacion=args.get('fecha_evaluacion'),
            fecha_revision=args.get('fecha_revision'), feedback=args.get('feedback'),
            reclamacion=args.get('reclamacion'), marco=args.get('marco', 'rd1112'),
            disponibilidad_alternativa=args.get('disponibilidad_alternativa'),
            lang=args.get('lang', 'en'))
        if 'error' in res:
            return {'content': [{'type': 'text', 'text': res['error']}], 'isError': True}
        salida = args.get('output_path')
        if salida:
            with open(salida, 'w', encoding='utf-8') as f:
                f.write(res['html'])
            return _texto({'guardado_en': salida, 'resumen': res['resumen']})
        return {'content': [{'type': 'text', 'text': res['html']}]}
    if nombre == 'a11y_audit_url':
        try:
            if args.get('html'):
                return _texto(audit_html_fn(args['html'], args.get('url') or '(html)',
                                            lang=args.get('lang', 'en')))
            if args.get('pages', 1) > 1:
                return _texto(audit_site_fn(args['url'], max_pages=args['pages'],
                                            timeout=args.get('timeout', 30),
                                            lang=args.get('lang', 'en')))
            return _texto(audit_url_fn(args['url'], timeout=args.get('timeout', 30),
                                       lang=args.get('lang', 'en')))
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_audit_dom':
        try:
            return _texto(audit_dom_url(args['url'], timeout=args.get('timeout', 45),
                                        lang=args.get('lang', 'en')))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium (or use a11y_audit_url for the zero-dependency static audit)'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_snapshot':
        try:
            return _texto(snapshot_fn(args['url']))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_diff':
        def _carga(v):
            v = v.strip()
            if v.startswith('{'):
                return json.loads(v)
            with open(v, encoding='utf-8') as f:
                return json.load(f)
        try:
            return _texto(diff_fn(_carga(args['a']), _carga(args['b'])))
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_diff_urls':
        try:
            return _texto(diff_fn(snapshot_fn(args['url_a']), snapshot_fn(args['url_b'])))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_scroll':
        try:
            return _texto(audit_scroll(args['url'], max_tandas=args.get('max_tandas', 5),
                                       lang=args.get('lang', 'en')))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_keyboard':
        try:
            return _texto(audit_keyboard(args['url'], max_pasos=args.get('max_pasos', 60),
                                         lang=args.get('lang', 'en')))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_forms':
        try:
            return _texto(audit_forms(args['url'], timeout=args.get('timeout', 45),
                                      lang=args.get('lang', 'en'),
                                      auth_state=args.get('auth_state'),
                                      browser=args.get('browser', 'auto')))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_evidence':
        try:
            return _texto(empaquetar_fn(args['informes'], snapshot=args.get('snapshot'),
                                        evaluador=args.get('evaluador'),
                                        verificados=args.get('verificados')))
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_autofix':
        return _texto(autofix_fn(args['html'], lang=args.get('lang'),
                                 title=args.get('title'), url=args.get('url') or '(html)',
                                 form_errors=args.get('form_errors', True)))
    if nombre == 'a11y_reflow':
        try:
            return _texto(audit_reflow(args['url'], timeout=args.get('timeout', 45),
                                       lang=args.get('lang', 'en')))
        except ImportError:
            return {'content': [{'type': 'text',
                                 'text': 'Playwright not installed: pip install playwright && playwright install chromium'}],
                    'isError': True}
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_html_validate':
        try:
            if args.get('html'):
                return _texto(validar_html(args['html'], lang=args.get('lang', 'en'),
                                           base_url=args.get('base_url')))
            return _texto(validar_url(args['url'], lang=args.get('lang', 'en'),
                                      base_url=args.get('base_url')))
        except Exception as e:  # noqa: BLE001
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_hover':
        try:
            return _texto(audit_hover(args['url'], timeout=args.get('timeout', 45),
                                       lang=args.get('lang', 'en')))
        except ImportError:
            return {'content': [{'type': 'text', 'text': 'Playwright not installed'}], 'isError': True}
        except Exception as e:
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_sr_transcript':
        try:
            return _texto(sr_transcript(args['url'], timeout=args.get('timeout', 45),
                                        lang=args.get('lang', 'en'),
                                        browser=args.get('browser', 'auto')))
        except ImportError:
            return {'content': [{'type': 'text', 'text': 'Playwright not installed'}], 'isError': True}
        except Exception as e:
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_disprove':
        try:
            return _texto(disprove_fn(args['url'], informe=args.get('informe'),
                                       timeout=args.get('timeout', 30),
                                       lang=args.get('lang', 'en')))
        except Exception as e:
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_ledger':
        try:
            ruta = args.get('ledger_path', 'a11y-ledger.json')
            accion = args['action']
            if accion == 'record':
                if not args.get('url') or not args.get('informe'):
                    return _texto({'error': 'record requires url + informe'})
                from a11yledger import record as _rec
                return _texto(_rec(args['url'], args['informe'], ruta=ruta))
            if accion == 'gaps':
                if not args.get('url'):
                    return _texto({'error': 'gaps requires url'})
                from a11yledger import gaps as _gaps
                return _texto(_gaps(args['url'], ruta=ruta))
            if accion == 'summary':
                from a11yledger import summary as _sum
                return _texto(_sum(ruta=ruta))
        except Exception as e:
            return {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
    if nombre == 'a11y_criterion':
        return _texto(criterio_fn(args['code'], lang=args.get('lang', 'en')))
    if nombre == 'a11y_badge':
        svg = badge_fn(args['score'], fecha=args.get('fecha'),
                       lang=args.get('lang', 'en'))
        return {'content': [{'type': 'text', 'text': svg}]}
    if nombre == 'a11y_aria_live_snippet':
        if ARIALIVE_JS is not None:
            js = ARIALIVE_JS
        else:
            with open(os.path.join(AQUI, 'arialive.js'), encoding='utf-8') as f:
                js = f.read()
        if args.get('lang') == 'en':
            js = "window.ALM_LANG='en';\n" + js
        return {'content': [{'type': 'text', 'text': js}]}
    raise ValueError(f'unknown tool: {nombre}')


def main():
    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        try:
            msg = json.loads(linea)
        except json.JSONDecodeError:
            continue
        metodo = msg.get('method', '')
        mid = msg.get('id')
        if mid is None:
            continue
        try:
            if metodo == 'initialize':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {
                    'protocolVersion': msg.get('params', {}).get('protocolVersion', '2024-11-05'),
                    'capabilities': {'tools': {}, 'prompts': {}},
                    'serverInfo': {'name': 'a11y-toolkit', 'version': VERSION},
                    'instructions': INSTRUCTIONS,
                }}
            elif metodo == 'ping':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {}}
            elif metodo == 'tools/list':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {'tools': TOOLS}}
            elif metodo == 'tools/call':
                p = msg.get('params', {})
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': llamar(p.get('name'), p.get('arguments') or {})}
            elif metodo == 'prompts/list':
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': {'prompts': _PROMPTS}}
            elif metodo == 'prompts/call':
                p = msg.get('params', {})
                resp = {'jsonrpc': '2.0', 'id': mid, 'result': _prompt(p.get('name'), p.get('arguments') or {})}
            else:
                resp = {'jsonrpc': '2.0', 'id': mid,
                        'error': {'code': -32601, 'message': f'unknown method: {metodo}'}}
        except Exception as e:  # noqa: BLE001
            resp = {'jsonrpc': '2.0', 'id': mid, 'result': {
                'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
