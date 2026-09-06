# Changelog

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
