# a11y-toolkit — the accessibility layer for AI coding agents

[![CI](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![Downloads](https://img.shields.io/pypi/dm/a11y-toolkit)](https://pypistats.org/packages/a11y-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-server-purple)](https://modelcontextprotocol.io)

**21 MCP tools + 5 prompts + a skill** covering the full WCAG 2.2 loop: **audit → fix →
document → watch → hand off**. **51 of 54 A/AA criteria carry automated signals (92%)**.
Zero dependencies at the core; every finding ships with a concrete remediation your
agent can apply.

The **European Accessibility Act** is in force since June 2025, ADA suits keep landing,
and AI agents now write most of the web. A scan is not a defence — the machine finds,
the human signs.

<p align="center">
  <img src="docs/demo.gif" alt="a11y-toolkit in action: audit (score 64), nearest passing color, re-audit (94) — real tool output" width="720">
</p>

## What no other a11y tool gives an agent

| Capability | axe-core / Lighthouse / pa11y | a11y-toolkit |
|---|---|---|
| Text contrast over **images/gradients** (pixel sampling, hostile-zone grid) | ✗ | ✓ |
| **Form error testing**: fills invalid data, submits, judges announcement (3.3.1/3.3.3) | ✗ | ✓ |
| **Keyboard traps** with real Tab walking + Escape-release test (2.1.2) | ✗ | ✓ |
| **Infinite-scroll audit**: focus survival, announcements, feed end (2.4.3, 4.1.3) | ✗ | ✓ |
| **Reflow at 320px** (1.4.10) + **text spacing override** (1.4.12) | ✗ | ✓ |
| **W3C Nu validator** integration (doctype, structural validity, mapped to criteria) | ✗ | ✓ |
| **Focus/input-triggered navigation** detection (3.2.1/3.2.2) | ✗ | ✓ |
| **Legal accessibility statements** (EAA / RD 1112/2018), es/en | ✗ | ✓ |
| **Evidence pack** for human countersigning (SHA-256, criteria matrix) | ✗ | ✓ |
| **Deterministic autofix** incl. accessible form-error layer (3.3.1/3.3.3) | ✗ | ✓ |
| **Regression watch**: budget, SARIF→GitHub PRs, tab-order + tree diffs | ✗ | ✓ |
| **Open shadow DOM** traversal + same-origin iframes | partial | ✓ |
| **Placeholder-only labels**, fieldset/legend, label quality, financial confirmation | ✗ | ✓ |
| Runs with **zero dependencies** at core (Playwright optional) | heavy runtimes | ✓ |
| Output optimized for **MCP/LLM consumption** (JSON, es/en, severity-ranked) | ✗ | ✓ |

## The tools (21)

### Audit

| Tool | What it does |
|---|---|
| `a11y_audit_url` | Express static audit of a URL or raw HTML: 40+ signals across 51 WCAG criteria with a weighted 0-100 score. Covers alt, names, labels, autocomplete (1.3.5), ARIA validity (roles/refs/values), headings, zoom, lang, captions, autoplay, link purpose (2.4.4), list structure, duplicate ids/accesskeys, placeholder-only labels, fieldset/legend for radio groups, label quality, required-field indication, financial forms without confirmation (3.3.4), character-key shortcuts (2.1.4), drag handlers (2.5.7), status regions (4.1.3), heading quality (2.4.6), sensory instructions (1.3.3), orientation lock (1.3.4), images of text (1.4.5), consistent help (3.2.6), site-level nav consistency (3.2.3) and multiple ways (2.4.5). |
| `a11y_audit_dom` | **Rendered audit** in Chromium: computed text contrast with alpha compositing (1.4.3), target size 24×24 (**2.5.8 — new in WCAG 2.2**), focus indicator (2.4.7), **:focus/:hover state contrast**, **text spacing override** (1.4.12 — injects WCAG spacing, counts clipped texts), **color-only links** (1.4.1), **DOM-vs-visual order** (1.3.2), looping animations (2.2.2), **open shadow DOM traversed**, **same-origin iframes scanned**. Accepts `auth_state` for behind-login auditing. |
| `a11y_forms` | **Form error testing** (3.3.1/3.3.3): fills validatable fields with invalid data, really submits, judges whether errors are identified and announced in the post-submit DOM. Native browser validation counts (unless `novalidate`). |
| `a11y_keyboard` | **Keyboard traps** (2.1.2) with real Tab walking + cycle detection + Escape-release test. Also detects **focus-triggered navigation** (3.2.1) and **input-triggered navigation** (3.2.2). |
| `a11y_scroll` | **Infinite-scroll audit**: does focus survive each batch? Is new content announced (4.1.3)? Does the feed end or offer load-more? |
| `a11y_reflow` | **320px reflow** (1.4.10): real horizontal scroll + overflowing elements. |
| `a11y_html_validate` | **W3C Nu validator** (validator.w3.org/nu): doctype, encoding, structural validity, authoritative alt/lang/role findings mapped to criteria. Self-hosted vnu supported. |

### Fix

| Tool | What it does |
|---|---|
| `a11y_autofix` | **Deterministic safe fixes**: unblock zoom (1.4.4), autocomplete tokens (1.3.5), missing lang, empty title, **accessible form-error layer** (aria-invalid + describedby + attribute-derived suggestions — skips forms with their own handling). Judgment fixes returned as `no_aplicados` with remediation. |
| `a11y_contrast_pair` | Exact ratio + verdicts 1.4.3/1.4.6/1.4.11. Accepts #hex, rgb(), hsl(), CSS names; alpha composites. Suggests nearest passing color. |
| `a11y_contrast_image` | **Text over images**: pixel-level sampling → worst/median/p95 ratio, % area passing AA, hostile-zone grid. |
| `a11y_suggest_color` | Nearest opaque color reaching the target ratio. |

### Document

| Tool | What it does |
|---|---|
| `a11y_generate_declaration` | Legal statement: RD 1112/2018 art. 10 or **European Accessibility Act** (EAA). es/en. The document is itself accessible. |
| `a11y_badge` | **Honest SVG badge**: score, date, "automated screening" scope — never claims conformance. |
| `a11y_criterion` | Explains any WCAG 2.2 criterion: what it requires, typical failures, which tool verifies it. |

### Watch

| Tool | What it does |
|---|---|
| `a11y_snapshot` | Interactive elements + real tab order + **computed accessibility tree** (what a screen reader announces). |
| `a11y_diff` | Regression diff between snapshots: interactives, focus order, tree changes. |
| `a11y_diff_urls` | Snapshot two URLs and diff (staging vs production). |
| `a11y_aria_live_snippet` | Injectable monitor logging every aria-live announcement. |

### Hand off

| Tool | What it does |
|---|---|
| `a11y_evidence` | **Countersignature-ready evidence pack**: full criteria matrix (fail/review/not-flagged/agent-verified/manual-only), SHA-256-hashed artifacts, empty signature block tied to the pack hash. Spec: [docs/evidence-pack-schema.md](docs/evidence-pack-schema.md). |

**5 prompts**: `audit-page`, `fix-contrast`, `pre-deploy-check` (GO/NO-GO), `declaration-eaa`, `conformance-wcagem` (three-tier WCAG-EM ladder).

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

Rendered tools use Playwright **if present** (`pip install playwright && playwright
install chromium`); everything else works with zero dependencies. Rendered tools accept
`auth_state` (Playwright storage_state path) to audit behind login.

### The skill

```bash
git clone https://github.com/kinti/a11y-toolkit && cd a11y-toolkit
./skill/install-skill.sh     # → ~/.zcode/skills and ~/.claude/skills
```

## CLI — same engine, one command

```bash
a11ytoolkit audit --url https://example.com --pages 5   # sitemap-first crawl
a11ytoolkit pair "#1f2328" "#fbfaf7"                    # contrast
a11ytoolkit image hero.jpg --text "#fff" --region 120,40,420,90
a11ytoolkit forms https://mysite/contact                # form errors
a11ytoolkit kbd https://mysite                          # keyboard traps + 3.2.1/3.2.2
a11ytoolkit reflow https://mysite                       # 320px reflow
a11ytoolkit scroll https://medium.com/feed              # infinite scroll
a11ytoolkit validate --url https://example.com          # W3C Nu
a11ytoolkit fix --file page.html -o fixed.html          # safe autofix
a11ytoolkit declaration --entidad "Acme" --url https://… --estado parcial --marco eaa
a11ytoolkit snapshot https://mysite --out before.json   # before deploy
a11ytoolkit diff before.json after.json                 # after deploy
a11ytoolkit evidence audit.json -o pack.json            # countersignature-ready pack
a11ytoolkit budget --budget budget.json --audit audit.json  # only NEW findings block
a11ytoolkit sarif --from-audit audit.json -o a11y.sarif # GitHub code scanning
a11ytoolkit badge --score 92 --out badge.svg            # honest SVG
```

## Coverage: 51 of 54 WCAG 2.2 A/AA criteria (92%)

| With automated signal | Manual-only (genuinely human) |
|---|---|
| 1.1.1, 1.2.2, 1.2.3, 1.2.5, 1.3.1–1.3.5, 1.4.1–1.4.5, 1.4.10, 1.4.11, 1.4.12, 2.1.1, 2.1.2, 2.1.4, 2.2.1, 2.2.2, 2.4.1–2.4.7, 2.4.11, 2.5.1–2.5.4, 2.5.7, 2.5.8, 3.1.1, 3.1.2, 3.2.1–3.2.6, 3.3.1–3.3.4, 3.3.8, 4.1.2, 4.1.3 | 1.2.1 (audio transcripts), 1.2.4 (live captions), 1.4.13 (hover dismissibility), 2.3.1 (flash detection), 3.3.7 (redundant entry) |

The 5 manual-only criteria each have a knowledge entry (`a11y_criterion`) telling the
agent exactly how to verify them by hand. The boundary is printed on every report.

## Free online analyzer

**[a11y.jquin.net](https://a11y.jquin.net)** — the machine half, free forever: full
report, honest badge, evidence-pack download. SSRF-guarded, rate-limited. Every free
report ends at the exact boundary where a qualified human begins.

## Validated against real pages

Benchmarked against axe-core 4.10 on real pages monthly ([methodology and
results](bench/README.md)). Found a real WCAG failure on gov.uk that axe does not
report (blue button at 3.91:1, manually verified). Drove out our own false positives
(hidden skip links, honeypot fields, single-context generic links, image-alt accname
— each with a regression fixture).

## Honesty, built in

Every audit says: **automation covers 92% of A/AA criteria; the rest needs a human**.
The `audit-page` prompt and the skill have the agent check what it can (keyboard,
focus, zoom, announced errors) using [the manual
checklist](skill/a11y-toolkit/references/wcag22-manual-checklist.md). A filter, not
a verdict. The evidence pack is the handoff object for the human who signs.

## Security & scope

A **local** tool: runs on your machine as your user. `a11y_audit_url` accepts
http/https only (no `file://` — use `--file`/`html` for local HTML). `a11y_html_validate`
in html mode POSTs content to the W3C service (url mode shares only the URL;
self-hosted vnu supported). `path`/`output_path` read/write local paths — use it in
MCP clients you trust.

## Development

```bash
python3 test_contrast.py && python3 test_audit.py && python3 test_v32.py \
  && python3 test_dom.py && python3 test_cli.py && python3 test_solido.py \
  && python3 test_mcp.py
```

`test_dom.py` self-skips without Playwright. `test_solido.py` enforces the design
invariants (catalog parity, version alignment, count coverage, hostile-HTML fuzz).
Releases: `make release V=X.Y.Z` — bumps, gates, tags and pushes atomically.

## Roadmap

- [x] Rendered audit (shadow DOM, state contrast, text spacing, color-only links)
- [x] 0-100 score · ARIA validity · criterion knowledge (56 entries)
- [x] Form error testing + autofix (find AND fix)
- [x] Keyboard traps + focus/input navigation detection (2.1.2, 3.2.1, 3.2.2)
- [x] Infinite scroll · reflow · W3C Nu validation
- [x] SARIF export · error budget · scheduled surveillance recipe
- [x] Evidence pack with agent-verified status (spec published)
- [x] Form deep-dive: placeholder-only, fieldset, label quality, financial confirmation
- [x] Sitemap-driven crawling · behind-login auditing (auth_state)
- [x] 50/54 A/AA criteria with automated signals (92%)

## Author

**Jesús Quintana Fernández** ([jquin.net](https://jquin.net/)) — SEO/GEO consultant and
web-accessibility practitioner since 2003. MIT © 2026.
