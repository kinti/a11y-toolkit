# ARCHITECTURE — the map

One file, the whole system. If you touch this project and read nothing else,
read this. Every claim here that can be pinned by a test IS pinned by
`tests/test_solido.py` — this document drifts, the tests fail.

## What this is

a11y-toolkit is the machine half of WCAG 2.2 conformance work: an MCP server
(31 tools + 6 prompts) and a CLI (`a11ytoolkit`) that audit, fix, document,
watch and hand off accessibility findings. The human half is priced, not
guessed. Zero dependencies at the core; Playwright/Pillow optional behind
import guards. Output es/en; wire keys English (`a11y-evidence-pack/2`).

## Module map

| Module | One line |
|---|---|
| `server.py` | MCP stdio server: 24 tools, 6 prompts, routing/annotations dicts. VERSION lives here. |
| `a11y.py` | CLI dispatcher (`SUBCOMANDOS` dict → module mains). |
| `a11yaudit.py` | Static auditor: 50+ signals, `CRIT` name maps, weighted 0-100 score, sitemap crawl (`evaluar_sitio`). |
| `a11ydom.py` | Rendered auditor (Playwright): shadow DOM, state contrast, target size, reflow, keyboard walk, forms, hover, sr_transcript; browser pool + auto-detection; `_TD` catalog. |
| `a11yscroll.py` | Infinite-scroll audit (focus survival, announcements, feed end). |
| `a11yevidence.py` | Evidence pack builder (`a11y-evidence-pack/2`): 55-criterion matrix, effort per row, SHA-256 chain, embedded bodies. |
| `a11ycrit.py` | Knowledge catalog: `_C` (56 criteria, es/en), `_EFFORT` (55 A/AA effort classes), `effort()`. |
| `a11yvpat.py` | VPAT 2.5 (WCAG edition) generator: pack → accessible HTML VPAT, machine fills Remarks, human sets levels (overrides), signature references pack sha256. |
| `a11yact.py` | ACT Rules interop: curated signal → ACT rule map (`ACT_MAP`, partial by design) + EARL 1.0 JSON-LD export (failures only, never asserts pass). |
| `a11yvtt.py` | WebVTT caption quality (1.2.2): parses the real .vtt — malformed/empty/overlapping/too-fast cues (>21 cps), coverage vs duration. |
| `a11ydocx.py` | DOCX structural screening (zip+XML): images w/o alt, fake headings (bold+big without Heading style), document language, header rows. |
| `a11ypdf.py` | PDF structural screening: tagged tree, title, /Lang, outline, /Alt, text layer (scans), encryption — zero-dep, the space nobody automated. |
| `a11yjourney.py` | Blindfold journey verdict: friction log → deterministic scored task verdict; `_J` friction catalogue (journey_* patterns → criterion + bilingual remediation). |
| `a11ydiff.py` | Snapshot + regression diff (interactives, focus order, tree). |
| `a11ybudget.py` | Error budget: only NEW blocking findings fail (exit 2). |
| `a11yledger.py` | Coverage ledger: what was audited, when, resolved across runs. |
| `a11ydisprove.py` | Disprover: re-audits live page, marks findings confirmed/rejected. |
| `a11yvalidate.py` | W3C Nu validator integration (url + html modes). |
| `a11ysarif.py` | SARIF 2.1.0 export for GitHub code scanning. |
| `a11ybadge.py` | Honest SVG badge (score + date + scope, XML-escaped). |
| `a11yfix.py` | Deterministic autofix (zoom, autocomplete, lang/title, form-error layer). |
| `contrast.py` | Contrast math (pairs, names, hsl/rgba) + pixel sampling over images. |
| `declaracion.py` | Legal statements: EAA / RD 1112/2018, es/en. |
| `arialive_js.py` | Embedded aria-live monitor JS (`ARIALIVE_JS` string). |
| `arialive.js` | The raw monitor script (package-data; regenerate `arialive_js.py` from it). |

## Surfaces (all must agree — pinned in test_solido)

PyPI `a11y-toolkit` · GitHub releases · official MCP registry
(`io.github.kinti/a11y-toolkit`) · `server.json` · console scripts
(`a11ytoolkit`, `a11y-toolkit-mcp`) · README counts · docs/gen-visuals.py.

## Release ritual (never manual)

`make release V=X.Y.Z` → `scripts/versionar.py`: atomic bump of pyproject +
`server.VERSION` + server.json (asserted anchors), fast suites gate, commit,
tag, push. Tag triggers PyPI publish. Then `mcp-publisher publish` **from the
repo root** (login token lives ~1 hour — publish immediately after
authenticating). Docs-only changes still get a version when canonical docs
change (see 4.0.1); internal dev docs don't.

## Decision log (the why, ADR-lite)

- **D1 — Zero-dep core.** Stdlib only; Playwright/Pillow optional behind
  import guards with graceful fallback. Agents install nothing to start.
- **D2 — es/en output, English-first everything else.** Bilingual output is
  the product; docs/wire/prose are English.
- **D3 — Signal IDs are frozen** (`img_sin_alt`…). They are IDs, not prose;
  renaming invalidates users' error budgets. (Kept through v5.0.0's rename.)
- **D4 — `not-run` ≠ `not-flagged`.** "Machine not asked" vs "machine looked
  and found nothing". Never conflate.
- **D5 — Evidence pack**: hash chain + embedded bodies (self-verifying),
  vendor-neutral empty signature block. The toolkit never claims conformance.
- **D6 — English wire keys, pack/2 (v5.0.0).** The frozen Spanish keys were
  the format's origin showing. Coordinated with the exchange pre-hardening.
- **D7 — Effort classes are data** (`_EFFORT`), emitted per pack row plus
  `effort_pending` totals. The marketplace prices; we state remaining scope.
- **D8 — Two-sided automated-fail rule + NA settlement** (4.0.1): confirming
  a measured fail = MIN; certifying pass = full class; not_applicable with
  reason settles at MIN. Buyer never pays for examination that didn't happen.
- **D9 — Normative counts pinned** (test_solido): 55 A/AA set, per-criterion
  levels, effort distribution 23/19/13, pack totals 313-649. Drift = red.
- **D10 — Disprover + ledger** (from Cloudflare's security-audit-skill):
  re-verify findings against the live page; accumulate coverage across runs.
- **D11 — Package layout (v4.0.0)**: `a11y_toolkit/` + `tests/`; console
  scripts and MCP wire unchanged.
- **D12 — Version discipline**: one command, three files, asserts, gates.
  Manual bumps drifted for 10 releases before this existed.
- **D14 — Contract tests (v5.6.0)**: schema ↔ dispatch ↔ firma reales,
  verificados parseando el dispatch y contrastando con `inspect`. Matan las
  clases browser= y auth_state-tirado. La forma del inputSchema también se
  valida (nada fuera de properties).
- **D15 — Journey budgets (v5.6.0)**: solo la fricción NUEVA (alta) o la
  degradación pass→peor bloquea el deploy; claves `criterio:señal` estables
  (D3); exit 2 = NO-GO, exit 1 = error de uso.
- **D13 — Blindfold testing (v5.1.0)**: the agent IS the non-visual user —
  tasks, not just rules. `blindfold-task` prompt drives perceive/act/log;
  `a11y_journey_verdict` scores deterministically (start 100, −25/−12/−5 per
  friction, −15 workaround; pass = completed, no high, no workaround, ≥85).
  Journeys enter the pack as `report:journey`. Usability evidence, never
  conformance: an AI agent is not a human screen-reader user.
- **D14 — VPAT honesty + ACT interop (next)**: the VPAT generator fills
  Remarks from the pack and leaves every Conformance Level at Not Evaluated
  unless an automated fail forces Does Not Support — only a qualified human's
  `overrides` (plus the signature block referencing pack.sha256) turn the
  draft into a claim. ACT/EARL mapping is curated and partial by design:
  only published rules that correspond directly; absence of findings is
  never asserted as pass. PNG decoding is stdlib-only (`contrast.py`) so the
  pixel-sampling path keeps the zero-dep core.

## Trap catalogue (each class cost a bug — recognize the class)

| # | Trap | Guard |
|---|---|---|
| T1 | Silent `str.replace` no-op (anchor absent) | **Assert every anchor.** Three historical bugs. |
| T2 | Regex renamer over code eats syntax (`informe:` prefix ate `if x in informe:`) | Scoped quoted-literal renames only; full suites before commit; grep result for orphans. |
| T3 | Renaming Python keys misses injected-JS bare keys (`foco:`) | After any rename: run the rendered path (test_dom/test_cli) and grep `_ESTADO`/`evaluate` snippets. |
| T4 | Count drift across surfaces (54 vs 55; README vs catalog) | Pin in test_solido against the normative source, not against prose. |
| T5 | A public surface without its own boundary test (CLI broke 3.7→3.9.1; MCP dispatch ignored a param in 3.13.1) | Every surface gets a subprocess/boundary test, not just the function. |
| T6 | Version literals pinned in tests | Derive from `server.VERSION`. |
| T7 | stdlib floor is 3.9 — no `tomllib` (3.11+) | Regex-parse config in tests. |
| T8 | Playwright context destroyed mid-walk (focus-triggered nav) | Catch and treat as a 3.2.1 signal, never a crash. |
| T9 | aria-live panel self-observation loop (`role="log"` panel) | Documented in SKILL.md — do not reintroduce. |
| T10 | Browser hardcoding | Auto-detect chain chromium→firefox→webkit→chrome→msedge; pool reuse. |
| T11 | `mcp-publisher` run outside repo root | `server.json not found` — run from repo root; token expires ~1h. |
| T13 | Changelog announces a fix that never landed (edit lost between batch writes; "verified" by the script's print) | Re-read the file after the write; assert the fixed string exists post-write; pin the reproduction. |
| T14 | Release cut by hand without versionar (tag ≠ file versions; PyPI rejects duplicate wheel) | `make release` / versionar ALWAYS, even for fix-only releases. Burned tag = superseded, never edited. |
| T12 | Private repos on deploy hosts | minipc pull needs `GIT_SSH_COMMAND="ssh -i /root/.ssh/a11y_deploy"`; remote is SSH. |

## Where things live

- Spec of the pack: `docs/evidence-pack-schema.md` (+ `evidence-pack.sample.json`)
- Effort table (citable, generated from `_EFFORT`): `docs/effort-class-table.md`
- Client configs: `docs/clients.md` · visuals: `docs/gen-visuals.py` (`make visual`)
- Skill: `skill/a11y-toolkit/` (mirror at `~/.zcode/skills/a11y-toolkit/`)
- Benchmark vs axe: `bench/` · CI: `.github/workflows/` (ci, publish on `v*`, monthly bench)
- Contribution rules incl. the signal checklist: `.github/CONTRIBUTING.md`
