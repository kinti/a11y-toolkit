# Security Policy

## Scope

a11y-toolkit is a **local** tool. It runs as your user on your machine:

- The MCP server speaks stdio JSON-RPC with the client that launched it.
- `a11y_audit_url` fetches **only http/https URLs** (non-http schemes are
  rejected — a prompt-injected caller cannot point it at `file://` to read
  local files; use `--file`/the `html` argument for local HTML). Standard
  library client, no cookie jar, no code execution from responses.
- The rendered tools (audit_dom/reflow/keyboard/scroll) run Playwright as
  **your user** and therefore can load `file://` by design (local fixture
  testing). Threat model: the MCP already runs with your privileges; the
  boundary that matters is exfiltration channels, which is why the fetch-based
  tool above is scheme-restricted.
- `path` (image contrast) and `output_path` (declarations) read/write the
  local paths you pass — as with any local tool, only point them at files you
  trust and directories you intend to change.
- The aria-live snippet is inert JavaScript that only logs announcements on
  the page where *you* inject it.

## Supported versions

| Version | Supported |
|---|---|
| 3.x | ✓ |
| < 3.0 | ✗ |

## Reporting a vulnerability

Please report privately via GitHub **Security Advisories → Report a
vulnerability** on this repository, or through [jquin.net](https://jquin.net/).
Do not open a public issue for security reports. Expect an initial response
within a few days; credit is given unless you prefer otherwise.
