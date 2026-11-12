# Installing a11y-toolkit (agent instructions)

Pick ONE path. Both start the same MCP stdio server. No API keys, no account, no telemetry.

## Path A — uv (preferred, matches the official MCP registry entry)

Requires `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

Add to `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "uvx",
      "args": ["--from", "a11y-toolkit", "a11y-toolkit-mcp"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Path B — npm (no Python install needed; the engine ships inside)

Requires Node >= 16 and `python3` on PATH.

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "npx",
      "args": ["-y", "-p", "@kinti/a11y-toolkit", "a11y-toolkit-mcp"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

The `-p` flag matters: the package ships two bins (the `a11ytoolkit` CLI and the
`a11y-toolkit-mcp` server) and plain `npx @kinti/a11y-toolkit` would run the CLI.

## Optional — rendered tools

Static audits, contrast math, PDF/DOCX screening and evidence packs work with zero
dependencies. For rendered checks (real contrast over images, keyboard traps, reflow,
forms): `pip install playwright && playwright install chromium`.

## Verify the install

Call `a11y_contrast_pair` with `{"fg": "#1f2328", "bg": "#fbfaf7"}`.
A JSON object with the ratio and per-criterion verdicts must come back
(15.13 for that pair). If it does, the server is wired correctly.

## Do not

- Do not pass `file://` URLs to `a11y_audit_url`; use the `html` argument, or the CLI:
  `a11ytoolkit audit --file page.html`.
- Do not expect a conformance certificate: reports state coverage and the human
  remainder by design.
