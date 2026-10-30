---
description: Audit the current page/project for WCAG 2.2 issues and read the sealed findings
---

Audit what we're working on with a11y-toolkit and report honestly.

## Steps

1. If auditing the open file: run `a11ytoolkit audit --file <file>` (CLI)
   or the `a11y_audit` MCP tool over the file's HTML.
2. If auditing a URL: `a11y_audit_url` / `a11ytoolkit audit --url <url>`.
3. If auditing only what changed in this branch:
   `a11ytoolkit audit --changed --base main`.
4. Read the report: for each finding show criterion, severity, examples and
   the remediation. Group by severity. Do NOT restate findings we can't see.
5. For contrast failures, propose the fix with `a11y_suggest_color`.
6. Optional seal: `a11y_evidence` over the report(s) → give the user the
   pack sha256 so anyone can re-verify later.
7. End with the honest line: what automation covered, what still needs a
   human (the report's `manual_pending` list).
