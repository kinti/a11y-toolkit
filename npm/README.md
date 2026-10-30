# @kinti/a11y-toolkit (npm launcher)

Zero-dependency WCAG 2.2 accessibility engine: **34 MCP tools + CLI**. This
npm package is a thin Node launcher — the engine itself is Python
(stdlib-only), run through [uv](https://docs.astral.sh/uv/) so nothing is
installed globally.

## Use

```bash
npx -y @kinti/a11y-toolkit audit --url https://example.com     # CLI
npx -y @kinti/a11y-toolkit pair "#1f2328" "#fbfaf7"            # contrast
```

As an MCP server (stdio):

```json
{ "mcpServers": { "a11y-toolkit": {
    "command": "npx", "args": ["-y", "@kinti/a11y-toolkit", "a11y-toolkit-mcp"] } } }
```

## Requirements

Python at runtime, installed on demand by [uv](https://docs.astral.sh/uv/)
(`curl -LsSf https://astral.sh/uv/install.sh | sh`). If uv is missing, the
launcher prints the exact one-liner for your OS.

Prefer pure Python? `uvx --from a11y-toolkit a11y-toolkit-mcp` is the same
thing without Node. Docs: [kinti/a11y-toolkit](https://github.com/kinti/a11y-toolkit).
