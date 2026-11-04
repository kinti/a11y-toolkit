# AGENTS.md — working on a11y-toolkit

Rules for coding agents (and humans) contributing to this repository.

## What this codebase is

A zero-dependency (stdlib-only) WCAG 2.2 accessibility engine + MCP server
(37 tools) + CLI. Python 3.9+. The engine runs as an MCP server, a CLI
(`a11ytoolkit`), and is vendored by a11y.es (production). Zero telemetry is a
product promise — never add phone-home code.

## The constellation (who consumes this engine)

This is the PUBLIC layer of a 4-repo system (canonical map lives in the
private `a11y-toolkit-pro/ARCHITECTURE.md`):

- **a11y-toolkit-pro** (private) — the consulting playbook (508 GSA tree,
  tender annexes, WCAG-EM sampling, remediation planning), extracted from
  this repo on 2026-11-04 by founder decision. Depends on this engine,
  never the reverse. Nothing from those modules comes back here.
- **a11y.es** (private product) — vendors this engine into its Docker
  image; changes here ship to production via their sync ritual.
- **Lince/cpa11y** (private product) — pins this engine by commit.

Implications for ANY change here: keep the engine runnable with the pro
package absent; the conformance DRAFT generators (`a11yvpat`,
`a11yopenacr`, `a11ystatement`) are a FROZEN layer — maintenance fixes
only, new conformance capability goes to the SaaS, not here (each carries
a "FROZEN LAYER" docstring stamp). Severities/messages are calibrated
against expert review — a change that moves a score is a public behavior
change and needs its regression test in the same commit.

## Non-negotiable invariants (all pinned by tests — `make test` runs them)

- `python3 tests/test_solido.py` — es/en message catalogs key-identical, every
  finding has `_rem` remediation, version files aligned, tool/prompt counts
  consistent across every surface, hostile-HTML fuzz never crashes.
- `python3 tests/test_naming.py` — the public surface and the code are
  English-only: tool params, enums, dict keys, identifiers, string-key READS,
  phrase-table/JS placeholder consistency. Spanish lives ONLY in `lang=es`
  output content and comments.
- `python3 tests/test_contract.py` — tool schema ↔ dispatcher ↔ function
  signature must agree mechanically.
- Signal→criterion map and Understanding-URL coverage are pinned in test_solido.

## Conventions

- Release flow: `make release V=X.Y.Z` (atomic bump, full-suite gate — every
  `tests/test_*.py` by discovery, single
  v-prefixed commit, tag, push — PyPI publishes the tag). No intermediate work
  commits; the working tree is picked up whole.
- Internal/strategy material NEVER goes in this repo (pre-commit guard blocks
  it; drafts live outside). Public docs are English; CHANGELOG keeps history.
- Bilingual output: every user-facing message exists in es AND en catalogs.
- Finding emission: `add(severity, 'X.Y.Z', 'signal_name')` — a new signal
  automatically joins the signal→criterion map (test re-derives it); a new
  message key needs its `_rem` twin in both languages.

## After changing anything

```bash
make test   # all suites; red means the invariant you touched is load-bearing
```

The accessibility rule applies to this repo too: it must audit clean.

## VITAL: publish every change (founder rule, 2026-11-01)

**Any change to public capabilities MUST ship with its publication in the
SAME commit** — no exceptions, no "later":

1. **CHANGELOG.md** — entry in the `pendiente` section at the top (what
   it is, which pattern it comes from, what it does NOT do).
2. **README.md AND README.es.md** — both, always: if the change adds or
   alters a user-facing capability, it goes in the command examples
   block; if it changes numbers or coverage claims, those lines update
   too. The Spanish README is a full sibling, never a stale translation.
3. If it alters architecture: **docs/ARCHITECTURE.md** (the module map is
   pinned by test_solido).
4. If it touches deployment of the SaaS: **deploy/README.md** the same
   day (the tunnel-era lesson: a runbook describing a dead architecture
   cost an hour of diagnosis).

Red means the publication invariant you touched is load-bearing.
