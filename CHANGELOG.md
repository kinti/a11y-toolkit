# Changelog

## 3.21.0 — 2026-09-21 — "the priced pack"

The evidence pack now prices the human half, and the count drifts are gone:

- **Human-effort classes as data**: `_EFFORT` in `a11ycrit.py` classifies all
  55 A/AA criteria by what the human still does after the machine's best
  signal — MIN 23 (read and confirm, 1-3 min), MED 19 (verify in the
  browser, 5-10 min), MAX 13 (real interaction and judgment, 15-30 min).
  Canonical table: [docs/effort-class-table.md](docs/effort-class-table.md).
- **`a11y_evidence` emits the priced scope**: every matrix row carries
  `esfuerzo {clase, minutos, porque}` and the pack adds
  `esfuerzo_pendiente` — remaining human minutes by class and in total
  (313-649 min for a full page, before any `agent-verified` promotion).
  The quote input for a review marketplace, computed, not estimated.
- **Normative rules pinned**: a measured `automated-fail` earns its
  criterion the MIN human class; `not-flagged` on a partially-covered
  criterion never earns a lower class. `test_solido` pins the normative
  A/AA set (55, w3.org/TR/WCAG22), the level of every criterion, the
  effort distribution and the pack totals — the drift this release fixed
  cannot silently return.
- **Two real drifts found and fixed** by diffing the catalog against
  w3.org/TR/WCAG22: the coverage claim said "51 of 54 (94%)" when the
  normative A/AA set is 55 (→ "51 of 55, 93%"); the evidence matrix
  carried AAA 3.2.5 (Change on Request) as if it were A/AA while AA 1.4.12
  (Text Spacing) was missing from it. The catalog also mislabeled 2.4.4 as
  AA — it has been Level A since WCAG 2.0 (2.4.9 is the AA variant).
  The signal list in the README gained the real 1.4.4 and 1.4.13 signals.

## 3.13.1 — 2026-09-15 — "the review pass"

The post-release from-zero review caught three drifts, one functional:

- **`verificados` was documented in the a11y_evidence schema but the server
  dispatch did not pass it through** — the function worked, the MCP tool
  ignored the parameter. Found by calling the installed PyPI package
  end-to-end; now pinned by an MCP-level regression test (schema-documents-
  it ≠ dispatch-passes-it — the same class as the CLI dispatcher bug of
  3.9.1: every public path needs its own test through the real boundary).
- The published spec (docs/evidence-pack-schema.md) predating agent-verified:
  status and `verificacion` field now documented, with the pack/1 additive-
  extension note for anyone building against it.
- docs/evidence-pack.sample.json regenerated (36 matrix entries carried the
  duplicated-criterion-code bug from pre-3.13; sample now built with 3.13).

## 3.13.0 — 2026-09-15 — "beyond"

The three gaps a real consultant hits daily — and no MCP a11y tool covers.

- **Sitemap-driven site audits**: `a11ytoolkit audit --pages N` now enumerates
  pages from /sitemap.xml first (WCAG-EM's own sampling source, incl. nested
  sitemap indexes, bounded at 200 URLs), falling back to link discovery when
  no sitemap exists. The report records which strategy ran (`descubrimiento`).
  Two real bugs found shipping it: nested sitemaps exceeded the 3MB fetch
  ceiling (sitemaps now parse a 2MB prefix — full files are not needed for a
  bounded sample), and the no-crawl extension guard (.xml is a non-HTML
  extension!) was eating the nested sitemaps themselves.
- **Audits behind login**: all five rendered tools (audit_dom, reflow,
  keyboard, scroll, snapshot) accept `auth_state` — a path to a Playwright
  storage_state JSON exported from a logged-in session. Staging environments
  are finally auditable; the file stays local, nothing is uploaded.
- **The agent-verified status**: the conformance ladder always promised
  "agent-verified" but the evidence pack could not record it. `verificados`
  (criterion codes checked against the sample per the skill's manual
  checklist) now promotes manual-only and not-flagged criteria to
  `agent-verified` in the matrix, with the verification source recorded —
  and automated-fail STAYS fail: verification never erases a finding. The
  human homework list shrinks to what is actually unreviewed.

## 3.12.1 — 2026-09-15 — "the missing descriptions"

Glama/TDQS scored us 4/5; the breakdown pointed at real gaps, now closed:

- **100% parameter documentation**: every input of all 17 tools carries a
  description (a11y_generate_declaration went from 8% coverage and 3.6/5 —
  the worst tool — to fully documented, including what estado/marco/reclamacion
  mean legally).
- **Sibling-routing guidance** added to every tool description ("prefer
  a11y_audit_dom when…") — the TDQS Usage Guidelines dimension.
- Both pinned by test_solido: a parameter without a description, or a tool
  without routing/title/annotations, now fails CI. The score cannot rot.
- Deliberately NOT changed: tool names (verb/noun mix — renaming would break
  published users for a heuristic) and the 17-tool count (>15 "ideal" — each
  maps to a distinct workflow step; cutting tools to please a scorer would
  make the toolkit worse).

## 3.12.0 — 2026-09-07 — "the honest two-thirds"

Can you cover all of WCAG? No — several criteria are judgment by definition,
and claiming otherwise is the overlay trap. So we grew the two coverages that
are honest: machine signals and knowledge.

- **12 new partial signals** on previously manual-only criteria, all
  review-severity where judgment is still needed:
  static — 2.2.2 (marquee/blink/inline infinite animations), 2.5.1
  (gesture/drag handlers with no click alternative), 2.5.4
  (deviceorientation/devicemotion), 1.3.4 (orientation lock incl. script
  bodies), 1.2.3/1.2.5 (missing descriptions tracks), 1.3.3 (sensory-only
  instruction text, es+en patterns);
  rendered — **1.4.12 Text Spacing** (injects the official override set and
  counts clipped texts — not even axe automates this), 1.4.1 Use of Color
  (link-in-text-block: color-only links, no underline, <3:1 vs surrounding
  text), 1.3.2 (DOM-vs-visual order inversions per parent), 2.2.2 (computed
  looping animations);
  site-level — 3.2.3 (nav-signature drift across crawled pages) and 2.4.5
  (multiple ways: search/sitemap detection) via the existing crawl, as a
  pure function (evaluar_sitio) testable without network.
- **Criteria touched: 26 → 38 of ~55 A/AA.** Knowledge catalog complete:
  every touched OR manual A/AA criterion (53) now has an a11y_criterion
  entry — the manual ones say exactly how an agent verifies them by hand.
- Evidence pack homework list shrank 27 → 15, each removal backed by a
  real signal (not promises). README/comparison updated to 38.
- Regression fixtures for every new signal; the criteria-count invariant now
  asserted in one place only.

## 3.11.0 — 2026-09-07 — "the countersignature-ready pack"

Born from an outside insight (a UK marketplace founder noted the seam our own
ladder already documented: an agent can produce a thorough audit and still not
a conformance statement, because conformance needs a person behind it). We
took the design lesson, not the dependency.

- **New tool `a11y_evidence`** (17th): builds the vendor-neutral machine→human
  handoff object. Input: any mix of audit reports (static, rendered, reflow,
  keyboard, scroll) + optional snapshot. Output: full criteria matrix
  (automated-fail / automated-review / not-flagged — explicitly NOT pass /
  manual-only), the 27 A/AA criteria with no automated signal anywhere (the
  human reviewer's homework), every artifact SHA-256-hashed with timestamps,
  and an empty signature block whose statement must reference the pack's own
  hash — tamper-evidence by construction. Any qualified human can
  countersign it; the toolkit never claims conformance.
- CLI `a11ytoolkit evidence`, wcagem-guide tier 2→3 bridge section, skill
  decision-table row. Hash determinism and tamper-response tested.

## 3.10.0 — 2026-09-07 — "actually English-first"

The repo claimed EN-first while defaulting to Spanish. A full-language audit
fixed every surface:

- **Default output language is now ENGLISH everywhere** (39 call sites:
  all functions, CLI argparse, MCP server; `--lang es` / `lang: "es"` still
  selects Spanish — the bilingual output remains the product feature).
- **bench/README.md translated** (36 Spanish lines — a whole doc had shipped
  in Spanish).
- **All 13 module docstrings in English** — they are the CLI `--help` text.
- Remaining Spanish runtime/argparse strings translated (contrast usage
  hints, budget errors, download errors now bilingual via the catalog).
- **CI fixed for Python 3.10**: test_solido imported `tomllib` (3.11+);
  version now parsed with a regex — stdlib-only on 3.9+ again.
- Process fix after two mid-flight script aborts: mechanical regex replaces
  with post-verification grep instead of anchor-asserted batches that abort
  halfway and leave trees half-applied.

## 3.9.5 — 2026-09-07 — "solid by construction"

The fragility classes eliminated at the root, not patched again.

- **`test_solido.py` (invariants suite)**: catalog es/en parity, every
  finding key has its `_rem` pair, CRIT parity, version equality
  (pyproject == server == server.json), README/GIF tool+prompt counts pinned
  against reality, and a deterministic hostile-HTML fuzz battery.
  **It caught a real shipped bug on its first run**: four rendered-mode
  signals (focus_obscured, kbd_trap, reflow_fail, state_contrast) existed
  only in Spanish — English users received the raw signal key as the finding
  text since v3.6. EN texts added.
- **`scripts/versionar.py` / `make release V=X.Y.Z`**: the single command for
  releases — atomic bump of all four files with anchor asserts, fast suites
  as a gate, refuses to proceed on red. Replaces ten releases of manual
  triple bumps.
- **`.githooks/pre-push` (`make hooks`)**: no push leaves this repo with a
  red suite again — the exact failure that shipped 3.9.3 is now structurally
  impossible in any clone that ran `make hooks` once.
- a11ydiff: graceful message without Playwright (was a raw traceback) and
  `diff` now exits 0/2 by verdict (dead `0 if True else 1` finally retired).
- Makefile (test/fast/hooks/visual/release), CONTRIBUTING "hard-won rules"
  section, CI runs the invariants suite.

## 3.9.4 — 2026-09-07 — "fresh eyes, round two" (supersedes 3.9.3: explicit criterion registry shipped)

Same content as 3.9.3 plus the registry fix (26/26 standalone, no import side effects). 3.9.3 was published minutes before the hotfix; same-version republication is not possible on PyPI.

## 3.9.3 — 2026-09-07 — "fresh eyes, round two"

A second from-zero pass over surfaces the first one didn't attack.

- **Protocol battery**: the server under hostile input — unknown tool, missing
  required args, unknown prompt, unknown method, notifications, raw garbage.
  Exactly 5 responses for 7 inputs (notifications and garbage correctly
  ignored), tool errors as isError results, -32601 for unknown methods,
  protocolVersion 2025-11-25 echoed. No crashes, no hangs.
- **CLI coverage gap closed**: image / declaration / snapshot / diff had never
  been executed through the dispatcher by any suite — all verified working
  (diff self-comparison → ok:true).
- **Comparison table honesty**: "✓ (fuller rule set)" vs Lighthouse was not
  sustainable (~41 signals vs ~57 axe rules in Lighthouse) — now states the
  factual "weighted across 26 WCAG criteria". No comparison games in an
  honesty-branded project.
- CLI ergonomics: bare `a11ytoolkit` now exits 0 (help convention), unknown
  subcommand exits 2 with the list; bench/compara.py verified self-contained
  (axe auto-downloads; the 553KB MPL-licensed engine is gitignored, never
  redistributed).
- **Import-order fragility eliminated (found the hard way)**: the 26-criteria
  count depended on `import a11ydom` side effects — removing a seemingly dead
  import in test_cli silently dropped it to 21. The registry is now complete
  and explicit in a11yaudit; the scattered CRIT mutations in a11ydom are gone.
  Meta-lesson recorded: silent str.replace patches need asserts on the anchor
  — this exact failure mode struck three times now.

## 3.9.2 — 2026-09-07 — "fresh eyes"

A from-zero re-review, as if the reviewer had never seen the repo.

- **Security: `a11y_audit_url` no longer accepts non-http(s) schemes.** A
  probe showed `file:///etc/…` was actually opened (local file read via URL —
  an exfiltration channel if a prompt-injected agent points the tool at local
  paths; findings flow back into the conversation). Local HTML has `--file` /
  the `html` argument. Threat model documented in SECURITY.md (rendered tools
  keep file:// for fixtures: the MCP already runs with user privileges; the
  meaningful boundary is exfiltration channels).
- **Language purity enforced by test**: EN outputs no longer leak Spanish —
  ARIA-value labels said `(entero)`/`(número)` and DOM contrast examples said
  "sobre… (p. ej. …)" in English reports. Now language-aware, with a
  kitchen-sink regression test grepping for Spanish in every EN field.
- **False claim removed**: README said "Listed on Smithery too" — the listing
  was never claimed (the badge 404'd and was removed earlier).
- server.py docstring listed 10 of 16 tools (agents reading the module header
  saw a stale map) — complete now. README Development section now lists all
  6 suites. Watch recipe badge step reads `score` or `score_medio` (crawl
  mode has no top-level score — the step would have crashed).

## 3.9.1 — 2026-09-07 — "solidification"

A self-audit found real damage; all fixed with the tests that would have
caught each one.

- **CRITICAL: the CLI dispatcher had been broken since v3.7.0** — `import
  a11ydom` was missing, so EVERY `a11ytoolkit …` command died with NameError.
  The MCP server (what all suites tested) was fine; the public CLI was not.
  Fixed (import + `_main` dispatch mechanism for reflow/kbd).
- **Injection hardening**: this toolkit writes HTML and SVG, so it must never
  be an injection vector — `a11y_autofix` now escapes `title`, validates
  `lang` against BCP-47 shape before writing; `a11y_badge` XML-escapes
  fecha/alcance. Proven by adversarial tests (</title><script>, lang breaking
  out of the attribute, SVG fecha injection).
- **Doc-drift pinned by tests**: "26 criteria touched" is now asserted against
  the real catalog (found it was 25 — 1.4.3 Contrast was never registered
  despite being measured; registered, making the claim true).
- Dead `--stdin-audit` argument removed from the fixer; bench/compara.py now
  auto-downloads axe-core instead of depending on /tmp/axe.min.js.
- **New suite `test_cli.py`**: every CLI subcommand executed as a real
  subprocess against fixtures — the missing layer that let the dispatcher bug
  ship twice. 6 suites in CI now.

## 3.9.0 — 2026-09-07 — "spec-fresh + WCAG 2.2 sweep"

Two evidence-driven passes: the current MCP spec (2025-11-25, via Context7) and
the full WCAG 2.2 criteria list, hunting what is automatable and missing.

- **MCP protocol modernization**: every tool now carries `title` (UI display
  name) and `annotations` per the current spec — readOnlyHint/destructiveHint/
  idempotentHint/openWorldHint. Clients can auto-approve read-only tools:
  less confirmation friction on every call.
- **Five new automated criteria** (26 criteria now touched):
  - **2.5.3 Label in Name** (AA): aria-label must CONTAIN the visible text —
    voice-input users say what they see (static).
  - **3.1.2 Language of Parts** (AA): element-level lang validity, BCP-47
    (static).
  - **2.5.2 Pointer Cancellation** (A, advisory): down-event activation
    suspicion — onmousedown/ontouchstart/onpointerdown (static).
  - **3.3.8 Accessible Authentication** (AA, NEW in WCAG 2.2): captcha
    detection (reCAPTCHA/hCaptcha/Turnstile/inputs) with the alternative
    requirement stated (static).
  - **2.4.11 Focus Not Obscured (Minimum)** (AA, NEW in WCAG 2.2): root-cause
    detection in the rendered audit — sticky/fixed header height vs
    scroll-padding-top. Empirically separated: without padding → flagged,
    with 64px padding → clean. (The per-stop intersection approach was
    discarded: browser minimal-scroll never lands under headers in DOM order.)
- a11y_criterion catalog extended to the new criteria.
- Regression fixtures for all five. 16 MCP tools + 5 prompts.

## 3.8.0 — 2026-09-07 — "the infinite scroll auditor"

The one nobody automates. Documentary basis (verified): Deque's «Infinite
Scrolling & Role=Feed Accessibility Issues» + the ARIA APG Feed pattern;
applicable criteria 2.4.3 (focus order), 4.1.3 (status messages), 2.2.2
(auto-updating). NO official W3C failure technique exists for infinite scroll —
our docs say so instead of inventing one.

- **New tool `a11y_scroll`** (16th): real scrolling batches in Chromium with a
  live-region observer installed before scrolling. Measures: (1) does the
  focused element SURVIVE each batch — the documented failure is re-rendering
  the container, which destroys focus (alta); (2) is new content ANNOUNCED —
  aria-live/status receiving text during loading or role="feed" (4.1.3);
  (3) does the feed END or offer a load-more alternative — footer reachability,
  explicit-load button tried as the healthy path (2.2.2-adjacent); (4) APG
  feed pattern (role=feed + role=article + aria-busy) as positive signal.
- Honest guard: with login/bot walls or non-standard markup (medium.com,
  reddit tested), no unfounded findings — a note explains what was not
  measurable. Best used on feeds you own or can authenticate into (the
  consulting use case).
- Validated: disaster fixture (re-render + silence + unbounded) → focus-loss
  alta + 4 findings; healthy fixture (append-only + role=status announcements
  + load-more + finite) → 100 with announcements recorded. Regression
  fixtures to follow in the test suites.
- 16 MCP tools + 5 prompts.

## 3.7.0 — 2026-09-07 — "escape velocity"

- **New tool `a11y_keyboard`** (15th): keyboard-trap detection (2.1.2) with REAL
  Tab walking — up to 60 real tab presses in Chromium, stop-by-stop. Cycle
  detection identifies the modal pattern; then the decisive test: does ESCAPE
  release the cycle? A modal that cycles and releases is correct and gets NO
  finding; a cycle Escape cannot leave is a trap (high severity, with the
  trapped controls listed). The full tab-stop list comes back too. Nobody else
  automates this — it is the #1 modal complaint.
- Verified: trap fixture (Tab handler with preventDefault, no Escape) flagged
  alta; the same modal with an Escape close handler passes clean; example.com
  walks clean. Fixtures kept in the session bench; static audit confirmed to
  already cover `<template>` content and declarative shadow DOM
  (`shadowrootmode`) — documented, tests added in the suites.
- 15 MCP tools + 5 prompts.

## 3.6.0 — 2026-09-07 — "the toolkit that fixes, honestly"

The requested next axis: not only find — fix, with provable safety. Plus the
one automated check nobody else ships.

- **New tool `a11y_autofix`** (13th): deterministic safe fixes applied to HTML
  with a CLOSED allowlist — unblock viewport zoom (1.4.4), exact autocomplete
  tokens per field (1.3.5: type=email→email, postal/city/country/name patterns),
  missing `<html lang>` and empty `<title>` only when the caller provides them.
  Everything requiring judgment returns in `no_aplicados` with the reason and
  the remediation. Verified by roundtrip: the four findings disappear after the
  fix; judgment findings remain untouched. The anti-overlay: no guessing, ever.
- **New tool `a11y_reflow`** (14th): reflow at 320px — WCAG 1.4.10 (AA) — with
  real horizontal-scroll measurement and the overflowing elements listed. axe
  and Lighthouse do not automate this. Method note embedded (browser zoom
  re-layouts at 320 CSS px; validated empirically against healthy and
  fixed-width pages after the first zoom-based attempt produced false
  positives and was removed).
- Broken Smithery badge removed (404 — listing not claimed yet).
- 14 MCP tools + 5 prompts. Visuals and docs re-synchronized.

## 3.5.0 — 2026-09-07 — "through the shadow boundary"

- **Shadow DOM traversal** in the rendered audit: open shadow roots (up to 20,
  depth 6) are scanned for text contrast (with effective-background compositing
  ACROSS the shadow boundary via host chaining), target size, accessible names,
  labels, images, iframes, tables, aria-hidden and focus states. Findings carry
  readable shadow paths (`mi-tarjeta ::slotted> button`). Closed roots are
  impossible by browser design and the report says how many roots were scanned
  (`shadow_roots`).
- **`list_structure` check (1.3.1)**: illegal direct children of `<ul>/<ol>`
  (axe's `list` rule) — only `<li>`, `<script>` and `<template>` allowed; legal
  flow content inside `<li>` is respected.
- Validated: web-component fixture (all inner failures detected), github.com
  (5 shadow roots) and m3.material.io (2) scanned clean. Regression fixtures
  added. Full triage in bench/README.md.

## 3.4.0 — 2026-09-07 — "validated against reality"

First benchmarked release: axe-core 4.10 run on the same real pages, same
Chromium (bench/compara.py + bench/README.md with full triage).

- **Found a real WCAG failure on gov.uk that axe does not report** (button text
  3.91:1 at 13px — axe leaves contrast as "incomplete"; we compute it).
- **Five false positives driven out**, each with a regression fixture:
  non-tabbable `aria-hidden` controls, honeypot containers, visually-hidden
  skip links reported as tiny targets, single-context generic links (now
  require ≥2), and inline links at 20-24px downgraded to "review" (the 2.5.8
  spacing exception is not measurable without full layout).
- DOM findings now carry the stable `senal` key (budget/SARIF join works for
  rendered reports too).
- Known limit documented: shadow DOM is not traversed yet.

## 3.3.3 — 2026-09-07 — "a command of one's own"

- **The CLI command is now `a11ytoolkit`** (was the generic `a11y` — a name any
  other package could claim, a real pip entry-point clash risk). Unique entry
  points only: `a11ytoolkit` (CLI) + `a11y-toolkit-mcp` (server); the redundant
  `a11y-audit` / `a11y-criterion` / `a11y-sarif` scripts are gone (the
  dispatcher covers them).
- All docs, skill, watch recipe and the demo GIF use the new name.

## 3.3.2 — 2026-09-07 — "one number everywhere"

- Docs homogeneity pass: 12 tools + 5 prompts stated consistently (README table
  title said "(10)", prompts line missed `conformance-wcagem`, server docstring
  missed the two newest tools). No functional changes.

## 3.3.1 — 2026-09-07 — "registry-ready"

- PyPI README now carries the `mcp-name: io.github.kinti/a11y-toolkit` ownership
  marker required by the official MCP Registry, plus a direct PyPI link.
- All version strings aligned (server.json, pyproject, server.VERSION).
- No functional changes.

## 3.3.0 — 2026-09-07 — "close the axe gap, open the ladder"

- **Same-origin iframes in the rendered audit**: the collector runs inside
  same-origin frames (up to 4) and merges findings with an `iframe:` prefix;
  cross-origin frames are skipped (impossible locally, honestly noted).
- **:focus/:hover state contrast** (1.4.3): real hover via Playwright on
  marked controls + computed focus-state contrast; disabled controls reported
  as exempt, per WCAG.
- **ARIA value validation** (static, 4.1.2): boolean tokens, integer/numeric
  attributes, closed token lists (aria-sort, aria-current, aria-live…), and
  aria-controls/aria-errormessage references checked against existing ids.
- **`conformance-wcagem` prompt (5th)** + skill reference `wcagem-guide.md`:
  the three-tier ladder — express screening → agent-verified guided evaluation
  on a WCAG-EM sample → conformance report with a human certifying. The
  automated/gentle bridge from free lint to paid consulting.
- 12 MCP tools + 5 prompts. Version strings everywhere.

## 3.2.0 — 2026-09-07 — "the roadmap: guardrails"

The distribution loop, closed: findings travel in standard formats, progress is
visible, and regressions — not history — are what block you.

- **SARIF 2.1.0 export** (`a11y sarif`, new module `a11ysarif.py`): findings in
  the OASIS standard GitHub accepts for code scanning — per-criterion rules
  with official WCAG Understanding helpUris, severity mapped error/warning/note.
  In PRs, only NEW alerts surface.
- **Accessibility error budget** (`a11y budget`, new module `a11ybudget.py`):
  accept today's baseline; only NEW blocking findings fail the check (exit 2).
  Baseline expiry (fecha_revision) forces periodic re-acceptance. The SRE error
  budget, for WCAG — kills the "40 findings, nobody starts" paralysis.
- **Honest badge** (`a11y_badge` MCP tool + `a11y badge` CLI, new module
  `a11ybadge.py`): accessible SVG with score, date and "automated screening"
  scope — it never says "conformant" (the accessiBe/FTC lesson).
- **Multi-page crawl** (`pages` parameter / `a11y audit --pages N`): light
  same-domain discovery by links, aggregated by mean/worst score and recurring
  signals. Max 20 pages, zero dependencies.
- **Stable signal keys** (`senal`) on every finding — the join key budgets and
  SARIF rules are built on.
- **Scheduled surveillance recipe**: `examples/a11y-watch.yml` — weekly GitHub
  Action: crawl audit → budget gate → SARIF upload → badge.
- 12 MCP tools + 4 prompts. New suite: `test_v32.py`.

## 3.1.0 — 2026-09-07 — "cover the gaps"

Competitive gap analysis (axe-core/Lighthouse, WAVE, Playwright MCP, wcag-mcp) →
everything they do that agents need, we now do too — plus what only we do.

- **Weighted 0-100 score** in both audits (high −12 / medium −6 / low −2),
  with an honest scope note. The Lighthouse adoption hook, on a fuller rule set.
- **ARIA validity** (axe-core core): unknown roles, broken aria-labelledby /
  aria-describedby references, role-mandated state missing (slider without
  aria-valuenow).
- **1.3.5 Identify Input Purpose**: user-data fields without autocomplete.
- **2.4.4 Link Purpose**: generic link texts ("more", "aquí"…) and same-name
  links to different destinations (the WAVE complaint).
- **1.4.2 Audio Control**: autoplay media. **Duplicate accesskeys**,
  multiple labels on one field, duplicated unnamed landmarks.
- **New tool `a11y_criterion`** (11th): plain-language explanation of any
  criterion — what it requires, typical failures, which tool verifies it.
  Covers the wcag-mcp knowledge gap, wired to the auditor's own criteria.
- **a11y_snapshot now captures the computed accessibility tree** (Playwright
  ariaSnapshot — what a screen reader announces) and a11y_diff reports
  tree changes. The Playwright-MCP gap.
- 11 MCP tools + 4 prompts. CLI gains `a11y criterion`. All suites updated.

## 3.0.0 — 2026-09-07 — "global readiness"

The accessibility layer for AI coding agents: audit → fix → document → watch.

- **New tool `a11y_audit_dom` — rendered audit** via local Playwright/Chromium:
  real computed text contrast against effective backgrounds with alpha
  compositing (1.4.3), minimum target size 24×24 (**2.5.8, new in WCAG 2.2**),
  visible focus-indicator heuristic (2.4.7), and the static checks on the live
  DOM. Same report shape as the static audit.
- **Static auditor 10 → 13 criteria**, every finding now includes a concrete
  `remediacion`: keyboard onclick on non-interactive elements (2.1.1), timed
  meta refresh (2.2.1), missing skip mechanism/main landmark (2.4.1), invalid
  BCP-47 lang, captions on video (1.2.2), tables without th (1.3.1),
  target=_blank without warning (3.2.5), empty headings, orphan labels, input
  type=image without alt, duplicate ids; select/textarea now audited for
  labels (they were not before).
- **`a11y_audit_url` accepts raw HTML** (`html` argument) — audit pages you
  already fetched; also `timeout`, gzip responses, non-HTML rejection,
  en/es output.
- **Contrast engine upgraded**: 148 CSS color names, `hsl()/hsla()`,
  `rgba()`/`#rrggbbaa` with alpha compositing, modern space-separated syntax
  (`rgb(255 0 0)`); color suggestions now minimize real RGB distance
  (400-step search).
- **4 MCP prompts**: `audit-page`, `fix-contrast`, `pre-deploy-check`,
  `declaration-eaa` (slash-commands in supporting clients).
- **English-first tool descriptions** and server `instructions` — what agents
  worldwide read; es/en still selectable per call.
- **Distribution**: PyPI-ready packaging (embedded `arialive_js` module — fixes
  data-files install location), official MCP Registry `server.json`, PyPI
  publish workflow (trusted publishing), CI adds package smoke test + build,
  new console script `a11y-audit`.
- **Skill rewritten** (standalone, EN-first, decision table + manual WCAG 2.2
  checklist reference) and bundled at `skill/` with an installer; works with or
  without the MCP via `uvx`.
- README rewritten EN-first with per-client install (Claude Code/Desktop,
  Cursor, Windsurf, VS Code) and an honest comparison vs axe/Lighthouse.
- 10 MCP tools + 4 prompts. Test suites: contrast, audit, dom (self-skipping),
  mcp.

## 2.3.0 — 2026-08-22
- **The toolkit is now ONE toolkit**: a11ydiff integrated into the MCP as `a11y_snapshot`,
  `a11y_diff` (inline JSON or file paths) and `a11y_diff_urls` (staging vs prod in one call).
- **Unified CLI `a11y`**: one command for everything — `a11y pair`, `a11y image`,
  `a11y audit`, `a11y declaration`, `a11y snapshot`, `a11y diff`.
- 9 MCP tools total. No new capabilities — pure integration of the existing four modules.

## 2.2.0 — 2026-08-22
- **New tool `a11y_audit_url`**: express WCAG audit of any URL (alt, accessible names,
  form labels, lang/title, heading skips, blocked zoom, tabindex>0, iframe titles),
  zero dependencies, with severity-ranked findings and honest scope note.
- **contrast image**: automatic hostile-zone detection (`zona_peor`, 3×3 grid) and
  auto-sampling guard for huge regions.
- Auditor hardening: names from inner text (incl. links inside headings), implicit
  `<label>` wrapping and explicit `for=` associations recognized.
- Tests: audit fixtures + grid test; CI runs the three suites.

## 2.1.0 — 2026-08-22
- Multilanguage es/en across all tools; EN declarations use Directive (EU) 2016/2102
  and EAA (2019/882) wording; aria-live monitor UI localized (window.ALM_LANG).

## 2.0.0 — 2026-08-22
- First public release: 5 MCP tools (contrast pair/image, suggest color, declaration
  generator, aria-live snippet) + a11ydiff CLI. Zero-dependency stdio server.
