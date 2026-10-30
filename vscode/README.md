# a11y-toolkit for VS Code (v0.1)

Audit the open HTML file — or just what your branch changed — against
WCAG 2.2, right from the editor. Findings land in the **Problems** panel
with criterion, severity and remediation.

- **Audit current file**: Command Palette → `a11y: Audit current file`
- **Audit what changed**: runs the engine's `--changed` gate (only NEW
  findings block; accepted debt does not)

Runs the self-contained npm package (`npx -y @kinti/a11y-toolkit`): the
pure-stdlib Python engine ships inside it — only `python3` (≥3.9) must
exist on the machine. No settings, no telemetry.

## Package & publish (maintainer)

```bash
cd vscode && npm install -D @vscode/vsce && npx vsce package   # → .vsix
# Publish: npx vsce publish (needs a publisher account "kinti" on the
# Marketplace). Until then: "Install from VSIX" works for anyone.
```
