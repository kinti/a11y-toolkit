# a11y-toolkit — the accessibility layer for AI coding agents

[![CI](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-server-purple)](https://modelcontextprotocol.io)
[![Smithery](https://smithery.ai/badge)](https://smithery.ai)

**10 MCP tools + 4 prompts + a skill** that give any AI agent (Claude, Cursor, Windsurf,
Codex…) the full WCAG 2.2 loop: **audit → fix → document → watch**. Zero dependencies at
its core; every finding ships with a concrete remediation your agent can apply.

Accessibility is not optional anymore: the **European Accessibility Act is in force since
June 2025**, ADA suits keep landing, and AI agents now write most of the web. This toolkit
makes "is it accessible?" a one-question ask — and "then fix it" a one-command job.

## What no other a11y tool gives an agent

| Capability | axe-core / Lighthouse / pa11y | a11y-toolkit |
|---|---|---|
| Text contrast over **images/gradients** (pixel sampling of the real background, hostile-zone grid) | ✗ | ✓ |
| Legal **accessibility statements** (EAA / RD 1112/2018), accessible HTML, es/en | ✗ | ✓ |
| **Regression watch** between builds: accessible names + real tab-order diff | ✗ | ✓ |
| **Remediation text per finding**, written for an agent to apply | ✗ | ✓ |
| **Focus-order regression detection** | ✗ | ✓ |
| Runs with **zero dependencies** (stdlib only; Playwright optional for the deep pass) | heavy runtimes | ✓ |
| Screen-reader **aria-live announcement monitor** | ✗ | ✓ |
| Output optimized for **MCP/LLM consumption** (JSON, severity-ranked, es/en) | ✗ | ✓ |

## The tools (10)

| Tool | What it does |
|---|---|
| `a11y_audit_url` | Express static WCAG audit of a URL **or raw HTML**: 13 criteria (alt, accessible names, labels, keyboard onclick, meta refresh, skip mechanism, lang validity, title, headings, blocked zoom, captions, tables, tabindex>0, aria-hidden-on-focusable, target=_blank warnings, duplicate ids). Per-finding remediation. |
| `a11y_audit_dom` | **Rendered audit** (local Playwright/Chromium): real computed text contrast vs effective backgrounds with alpha compositing (1.4.3), minimum target size 24×24 (**2.5.8 — new in WCAG 2.2**), focus-indicator heuristic (2.4.7), all static checks on the live DOM. |
| `a11y_contrast_pair` | Exact ratio + verdicts 1.4.3/1.4.6/1.4.11. Accepts `#hex`, `rgb()`, `hsl()`, **CSS color names**; alpha composites over the background. Suggests the nearest passing color. |
| `a11y_contrast_image` | **Text over images**: pixel-level sampling of the actual background → worst/median/p95 ratio, % area passing AA, hostile-zone detection on a 3×3 grid. |
| `a11y_suggest_color` | Nearest opaque color (true RGB distance) reaching the target ratio (4.5 default). |
| `a11y_generate_declaration` | Legal accessibility statement in HTML: RD 1112/2018 art. 10 (Spanish public sector) or **European Accessibility Act** wording (Directive (EU) 2019/882 / Ley 11/2023). es/en. The document is itself accessible. |
| `a11y_snapshot` | Interactive elements (tag, role, accessible name, href) + **real tab focus order**. Requires Playwright. |
| `a11y_diff` | Regression diff between two snapshots: added/removed/renamed interactives, focus-order changes. |
| `a11y_diff_urls` | Snapshot two URLs and diff in one call (staging vs production). |
| `a11y_aria_live_snippet` | Injectable monitor logging every aria-live announcement (time, politeness, role, text) — what a screen reader would say, visible on screen. |

**Prompts** (slash-commands in supporting clients): `audit-page` (full audit workflow +
what automation can't check), `fix-contrast`, `pre-deploy-check` (audit + diff → GO/NO-GO),
`declaration-eaa` (collects legal fields, generates).

## Install

**Claude Code** (one command):

```bash
claude mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp
```

**Any MCP client with JSON config** (Claude Desktop, Cursor, Windsurf, VS Code…):

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

Or from the repo without publishing:

```json
{ "mcpServers": { "a11y-toolkit": {
    "command": "uvx", "args": ["--from", "git+https://github.com/kinti/a11y-toolkit", "a11y-toolkit-mcp"] } } }
```

The rendered audit, snapshots and diffs use Playwright **if present**
(`pip install playwright && playwright install chromium`); everything else works with
zero dependencies.

### The skill (teaches your agent when/how to use all of this)

```bash
git clone https://github.com/kinti/a11y-toolkit && cd a11y-toolkit
./skill/install-skill.sh     # → ~/.zcode/skills and ~/.claude/skills
```

## CLI — same engine, one command

```bash
a11y pair "#1f2328" "#fbfaf7"                     # contrast, per-criterion verdicts
a11y image hero.jpg --text "#ffffff" --region 120,40,420,90
a11y audit --url https://example.com --lang en    # express static audit
a11y declaration --entidad "Acme" --url https://acme.example \
       --estado parcial --marco eaa --lang en --output decl.html
a11y snapshot https://mysite --out before.json    # before deploy (needs Playwright)
a11y diff before.json after.json                  # after deploy
```

Run from a clone with `python3 a11y.py <subcommand>`; from PyPI with `uvx --from
a11y-toolkit a11y …`.

## Honesty, built in

Automation covers **~1/3 of WCAG** — every audit says so. The `audit-page` prompt and the
bundled skill then have the agent check what it *can* (keyboard operability, focus
visibility, zoom reflow, announced errors) using
[the manual checklist](skill/a11y-toolkit/references/wcag22-manual-checklist.md), and
recommend a screen-reader pass for the rest. A filter, not a verdict.

## Security & scope

A **local** tool: runs on your machine as your user. `path` (image) and `output_path`
(statement) read/write local paths — use it in MCP clients you trust. Nothing leaves your
machine except the URL you explicitly audit.

## Development

```bash
python3 test_contrast.py && python3 test_audit.py && python3 test_dom.py && python3 test_mcp.py
```

`test_dom.py` self-skips without Playwright. Releases: tag `vX.Y.Z` → CI publishes to PyPI
(trusted publishing); `server.json` is the official MCP Registry manifest. Listed on
[Smithery](https://smithery.ai) too.

---

## Español

Suite de accesibilidad **WCAG 2.2** como servidor MCP (10 tools + 4 prompts) + CLI
unificada, **cero dependencias** en el núcleo (Pillow opcional; `sips` en macOS; PPM
siempre; Playwright opcional para la auditoría renderizada). Todo el ciclo: **auditar**
(`a11y_audit_url` estático · `a11y_audit_dom` renderizado con contraste computado real,
tamaño de objetivo 2.5.8 e indicador de foco) → **corregir** (contraste de pares con
nombres CSS/hsl/rgba+alfa, **texto sobre imagen** con muestreo píxel a píxel y zona hostil,
sugerencia por distancia RGB real) → **documentar** (declaración RD 1112/2018 art. 10 o
Ley 11/2023/EAA, HTML accesible) → **vigilar** (snapshots y diff entre builds: añadidos,
eliminados, renombrados y orden de foco). Multilenguaje **es/en**; cada hallazgo con
remediación concreta. Instalación: `claude mcp add a11y-toolkit -- uvx --from
a11y-toolkit a11y-toolkit-mcp`. Skill incluida en `skill/` (`install-skill.sh`).

Herramienta **local**: `path` y `output_path` leen/escriben rutas locales; nada sale a la
red salvo la URL que audites. El monitor aria-live documenta su lección de diseño: el
panel NO es una región viva y se autoexcluye del observador (un `role="log"` casaría con
su propio selector y crearía un bucle infinito de auto-observación — lo sabemos porque nos
pasó). Versiones web para humanos: [jquin.net/lab](https://jquin.net/lab/).

## Author

**Jesús Quintana Fernández** ([jquin.net](https://jquin.net/)) — SEO/GEO consultant and
web-accessibility practitioner since 2003. MIT © 2026.
