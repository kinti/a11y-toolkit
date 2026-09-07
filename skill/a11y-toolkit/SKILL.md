---
name: a11y-toolkit
description: Use for ALL accessibility work — WCAG 2.2 audits of URLs or HTML, real rendered contrast checks (including text over images, pixel-level), color-pair contrast and nearest passing color, European Accessibility Act / RD 1112/2018 accessibility statements, pre-deploy regression detection (accessible names, tab order), aria-live announcement monitoring, keyboard/focus review. Triggers on "accessibility", "a11y", "WCAG", "contrast", "screen reader", "accesibilidad", "contraste", "auditoría", "EAA", "declaration", "declaración", "target size", "focus order", "aria".
---

# Skill: A11Y Toolkit — the WCAG 2.2 loop for agents

Audit → fix → document → watch, with zero-dependency tools. Prefer the MCP tools
(`a11y_*`) when the a11y-toolkit MCP server is connected; otherwise run the same
engine via `uvx` — no clone, no venv:

```bash
uvx --from a11y-toolkit a11y pair "#1f2328" "#fbfaf7"          # color pair
uvx --from a11y-toolkit a11y audit --url https://example.com   # static audit
uvx --from a11y-toolkit a11y image hero.jpg --text "#fff" --region 120,40,420,90
uvx --from a11y-toolkit a11y declaration --entidad "Acme" --url https://acme.example --estado parcial --marco eaa --lang en --output decl.html
```

All output is es/en (pass `--lang en` or the `lang` MCP argument; default es).

## Decide in one step

| The user asks about… | Use |
|---|---|
| "is this site/page accessible?" | `a11y_audit_url` (fast, static, 0-100 score) then `a11y_audit_dom` if Playwright exists |
| real text contrast, incl. over images/gradients | `a11y_contrast_pair` / `a11y_contrast_image` / `a11y_audit_dom` |
| "what color passes AA here?" | `a11y_suggest_color` (target 4.5 normal, 3.0 large/UI) |
| legal accessibility statement (EU/Spain) | `a11y_generate_declaration` |
| "did the deploy break a11y?" | `a11y_snapshot` + `a11y_diff` (or `a11y_diff_urls`) |
| "what does the screen reader hear?" | `a11y_aria_live_snippet` injected via Playwright + the snapshot's focus order |
| keyboard/zoom/manual items | do them yourself as the agent — checklist in `references/wcag22-manual-checklist.md` |
| "what does criterion X.Y.Z mean?" | `a11y_criterion` (code like `1.4.3`, `2.5.8`) |
| "watch the site / only NEW regressions should block" | `a11y budget`: accept the baseline once, then only new blocking findings fail (exit 2). Recipe: `examples/a11y-watch.yml` (weekly GitHub Action) |
| "put these findings in the PR / code scanning" | `a11y sarif --from-audit audit.json -o a11y.sarif` → upload with github/codeql-action/upload-sarif |
| "a badge for the audited site" | `a11y_badge` (score + date + "automated screening" scope — never claims conformance) |
| "audit the section, not just one page" | `pages` parameter (or `a11y audit --pages N`): light same-domain crawl, aggregated by mean/worst score |
| "full evaluation / conformance / WCAG-EM" | the `conformance-wcagem` prompt — three tiers, escalate one at a time; protocol in `references/wcagem-guide.md` |

## 1. Audit

`a11y_audit_url` = express static pass: 20+ signals across 17 WCAG criteria with a
weighted **0-100 score** (alt, accessible names, labels, autocomplete 1.3.5, keyboard
onclick, unknown ARIA roles, broken aria-labelledby, unnamed duplicated landmarks,
meta refresh, skip mechanism, lang validity, title, headings, zoom, captions, autoplay,
generic/duplicated link text, tabindex, aria-hidden-on-focusable, tables, duplicate ids,
accesskeys). Each finding carries a concrete `remediacion`. **Always relay finding +
remediation + WCAG criterion to the user, grouped by severity; quote the score with the
score_nota caveat.** When you need to explain a criterion, call `a11y_criterion`.

`a11y_audit_dom` = rendered audit in Chromium: computed text contrast against
effective backgrounds with alpha compositing (1.4.3), 24×24 minimum target size
(2.5.8 — new in WCAG 2.2), visible focus indicator heuristic (2.4.7),
**:focus/:hover state contrast** (disabled controls are WCAG-exempt — say so),
and **same-origin iframes scanned too**, same 0-100 score. If Playwright is
missing, fall back to the static audit and say so.

`a11y_audit_url` also accepts raw HTML you already fetched (`html` argument) —
audit without re-fetching.

**Honesty rule (non-negotiable):** automation ≈ 1/3 of WCAG. Every audit report
must say so and then cover what you CAN check manually as the agent — that is
what separates a real audit from a lint run. Use the manual checklist.

## 2. Fix contrast

Colors accept `#hex`, `rgb()`, `hsl()`, CSS color names; alpha composites over
the background. The pair tool returns per-criterion verdicts (1.4.3 AA, 1.4.6
AAA, 1.4.11 non-text) and the nearest passing color. Apply the suggestion to the
source, then re-verify the pair. For text over an image, NEVER trust a pair
check against a guessed color: screenshot the region and use `a11y_contrast_image`
— if `area_pasa_aa_texto_normal_4_5` < 100%, you need a scrim, a crop, or to move
the text (`zona_peor` tells you where).

## 3. Document (EU law)

`a11y_generate_declaration`: `marco="eaa"` for the European Accessibility Act /
Ley 11/2023 (private sector), `marco="rd1112"` for art. 10 RD 1112/2018 (Spanish
public sector). Collect missing legal fields (feedback contact, claim procedure,
evaluation method/dates) before generating; derive `contenido_no_accesible` from
audit findings. The statement must be linked from every page.

## 4. Watch regressions

Before deploy: `a11y_snapshot` (also captures the computed accessibility tree) → save
JSON. After: snapshot again, `a11y_diff` (now also reports accessibility-tree changes).
For continuous watching, set up the error budget: `a11y budget --init` from today's
audit, then every run only flags NEW blocking signals — recommend it for every client.
`ok: false` = interactives added/removed/renamed or focus-order changed. Elements
without `id` are matched by tag+name+href — recommend stable ids for fine-grained
diffs. This is a great pre-deploy gate: audit + diff, then GO/NO-GO.

## 5. The aria-live monitor (arialive.js)

Inject via `page.evaluate` (Playwright) or as a bookmarklet; `lang` argument or
`window.ALM_LANG='en'` localizes the panel. It logs every live-region
announcement with time, politeness, role, text.

**Bug already fixed — do not reintroduce:** the panel must NOT carry `role="log"`
and must exclude itself from the MutationObserver; a `role="log"` panel matches
its own selector and creates an infinite self-observation loop that hangs the
page. If a run hangs, look for orphan chromium processes and retry.

## Notes

- Images: Pillow if present, else macOS `sips`; PPM always — zero deps otherwise.
- The math is identical to the public web version: https://jquin.net/lab/
- Canonical source + MCP install: https://github.com/kinti/a11y-toolkit
- Test suites: `test_audit.py`, `test_contrast.py`, `test_dom.py`, `test_mcp.py`.
