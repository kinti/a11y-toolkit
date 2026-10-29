# a11y-toolkit — the accessibility layer for AI coding agents

> WCAG 2.2 for your coding agent — audit, fix, document and watch. Zero dependencies, es/en.

[![CI](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![Downloads](https://img.shields.io/pypi/dm/a11y-toolkit)](https://pypistats.org/packages/a11y-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-server-purple)](https://modelcontextprotocol.io)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink)](https://github.com/sponsors/kinti)

33 MCP tools, 6 prompts and a skill covering the whole WCAG 2.2 loop: audit, fix,
document, watch, hand off — and now blindfold usability testing, where the agent
attempts real tasks perceiving only what a screen reader exposes. 51 of 55 A/AA criteria carry automated signals (93%), every
finding ships with a concrete remediation your agent can apply, and the rendered tools
run on whichever browser you have — Chromium, Firefox, WebKit, Chrome or Edge.

The European Accessibility Act is in force since June 2025, ADA suits keep landing,
and AI agents now write most of the web. A scan is not a defence: the machine finds,
the human signs.

<p align="center">
  <img src="docs/demo.gif" alt="a11y-toolkit in action: audit (score 64), nearest passing color, re-audit (94) — real tool output" width="720">
</p>

## Quickstart

```bash
# MCP — one line, any MCP client (Claude, Cursor, Codex, Windsurf, …)
claude mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp

# CLI — same engine, one command
pip install a11y-toolkit
a11ytoolkit audit --url https://example.com
a11ytoolkit pair "#1f2328" "#fbfaf7"
```

Static audits, contrast math, PDF/DOCX screening and the evidence pack run with
**zero dependencies**. The rendered tools (real contrast over images, keyboard
traps, reflow, forms) additionally need Playwright:
`pip install playwright && playwright install chromium`.

## Features

| Capability | axe-core / Lighthouse / pa11y | a11y-toolkit |
|---|---|---|
| Text contrast over images and gradients (pixel sampling of the real background) | No | Yes |
| VPAT 2.5 (WCAG) draft from the evidence pack — US/ADA counterpart of the EAA statement | No | Yes |
| Form error testing: fills invalid data, really submits, judges what happens | No | Yes |
| Keyboard traps: real Tab walk + Escape-release test, plus focus/input-triggered navigation | No | Yes |
| Infinite-scroll audit: focus survival, announcements, feed end | No | Yes |
| Reflow at 320px and the WCAG text-spacing override, measured | No | Yes |
| Screen reader transcript: what a blind user hears, linearized | No | Yes |
| Tooltips that ignore Escape caught by actually hovering (1.4.13) | No | Yes |
| Legal statements for the EAA / RD 1112/2018, in Spanish and English | No | Yes |
| An evidence pack a human can sign — hashes, matrix, empty signature block | No | Yes |
| ACT Rules interop: EARL export + per-rule consistency report against official W3C test cases | No | Yes |
| WCAG 3 draft preview — regroup 2.2 findings under the draft's outcomes, no fake score | No | Yes |
| The engine examines itself: seeded WCAG mutant bank — regenerable exam, kill rate + false positives via placebos | No | Yes |
| Sequential diagnosis: pass a URL and the page's own evidence orders the exams (severity only breaks ties) | No | Yes |
| Runs with zero dependencies at core, speaks es/en, any browser you have | Heavy runtimes | Zero dependencies |

<!-- TOOLS:BEGIN -->
## The tools (33)

Full reference — descriptions, arguments, return shapes and behavior — in [docs/tools.md](docs/tools.md). All tools accept `lang` (`en`|`es`) unless noted; output is JSON unless noted. Generated from `server.TOOLS` by `scripts/gen_readme.py`.

| Tool | Category | What it does |
|---|---|---|
| [`a11y_audit_url`](docs/tools.md#a11y_audit_url) | Audit | Express WCAG audit |
| [`a11y_audit_dom`](docs/tools.md#a11y_audit_dom) | Audit | Rendered WCAG audit |
| [`a11y_audit_pdf`](docs/tools.md#a11y_audit_pdf) | Audit | PDF accessibility screening |
| [`a11y_docx_screen`](docs/tools.md#a11y_docx_screen) | Audit | DOCX accessibility screening |
| [`a11y_journey_verdict`](docs/tools.md#a11y_journey_verdict) | Blindfold testing | Blindfold journey verdict |
| [`a11y_autofix`](docs/tools.md#a11y_autofix) | Fix & contrast | Deterministic safe auto-fixes |
| [`a11y_contrast_pair`](docs/tools.md#a11y_contrast_pair) | Fix & contrast | Contrast ratio + verdicts |
| [`a11y_contrast_image`](docs/tools.md#a11y_contrast_image) | Fix & contrast | Text-over-image contrast |
| [`a11y_contrast_dom`](docs/tools.md#a11y_contrast_dom) | Fix & contrast | Live-element contrast sampling |
| [`a11y_suggest_color`](docs/tools.md#a11y_suggest_color) | Fix & contrast | Nearest passing color |
| [`a11y_generate_declaration`](docs/tools.md#a11y_generate_declaration) | Document | Accessibility statement (EAA/RD 1112) |
| [`a11y_generate_vpat`](docs/tools.md#a11y_generate_vpat) | Document | VPAT 2.5 report (WCAG edition) |
| [`a11y_badge`](docs/tools.md#a11y_badge) | Document | Honest SVG badge |
| [`a11y_snapshot`](docs/tools.md#a11y_snapshot) | Watch (regressions) | A11y snapshot + tab order |
| [`a11y_diff`](docs/tools.md#a11y_diff) | Watch (regressions) | Snapshot regression diff |
| [`a11y_diff_urls`](docs/tools.md#a11y_diff_urls) | Watch (regressions) | Staging vs production diff |
| [`a11y_aria_live_snippet`](docs/tools.md#a11y_aria_live_snippet) | Watch (regressions) | aria-live monitor snippet |
| [`a11y_criterion`](docs/tools.md#a11y_criterion) | Knowledge & context | WCAG criterion explained |
| [`a11y_html_validate`](docs/tools.md#a11y_html_validate) | Knowledge & context | W3C Nu validation |
| [`a11y_keyboard`](docs/tools.md#a11y_keyboard) | Interactions | Keyboard-trap detector |
| [`a11y_forms`](docs/tools.md#a11y_forms) | Interactions | Form error testing |
| [`a11y_hover`](docs/tools.md#a11y_hover) | Interactions | Hover dismissibility (1.4.13) |
| [`a11y_reflow`](docs/tools.md#a11y_reflow) | Interactions | 320px reflow check |
| [`a11y_scroll`](docs/tools.md#a11y_scroll) | Interactions | Infinite-scroll audit |
| [`a11y_sr_transcript`](docs/tools.md#a11y_sr_transcript) | Interactions | Screen reader transcript |
| [`a11y_reduced_motion`](docs/tools.md#a11y_reduced_motion) | Interactions | prefers-reduced-motion honored? |
| [`a11y_forced_colors`](docs/tools.md#a11y_forced_colors) | Interactions | forced-colors survival heuristic |
| [`a11y_vtt_check`](docs/tools.md#a11y_vtt_check) | Interactions | WebVTT caption quality |
| [`a11y_evidence`](docs/tools.md#a11y_evidence) | Coverage & evidence | Evidence pack (verifiable handoff) |
| [`a11y_disprove`](docs/tools.md#a11y_disprove) | Coverage & evidence | Disprover: re-verify findings |
| [`a11y_ledger`](docs/tools.md#a11y_ledger) | Coverage & evidence | Coverage ledger (persistent) |
| [`a11y_wcag3_preview`](docs/tools.md#a11y_wcag3_preview) | Coverage & evidence | WCAG 3 draft preview (no score) |
| [`a11y_route`](docs/tools.md#a11y_route) | Routing | Tool router (goal or page to steps) |
<!-- TOOLS:END -->

## The 6 prompts

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

Install it with `pip install a11y-toolkit` (or `uv tool install a11y-toolkit`).

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
a11ytoolkit route --goal "gate my PR"                          # which tools for the task
a11ytoolkit route --file page.html                             # diagnosis: the page orders the exams
a11ytoolkit mutants --seed 7 --n 12                            # the engine's sealed self-exam
```

## Coverage: 51 of 55 WCAG 2.2 A/AA criteria (93%)

| With automated signal | Manual-only (genuinely human) |
|---|---|
| 1.1.1, 1.2.2, 1.2.3, 1.2.5, 1.3.1–1.3.5, 1.4.1–1.4.5, 1.4.10–1.4.13, 2.1.1, 2.1.2, 2.1.4, 2.2.1, 2.2.2, 2.4.1–2.4.7, 2.4.11, 2.5.1–2.5.4, 2.5.7, 2.5.8, 3.1.1, 3.1.2, 3.2.1–3.2.4, 3.2.6, 3.3.1–3.3.4, 3.3.8, 4.1.2, 4.1.3 | 1.2.1 (audio transcripts), 1.2.4 (live captions), 2.3.1 (flash detection), 3.3.7 (redundant entry) |

The 4 manual-only criteria each have a knowledge entry (`a11y_criterion`) telling the
agent exactly how to verify them by hand. The boundary is printed on every report.

## The engine behind a11y.es

[a11y.es](https://a11y.es) is a Spanish-market accessibility service that runs
this engine. The service is a separate codebase; this repository is the engine.

## Validated against real pages

Benchmarked against axe-core 4.10 on real pages monthly ([methodology and
results](bench/README.md)). Task-based agent benchmark on live sites,
including a stratified sample of Spain's most important pages
([method and results](docs/benchmark-agents.md)). Found a real WCAG failure on gov.uk that axe does not
report (blue button at 3.91:1, manually verified). Drove out our own false positives
(hidden skip links, honeypot fields, single-context generic links, image-alt accname
— each with a regression fixture).

Also run against the official W3C ACT test cases: `scripts/act_report.py`
regenerates the [EARL implementation report](docs/act-implementation-report.json)
— **100% consistent with every published ACT rule it implements** (355 official
test cases, 20/20 rules, zero inconsistencies, verified per release against the
w3c/wcag-act-rules repository; per-rule breakdown in
[docs/act-report-summary.md](docs/act-report-summary.md)). The WCAG 2.2 catalog
(86 criteria, A/AA/AAA) and the WCAG 3 outcome registry are likewise verified
against their canonical w3.org sources (`scripts/wcag22_ingest.py`,
`scripts/wcag3_ingest.py`).

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

Every audit says: **automation covers 93% of the 55 A/AA criteria** (roughly a
third of all WCAG once AAA and the genuinely-human checks are counted) **— the
rest needs a human**.
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

Generated surfaces — never edit by hand: this README's tool table and
[docs/tools.md](docs/tools.md) come from `server.TOOLS`
(`scripts/gen_readme.py`), and [llms.txt](llms.txt) — this repo's index for
agents, llmstxt.org convention — from the same source
(`scripts/gen_llms.py`). Both `--check` in the Makefile gates: adding a
tool and forgetting them fails the suite.

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
