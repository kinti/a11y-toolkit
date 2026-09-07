# Changelog

## 3.3.2 — 2026-09-07 — "one number everywhere"

- Docs homogeneity pass: 12 tools + 5 prompts stated consistently (README table
  title said "(10)", prompts line missed `conformance-wcagem`, server docstring
  missed the two newest tools). No functional changes.

## 3.3.1 — 2026-09-07 — "registry-ready"

- PyPI README now carries the `mcp-name: io.github.kinti/a11y-toolkit` ownership
  marker required by the official MCP Registry, plus a direct PyPI link.
- All version strings aligned (server.json, pyproject, server.VERSION).
- No functional changes.

## 3.3.0 — 2026-09-07 — "close the axe gap, open the ladder"

- **Same-origin iframes in the rendered audit**: the collector runs inside
  same-origin frames (up to 4) and merges findings with an `iframe:` prefix;
  cross-origin frames are skipped (impossible locally, honestly noted).
- **:focus/:hover state contrast** (1.4.3): real hover via Playwright on
  marked controls + computed focus-state contrast; disabled controls reported
  as exempt, per WCAG.
- **ARIA value validation** (static, 4.1.2): boolean tokens, integer/numeric
  attributes, closed token lists (aria-sort, aria-current, aria-live…), and
  aria-controls/aria-errormessage references checked against existing ids.
- **`conformance-wcagem` prompt (5th)** + skill reference `wcagem-guide.md`:
  the three-tier ladder — express screening → agent-verified guided evaluation
  on a WCAG-EM sample → conformance report with a human certifying. The
  automated/gentle bridge from free lint to paid consulting.
- 12 MCP tools + 5 prompts. Version strings everywhere.

## 3.2.0 — 2026-09-07 — "the roadmap: guardrails"

The distribution loop, closed: findings travel in standard formats, progress is
visible, and regressions — not history — are what block you.

- **SARIF 2.1.0 export** (`a11y sarif`, new module `a11ysarif.py`): findings in
  the OASIS standard GitHub accepts for code scanning — per-criterion rules
  with official WCAG Understanding helpUris, severity mapped error/warning/note.
  In PRs, only NEW alerts surface.
- **Accessibility error budget** (`a11y budget`, new module `a11ybudget.py`):
  accept today's baseline; only NEW blocking findings fail the check (exit 2).
  Baseline expiry (fecha_revision) forces periodic re-acceptance. The SRE error
  budget, for WCAG — kills the "40 findings, nobody starts" paralysis.
- **Honest badge** (`a11y_badge` MCP tool + `a11y badge` CLI, new module
  `a11ybadge.py`): accessible SVG with score, date and "automated screening"
  scope — it never says "conformant" (the accessiBe/FTC lesson).
- **Multi-page crawl** (`pages` parameter / `a11y audit --pages N`): light
  same-domain discovery by links, aggregated by mean/worst score and recurring
  signals. Max 20 pages, zero dependencies.
- **Stable signal keys** (`senal`) on every finding — the join key budgets and
  SARIF rules are built on.
- **Scheduled surveillance recipe**: `examples/a11y-watch.yml` — weekly GitHub
  Action: crawl audit → budget gate → SARIF upload → badge.
- 12 MCP tools + 4 prompts. New suite: `test_v32.py`.

## 3.1.0 — 2026-09-07 — "cover the gaps"

Competitive gap analysis (axe-core/Lighthouse, WAVE, Playwright MCP, wcag-mcp) →
everything they do that agents need, we now do too — plus what only we do.

- **Weighted 0-100 score** in both audits (high −12 / medium −6 / low −2),
  with an honest scope note. The Lighthouse adoption hook, on a fuller rule set.
- **ARIA validity** (axe-core core): unknown roles, broken aria-labelledby /
  aria-describedby references, role-mandated state missing (slider without
  aria-valuenow).
- **1.3.5 Identify Input Purpose**: user-data fields without autocomplete.
- **2.4.4 Link Purpose**: generic link texts ("more", "aquí"…) and same-name
  links to different destinations (the WAVE complaint).
- **1.4.2 Audio Control**: autoplay media. **Duplicate accesskeys**,
  multiple labels on one field, duplicated unnamed landmarks.
- **New tool `a11y_criterion`** (11th): plain-language explanation of any
  criterion — what it requires, typical failures, which tool verifies it.
  Covers the wcag-mcp knowledge gap, wired to the auditor's own criteria.
- **a11y_snapshot now captures the computed accessibility tree** (Playwright
  ariaSnapshot — what a screen reader announces) and a11y_diff reports
  tree changes. The Playwright-MCP gap.
- 11 MCP tools + 4 prompts. CLI gains `a11y criterion`. All suites updated.

## 3.0.0 — 2026-09-07 — "global readiness"

The accessibility layer for AI coding agents: audit → fix → document → watch.

- **New tool `a11y_audit_dom` — rendered audit** via local Playwright/Chromium:
  real computed text contrast against effective backgrounds with alpha
  compositing (1.4.3), minimum target size 24×24 (**2.5.8, new in WCAG 2.2**),
  visible focus-indicator heuristic (2.4.7), and the static checks on the live
  DOM. Same report shape as the static audit.
- **Static auditor 10 → 13 criteria**, every finding now includes a concrete
  `remediacion`: keyboard onclick on non-interactive elements (2.1.1), timed
  meta refresh (2.2.1), missing skip mechanism/main landmark (2.4.1), invalid
  BCP-47 lang, captions on video (1.2.2), tables without th (1.3.1),
  target=_blank without warning (3.2.5), empty headings, orphan labels, input
  type=image without alt, duplicate ids; select/textarea now audited for
  labels (they were not before).
- **`a11y_audit_url` accepts raw HTML** (`html` argument) — audit pages you
  already fetched; also `timeout`, gzip responses, non-HTML rejection,
  en/es output.
- **Contrast engine upgraded**: 148 CSS color names, `hsl()/hsla()`,
  `rgba()`/`#rrggbbaa` with alpha compositing, modern space-separated syntax
  (`rgb(255 0 0)`); color suggestions now minimize real RGB distance
  (400-step search).
- **4 MCP prompts**: `audit-page`, `fix-contrast`, `pre-deploy-check`,
  `declaration-eaa` (slash-commands in supporting clients).
- **English-first tool descriptions** and server `instructions` — what agents
  worldwide read; es/en still selectable per call.
- **Distribution**: PyPI-ready packaging (embedded `arialive_js` module — fixes
  data-files install location), official MCP Registry `server.json`, PyPI
  publish workflow (trusted publishing), CI adds package smoke test + build,
  new console script `a11y-audit`.
- **Skill rewritten** (standalone, EN-first, decision table + manual WCAG 2.2
  checklist reference) and bundled at `skill/` with an installer; works with or
  without the MCP via `uvx`.
- README rewritten EN-first with per-client install (Claude Code/Desktop,
  Cursor, Windsurf, VS Code) and an honest comparison vs axe/Lighthouse.
- 10 MCP tools + 4 prompts. Test suites: contrast, audit, dom (self-skipping),
  mcp.

## 2.3.0 — 2026-08-22
- **The toolkit is now ONE toolkit**: a11ydiff integrated into the MCP as `a11y_snapshot`,
  `a11y_diff` (inline JSON or file paths) and `a11y_diff_urls` (staging vs prod in one call).
- **Unified CLI `a11y`**: one command for everything — `a11y pair`, `a11y image`,
  `a11y audit`, `a11y declaration`, `a11y snapshot`, `a11y diff`.
- 9 MCP tools total. No new capabilities — pure integration of the existing four modules.

## 2.2.0 — 2026-08-22
- **New tool `a11y_audit_url`**: express WCAG audit of any URL (alt, accessible names,
  form labels, lang/title, heading skips, blocked zoom, tabindex>0, iframe titles),
  zero dependencies, with severity-ranked findings and honest scope note.
- **contrast image**: automatic hostile-zone detection (`zona_peor`, 3×3 grid) and
  auto-sampling guard for huge regions.
- Auditor hardening: names from inner text (incl. links inside headings), implicit
  `<label>` wrapping and explicit `for=` associations recognized.
- Tests: audit fixtures + grid test; CI runs the three suites.

## 2.1.0 — 2026-08-22
- Multilanguage es/en across all tools; EN declarations use Directive (EU) 2016/2102
  and EAA (2019/882) wording; aria-live monitor UI localized (window.ALM_LANG).

## 2.0.0 — 2026-08-22
- First public release: 5 MCP tools (contrast pair/image, suggest color, declaration
  generator, aria-live snippet) + a11ydiff CLI. Zero-dependency stdio server.
