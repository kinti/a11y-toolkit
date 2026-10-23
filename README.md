# a11y-toolkit — the accessibility layer for AI coding agents

[![CI](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![Downloads](https://img.shields.io/pypi/dm/a11y-toolkit)](https://pypistats.org/packages/a11y-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-server-purple)](https://modelcontextprotocol.io)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink)](https://github.com/sponsors/kinti)

32 MCP tools, 6 prompts and a skill covering the whole WCAG 2.2 loop: audit, fix,
document, watch, hand off — and now blindfold usability testing, where the agent
attempts real tasks perceiving only what a screen reader exposes. 51 of 55 A/AA criteria carry automated signals (93%), every
finding ships with a concrete remediation your agent can apply, and the rendered tools
run on whichever browser you have — Chromium, Firefox, WebKit, Chrome or Edge.

The European Accessibility Act is in force since June 2025, ADA suits keep landing,
and AI agents now write most of the web. A scan is not a defence: the machine finds,
the human signs.

> **This engine is in production at [a11y.es](https://a11y.es)** — continuous WCAG 2.2
> monitoring with hash-verifiable evidence packs and human-signed reports. En español.
> The service layer —panel, scheduling, the signing workflow, client operations— is
> NOT in this repository: cloning this engine is not cloning a11y.es.

<p align="center">
  <img src="docs/demo.gif" alt="a11y-toolkit in action: audit (score 64), nearest passing color, re-audit (94) — real tool output" width="720">
</p>

## What no other a11y tool gives an agent

| Capability | axe-core / Lighthouse / pa11y | a11y-toolkit |
|---|---|---|
| Text contrast over images and gradients (pixel sampling of the real background) | ✗ | ✓ |
| VPAT 2.5 (WCAG) draft from the evidence pack — US/ADA counterpart of the EAA statement | ✗ | ✓ |
| Form error testing: fills invalid data, really submits, judges what happens | ✗ | ✓ |
| Keyboard traps: real Tab walk + Escape-release test, plus focus/input-triggered navigation | ✗ | ✓ |
| Infinite-scroll audit: focus survival, announcements, feed end | ✗ | ✓ |
| Reflow at 320px and the WCAG text-spacing override, measured | ✗ | ✓ |
| Screen reader transcript: what a blind user hears, linearized | ✗ | ✓ |
| Tooltips that ignore Escape caught by actually hovering (1.4.13) | ✗ | ✓ |
| Legal statements for the EAA / RD 1112/2018, in Spanish and English | ✗ | ✓ |
| An evidence pack a human can sign — hashes, matrix, empty signature block | ✗ | ✓ |
| Runs with zero dependencies at core, speaks es/en, any browser you have | heavy runtimes | ✓ |

## The tools (32)

Every tool, complete — description, arguments, and behavior annotations, generated from the server itself (`server.TOOLS` is the source of truth). All tools accept `lang` (`en`|`es`) unless noted; output is JSON unless noted.


### Audit


#### `a11y_audit_url`

<sub>read-only · network</sub>

Express WCAG 2.2 audit of a URL or an HTML string: 20+ automated signals with a weighted 0-100 score — images without alt (1.1.1), controls without accessible names (4.1.2), form fields without labels (3.3.2), missing autocomplete on user-data fields (1.3.5), click handlers on non-interactive elements (2.1.1), unknown ARIA roles and broken aria-labelledby (4.1.2), duplicated unnamed landmarks, timed meta refresh (2.2.1), missing skip mechanism (2.4.1), lang/title (3.1.1, 2.4.2), heading structure (1.3.1), blocked zoom (1.4.4), captions (1.2.2), autoplay audio (1.4.2), generic/duplicated link text (2.4.4), target=_blank without warning (3.2.5), positive tabindex (2.4.3), aria-hidden on focusable elements, tables without th, duplicate ids, duplicate accesskeys. Each finding includes concrete remediation. Filter, not verdict: automation covers ~1/3 of WCAG; query a11y_criterion for what a criterion means. — Prefer a11y_audit_dom when JS renders the content or contrast/2.5.8/focus matter; use pages for light multi-page sampling. Returns JSON: {mode, url|file, score 0-100, findings [{criterion, severity, signal, issue, remediation}], summary {high, medium, low}, limits, score_note}.


**Arguments**

- `url`: URL to fetch and audit.

- `html`: raw HTML to audit directly (overrides url).

- `pages` — range 1…20: light same-domain crawl: audit up to N pages, aggregated by score and recurring signals (default 1, max 20).

- `lang` — one of ['es', 'en']: output language (en default).

- `timeout`: fetch timeout seconds (30 default).


#### `a11y_audit_dom`

<sub>read-only · network</sub>

Deep RENDERED WCAG audit via local Playwright/Chromium: real computed text contrast against effective backgrounds with alpha compositing (1.4.3), pixel-sampled measurement of text sitting over images/gradients (background captured with the text transparent — no text pixels, no antialiasing bias), minimum target size 24×24 (2.5.8, new in WCAG 2.2), visible focus indicator heuristic (2.4.7), plus rendered versions of the static checks (alt, accessible names, labels, headings, lang/title, tabindex, aria-hidden, captions, tables). Findings include remediation. Requires playwright: pip install playwright && playwright install chromium. — Use instead of a11y_audit_url on JS-heavy pages; needs local Playwright. Returns JSON: {mode, url, score 0-100, findings [{criterion, severity, signal, issue, remediation}], summary, score_note} — same shape as the static audit.


**Arguments**

- `url` *(required)*: Page URL to load in Chromium (http/https or file:// for local fixtures).

- `lang` — one of ['es', 'en']: Output language for findings and remediation (default en).

- `timeout`: page load timeout seconds (45 default).

- `auth_state`: Path to a Playwright storage_state JSON (exported session) to audit behind login — local file, never uploaded.


#### `a11y_forms`

<sub>mutates state · not idempotent · network</sub>

Form error testing (3.3.1 Error Identification, 3.3.3 Error Suggestion) — the guided flow no competitor automates: fills every validatable field with INVALID data, really submits, and judges the post-submit DOM — are errors identified in text and associated with the field (aria-invalid + aria-describedby, error summary, role=alert), or does the form swallow them? Native browser validation counts as identification (unless the form has novalidate); forms that navigate on submit are honestly noted as not measurable in-page. Requires local Playwright. Returns JSON: per-field error judgments {field, submitted_value_class, error_identified, announced, suggestion_present} plus an overall 3.3.1/3.3.3 verdict. Use on test/staging forms, or forms you own: invalid data is REALLY submitted. Do not run against production forms that trigger real emails, orders or leads.


**Arguments**

- `url` *(required)*: Page URL with the form(s) to test.

- `lang` — one of ['es', 'en']: Output language (en default).

- `timeout`: Page load timeout seconds (45 default).

- `auth_state`: Path to a Playwright storage_state JSON to test forms behind login.


#### `a11y_keyboard`

<sub>read-only · network</sub>

Keyboard-trap detection (2.1.2) with REAL Tab walking in Chromium: up to 60 real tab stops, cycle detection (the modal pattern), then the decisive test — does ESCAPE release the cycle? A modal that cycles and releases on Escape is correct and NOT reported; a cycle Escape cannot leave is a trap (high severity). Returns the full tab stop list too. Requires local Playwright. — Scope: keyboard traps (2.1.2); focus visibility is part of a11y_audit_dom. Returns JSON: {tab_stops, trap_detected, escape_releases, findings}. Run on pages with modals, dialogs or embedded apps; a plain content page has nothing to trap.


**Arguments**

- `url` *(required)*: Page URL to Tab-walk (http/https or file://).

- `lang` — one of ['es', 'en']: Output language (default en).

- `max_steps`: max real Tab presses (60 default).

- `auth_state`: Path to a Playwright storage_state JSON (exported session) to Tab-walk behind login.


#### `a11y_scroll`

<sub>read-only · network</sub>

Infinite-scroll accessibility audit — the documented disaster nobody automates (Deque guidance + ARIA APG Feed pattern; criteria 2.4.3, 4.1.3, 2.2.2). Real scrolling batches in Chromium with a live-region observer: does the focused element SURVIVE each batch (re-render destroys it — the documented failure)? Is new content ANNOUNCED (aria-live/status receives text, role=feed)? Does the feed END or offer a load-more alternative (footer reachability)? APG feed pattern as positive signal. Honest guard: if no standard items are detected (login walls, non-standard markup) the unfounded signals are skipped with a note. Requires local Playwright. — For paginated feeds only; general page audit is a11y_audit_url/dom. Returns JSON: {mode, url, score, findings [{criterion, severity, signal, issue, remediation}], summary} — same shape as the audits.


**Arguments**

- `url` *(required)*: Feed URL to audit (best on feeds you own or can authenticate into).

- `lang` — one of ['es', 'en']: Output language (default en).

- `max_batches`: scroll batches (5 default).

- `auth_state`: Path to a Playwright storage_state JSON (exported session) to audit an authenticated feed.


#### `a11y_reflow`

<sub>read-only · network</sub>

Reflow check at 320px — criterion 1.4.10 (AA), the check axe and Lighthouse do not automate. Loads the URL at 1280px, then at 320px, and reports real horizontal scroll + the overflowing elements. Method note: browser zoom RE-LAYS OUT at 320 CSS px (that is the standard's own equivalence: 1280 @ 400% zoom = 320px), so the correct measurement is a 320px viewport. Requires local Playwright. — Scope: 320px reflow only (1.4.10); for the full rendered pass use a11y_audit_dom. Returns JSON: {url, viewport, horizontal_scroll, offenders [{selector, width}]}. Run once per template, not per page: fixed-width layouts are a property of the template.


**Arguments**

- `url` *(required)*: Page URL to test at 320px (http/https or file://).

- `lang` — one of ['es', 'en']: Output language (default en).

- `timeout`: Page load timeout in seconds (default 45).

- `auth_state`: Path to a Playwright storage_state JSON (exported session) to test behind login.


#### `a11y_hover`

<sub>read-only · network</sub>

Content on Hover or Focus (1.4.13): finds tooltip/overlay candidates, hovers each, and tests whether Escape dismisses the result — tooltips that do not dismiss are flagged. Requires local Playwright. — Scope: tooltips only; full audit is a11y_audit_dom, keyboard traps are a11y_keyboard. Returns JSON: {candidates, dismissed_on_escape, findings}.


**Arguments**

- `url` *(required)*: Page URL to test.

- `lang` — one of ['es', 'en']: Output language (en default).

- `timeout`: Page load timeout (45 default).


#### `a11y_sr_transcript`

<sub>read-only · network</sub>

Screen reader TRANSCRIPT: what a blind user HEARS on this page. Walks the accessibility tree linearly and returns the announcement text with roles, names and states — the linearized reading experience, as prose an agent can READ to understand the page from a blind user's perspective. — Read-only: for structure use a11y_snapshot, for keyboard traps use a11y_keyboard. Requires Playwright. Returns JSON: {url, total, announcements [{time, politeness, role, text}] — the linearized reading order}.


**Arguments**

- `url` *(required)*: Page URL to transcribe.

- `lang` — one of ['es', 'en']: Output language (en default).

- `timeout`: Page load timeout (45 default).


#### `a11y_html_validate`

<sub>read-only · network</sub>

The W3C's own parser as a toolkit mode: checks a URL or raw HTML against the Nu Html Checker (validator.w3.org/nu) — doctype, encoding, structural validity, plus alt/lang/role issues from the authoritative source, mapped to WCAG criteria where they overlap. PRIVACY: html mode POSTs the document to the W3C service (url mode shares only the URL, like a11y_audit_url); self-hosted vnu instances supported via base_url for sensitive content. Returns JSON: Nu validator messages mapped to WCAG criteria where they overlap.


**Arguments**

- `url`: Page URL to validate (shares the URL with the W3C service).

- `html`: Raw HTML to validate — POSTs the content to validator.w3.org/nu; use url or a self-hosted instance for sensitive pages.

- `base_url`: Base URL of a self-hosted vnu instance (docker ghcr.io/validator/validator) instead of the public W3C service.

- `lang` — one of ['es', 'en']: Output language (en default).


### Blindfold testing


#### `a11y_journey_verdict`

<sub>read-only</sub>

Blindfold journey verdict — the capability no other accessibility tool has: the agent attempted a REAL task (sign up, checkout, password reset) perceiving only the accessibility tree and acting by accessible name and keyboard; perceive via your browser accessibility snapshot (state-preserving). This turns its friction log into a deterministic scored verdict. Pass = task completable non-visually by the agent; friction items map to WCAG criteria and flow into the evidence pack (report:journey). Use with the blindfold-task prompt: act by accessible name, log friction per step, then call this. Task usability evidence, never conformance. Returns JSON: {verdict pass|partial|fail|blocked, score 0-100, findings [{criterion, severity, signal, issue, remediation, step}], summary, rules} — writes a file only when output_path is given. Run only after a real blindfold attempt (the blindfold-task prompt): the verdict prices the walk, it does not replace it.


**Arguments**

- `task` *(required)*: {"goal": what the agent attempted, "kind": sign-up|checkout|password-reset|search|custom}.

- `steps` *(required)*: journey steps: {action, target (accessible name), perceived, friction?} — friction is {pattern: journey_* key} or {criterion, severity, issue, remediation?}.

- `outcome` *(required)*: {"completed": bool, "gave_up": bool, "workaround_used": bool, "notes"}.

- `url`: page(s) where the journey ran.

- `lang` — one of ['en', 'es']: output language.

- `output_path`: write the full verdict JSON here instead of returning it inline.


### Fix & contrast


#### `a11y_autofix`

<sub>read-only</sub>

DETERMINISTIC safe auto-fixes applied to HTML — the honest anti-overlay: a short closed list of fixes where the correct answer is unique (unblock viewport zoom 1.4.4, add the exact autocomplete token 1.3.5, fill missing html lang and empty title when provided). Everything requiring judgment (alt text, contrast, accessible names) is NOT touched — it returns not_applied with the reason and remediation instead. Returns fixed_html + applied + not_applied. — Only the closed allowlist of provably safe fixes; judgment fixes come back as not_applied with remediation. Returns JSON: {fixed_html, applied [{fix, …}], not_applied [{issue, remediation}]} — writes a file only when output_path is given.


**Arguments**

- `html` *(required)*: raw HTML to fix.

- `lang`: only if provided and <html> lacks lang.

- `title`: only if provided and <title> is empty.


#### `a11y_contrast_pair`

<sub>read-only</sub>

Exact WCAG contrast ratio for a color pair: per-criterion verdicts 1.4.3 (AA), 1.4.6 (AAA), 1.4.11 (non-text). Accepts #hex, rgb(), hsl(), CSS color names; rgba/hsl with alpha is composited over the background. If AA fails, suggests the nearest passing color. — For flat pairs; text over images needs a11y_contrast_image. Returns JSON: {text, background, ratio, verdicts [{criterion, level, threshold, passes}], aa_suggestion?}.


**Arguments**

- `fg` *(required)*: Foreground/text color: #hex, rgb(), hsl() or a CSS color name; alpha composites over bg.

- `bg` *(required)*: Background color: same formats; alpha composites over white.

- `lang` — one of ['es', 'en']: output language (en default).


#### `a11y_contrast_image`

<sub>read-only</sub>

TEXT OVER IMAGE contrast: pixel-level sampling of the real background behind the text box → worst/median/p95 ratio, % of area passing AA, and automatic hostile-zone detection on a 3×3 grid (zona_peor). What pair-only checkers cannot do. region="x,y,w,h" recommended. — Use instead of a11y_contrast_pair whenever the background is a photo/gradient. Returns JSON: {worst_ratio, median_ratio, p95_ratio, area_passes_aa_normal_text_4_5, worst_zone, sampled_pixels}.


**Arguments**

- `path` *(required)*: Local path to the screenshot/image the text sits on (PNG/JPG/PPM).

- `text_color` *(required)*: The text color as rendered over the image (must be opaque).

- `region`: Text bounding box as "x,y,width,height" in pixels (strongly recommended: defines what to sample).

- `sample`: Pixel step: 4 samples every 4px (auto-raised for huge regions).

- `lang` — one of ['es', 'en']: Output language (default en).


#### `a11y_contrast_dom`

<sub>read-only · network</sub>

REAL contrast of an element against whatever is behind it (image, gradient, video, photo): loads the page in Chromium, screenshots the element matched by selector with its text turned transparent — so only the real background is sampled, no text pixels, no antialiasing edges — and contrasts the pixels with the text color (computed from the element when not given). The automated version of a11y_contrast_image: no manual screenshot, no region math. Requires local Playwright. — Use instead of a11y_contrast_image when the text lives in a live page (captures and measures it automatically); for flat pairs use a11y_contrast_pair. Returns JSON: {url, selector, text_color, worst_ratio, median_ratio, p95_ratio, area_passes_aa_normal_text_4_5, worst_zone?, sampled_pixels, interpretation}.


**Arguments**

- `url` *(required)*: Page URL where the element lives (http/https or file://).

- `selector` *(required)*: CSS selector of the text element to measure.

- `text_color`: Text color (default: computed from the element).

- `sample`: Pixel step (default 4).

- `lang` — one of ['es', 'en']: Output language (default en).

- `timeout`: Page load timeout seconds (default 45).

- `auth_state`: Path to a Playwright storage_state JSON to measure behind login — stays local.

- `browser` — one of ['auto', 'chromium', 'firefox', 'webkit', 'chrome', 'msedge']: Browser engine (auto = detect the first available).


#### `a11y_vtt_check`

<sub>read-only · network</sub>

WebVTT caption QUALITY (1.2.2) — the substance, not the presence. Everyone stops at "<track> exists"; this downloads and parses the actual .vtt and judges what viewers get: malformed timing lines, empty cues, overlaps, impossible reading speed (>21 chars/second, BBC/Netflix standard) and coverage vs the media duration when given. Not a substitute for human review of accuracy or speaker identification. Returns JSON: {mode: "vtt", cues, characters, captioned_seconds, findings [{criterion, severity, signal, issue, remediation}], summary, limits}.


**Arguments**

- `url` *(required)*: URL of the .vtt caption file.
- `duration`: media duration in seconds — enables the coverage check (1.2.2 completeness) — range 1…∞.
- `lang` — one of ['en', 'es']: output language.

#### `a11y_audit_pdf`

<sub>read-only</sub>

PDF accessibility screening — the space nobody automated (axe, pa11y, Lighthouse: HTML only). Zero-dep structural first pass on a LOCAL file: tagged tree (/StructTreeRoot — the root failure), title, language, outline, /Alt entries, text layer (scanned detection), encryption. Full PDF/UA conformance needs a spec validator (veraPDF); this finds the failures that make full validation pointless. Use for enterprise document pipelines and PDFs linked from the audited site. Returns JSON: {mode: "pdf", pages, tagged, lang, title, images, alt_entries, findings, summary, limits}.


**Arguments**

- `path` *(required)*: local PDF file path (never fetched remotely — download it yourself first).
- `lang` — one of ['en', 'es']: output language.

#### `a11y_docx_screen`

<sub>read-only</sub>

DOCX accessibility screening — the other half of enterprise paperwork. Zero-dep structural pass on a LOCAL .docx: images with no alt text (docPr without descr), fake headings (bold+big paragraphs with no Heading style — invisible to the navigation pane and TOC), document language, tables without marked header row. Returns JSON: {mode: "docx", language, images, tables, findings, summary, limits}.


**Arguments**

- `path` *(required)*: local .docx file path.
- `lang` — one of ['en', 'es']: output language.

#### `a11y_reduced_motion`

<sub>read-only · network</sub>

Does the site HONOR prefers-reduced-motion? Loads the page normally, counts looping CSS animations (>0.15s infinite), then reloads emulating prefers-reduced-motion: reduce and counts again. If the number does not drop, the site ignores the user's preference (2.2.2; 2.3.3 AAA). Nobody else automates this. Covers CSS animations and video[autoplay]; JS/WebGL/scroll-parallax remain manual. Returns JSON: {mode, normal, reduced, respects, score, findings, limits}.


**Arguments**

- `url` *(required)*: page URL to test with and without prefers-reduced-motion.
- `auth_state`: path to a Playwright storage_state JSON — test behind login, stays local.
- `browser` — one of ['auto', 'chromium', 'firefox', 'webkit', 'chrome', 'msedge']: engine.
- `lang` — one of ['en', 'es']: output language.
- `timeout`: page load timeout seconds (45 default).

#### `a11y_forced_colors`

<sub>read-only · network</sub>

Does content survive forced-colors: active (Windows High Contrast)? Flags SVGs with hardcoded colored fills (they fall back to inherited and icons can vanish). Review-grade heuristic — the definitive check is visual on Windows HCM; this prepares it. Returns JSON: {mode, normal, forced, score, findings, limits}.


**Arguments**

- `url` *(required)*: page URL to test under forced-colors emulation.
- `auth_state`, `browser`, `lang`, `timeout`: as a11y_reduced_motion.


#### `a11y_suggest_color`

<sub>read-only</sub>

Nearest opaque color (RGB distance) to fg that reaches the target ratio against bg (4.5 default). Returns the color, its ratio and whether it lightens or darkens. — The fixer companion to a11y_contrast_pair failures. Returns JSON: {color, ratio, action} — the nearest opaque color reaching the target.


**Arguments**

- `fg` *(required)*: The failing foreground color to fix.

- `bg` *(required)*: The background it must pass against.

- `target`: Ratio to reach: 4.5 normal text, 3.0 large text/UI, 7.0 AAA (default 4.5).


### Document


#### `a11y_generate_declaration`

<sub>mutates state</sub>

Generates an Accessibility Statement in HTML: art. 10 RD 1112/2018 (Spanish public sector, marco="rd1112") or European Accessibility Act wording (Directive (EU) 2019/882 / Ley 11/2023, marco="eaa"; EN output uses Directive (EU) 2016/2102 / EAA wording). Every statement carries the EN 301 549 status note: v4.1.1 (September 2026) adopts WCAG 2.2 as the benchmark and adds the EAA mapping, but is not yet cited in the Official Journal — presumption of conformity stays with the already cited version (v3.2.1, WCAG 2.1 AA) until that citation. The generated document is itself accessible. Saves to output_path when given. — Legal statement generator; drive inaccessible_content from audit findings and a11y_evidence. Returns {html, summary} — the accessible legal statement; writes a file only when output_path is given.


**Arguments**

- `entity` *(required)*: Legal entity name as it should appear in the statement (company, body…).

- `url` *(required)*: Website URL the statement covers.

- `status` *(required)* — one of ['full', 'partial', 'not_conformant']: Compliance state (partial is the honest default when findings exist). The pre-5.11 values plena | parcial | no_conforme still work as aliases.

- `inaccessible_content`: Non-accessible content list: one string per item, ideally criterion + reason + alternative.

- `method`: How conformance was evaluated (e.g. "self-evaluation: a11y-toolkit screening + manual review").

- `evaluation_date`: ISO date of the last evaluation (YYYY-MM-DD).

- `review_date`: ISO date of the next scheduled review.

- `feedback`: Contact channel for accessibility feedback (email or URL).

- `complaints`: Claim/complaint procedure URL or address (legally required in several jurisdictions).

- `framework` — one of ['rd1112', 'eaa']: Legal framework: rd1112 (Spanish public sector, art. 10) or eaa (European Accessibility Act / private sector).

- `alternative_format`: Where to get the content in an alternative accessible format.

- `output_path`: save the HTML here (optional).

- `lang` — one of ['es', 'en']: Statement language (default en; es uses the Spanish legal wording).


#### `a11y_generate_vpat`

<sub>mutates state</sub>

Generates a VPAT 2.5 (WCAG edition) accessibility conformance report in accessible HTML from an a11y_evidence pack (or raw audit reports): the full 55-criterion WCAG 2.2 A/AA table with Remarks auto-filled from the pack (status, measured values, examples, remaining human effort) and every Conformance Level starting at Not Evaluated — automated fails force Does Not Support and a qualified human sets the final level via overrides (supports, partially_supports, does_not_support, not_applicable, not_evaluated). The document is a DRAFT until the signature block, which must reference the pack sha256, is completed. VPAT is the US/ADA counterpart of a11y_generate_declaration (EU/EAA): the machine fills Remarks, the human signs the claim. — The US/ADA counterpart of a11y_generate_declaration; feed it the a11y_evidence pack — levels stay Not Evaluated until a qualified human sets them. Returns {html, summary {level: count}, levels {code: level}, pack_sha256, draft} — the VPAT draft; writes a file only when output_path is given. Run after the audits you trust; a qualified human must set the final levels (overrides) and sign before publishing — the machine fills Remarks, never the claim.


**Arguments**

- `product` *(required)*: Product name as it must appear in the VPAT title and header.

- `pack`: a11y_evidence output (evidence pack); alternative to reports.

- `reports`: Audit report objects to bundle (when pack is not given, the pack is built here first).

- `report_date`: VPAT report date ISO (default: today).

- `product_description`: Product description paragraph.

- `contact`: Contact information for questions about this VPAT.

- `methods`: Evaluation methods used (default: honest automated-screening note).

- `notes`: Additional notes to include.

- `overrides`: Criterion → conformance level set by a qualified human: {"1.1.1": "supports", "1.2.2": "not_applicable", …}.

- `reviewer`: {"name":…, "credential":…, "review_date":…} to prefill the signature block.

- `output_path`: Local path to save the VPAT HTML (omit to receive it inline).

- `lang` — one of ['es', 'en']: Document language (default en).


#### `a11y_badge`

<sub>read-only</sub>

Returns an HONEST accessibility badge as accessible SVG: score, date and scope (automated screening ≈ 1/3 of WCAG), color-coded by score. Deliberately does NOT say "conformant" — the honest seal. Embed it in audited sites or statements. — Scope: the honest SVG seal for audited sites; the machine-readable bundle is a11y_evidence. Returns the honest SVG badge; writes a file only when output_path is given.


**Arguments**

- `score` *(required)*: 0-100 (from an audit result).

- `fecha`: ISO date (today by default).

- `lang` — one of ['es', 'en']: Badge language (default en).


#### `a11y_criterion`

<sub>read-only</sub>

Explains a WCAG 2.2 success criterion in plain language (es/en): what it requires, typical failures, and how to verify it with this toolkit (which tool automates which part). Codes like "1.4.3", "2.5.8", "4.1.2". Give a finding SIGNAL instead (e.g. img_no_alt, kbd_trap — the id in every audit finding) and it resolves to its criterion AND its published ACT rule(s) with official w3.org links. Use it whenever you need to explain WHY a finding matters or what the criterion actually says. — Knowledge lookup; does not fetch or audit anything. Returns JSON: {criterion, level, understanding, toolkit_signals, requires, typical_failures, how_to_check} or, in signal mode, adds {signal, act_rules [{id, name, status, url}]}; {error, …} for unknown codes.


**Arguments**

- `code`: criterion number, e.g. 1.4.3 — or pass `signal` instead.

- `signal`: engine signal id from any finding (e.g. `kbd_trap`): resolves its criterion and its published ACT rule(s) with w3.org links (proposed rules are labeled as such).

- `lang` — one of ['es', 'en']: Explanation language (default en).


### Watch (regressions)


#### `a11y_snapshot`

<sub>read-only · network</sub>

Accessibility snapshot of a URL: interactive elements (tag, role, accessible name, href) in DOM order, the REAL tab focus order, and when Playwright ≥1.49 is available the computed ACCESSIBILITY TREE (aria snapshot — what a screen reader announces). Save it before a deploy and compare after with a11y_diff. Requires local Playwright. — Capture half of the watch loop; compare with a11y_diff (or a11y_diff_urls for two live URLs). Returns JSON: {url, ts, elements [{tag, role, name, ref…}], focus_order}.


**Arguments**

- `url` *(required)*: Page URL to snapshot (http/https or file://).

- `auth_state`: Path to a Playwright storage_state JSON (exported session) to snapshot behind login.


#### `a11y_diff`

<sub>read-only</sub>

Regression diff between two accessibility snapshots (before/after a deploy): added/removed/renamed interactives and focus-order changes. ok=false means a regression to review. Accepts inline JSON (starting with "{") or file paths. — Compares two existing snapshots; a11y_diff_urls snapshots both for you. Returns JSON: {ok, added, removed, renamed, focus_order_changed, first_differences} — ok:false means a regression to review.


**Arguments**

- `a` *(required)*: BEFORE snapshot (inline JSON or path).

- `b` *(required)*: AFTER snapshot (inline JSON or path).


#### `a11y_diff_urls`

<sub>read-only · network</sub>

Snapshot two URLs and diff them in a single call (e.g. staging vs production). Requires local Playwright. — Convenience for staging-vs-production; manual control is snapshot + a11y_diff. Returns the same diff shape as a11y_diff, for two live URLs.


**Arguments**

- `url_a` *(required)*: First URL (usually staging).

- `url_b` *(required)*: Second URL (usually production).


#### `a11y_aria_live_snippet`

<sub>read-only</sub>

Returns injectable JavaScript for an aria-live announcement monitor (bookmarklet or page.evaluate): logs every dynamic-region announcement with time, politeness, role and text — what a screen reader would say, visible on screen. — Diagnostics aid to inject in a browser; not an audit by itself. Returns the injectable JavaScript as text (bookmarklet or page.evaluate).


**Arguments**

- `lang` — one of ['es', 'en']: monitor panel language (en default).


### Hand off (evidence)


#### `a11y_evidence`

<sub>read-only</sub>

Builds the verifiable evidence pack: the machine→human handoff object for WCAG conformance work. Takes one or more audit reports (any mode — static, rendered, reflow, keyboard, scroll) and returns: the full 55-criterion A/AA matrix (automated-fail / automated-review / not-flagged — NOT pass / not-run / manual-only), each row priced with its human-effort class (MIN 1-3 / MED 5-10 / MAX 15-30 min of human review remaining) and total remaining minutes (the quote input for a review marketplace), every artifact SHA-256-hashed with timestamps, an empty signature block (name, credential, date) whose statement must reference the pack's own sha256, and the tamper-evidence rule stated. Vendor-neutral: any qualified human can review it. Evidence, never conformance. — The tier-3 handoff object; feed it every audit report you have. Returns the pack JSON (a11y-evidence-pack/2); writes a file only when output_path is given. Run after the audits you trust, and pass verified codes from the manual checklist — agent-verified never erases an automated-fail.


**Arguments**

- `reports` *(required)*: audit report objects (any mode).

- `snapshot`: a11y_snapshot output (optional).

- `reviewer`: {"name":…, "credential":…, "review_date":…} to prefill the signature block.

- `verified`: Criterion codes an agent/human verified against this sample (manual checklist protocol) — they become agent-verified in the matrix; automated-fail stays fail.


#### `a11y_disprove`

<sub>read-only · network</sub>

Disprover pattern (from Cloudflare's security-audit-skill): re-runs the audit against the live page and marks each finding confirmed or rejected — findings that don't reproduce are rejected with the reason. Catches false positives, race conditions, and page changes between audit and report. Returns a fresh score over confirmed findings only. — Run this before acting on any audit report. Returns JSON: {confirmed, rejected, score} — a fresh score over confirmed findings only.


**Arguments**

- `url` *(required)*: URL to re-verify against.

- `report`: existing audit report (optional; if absent, audits first).

- `lang` — one of ['es', 'en']: Output language (en default).

- `timeout`: Timeout seconds (30 default).


#### `a11y_ledger`

<sub>mutates state · not idempotent</sub>

Coverage ledger (from Cloudflare's security-audit-skill): persistent record of what has been audited, when, and with what result. Actions: record (add audit result), gaps (what has never been checked on a URL), summary (portfolio overview). Accumulates across runs — second audits show resolved findings. record returns the stored entry; gaps returns criteria never checked; summary returns {entries, active_signals, resolved, mean_score}. record after every audit run; gaps before planning the next pass. The ledger file accumulates across runs — give each project its own ledger_path.


**Arguments**

- `action` *(required)* — one of ['record', 'gaps', 'summary']: What to do.

- `url`: URL (for record/gaps).

- `report`: audit report object (for record).

- `ledger_path`: ledger file path (default: a11y-ledger.json).

#### `a11y_wcag3_preview`

<sub>read-only</sub>

WCAG 3 demo — the view layer nobody ships: takes an audit report and re-groups its WCAG 2.2 findings under the outcomes of the WCAG 3 Working Draft (10 September 2026). Informative only: WCAG 3 is not a completed standard, the W3C has published no official WCAG 2 to WCAG 3 mapping (this one is curated and labeled as such), and NO score, tier or conformance claim is produced — the draft's tier thresholds are still TBD. Use it to show teams where today's 2.2 findings will land tomorrow; keep auditing against WCAG 2.2. Returns JSON: {mode, draft, disclaimer, mapping_note, no_score, conformance_model, outcomes [{outcome, draft_url, findings, severity, signals, criteria_22}], counts, unmapped} — never a score. Run after any audit when the team asks "what about WCAG 3?"; re-baseline on each W3C draft publication (roughly March/September).


**Arguments**

- `report` *(required)*: audit report object with a findings list (from a11y_audit_url, a11y_audit_dom, a11y_disprove, …).

- `lang` — one of ['es', 'en']: Output language (en default).


### The 6 prompts

- **`audit-page`** (`url*`, `language`): Full accessibility audit workflow for a URL: automated tools + what to verify manually (keyboard, screen reader, zoom). Every prompt exists in English and Spanish.

- **`fix-contrast`** (`fg*`, `bg*`, `context`): Guided contrast fix: verify the pair (or the text-over-image region), get the nearest passing color, apply it to the code. Every prompt exists in English and Spanish.

- **`pre-deploy-check`** (`url*`, `baseline`): Pre-deploy regression check: express audit of the URL plus snapshot diff against a baseline snapshot. Every prompt exists in English and Spanish.

- **`declaration-eaa`** (`entity*`, `url*`, `status`): Generate a European Accessibility Act / RD 1112/2018 accessibility statement, collecting any missing legal fields from the user. Every prompt exists in English and Spanish.

- **`conformance-wcagem`** (`url*`, `tier`, `language`): Guided WCAG-EM conformance ladder for a site: express screening → agent-verified guided evaluation on a representative sample → conformance report inputs. Every prompt exists in English and Spanish.

- **`blindfold-task`** (`url*`, `goal*`, `kind`, `language`): Blindfold usability test — the agent attempts a real task perceiving ONLY the accessibility tree and acting only by accessible name and keyboard, logging friction per step; closes with a11y_journey_verdict. The capability no other accessibility tool has: task-based non-visual testing where the agent IS the screen-reader user. Every prompt exists in English and Spanish.


## Install

> mcp-name: io.github.kinti/a11y-toolkit · PyPI: [a11y-toolkit](https://pypi.org/project/a11y-toolkit/) · Zenodo DOI: `10.5281/zenodo.22843722`

Works with **any MCP-capable client** — Claude Code/Desktop, Cursor, Windsurf, VS Code,
Codex CLI, OpenCode, ZCode, Zed, Cline, Continue, Kimi Code… See
[docs/clients.md](docs/clients.md) for every verified config format.

```bash
claude mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp
```

Or with JSON config:

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "uvx",
      "args": ["--from", "a11y-toolkit", "a11y-toolkit-mcp"],
      "timeoutMs": 60000
    }
  }
}
```

Rendered tools use Playwright **if present** and accept a `browser` parameter
(`auto`, `chromium`, `firefox`, `webkit`, `chrome`, `msedge` — auto-detects the first
available). Accept `auth_state` (Playwright storage_state path) to audit behind login.
Everything else works with zero dependencies.

### The skill

```bash
git clone https://github.com/kinti/a11y-toolkit && cd a11y-toolkit
./skill/install-skill.sh     # → ~/.zcode/skills and ~/.claude/skills
```

## Agent hook — `a11ytoolkit init`

Agents that read `AGENTS.md` on their own get the
rule that matters — *after any UI change, re-audit before calling the work
done* — with the exact commands:

```bash
cd your-project
uvx --from a11y-toolkit a11ytoolkit init     # writes/merges the AGENTS.md hook (idempotent)
```

It also prints the MCP config block and the optional skill install step.
`--check` reports whether the hook is present (exit 1 if not — CI-friendly).

## Languages — community locale packs

All user-facing messages (findings, remediations, legal wording) live in
[locale packs](a11y_toolkit/locales/) — one JSON per language, `es` and `en`
ship today. **Adding a language is a single-file PR**: copy
[`_template.json`](a11y_toolkit/locales/_template.json), translate keeping the
`{placeholders}`, and `python3 tests/test_locales.py` validates it mechanically
(keys, placeholders, plural rule, completeness). Same community model as
axe-core's locales — with validation axe-core doesn't have. Guide:
[docs/i18n.md](docs/i18n.md). Downstream products can layer brand wording via
overlays without forking.

## CLI — same engine, one command

```bash
a11ytoolkit audit --changed                     # ONLY what changed since HEAD (CI gate)
a11ytoolkit audit --changed --base origin/main  # a branch's changes — exit 2 on high/medium
a11ytoolkit audit --url https://example.com --pages 5   # sitemap-first crawl
a11ytoolkit pair "#1f2328" "#fbfaf7"                    # contrast
a11ytoolkit image hero.jpg --text "#fff" --region 120,40,420,90
a11ytoolkit forms https://mysite/contact                # form errors
a11ytoolkit kbd https://mysite                          # keyboard traps + 3.2.1/3.2.2
a11ytoolkit reflow https://mysite                       # 320px reflow
a11ytoolkit scroll https://medium.com/feed              # infinite scroll
a11ytoolkit validate --url https://example.com          # W3C Nu
a11ytoolkit hover https://mysite                        # tooltip dismissibility
a11ytoolkit fix --file page.html -o fixed.html          # safe autofix
a11ytoolkit declaration --entity "Acme" --url https://… --status partial --framework eaa
a11ytoolkit snapshot https://mysite --out before.json   # before deploy
a11ytoolkit diff before.json after.json                 # after deploy
a11ytoolkit evidence audit.json -o pack.json            # verifiable evidence pack
a11ytoolkit disprove --url https://mysite               # re-verify findings
a11ytoolkit budget --budget budget.json --audit audit.json  # only NEW findings block
a11ytoolkit sarif --from-audit audit.json -o a11y.sarif # GitHub code scanning
a11ytoolkit badge --score 92 --out badge.svg            # honest SVG
a11ytoolkit contrast-dom https://mysite --selector ".hero h1"  # auto-region pixel sampling
a11ytoolkit vpat pack.json --product "Acme" -o vpat.html      # VPAT 2.5 (WCAG) draft
a11ytoolkit earl --from-audit audit.json -o earl.json          # ACT Rules / EARL export
a11ytoolkit wcag3 --from-audit audit.json                      # WCAG 3 draft preview (no score)
```

## Coverage: 51 of 55 WCAG 2.2 A/AA criteria (93%)

| With automated signal | Manual-only (genuinely human) |
|---|---|
| 1.1.1, 1.2.2, 1.2.3, 1.2.5, 1.3.1–1.3.5, 1.4.1–1.4.5, 1.4.10–1.4.13, 2.1.1, 2.1.2, 2.1.4, 2.2.1, 2.2.2, 2.4.1–2.4.7, 2.4.11, 2.5.1–2.5.4, 2.5.7, 2.5.8, 3.1.1, 3.1.2, 3.2.1–3.2.4, 3.2.6, 3.3.1–3.3.4, 3.3.8, 4.1.2, 4.1.3 | 1.2.1 (audio transcripts), 1.2.4 (live captions), 2.3.1 (flash detection), 3.3.7 (redundant entry) |

The 4 manual-only criteria each have a knowledge entry (`a11y_criterion`) telling the
agent exactly how to verify them by hand. The boundary is printed on every report.

## a11y.es — the engine in production

**[a11y.es](https://a11y.es)** runs this engine in production: continuous WCAG 2.2
monitoring with hash-verifiable evidence packs and human-signed reports, in Spanish,
built for the European Accessibility Act / RD 1112/2012 market. Every report ends at
the exact boundary where a qualified human begins — that boundary is the product.

## Validated against real pages

Benchmarked against axe-core 4.10 on real pages monthly ([methodology and
results](bench/README.md)). Found a real WCAG failure on gov.uk that axe does not
report (blue button at 3.91:1, manually verified). Drove out our own false positives
(hidden skip links, honeypot fields, single-context generic links, image-alt accname
— each with a regression fixture).

## Why I built this

I have been auditing websites for accessibility since 2003. In twenty years the
tools got faster and the failures stayed the same: the same missing alt text, the
same keyboard traps, the same forms that swallow your work. When AI agents started
writing most of the web, the audit gap stopped being a staffing problem and became
an infrastructure one.

So I built the tool I always wanted next to me on an audit. Not another scanner —
scanners exist. A toolkit that does half the work, says exactly where it stops, and
packages the rest for the person who signs. The gov.uk failure you read about above
is not a synthetic benchmark case: this engine found it, and I confirmed it with my
own eyes before writing it down.

If it saves you an afternoon, leave a star — it genuinely helps the next auditor
find it. If it doesn't, open an issue and tell me what is missing.

## Honesty, built in

Every audit says: **automation covers 93% of A/AA criteria; the rest needs a human**.
The `audit-page` prompt and the skill have the agent check what it can (keyboard,
focus, zoom, announced errors) using [the manual
checklist](skill/a11y-toolkit/references/wcag22-manual-checklist.md). A filter, not
a verdict. The remaining human work is priced per criterion — MIN 23 (read and
confirm), MED 19 (verify in the browser), MAX 13 (real interaction and judgment);
[full table](docs/effort-class-table.md). And the evidence pack is the handoff object
for the person who signs, screen reader transcript included, so the reviewer sees
what a blind user hears.

## Security & scope

A **local** tool: runs on your machine as your user. `a11y_audit_url` accepts
http/https only (no `file://` — use `--file`/`html` for local HTML). `a11y_html_validate`
in html mode POSTs content to the W3C service (url mode shares only the URL;
self-hosted vnu supported). `path`/`output_path` read/write local paths — use it in
MCP clients you trust.

## Development

```bash
python3 tests/test_contrast.py && python3 tests/test_audit.py && python3 tests/test_v32.py \
  && python3 tests/test_dom.py && python3 tests/test_cli.py && python3 tests/test_solido.py \
  && python3 tests/test_mcp.py && python3 tests/test_png.py && python3 tests/test_vpat.py \
  && python3 tests/test_act.py
```

`tests/test_dom.py` self-skips without Playwright. `tests/test_solido.py` enforces the design
invariants (catalog parity, version alignment, count coverage, hostile-HTML fuzz).
Releases: `make release V=X.Y.Z` — bumps, gates, tags and pushes atomically.

## Roadmap

Done recently: rendered audit with shadow DOM and state contrast, form error
testing plus autofix, keyboard traps, infinite scroll, reflow, the W3C Nu
integration, SARIF and error budgets, the evidence pack (spec published,
self-verifying), sitemap crawling, behind-login auditing, browser
auto-detection, the screen reader transcript, and per-criterion effort
pricing. The full history lives in the [changelog](CHANGELOG.md).

Next, roughly in this order:

- [ ] Attestation interlock: let an external auditor's signature reference the evidence pack by hash (their schema, my side adapts)
- [ ] Publish the monthly axe-core benchmark results from CI, run over real pages
- [ ] Screen-reader transcript cross-checks against NVDA and VoiceOver output
- [ ] More verified client configs (JetBrains AI, Gemini CLI), same treatment as [docs/clients.md](docs/clients.md)

## Author

**Jesús Quintana Fernández** ([jquin.net](https://jquin.net/)) — SEO/GEO consultant and
web-accessibility practitioner since 2003. MIT © 2026.
