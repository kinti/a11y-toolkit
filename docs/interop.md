# Interop — composing a11y-toolkit with the popular MCP servers

This engine is one tool in the agent's toolbox. The recipes below compose it
with the most-used MCP servers in the ecosystem (rankings: mcp.so,
mcpservers.org, glama.ai — October 2026). Client setup for this server
itself lives in [clients.md](clients.md).

## With Playwright MCP / Chrome DevTools MCP (browser automation, #1 and top-5)

The agent navigates the real page, captures the served HTML, and audits
exactly what the browser got (no fetching race):

```
1. browser_navigate → https://example.com
2. browser_evaluate → document.documentElement.outerHTML        (capture)
3. a11y_audit_file  → paste/save the HTML, audit it             (engine)
4. a11y_evidence    → seal the findings into a pack             (engine)
```

Why capture instead of letting the auditor fetch? You audit what the user's
session actually received — behind auth, behind a cookie banner, after JS.
`a11y_audit_dom` covers the rendered path when Playwright is unavailable.

## With GitHub MCP (official)

Turn findings into tracked work without losing the evidence:

```
1. a11y_audit (or the Action's SARIF in code scanning)
2. for each high/medium finding → GitHub create_issue:
   title:  "[a11y] {criterion}: {issue, first 60 chars}"
   body:   finding + remediation + examples + the pack sha256
3. a11y_diff before/after a fix → comment the issue with the delta
```

The pack sha256 in the issue body is what makes the report auditable later:
anyone can re-verify the seal with `scripts/verify_pack.py`.

## With Filesystem MCP

Local-first flows: `a11ytoolkit audit --changed [--base main]` audits only
the HTML your PR touches; the Filesystem server reads/writes the reports,
the engine reads them back (`a11y_audit_file --from-report`, `a11y_evidence`).

## With Fetch MCP

- `llms.txt` at the repo root is the engine's own machine-readable index.
- `/docs/*.schema.json` (audit report, evidence pack) give Fetch-based agents
  the contracts without installing anything.

## With Context7 (documentation for agents)

This repo's docs are plain markdown from source (`docs/`), and the tool
catalog is generated — no drift between docs and code, which is what
documentation servers need. To use it via Context7, add the repo there
(github.com/upstash/context7 → Add your library).

## CI without MCP at all

The [GitHub Action](https://github.com/kinti/a11y-watch) and the GitLab
template in `examples/` run the same engine with the error-budget ratchet:
only NEW findings block. SARIF lands in code scanning; EARL for W3C-land.

## The pattern behind every recipe

Agents compose by passing artifacts, not by coupling: **HTML in, findings
out, pack sealed, verdict decided**. Every artifact this engine emits is
plain JSON with a documented schema — that is the whole integration surface,
and it is not going to change shape under you (schemas are pinned by tests).
