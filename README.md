# a11y-toolkit MCP

[![CI](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-server-purple)](https://modelcontextprotocol.io)

A **WCAG 2.2 accessibility suite** as an MCP server (Model Context Protocol) for AI agents — plus a unified CLI. **Zero dependencies** at its core; all math is local and exact (the official relative-luminance formula).

The full audit → fix → document → regression-watch loop, in one toolkit:

1. **Audit**: express WCAG audit of any URL (severity-ranked findings)
2. **Fix**: exact contrast checks — color pairs *and* **text over images** (pixel-level sampling of the real background) — with nearest-passing-color suggestions
3. **Document**: legal accessibility declarations (EU), generated as accessible HTML
4. **Watch**: snapshots + diffs between builds to catch accessibility regressions before production

Multilanguage **es/en** across all tools (EN declarations use Directive (EU) 2016/2102 and Directive (EU) 2019/882 — European Accessibility Act — wording, useful EU-wide).

## MCP tools (9)

| Tool | What it does |
|---|---|
| `a11y_audit_url` | Express WCAG audit of a URL: images without alt (1.1.1), controls without accessible names (4.1.2), form fields without labels (3.3.2), missing lang/title (3.1.1, 2.4.2), heading level skips (1.3.1), blocked zoom (1.4.4), positive tabindex (2.4.3), untitled iframes. Severity-ranked. Filter, not verdict — automation covers ~1/3 of WCAG. |
| `a11y_contrast_pair` | Exact contrast ratio + per-criterion verdicts: 1.4.3 (AA), 1.4.6 (AAA), 1.4.11 (non-text). If AA fails, suggests the nearest passing color. |
| `a11y_contrast_image` | **Text over images**: pixel-level sampling of the actual background behind the text box → worst/median/p95 ratio, % of area passing AA, and `zona_peor` (automatic hostile-zone detection on a 3×3 grid). What pair-only checkers can't do. |
| `a11y_suggest_color` | Nearest color to yours that reaches a target ratio (4.5 by default). |
| `a11y_generate_declaration` | Legal accessibility declaration in HTML: RD 1112/2018 art. 10 (Spain, public sector) or Ley 11/2023 / European Accessibility Act wording. es/en. The generated document is itself accessible. |
| `a11y_snapshot` | Accessibility snapshot of a URL: interactive elements (tag, role, accessible name, href) + real tab focus order. Requires Playwright locally. |
| `a11y_diff` | Compares two snapshots: added/removed/renamed interactives and focus-order changes. Accepts inline JSON or file paths. |
| `a11y_diff_urls` | Snapshot two URLs and diff in one call (staging vs production). |
| `a11y_aria_live_snippet` | Injectable monitor that logs every dynamic-region announcement (aria-live, role=alert/status): time, politeness, role, text — what a screen reader would say, visible on screen. |

## Install as MCP

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "python3",
      "args": ["/path/to/a11y-toolkit/server.py"]
    }
  }
}
```

Or with [uv](https://docs.astral.sh/uv/), no clone needed:

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/kinti/a11y-toolkit", "a11y-toolkit-mcp"]
    }
  }
}
```

Add `"timeoutMs": 60000` if you plan to use `a11y_snapshot` (browser startup).

## Unified CLI — one command for everything

```bash
a11y pair "#1f2328" "#fbfaf7"                     # contrast, per-criterion verdicts
a11y image hero.jpg --text "#ffffff" --region 120,40,420,90
a11y audit --url https://example.com              # express WCAG audit
a11y declaration --entidad "Acme" --url https://acme.example \
       --estado parcial --marco eaa --lang en --output decl.html
a11y snapshot https://mysite --out before.json    # before deploy (needs Playwright)
a11y diff before.json after.json                  # after deploy
```

Run from the repo: `python3 a11y.py <subcommand>`.

## Interpreting image mode

- `ratio_peor` (worst) — the most hostile spot for your text color.
- `area_pasa_aa_texto_normal_4_5` — % of safe surface. **If < 100% where the text sits: scrim/overlay, crop, or move the text.**
- `zona_peor` — the 3×3 grid cell that fails hardest, with exact coordinates.

## Security & scope

A **local** tool: runs on your machine as your user. The `path` (image) and `output_path` (declaration) arguments read/write local paths — use it in MCP clients you trust. Nothing is sent over the network (except fetching the URL you explicitly audit).

## Technical notes

- Image decoding: Pillow if available, else `sips` (macOS); PPM always (that's why CI needs no dependencies).
- The aria-live monitor carries a documented design lesson: its panel is deliberately NOT a live region and excludes itself from the observer — a `role="log"` panel would match its own selector and create an infinite self-observation loop. We know because it happened to us.
- Tested against real production sites (the author's own, which must pass its own audit).
- Web versions for humans (same math): [jquin.net/lab](https://jquin.net/lab/) — contrast (pairs + image), declaration generator, aria-live monitor, build diff.

---

## Español

Suite de accesibilidad **WCAG 2.2** como servidor MCP + CLI unificado. **Cero dependencias** en el núcleo (Pillow opcional; `sips` en macOS; PPM siempre). Todo el ciclo en un toolkit: auditar (`a11y_audit_url`) → corregir (contraste de pares **y texto sobre imagen** con muestreo píxel a píxel y detección de zona hostil; sugerencia de color accesible) → documentar (declaración legal RD 1112/2018 art. 10 o Ley 11/2023/EAA, en HTML accesible) → vigilar (snapshots y diff entre builds: añadidos/eliminados/renombrados y orden de foco).

**9 herramientas MCP** (ver tabla superior) · multilenguaje **es/en** (la declaración EN usa la terminología de las Directivas (UE) 2016/2102 y 2019/882) · CLI unificado `a11y` con subcomandos `pair`, `image`, `audit`, `declaration`, `snapshot`, `diff`.

```json
{ "mcpServers": { "a11y-toolkit": {
    "command": "python3", "args": ["/ruta/al/repo/server.py"] } } }
```

Herramienta **local**: los argumentos `path` y `output_path` leen/escriben rutas locales; nada sale a la red salvo la URL que audites explícitamente. El monitor aria-live documenta su lección de diseño: el panel NO es una región viva y se autoexcluye del observador (un `role="log"` casaría con su propio selector y crearía un bucle infinito de auto-observación — lo sabemos porque nos pasó). Versiones web para humanos: [jquin.net/lab](https://jquin.net/lab/).

## Autor / Author

**Jesús Quintana Fernández** ([jquin.net](https://jquin.net/)) — SEO/GEO consultant and web-accessibility practitioner since 2003. MIT © 2026.
