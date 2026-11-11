# Changelog

## main — pendiente
- **`a11ygate` — the write-time guard** (the edit-gate pattern, our engine under it): `a11ytoolkit init` now installs a real client hook (Claude Code PreToolUse) that audits every save of a user-facing file against git HEAD — NEW high/medium findings refuse the write with the fix right there (the AI holding the pen applies it instantly); low severity and known findings warn. Kinds, not counts (the engine aggregates); fails open on unreadable input; `A11Y_GATE=off` disables; `--no-gate` skips install. The gate refuses on OUR engine error too... never: it fails open by design. What it does NOT do: it is not a conformance verdict — the refusal carries the honesty line.
- **README: the managed path, said out loud** — the engine section now states the covenant plainly: building your own monitoring with cron + budget/diff is legitimate and deliberate, and a11y.es exists for those who would rather not maintain it (free to start with 3 sites; pricing promises live on a11y.es, not here).
- **`onfocus_blur` — focus-stealing static signal (2.1.1, high)** (the exact case GitHub's scanner misses, their issue #288): an element whose `onfocus` handler calls `blur()` removes itself from keyboard reach entirely — aggregate high finding with the element snippet as example and annotate-compatible paths. Harmless onfocus handlers (highlight etc.) do not trigger.
## 5.27.0 — 2026-11-06 — "the ladder: annotate, trace, locate, seal"
- **`financial_no_confirm` recognizes the Spanish confirmation-checkbox
  pattern** (found by eating our own cooking: the Action flagged a11y.es
  forms that DO have an enforced review checkbox named `confirmo`): the
  3.3.4 checkbox regex was anglocentric (terms/accept/agree) and could not
  see `confirmo`, `confirmar*` or `revisado` — the most common Spanish
  pattern there is. Boxes whose name carries confirm/revis now count as
  the review step; an unrelated checkbox still does not.
- **`alt_quality` — low-quality alt text signal (1.1.1)** (stolen from
  GitHub's accessibility-scanner alt-text plugin, the honest way): alt that
  PASSES the presence check (axe `image-alt` included) but says nothing —
  filenames (`chart.webp`, `IMG_2023.jpg`), generic words (`image`, `foto`,
  `icon`, `logo`), placeholders (`-`, `x`), and the SAME alt repeated on 4+
  images (an icon list that should be `alt=""`). Aggregate medium finding
  with examples, distinct-value dedupe, annotate-compatible paths;
  presentation/hidden/empty alts excluded (missing alt stays `img_no_alt`).
  Scores move on pages with junk alts — regression tests pin the fixture.

- AGENTS.md documents the constellation (the private pro layer, the
  vendoring products, the frozen draft generators and what they imply for
  any change here) — the map agents and contributors read first.

- **Founder decision (2026-11-04): the consulting playbook leaves the
  public engine.** Moved to a private repo (`a11y-toolkit-pro`, what our
  SaaS consumes by pin): the Section 508 GSA applicability tree
  (`--standard 508`), the procurement-annex generator
  (`scope --solicitation`), the WCAG-EM sampling methodology
  (`a11ywcagem` CLI + the conformance-wcagem MCP prompt), and the
  remediation-planning layer (`a11yplan` CLI). Rationale: none of it has
  developer-community value; it IS the consulting playbook (what to ask,
  how much to audit, how to word a tender annex, in what order to
  remediate). The wizard keeps wcag22/EN 301 549/RGAA; `scope` keeps the
  same three standards; the prompts go 6 → 5; the tools stay 37. The
  docs say "moved to the private pro layer" — no mystery, no lie.
- **The conformance DRAFT generators (VPAT, OpenACR, declarations) stay
  public but FROZEN** (stated in each module docstring): the machine
  fills Remarks/texts, never the claim — every document prints that a
  qualified human must set levels and sign. They receive maintenance
  fixes only; new conformance capabilities go to the SaaS. This is the
  Deque line: the engine stays open, the practice stays ours.
- Tests for the moved pieces live in the pro repo now; the public suite
  re-verifies their ABSENCE (wizard without 508/annex, scope enum
  without 508, prompts == 5, locales without std508/sol).

## main — pendiente — "external QA 2026-11: round 4 — fresh-eyes from zero"

- **Fresh full-repo re-analysis from zero** (6 fresh reviewers + live chain
  on the post-120-fix tree) found what a day of fixes leaves behind —
  every finding verified live before fixing, every fix pinned
  (tests/test_round4.py, 31 pins). One regression of our own caught and
  killed: a duplicated edit had registered img-alts twice for
  aria-labelledby resolution ("Acme Acme").
- **Static engine**: svg[role=img] with no name is now a 1.1.1 finding (the
  svg dispatch was consuming the tag before the role machinery — the
  svg-title lookup was dead code); captions/descriptions counted per-TRACK
  anywhere now count per-VIDEO (two tracks on one video no longer pardon a
  second video; template/orphan tracks never pardon); nested
  presentation/template tables no longer corrupt the enclosing table's
  verdict (identity-keyed stack); border="1" means DATA table per the HTML
  spec (only border=0 stays layout-suspect) — a 1990s visible-borders data
  table can no longer vanish; template text is inert everywhere (was
  feeding reading level, 3.1.2 lang checks and control names);
  stray-click delegation only exempts on REAL operability (a href-less
  <a>, hidden/disabled inputs or template content no longer pardon the
  wrapper); a href-less anchor dragged past its </div> is still counted;
  ids inside <template> no longer exist (dup_ids FP, broken-ref FN);
  username/fullname inputs now trigger 1.3.5; an SVG-root document gets no
  HTML title_missing; multi-viewport pages point zoom findings at the meta
  that decides; tabindex superscripts can no longer destroy the report;
  the redirect guard allows same-host hops (localhost dev /app→/app/,
  http→https — the user's stated host preserves their intent) and its
  message travels the bilingual catalog; .a, .b {} grouped CSS selectors
  feed BOTH classes to the hidden-class sets; an svg <title> no longer
  counts as VISIBLE text (2.5.3 label-in-name).
- **Live microscopy found the last FP class**: the W3C WAI search button
  carries its aria-label on the child <svg> — accname 2F.ii includes
  descendant names, so the button IS named; w3.org/WAI now audits 94 with
  zero false highs (was 82 with one). aria-hidden inner elements never
  contribute names.
- **Rendered layer**: the forms driver's 3.3.1 HIGH signal was dead (JS
  wrote `campos`, Python read `fields`) — restored; the scroll tool
  crashed with auth_state (BrowserContext.new_page takes no viewport);
  sr_transcript leaked one Playwright driver per call (pw.stop() now
  guaranteed); the browser pool never pooled for browser='auto'; vertical
  tablists (aria-orientation) are no longer flagged HIGH for not answering
  ArrowRight (ArrowDown accepted per APG); rendered severities aligned
  with the static engine (zoom_max high, no_bypass/no_h1/no_headings low)
  — the round-1 claim is now true on BOTH layers; trace via the CLI hub
  works (argparse subcommand prepended — the README example was a lie in
  both languages).
- **Conformance chain**: a disprover-processed SITE report re-animated its
  dead findings in the pack (the flattening preferred the nested unmarked
  copies over the re-checked top-level ones) — pinned with the real
  audit→disprove→evidence pipeline; VPAT/OpenACR Remarks were EMPTY for
  crawl packs (the citation walker did not descend into reports[]) —
  fixed both directions (clean crawls cite, dead findings never do);
  earl flattens sites and survives hostile JSON; build_pack/
  normalize_report accept findings-as-dict without tracebacks; the
  patches CLI --lang actually reaches the build; the solicitation annex
  survives a criterion without a title.
- **Infra/docs**: the vscode extension spawns npx.cmd on Windows (was
  silently dead for every Windows user); the skill taught agents to read
  `remediacion`/`score_nota` — keys that do not exist (now remediation/
  score_note); the Cursor rule referenced a dead a11y_audit tool; the
  pre-push hook runs `make fast` (its hand list had drifted 6 suites from
  the Makefile — the exact class that hid test_locate); versionar prints
  the failing suite's output tail and catches timeouts; count pins now
  enforce EXACT tool counts on plugin.json/npm-README (a stale 34 passed
  the old <=) and the Spanish README table is pinned row-by-row with its
  self-demoting "may lag" disclaimers deleted; README.md's garbled
  Install paragraph repaired, corpus-verify line parity, Development
  sections teach `make test`; gen_llms derives the prompts count; the npm
  README describes the self-contained launcher; the corpus builder
  defaults to 2026.11.0; the verify_pack not-applicable pin was dead code
  after a sys.exit() — revived as a real build_scope→build_pack→verify
  chain; the audit-report schema's "validated programmatically" claim
  softened to what is true. No release is cut from this entry.

## main — pendiente — "external QA 2026-11: round 3 — the gate and the surface"

- **The gate now runs everything.** `make test` executes EVERY
  `tests/test_*.py` by discovery (sorted loop) instead of a hand-picked
  list that omitted 8 suites — `test_locate` had been broken (pinned to
  36 tools, tool #36) with no gate seeing it. The release gate
  (`scripts/versionar.py`) and CI (`.github/workflows/ci.yml`) now run the
  same full discovery — a red suite can no longer hide outside the list.
  AGENTS.md's release-flow wording updated to match.
- **scripts/verify_pack.py accepted only 6 of the 7 pack states**: packs
  built with a human-confirmed scope (not-applicable rows) were rejected
  by the independent verifier — exactly the packs an auditor uses after an
  applicability analysis. 'not-applicable' added, pinned by a test that
  builds a scoped pack and verifies it.
- **`browser` param was decorative** in every rendered tool: 13 direct
  `p.chromium.launch()` sites now go through the existing browser pool
  (`_get_browser(preferred=…)`) — a11ydom's nine rendered functions plus
  scroll/patterns/trace; forms/hover gained the param; the MCP schemas for
  forms/hover/scroll now declare what the dispatch passes
  (schema↔dispatch contract green).
- **Spanish leaks closed in English paths** (the bilingual invariant,
  enforced nowhere until now): a11ydom load errors and the
  forced-colors/reduced-motion limits are bilingual via the function's
  `lang`; a11ydiff's note bilingual (+ `diff(lang=)`); journey validation
  errors bilingual; disprove reject_reasons bilingual; ledger
  gaps/summary/recurrence notes bilingual (+ `lang` param, MCP schema);
  the Nu-validate notice bilingual; autofix's `not_applied` respects
  `lang` (the audit inside was hardcoded to English) and its do-not-touch
  reasons are bilingual. The snapshot key `arbol_accesible` is now
  `accessibility_tree` (the public surface is English — readers accept
  the old key: existing snapshots still diff).
- **a11ycrit `_C` es branch: ~55 untranslated strings** (typical failures
  and how-to-checks were English inside the Spanish rows) translated; a
  phrase-level leak test pins it (loanwords like tooltips/sliders are
  deliberate).
- **hsl() with slash alpha lost the channel**: `hsl(0 0% 0% / 0.5)`
  parsed opaque while rgb-with-slash worked — same treatment now, pinned.
  SARIF `driverVersion` was frozen at '3.2.0' — derived from the single
  version source. `--standard rgaa` was silently dropped in site crawls
  and `--changed` (`_apply_standard` only knew EN 301 549) — RGAA
  enriches post-hoc now, pinned.
- **Honest server surface**: `_RETURNS` no longer promises output_path
  writes for badge/autofix/evidence (they return content; the agent writes
  the file); a11y_evidence passes `lang` through to build_pack (a Spanish
  matrix was impossible via MCP); `destructiveHint` is now true only for
  a11y_forms (which really submits data to the audited site) — writing
  the file you asked for is not "destructive" in MCP semantics.
- **The badge practices what it measures**: default palette colors all
  pass 4.5:1 with the badge's white text (were 1.69-3.22:1) — computed
  with the toolkit itself and pinned. Declaration `--feedback` URLs
  render as links (same as complaints, RD 1112 art. 10.1(b)). vtt CLI
  catches network errors (clean JSON, exit 1). audit_forms dead code
  removed; a11yfix CLI declares only the languages that exist (es/en);
  docs/ARCHITECTURE corrected (86 criteria, not 56); vscode/package.json
  versioned with the engine (was an orphan 0.1.0; versionar bumps it).
  What does NOT change: tool count (37), prompts (6), scores, no release.

## main — pendiente — "external QA 2026-11: engine truth pass"

- **Round 2 (same day, "soluciona todo")**: element paths extended to the
  attribute-level signals — zoom_no/zoom_max point at the viewport meta,
  meta_refresh at its meta, field_label/blank_no_warning/tabindex_pos at
  their elements (bugs.html fixture: 18/27 findings now carry paths, up
  from 6/27; the rest are page-level or inherently ambiguous — duplicate
  ids/accesskeys make selectors meaningless by definition). Layout-table
  heuristic: a `<table>` with presentational-era attributes (width/
  cellpadding/cellspacing/border) and NO data markers (th, caption,
  summary, scope, headers) is treated as layout — not flagged under 1.3.1
  (the classic false positive on 1990s-style sites like Hacker News);
  with any data marker the th requirement stands. SECURITY.md documents
  the default private-IP redirect guard. Both READMEs gain the
  `a11ytoolkit dom` CLI line (the command registered earlier today).
  Pinned by regression tests (paths per signal, layout-vs-data table).

- **Static engine — 13 false positives and 3 false negatives fixed, every
  one reproduced live before the fix and pinned by a regression test.**
  A page built only from canonical W3C patterns (search landmark,
  `<template>`, muted hero video, SVG-title icon button) scored 32/100
  with four HIGH false findings; it now scores 96 with none. What changed:
  `role="search"` is a landmark, not an unlabeled field (the W3C tutorial
  pattern no longer yields HIGH 3.3.2); `<template>` content is inert
  (per the HTML spec — no more phantom missing alts/labels from web
  components); an SVG `<title>` is the svg's accessible name (the
  recommended icon-button pattern has a name); autoplay with `muted` or
  `controls` is not 1.4.2; `no_status_regions` (4.1.3) only fires on
  strong interactivity evidence, as review severity; the hamburger-menu
  pattern (`display:none` by class + aria-hidden) is not a HIGH 4.1.2
  failure; `<track>` without `kind` counts as subtitles (the spec
  default); `role="presentation"` tables are not asked for `<th>`;
  `aria-rowcount="-1"` is the ARIA-mandated unknown-total value; a
  `<div onclick>` wrapping a native control is delegation, not a 2.1.1
  failure; accesskey is no longer reported under 2.1.4 (it needs a
  platform modifier); an image inside a heading is not an image *of text*
  (logotypes are exempt per 1.4.5 itself); a captcha outside an
  authentication form is not 3.3.8. New review signal `role_no_tabindex`
  (low, 2.1.1): interactive roles without tabindex. Severity corrections:
  `no_bypass`/`no_h1`/`no_headings` are best-practice LOW (axe's own
  tagging), not scored mediums — a bare page no longer loses 12 points
  for structure WCAG does not require; `zoom_max` matches `zoom_no` at
  HIGH (ACT b4f0c3 does not distinguish them).
- **Static engine — robustness and precision infrastructure.** A single
  valueless attribute (`<div role>`, `<meta name>` — valid HTML5) no
  longer destroys the whole report (`'error': unparseable HTML'`); the
  fuzz suite now pins this class. Duplicate attributes resolve first-wins
  (HTML spec) instead of last-wins. Mismatched end tags pop the element
  stack to the matching frame (a stray `</span>` no longer
  mis-attributes text). `label[for]` pointing elsewhere no longer labels
  the field it wraps (FN closed). `aria-labelledby` pointing at an image
  resolves to its alt. Most element-level findings now carry element
  paths (ctrl_name, aria_hidden_focusable, click_nonfocusable,
  video_captions, video_autoplay, table_no_th, dup_ids, the new
  role_no_tabindex) — the annotation kernel marks what it can locate.
  Redirect hops are resolved and rejected when they land on private
  networks (loopback/RFC1918/link-local incl. cloud metadata): the URL
  the user typed is never blocked, only implicit redirect pivots
  (defense for the vendored server-side use; injection point unchanged).
  audit_site survives a hostile page (error page skipped, crawl
  continues) and recomputes per-page summaries. 2.4.5 no longer fires on
  single-page samples.
- **i18n**: n=1 messages render in grammatical singular in both languages
  ("1 interactive element", "1 campo de formulario") via the CLDR
  one/other machinery — 21 keys converted; the mojibake in the Spanish
  PDF contrast remediation fixed; fetch/parse errors travel through the
  catalog (no more Spanish-only or English-only error strings).
- **Deterministic fix chain (a11yfix/a11ypatches/a11yannotate)** — the
  "provably safe fixes" promise repaired: build parameters (lang/title/
  form_errors) are sealed in the patch-set and verify replays with them,
  so form-error sets no longer verify as false "engine drift or tampered"
  (P1: build ran with form_errors=True, verify re-ran with False);
  mask/unmask order fixed (a commented-out script no longer leaks
  \x00A11YFXMASK tokens into "fixed" output); the own-error-handling
  guard reads the real script bodies (was reading masked text — always
  empty); the form/textarea opening-tag regexes are quote-aware
  (`action="/search?q=a>b"` is no longer rewritten to a broken tag —
  reproduced and pinned); self-closing inputs stay well-formed;
  maximum-scale≥2 no longer records a phantom viewport fix; lang
  detection ignores xml:lang/data-lang and fills empty lang="" in place;
  the autocomplete hint requires word boundaries (name="hotel" is not a
  phone); the error-layer JS injects before `</BODY>` case-insensitively.
  annotate: a stale report (sha mismatch) no longer injects marks on
  colliding paths — everything falls to unplaced; two findings on one
  element share a single data-a11y-id.
- **Evidence/conformance chain — honesty repairs.** build_pack flattens
  site-crawl reports (findings nested in reports[] were silently dropped:
  a crawl with real failures produced an all-not-flagged pack —
  reproduced, fixed, pinned); VPAT/OpenACR Remarks no longer quote
  findings the disprover rejected; **behavior change: review-level
  signals no longer auto-set "Partially Supports" — every level starts
  Not Evaluated, only an automated fail forces Does Not Support, the
  evidence stays in Remarks** (the machine fills Remarks, never the
  claim, now also in the level mapping); SARIF filters dead findings and
  degrades on hostile --from-audit JSON; the badge escapes quotes in
  aria-label (attribute breakout), truncates before escaping and escapes
  brand; apply_scope recomputes effort_pending/manual_pending (excluded
  criteria cost zero); RGAA scope honors human answers; Section 508
  machine proposals never override a human answer in either direction;
  EN 301 549 software targets surface honest human-review rows for
  clauses 11.5-11.7; the declaration renders --complaints URLs as links
  (RD 1112/2018 art. 10.1(b)) and reads the clock once.
- **Behavioral layer**: a scripted `goto` no longer kills a11ytrace
  (collector re-injected, guarded drain, null-safe summary); journey
  records seal their language and verify cross-language without false
  "tampered"; the snapshot focus walk stops by element identity
  (duplicate signatures no longer truncate the tab order) and diff
  counts duplicate controls; engines gives the pip advice when Playwright
  is missing; scroll exits 1 on failed load; the ledger persists
  resolutions with their original date and computes criteria-without-
  signal for audited URLs; WCAG-EM aggregate rejects unknown statuses and
  tolerates null effort; the corpus seals its README (submission
  contract) — corpus rebuilt as 2026.11.0; budget/sarif/plan hardening.
- **Documents**: PDF `re` rectangles are no longer parsed as RGB (false
  low-contrast on nearly every designed PDF); TJ-array text is visible to
  the contrast check; hex `/Alt` counts; decompression enforces a
  cumulative budget; DOCX scores use the shared weights (cross-mode
  comparability) and `<w:b w:val="0"/>` is not bold; VTT accepts a BOM
  and measures reading speed on visible text (markup excluded, voice
  tags included); contrast converts hue units properly (turn/rad/grad),
  returns clean errors on garbage colors instead of tracebacks, rejects
  PNG color-type 4/interlaced with clear errors, and rounds the ratio
  before the verdict (display and verdict always agree).
- **MCP/CLI**: stdio forced to UTF-8 (a CJK finding can no longer kill
  cp1252 pipes mid-protocol); initialize answers with the supported
  protocolVersion; a11y_ledger rejects invalid actions by name;
  a11y_aria_live_snippet defaults to English per its schema;
  a11y_journey_verdict accepts verify-only calls; the rendered
  nameOf resolves multi-id aria-labelledby with correct accname
  precedence (labelledby > aria-label > label > content > title) — it now
  agrees with the static layer; the router routes "document the
  accessibility…" to the statement goal and speaks Spanish in diagnosis
  evidence; **the four CLI commands the READMEs advertise now exist:
  criteria (criterion alias), dom, hover, wizard** (they all exited 2);
  criterion exits 1 on unknown codes with bilingual errors and honors
  --standard/--target/--json.
- **Packaging/publication**: rgaa.json ships in the wheel/sdist (it
  crashed every pip-installed `--standard rgaa`; the CI smoke test now
  imports it from the installed copy); the CHANGELOG's accidentally
  duplicated history removed (1773 lines) and 11 tagged versions dated;
  the Spanish README's broken code fence (a heading rendered inside the
  block) and tool-table drift fixed; the stale "33/34 tools" counts
  (server router text, plugin.json, npm/README) corrected to 37;
  the npm tarball no longer ships __pycache__; the 508 citation
  corrected to E205.4.1; a stray run artifact (evidence-pack.json)
  removed from the tree and gitignored; the Nu validator UA derives
  from the single version source. What this does NOT change: tool count
  (37), prompts (6), the score weights, zero telemetry, and no release
  is cut from this entry.

### earlier main-pending work (same unreleased batch)

- **License & name — MIT for the code, the name is reserved** (founder
- **`a11y-journey/1` — the sealed journey record** (deal-flow pick, the
  "replayable traces" the whole monitoring market sells): `seal_record`
  bundles the walk (the agent's steps as walked), the outcome, the
  deterministic verdict and an optional a11ytrace capture into one
  SHA-256-sealed envelope; `record_verify` re-derives the verdict from the
  stored steps (the scoring is deterministic) and demands it matches —
  tampering is caught twice, by sha AND by re-scoring. MCP:
  `a11y_journey_verdict` gains `seal` (return the record) and
  `verify_record` (judge a record instead of steps); the plain verdict
  path is untouched. Same input → same record: baselines and deltas now
  have a portable artifact.
- **`a11y_patches` — sealed patch-sets of the deterministic fixes**
  (deal-flow pick, the "signed repairs verified after updates" demand):
  `build` runs autofix once and seals the record — format `a11y-patches/1`,
  source SHA-256, engine version, what was applied AND what was declined.
  `verify` re-runs the deterministic fixes and cross-checks: same page →
  same fixes or nothing applies; different page → the set declares itself
  `stale` (patches never blind-apply); divergence → `mismatch` with both
  lists. Serves the doctrine "fixing the original web is the client's job":
  the agent takes the JSON upstream. Tool #37, CLI `a11ytoolkit patches`.
- **`a11y_locate` — find an element by its accessible name** (deal-flow pick,
  "Semantic Locators" demand): parses with the SAME `_Auditor` the audit uses
  (shared deterministic routes and naming — the locator and the auditor cannot
  drift) and returns the route selector + confidence for controls, headings,
  images with alt, iframes with title and fields with an explicit name. The
  honesty rule intact: several elements sharing the name → `ambiguous: true`
  plus the full candidate list (`multiple` to list anyway), never an invented
  pick. Headings now carry their route in `headings_raw` (the auditor stamps
  the path at start-tag). What it does NOT do: no fuzz, no rendering — static
  HTML only. Feeds agents that edit code by selector and panel deep-links.
  Tool #36, CLI `a11ytoolkit locate`.

- **Per-element annotation kernel** (`a11yannotate`): every element gets a
  deterministic CSS route during the parse (`tag:nth-of-type(n)` from the
  root; ids ignored by design — duplicate ids cannot break identity) and
  findings can carry `paths`. `annotate(html, report)` re-parses the same
  html with the SHARED route algorithm and injects `data-a11y-id` attrs by
  byte-exact offset surgery: the copy equals the original except the
  injected attributes. Reports seal their source (`source_sha256`);
  annotation flags `source_mismatch`. CLI: `a11ytoolkit annotate`.
- **Standards workbench**: `--standard 508` on scope (the GSA "Determine
  which Standards apply" tree as data — product questions, WCAG
  exceptions for non-web E203/E204, chapters 302/502/503/504/602/603),
  `--solicitation FILE` (procurement annex es/en from the scope:
  numbered requirements by principle, confirmed exclusions with reasons,
  evidence list, traceability to the scope sha), `--targets web,documents`
  (multi-ICT combined scope, clauses dict per target), families with
  `status_per_target`.
- **`wizard` — the guided entry point** (the Canadian pattern, inverted,
  in the terminal): 2-3 questions a person CAN answer (what are you
  building, which standard applies to your market, the 508 product
  questions) configure everything: the audit runs with the right
  standard, the scope artifact carries the machine proposals, and the
  tender annex is generated in the chosen language — landing next to the
  scope. Everything it composes is also available as the individual
  non-interactive commands (it composes, it does not hide); piped stdin
  works (tests, CI) and an exhausted stdin aborts gracefully pointing to
  those commands.
- **`criteria --list --filters`**: the offline Quick Ref — `--level`,
  `--new-in 2.2` (the nine 2.2 SC), `--signal-filter yes|no`,
  `--standard en301549 --target` (clause per row), `--json`.
- **Community invitation layer** (from the community-growth research: the
  entry point must be concrete and labeled the way the good-first-issue
  indexes crawl): the **"Add a language (translation)" issue template**
  (pre-labeled `good first issue` + `help wanted`), **Community +
  Contributors sections in both READMEs** (contribution ladder:
  translate → docs → bug → feature; credit promised per release), and the
  CONTRIBUTING translations bullet rewritten to point at the seeded locale
  issues (fr, pt-BR, de). What it does NOT do: no external translation
  platform (Crowdin/Weblate deliberately deferred until 3+ languages — plain
  git/PR by design), no contributor bot.
- **`engines` — cross-engine behavioral matrix** (the cross-browser lab
  pattern): ONE url snapshotted in chromium/firefox/webkit (or
  `--engines chrome,msedge`), pairwise divergence per pair. DOM-level facts
  (added/lost/renamed interactives, focus-order fork) BLOCK (exit 2); the
  engine-computed accessibility tree is reported as `tree_changed` but never
  blocks (engines legitimately compute some roles/names differently). Honest
  `engines_failed` per engine and `insufficient_engines` (fewer than 2 launch
  → exit 1, never a fake pass). `a11ydiff.snapshot` gains `engine=`.
  What it does NOT do: no screen-reader binaries (NVDA/JAWS/VoiceOver are
  separate AT, not engines), no cross-OS matrix, no cloud farm — the engine
  matrix runs where you run Playwright.
- **Structural budget** (`budget --init-snapshot` / `--snapshot`): the SRE
  error-budget doctrine applied to the RENDERED structure. Today's snapshot
  is ACCEPTED as the baseline (stable keys: `#id` or tag+name+href); only
  what is NEW blocks — added interactives (up to `max_new`), a lost baseline
  element (`removed_block`, on by default: it contradicts the approved
  baseline), a reorder of the surviving focus chain (relative order of common
  keys, same semantics as the diff — appended new elements are governed by
  `added`, not double-punished as focus churn), expired `review_date`. Exit
  0/2 like the static budget. What it does NOT do: it does not judge whether
  the accepted baseline is accessible (the audit and its own budget do that)
  — it freezes structure so a release gate survives noise.
- **`contrast-dom --walk` — perceptual pass over every rendered text**
  (the design-system-facing layer of the contrast family, idea seed: measure
  what users SEE, not declared values): per-element table over all visible
  text — computed color vs effective background with alpha compositing,
  WCAG large-text threshold from the COMPUTED font-size/weight (24px, or
  18.66px bold → 3.0; else 4.5), verdict per element, `contrast.suggest`
  color for the worst flat-background fails. Text over images/gradients is
  PIXEL-sampled (worst case, same mechanics as contrast-dom) up to
  `--max-sample`; the rest is declared `unmeasured`, never invented.
  `--dark` adds a second pass under `prefers-color-scheme: dark` plus the
  delta (new fails / resolved) — display conditions the declared CSS cannot
  show. What it does NOT do: no shadow DOM/canvas/video/pseudo-element text,
  no AAA pass/fail claims — a filter finding (1.4.3), not a verdict.
- **Journey catalogue grows**: 6 new friction patterns with bilingual
  remediation (`journey_drag_only` 2.5.7, `journey_error_no_suggestion`
  3.3.3, `journey_focus_not_visible` 2.4.7, `journey_hover_only` 1.4.13,
  `journey_reflow_breaks` 1.4.10, `journey_zoom_blocked` 1.4.4) and
  recommended task kinds (sign-up, checkout, password-reset, search,
  onboarding, settings, data-export, custom) documented across the MCP
  schema and the blindfold-task prompt. Kinds stay free-form (comparability
  by convention, not enforcement); the journey test now derives its criteria
  whitelist from the A/AA catalog instead of a hardcoded list.
- **`trace` — behavioral trace + journey gate** (`a11ytrace`): one keyboard
  walk of a page recording PER TAB STEP the focused element's stable
  signature (shared `FOCUS_KEY_JS` with the snapshot — one key doctrine),
  the aria-live announcements the step triggered, and the url, plus the
  accessibility tree at the end. The collector is SILENT (no panel
  injected): a trace must not mutate the page it measures. `trace diff`
  compares two traces: a lost or forked focus sequence BLOCKS (exit 2);
  announcement counts are informational (a collapsed announcement layer is
  flagged, not gated). The journey release gate that completes the ladder:
  structure (`budget`) → rendered structure (`engines`) → journey (`trace`).
  What it does NOT do: it captures the tree/live-region layer, not
  synthesized NVDA/JAWS speech (real AT testing stays human/agent —
  a11y_journey_verdict is the complement); it does not script clicks (v1 is
  the keyboard walk).
- **`patterns` — APG keyboard contracts, tested live** (`a11ypatterns`):
  detect the widget pattern in the rendered page and PROVE its keyboard
  contract: dialogs (Esc closes; focus stays inside a modal), tablists
  (ArrowRight/Left move focus — roving tabindex; selection follows focus or
  Enter/Space), disclosures (activation flips aria-expanded). Findings
  family `pattern_*` with bilingual remediation (new `patterns` locale
  section). What it does NOT do: only patterns VISIBLE at load — opening a
  closed dialog means guessing a trigger flow, never acceptable on a live
  site; combobox/menu/slider are declared future operators, not silent
  gaps. A clean pass proves THESE contracts at THIS moment, not full APG
  conformance.
- **`canvas_no_accessible_layer` — the data-viz signal (1.1.1)**: the audit
  never looked at canvas (svg[role=img] without a name was already covered
  by img_no_alt — verified, not assumed). Static: a canvas with no
  aria-label/labelledby/title/role and no fallback text is flagged MEDIUM —
  an honest filter, because chart libraries routinely inject the layer at
  runtime; the RENDERED pass is the judge (computed accessible name in the
  live DOM → HIGH). Conservative: decorative/hidden canvases are never
  accused. What it does NOT do: no chart-type detection, no data-table
  equivalence heuristics — those are review-level.
- **`ledger recurrence` + evidence `build` — the review queue without ML**
  (the deterministic core of "predictive guardrails"): `ledger recurrence`
  aggregates the ledger itself as the model — chronic signals (active on
  many urls, or resolved somewhere and still active elsewhere = `recurring`),
  hot urls by score, review queue note. Evidence pack gains an optional
  `build` reference ("git:sha" or JSON commit/ci) SEALED into the pack
  sha256: the chain between the WCAG claim and the build that produced it.
  What it does NOT do: no predictions, no risk scores — ranking of what the
  ledger actually saw, nothing more.
- **`trace --script` — scripted real journeys**: a JSON action list
  (`click`/`fill`/`select`/`press`/`wait`/`goto`, each with a CSS selector)
  replaces the keyboard walk — the trace records what a REAL journey does,
  step by step, with the same focus signature and the same announcement
  collector, so `trace diff` works identically over scripted traces. A
  failed action is recorded as a step (`(failed: …)`), never swallowed.
  What it does NOT do: no auto-discovery of journeys (you write the script),
  no password entry (values land in the trace file — never put secrets in a
  script; use test accounts).
- **`patterns` grows to 6 operators — combobox, menu button, slider**:
  combobox (ArrowDown opens the popup + flips aria-expanded; Escape closes),
  menu button (activation opens a visible menu; Escape closes and returns
  focus), slider (ArrowRight/Up and ArrowLeft/Down change aria-valuenow;
  the value trio valuenow/valuemin/valuemax must be exposed — its absence is
  its own finding, 4.1.2). Menu buttons are excluded from the disclosure
  operator (they carry aria-expanded too — double-testing left them open).
  What it does NOT do: nested/edge cases (combobox with inline autocomplete
  filtering, multi-level menus) remain review-level.
- **`chart_no_data_equivalent` (1.1.1, LOW — review finding)**: the
  data-viz pass now asks the next question after naming: does a NAMED chart
  expose its DATA in machine-visible text? Equivalent = resolvable
  `aria-details`/`aria-describedby`, or a real `<table>` inside the same
  figure/section/cell/list item (a generic parent does NOT count — one
  chart's table must not vouch for its neighbors). Rendered pass only.
  What it does NOT do: it does not judge whether the equivalent is GOOD, nor
  detect chart types, nor verify keyboard exploration — those stay human
  review; the finding exists so the gap is at least VISIBLE.

## 5.26.0 — 2026-11-01 — "EN 301 549 + applicability scope"

- **`a11y_scope` (tool 35) — semi-automatic applicability scoping** (the
  pattern of the Government of Canada CIO wizard for EN 301 549, informed
  by the audit instead of 118 hand-answered questions): the reports'
  new `features` block is positive evidence of what the audit SAW — zero
  media elements proposes 1.2.x excluded, zero form controls proposes
  3.3.x; embedded iframes leave media undetermined (nothing proposed);
  reports without the block emit zero proposals. The machine PROPOSES
  (`proposed-excluded`), the human CONFIRMS (`answers`), and only
  confirmed exclusions flow downstream — each with its reason. Live
  counter: N of 55 in scope (the mirror of the wizard's "Total Clauses").
- **EN 301 549 V4.1.1 (2026) as an output of the engine**: `--standard
  en301549` on audit (CLI + MCP) adds the clause to every finding
  (9.x web / 10.x documents / 11.x software; pdf/docx default to 10.x)
  and a standard block; SARIF rules gain `en301549` properties + tags
  (filterable in code scanning). The SC↔clause numbering identity was
  verified against the standard's official applicability wizard: 55/55
  A/AA mirrored in clauses 9, 10 AND 11. AAA is not claimed. The EN-only
  families (5, 6, 7, 8, 12, 13) appear in the scope as honest rows this
  toolkit does not evaluate.
- **Scope sealed inside the evidence chain**: `evidence --scope` embeds the
  scope artifact (sha256) and turns confirmed exclusions into
  `not-applicable` rows with their reason; VPAT/OpenACR render them as
  Not Applicable (overrides still win); `apply_scope` applies a scope to
  an already-built pack without touching its seal.
- **Honesty rule, pinned**: a machine proposal never excludes anything —
  only a human answer does (49 checks in tests/test_scope.py, including
  8 regressions from an independent review).
- **GIF banner now derives from `server.TOOLS`** (count drift impossible);
  AGENTS.md / Cursor rules / npm description re-pinned to 35 tools by the
  solido suite.

## 5.25.2 — 2026-10-31 — "the slim sdist + the serious badges"

- **README in Spanish** (`README.es.md`) with a language switcher at the top
  of both; **README conversion optics** — the demo GIF and quickstart come
  first, the 15-badge trust row moved to its own "Trust, verified" section;
  **Human in the Loop** badge added next to the thesis line.
- **Cookbook fixes** — three recipes used subcommands that don't exist
  (`dom`, `sr`) or a script that doesn't ship in the package
  (`verify_pack.py` under uvx); the repeated 22× uvx prefix is now a
  one-line runner; every recipe verified against the CLI.
- **Tests stay OUT of the sdist** (`MANIFEST.in`: `prune tests`) — the
  published artifact ships the product; tests live at the release tag.
  sdist 1598KB → ~290KB, and three scanner claim-surface categories
  (env, eval literal, most of shell) dissolve because the code truly
  leaves the artifact. LESSON: setuptools merges SOURCES.txt
  incrementally and never removes entries — plain omission re-added
  tests from stale manifests; `prune` is impermeable (verified with a
  rebuild without cleaning).
- **Filesystem boundary pinned** (test_solido): the engine opens ZERO
  hardcoded absolute paths and never touches the user's home — the
  verified answer to the scanner's "Filesystem access" category, now
  unable to regress silently. SECURITY.md rows expanded (namespaces are
  format identifiers, never fetched; arialive.js is browser-only UI).
- **OpenSSF Scorecard workflow** (weekly + push to main, published
  results) — the industry-standard supply-chain score joins the README
  badge row, next to: Socket (audited), npm version, ACT Rules 20/20,
  releases OIDC provenance signed, dependencies zero, Python versions,
  GitHub release. The score starts wherever it starts and climbs with
  real fixes per release — the house never paints the meter.

## 5.25.1 — 2026-10-30 — "mcpName (registry requirement)"

- **npm/package.json gains `mcpName: io.github.kinti/a11y-toolkit`**: the
  official MCP registry now validates the npm package during publish and
  rejects it without the field (400 "missing required 'mcpName' field").
  JSON-only patch — no engine change; the npm version is immutable, so the
  field ships as its own patch release (PyPI+npm stay version-aligned via
  versionar, as always).

## 5.25.0 — 2026-10-30 — "the ecosystem corpus + honest intervals"

- **Supply-chain hardening (Socket PyPI review, 84)**: the five scanner
  findings audited against the actual 5.24.0 sdist — one was real and is
  GONE: the CLDR plural rule was `eval()`'d (`a11yi18n.plural_category`),
  which made a community-editable locale pack (or a third-party
  `use_overlay()` pack) a code-execution vector. It is now parsed by an
  AST whitelist (`eval_plural_rule`: comparisons, and/or/not, % + - *,
  int/float, `n` — anything else raises, never executes; 11 hostile
  payloads pinned as rejected in test_locales, plus a repo-wide no-eval
  pin). The other four findings are declared capabilities, not defects:
  `SECURITY.md` (new, ships in the sdist via MANIFEST.in) documents
  filesystem/network/subprocess/env usage with the exact why — subprocess
  is list-argv only (`git` under `--changed`, macOS `sips` fallback), the
  runtime engine reads zero environment variables, and every w3.org URL
  is a static documentation link in the knowledge catalog.
- **Tasteful star nudge (CLI `fix`, once per machine)**: after a fix writes a
  file, stderr gets one line — "if it saved you time, a star helps other
  auditors find it". Never in CI (env-detected), silenced with
  `A11Y_NO_STAR_NUDGE=1`, marker in the system temp dir (never the user's
  home — the filesystem-boundary pin applies), stdout JSON stays
  machine-parseable (the line goes to stderr). The explicit star-gate idea
  was rejected: it would be starjacking with extra steps and contradicts
  the zero-telemetry promise.
- **`a11ycorpus.py` + `corpus/` v2026.10.0 — the versioned audit corpus
  (VK-LSVD translation)**: the sealed mutant exam frozen as a DATASET
  RELEASE. 18 mutants (one per operator, 13 criteria) + 3 placebo
  controls, byte-frozen pages + `cases.jsonl` with the sealed ground
  truth + `MANIFEST.json` sealing every file hash (a11y-corpus/1) +
  `results/reference.json` — this engine's own baseline published WITH
  the dataset (kill 1.0, 0 false positives, 3 additional findings
  honestly reported-not-scored). The evaluation contract is
  ENGINE-NEUTRAL: one JSON line per case with WCAG criterion codes, so
  axe, Lighthouse, IBM or any evaluator can be scored by the same
  harness (`corpus evaluate` → kill rate, placebo false positives,
  per-criterion confusion; JSONL or a JSON array, both accepted). A
  published version is never edited (D22): changes ship as a new
  version + changelog entry, every hash sealed. CLI `a11ytoolkit corpus
  build|verify|evaluate|reference`. The recipe is VK-LSVD's: dataset +
  baselines + neutral contract = ecosystem gravity.
- **`a11ydistrib.py` — the statistics layer of WCAG-EM aggregation (HEGM
  translation)**: WCAG-EM reports stop publishing naked point estimates.
  Every criterion row in `a11ywcagem` now carries its sample prevalence
  with a Wilson score interval (what a random unaudited page may hold);
  the report gains an `inference` block — per-page human effort modeled
  as a zero-inflated mixture (declared point mass at zero + exponential
  tail + gaussian body, pure-Python EM with declared init) plus a seeded
  percentile bootstrap over BOTH minute bands (minutes are a range per
  criterion everywhere; the interval is the declared OUTER ENVELOPE,
  never a point that hides the range), and a site projection when the
  plan declares `estimated_pages`. HEGM's own failure catalog is
  imported as fit validations: dead component, collapsed variance,
  single distinct value — a fit that trips one NEVER publishes an
  interval; the rejection and the bootstrap fallback are declared in the
  output (D21). On small samples the mixture honestly refuses more often
  than it fits; that is the finding, not an embarrassment. Format bumped
  to a11y-wcagem-report/2 (seal unchanged, covers the new block).
  Statistics over the sample, never conformance.

## 5.24.0 — 2026-10-30 — "one audit per template (twin-page fingerprints)"

- **`a11yfingerprints.py` + CLI `fingerprints`** — multi-hash template
  fingerprints: every page hashed from three independent views (structure /
  classes / attributes) per landmark region, text always excluded and the
  id-referencing volatile attributes (id, for, name, href, src, aria-*
  references…) excluded by design — csrf tokens and per-page ids can never
  split a template. The template IS the structure view (a declared rule,
  not fuzzy similarity); inside a template each page is compared
  view-by-view against the representative, so divergence is localized
  ({page, region, view}: "header diverges in classes, footer identical"),
  and `sample_suggestion` collapses the audit budget to one representative
  per template — the WCAG-EM Step 3 helper. Deterministic hashlib-only,
  hostile-HTML tolerant, cross-process determinism pinned by test.
  CLI-only like the sealed exam (D17 — the tool count does not move);
  tests in every gate; recipe 13 in the cookbook; D20 in ARCHITECTURE.
  Cross-industry origin: multi-hash identification from industrial
  recommender systems (one hash breaks with one token; several independent
  hashes identify by intersection).

## 5.23.0 — 2026-10-30 — "the fix plan" (in tree, awaiting seal)

- **`a11yplan.py` + CLI `plan`** — findings → ordered fix route: batches by
  shared cause, declared phase ordering (infrastructure → design-system →
  instances; redesign zones flagged last), minute ranges from declared
  severity assumptions or the evidence pack's effort pricing, cumulative
  totals, declared grouping savings, root seal. Deterministic, no ML, no
  network; the human reorders. Cross-industry origin: planning over
  evolving state (arXiv 2607.02115), translated into an auditable
  heuristic. Tests in every gate; recipe 12 in the cookbook.

## 5.22.3 — 2026-10-30 — "the three adds (WCAG-EM, Cursor rules, VS Code) + npm hygiene"

- **`a11ywcagem.py` + CLI `wcagem`** — the WCAG-EM 2.0 layer: a validated
  evaluation plan (scope, conformance target, support baseline, sample set)
  plus one sealed pack per sample aggregate into a root-sealed report
  (sha over the pack seals). Worst-status-wins per criterion across the
  sample, priced human work, the standard's step trace — and zero
  conformance claims: random selection (3.2) stays with the evaluator.
  Tests in every gate; recipe 11 in the cookbook; ticket 22 closed.
- **Cursor rules + commands** (`rules/a11y-toolkit.mdc`,
  `commands/a11y-audit.md`) — the two Agent Plugins components we were
  missing: contextual discipline while writing HTML/CSS, and a
  slash-command audit flow.
- **VS Code extension v0.1** (`vscode/`) — audit the open file or the
  branch diff from the editor, findings in the Problems panel, powered by
  the self-contained npm package (no config, no telemetry). Ships as
  source; Marketplace publish needs the kinti publisher account.


- npm package metadata catches up with the self-contained reality: the
  description no longer says "launcher via uv" (the engine ships inside),
  `bugs` URL added, and **LICENSE now travels in the tarball** (whitelist
  + workflow). Verified with `npm pack --dry-run` before sealing — the
  packaging protocol born from the 5.22.1 lesson.

## 5.22.2 — 2026-10-30 — "the self-contained npm package (this time for real)"

- The 5.22.1 tarball shipped WITHOUT the engine: npm's `files` whitelist
  excluded `a11y_toolkit/` even though the workflow bundled it. Now the
  whitelist includes it (94 engine files verified via `npm pack --dry-run`
  before sealing — the test the 5.22.1 seal deserved).

## 5.22.1 — 2026-10-30 — "the self-contained npm package"

- **The npm package now carries the engine inside** (a11y_toolkit/, pure
  stdlib): `npx -y @kinti/a11y-toolkit …` runs the bundled Python directly
  via `python3 -m` — zero downloads at runtime, zero uv requirement, offline
  by construction. Falls back to the version-pinned uvx when python3 is
  absent. Pinned end-to-end by tests (a real `pair` through the Node bin).
  The CI bundles the engine into the tarball at publish time; the published
  npm tarball is now self-contained like the PyPI one.

## 5.22.0 — 2026-10-30 — "the cookbook"

- **`docs/cookbook.md`** — ten start-to-finish recipes (audit → fix → seal
  → document → CI → hear → disprove), every command verified against the
  real CLI (four doc-bugs caught and fixed by that verification: vpat/openacr
  take `--reports`, disprove takes `--file`, declaration takes `--output`).
  The last roadmap doc after interop.md: now a newcomer can go from zero to
  a sealed pack with copy-paste. Linked from the README.

## 5.21.0 — 2026-10-30 — "an agent plugin, properly"

- **npm launcher: `@kinti/a11y-toolkit`** — a 2KB Node wrapper so the whole
  npx-first MCP ecosystem gets a working one-liner (`npx -y
  @kinti/a11y-toolkit a11y-toolkit-mcp`). The engine stays Python/stdlib;
  the wrapper runs it via uv and, if uv is missing, prints the exact
  install line for the user's OS. server.json now carries BOTH packages
  (PyPI + npm); versionar bumps them together; publishes on tag via
  `.github/workflows/npm.yml` (needs the NPM_TOKEN secret).
- **`docs/interop.md`** — composition recipes with the most-used MCP servers
  (Playwright/Chrome DevTools capture → audit, GitHub issues with the pack
  seal, Filesystem/Fetch/Context7) — the agent-facing integration layer.
- **Agent Plugins 1.0.0 compliance** (the Cursor/open-plugins standard,
  backed by Cursor/Microsoft/OpenAI/Amazon/Vercel): `plugin.json` manifest +
  `mcp.json` (stdio, uvx launch — the same official registry command) at the
  repo root, and `skill/` renamed to `skills/` so `skills/*/SKILL.md` is
  discoverable as a plugin component. `versionar.py` now bumps plugin.json
  with every release so the manifest never drifts. Cursor (and any
  Agent-Plugins-compatible client) can now install the whole toolkit —
  34 tools + the skill — as a one-click plugin.

## 5.20.0 — 2026-10-29 — "verify it yourself"

- **`scripts/verify_pack.py` — the independent evidence-pack verifier.**
  Copy the single stdlib-only file anywhere with Python 3.9+ and verify any
  `a11y-evidence-pack/2`: recomputes every embedded body hash and the pack
  seal (current rule: minus `sha256`/`generated`; legacy pre-5.13 rule
  labelled), checks the 55-criteria matrix and summary consistency, exits
  0/1 naming the field that broke the chain. `--json` for machines. It
  deliberately imports NOTHING from the engine — a third party verifies
  without installing us (`tests/test_verify_pack.py`, all gates). The
  evidence format is now verifiable by anyone: the last link of the
  de-facto-standard play.
- **evidence-pack spec fixes** (found by the verifier's first run):
  `docs/evidence-pack-schema.md`'s normative hash rule still described the
  pre-5.13 seal and the pack/1 `artefactos[]` key — now states the current
  rule and both eras; the sample pack was hand-edited at some point (its
  recorded hashes no longer matched its content) and is regenerated with
  the current builder; `(sin name)` leftover → `(no name)` in audit
  examples (the -0e decision, applied everywhere).
- **Official GitHub Action + GitLab CI template** —
  **[`kinti/a11y-watch@v1`](https://github.com/kinti/a11y-watch)** (published;
  composite action: audit → SARIF → budget ratchet; first run without
  `budget.json` generates the accepted baseline and fails with instructions
  — adoption is explicit; this folder is the mirrored source); the
  copy-paste workflow gained its missing SARIF generation step; GitLab
  template `examples/a11y-watch-gitlab.yml` (include-by-remote).
- **`bench/RUNBOOK.md`** — the monthly benchmark loop (fixed page panel,
  raw JSON always in-repo, every divergence explained; mutant cross-check
  phrasing rule) so the monthly credibility cadence is a 30-minute routine.
- Gate hygiene: the pre-push hook now runs the mutant suite it claimed to
  cover (drift since 5.18.1).
- Registry card now points at **https://a11y.es** (the service brand;
  jquin.net stays author credit only).

## 5.19.0 — 2026-10-29 — "the overlay tell + the procurement YAML"

- **`a11y_generate_openacr` (tool 34) + `a11ytoolkit openacr`** — OpenACR
  (GSA open standard, VPAT-derived) generator: the evidence pack becomes a
  machine-readable ACR in YAML (chapters success_criteria_level_a/_aa, one
  `web` component per criterion, 55 criteria). Same honesty rule as the
  VPAT: the machine fills the adherence `notes`, never the level — every
  criterion starts at `not-evaluated` unless an automated fail forces
  `does-not-support`; a qualified human sets levels via `overrides`
  (VPAT vocabulary; hyphenated OpenACR forms accepted). Fixed-schema YAML
  emitter where JSON escaping is valid YAML double-quoted style: zero
  dependencies AND no injection — user text can never break the document.
  Every remark cites the pack sha256 (tamper-evidence chain). US federal
  procurement and GSA buyers parse OpenACR; humans keep the VPAT.
- **Overlay widget detection in the static audit** — `a11y_audit_url`
  (and `audit_site` pages) now fingerprint third-party accessibility
  overlay scripts (accessiBe, UserWay, AudioEye, EqualWeb, FACIL'ITI) by
  script domain and report them as `overlay_widgets` + a localized note
  citing the community Overlay Fact Sheet. Deliberately NOT a WCAG
  finding and score-neutral: no success criterion says "don't use
  overlays" — it is procurement-diligence data, detection ≠ judgment.
  SaaS layering: products can add their own overlay-guide link via the
  existing locale `use_overlay()` mechanism.

## 5.18.1 — 2026-10-29 — "3.9 grammar guard"

- **Fix: v5.18.0 was broken on Python ≤3.11** — one `_DIAG` lambda in
  `a11yroute.py` had a backslash inside f-string braces (`\b` in a regex
  inside the interpolation): valid from 3.12, `SyntaxError` on the
  product floor 3.9, so every import of the CLI/router crashed there.
  Local dev on 3.13 swallowed it; only CI's 3.9 job caught it (after
  PyPI had already published). Fixed; per T14 the burned tag stays,
  superseded by this one.
- **New invariant in test_solido (every gate)**: no backslash inside
  f-string braces anywhere in the package — a tokenize-based guard that
  self-validates against the exact line that burned v5.18.0. On <3.12
  interpreters the suite cannot even run past import, so the guard only
  needs teeth on 3.12+.

## 5.18.0 — 2026-10-29 — "the sealed exam + sequential diagnosis"

- **`a11ymutants.py` — the engine examines itself (WCAG mutation
  testing)**: a seeded mutant bank where the exam is regenerable — same
  seed, same exam (byte-identical, stable across processes and Python
  3.9–3.13); fresh seed, an exam nobody has memorized. 18 operators
  inject one violation each into clean generated pages, every operator
  derived from the engine's own signal→criterion map (13 criteria; a
  test pins bank↔map, they cannot diverge). The sealed answer log
  (operator/signal/criterion) opens only after scoring. Placebo control
  pages ride every exam: any finding on them is a false positive by
  construction. The suite clamps the engine's kill rate at 1.0 — a
  detection regression in ANY of the 18 signals turns `make test` red
  (detection now has a regression gate, like parsing always had the fuzz
  suite). `run_exam(engine=…)` scores EXTERNAL evaluators (with or
  without `lang=`) — the door to measuring axe, an LLM judge or a human
  auditor on a fresh exam any day. CLI: `a11ytoolkit mutants --seed 7
  --n 12 [--out dir]` (writes pages + answers.json for external
  examiners). D18. Academic precedent: Ma11y (2024); the product delta
  is the regenerable exam shipped inside the analyzer.
- **`a11y_route` v2 — sequential diagnosis (evidence orders, severity
  only breaks ties)**: pass `url` or `html` (MCP params, CLI `--url` /
  `--file`) and the router takes the page's cheap vitals (the static
  pass: score, findings) and lets its symptoms — forms, menus, video,
  animation, SVG — order the next exams by expected yield. Differential
  diagnosis, not a fixed criterion priority: a page without forms does
  not need the form exam however severe 3.3.1 is on paper. The rendered
  deepener (`a11y_audit_dom`) closes every plan, and the guarantee ships
  in every response (es/en): diagnosis ORDERS the exams, never trims
  them — the full catalog stays one `route(goal)` away. Goal routing is
  unchanged (test_route sections 1–7 still pin it). D19.
- **versionar.py regenerates llms.txt after the bump**: v5.17.0 shipped
  llms.txt still saying 5.16.0 (the version is embedded; the release
  script never regenerated it). Now it always does, and RAPIDAS runs the
  new mutant suite too.

## 5.17.0 — 2026-10-28 — "a11y_route: the router"

- **llms.txt (generated)**: the repo publishes its own index for
  agents (llmstxt.org convention — the pattern a11y.es invented,
  ported): what is verifiably true, quickstart, the 33 tools by
  category, prompts, docs and the honest boundary. Generated from
  `server.TOOLS` by `scripts/gen_llms.py` with `--check` pinned in
  the Makefile gates — a new tool regenerates the index, nobody
  edits it by hand. D17 recorded in ARCHITECTURE: grow in signals,
  not tools.
- **Tool 33, `a11y_route` — the router nobody has**: state a goal in plain
  language ("gate my PR", "fix the contrast of my hero", "quiero una
  declaración EAA") and get the ordered tool sequence with the why of each
  step, the matching prompts and the CLI equivalent. Deterministic by
  design: a word-boundary keyword index over an 18-route table (es/en),
  NOT an LLM; when nothing matches, the honest fallback says where everyone
  starts (the express audit). Turns the "too many tools" penalty into the
  opposite argument: 33 specialized tools, an O(1) choice. CLI:
  `a11ytoolkit route --goal "gate my PR"`. Pinned by tests/test_route.py
  (every referenced tool/prompt/CLI exists, determinism, es/en, fallback,
  hostile goals) in every gate (make test, make fast, RAPIDAS, pre-push).

## 5.16.0 — 2026-10-25 — "README: quickstart + compact tool table, honest labels"

- **README restructured for onboarding**: a `## Quickstart` at the top (MCP
  one-liner, `pip install`, two example commands, the zero-dep vs Playwright
  split), a one-line tagline, and the tools section reduced to a compact
  32-row table (Tool | Category | What it does) — the full reference moved to
  the new `docs/tools.md`. README goes from ~860 to ~310 lines.
- **`docs/tools.md` — the full tool reference, auto-generated**: the long
  claim is now literal on two surfaces. `scripts/gen_readme.py` emits both the
  README table and the `docs/tools.md` catalog from `server.TOOLS`, with
  `--check` (exit 1 when stale) wired into `make test`, `make fast` and CI —
  neither surface can drift.
- **Behavior annotations restored on every tool**: labels now surface the
  three MCP annotations — `read-only`/`mutates state` · `network` ·
  `not idempotent`. This fixes a regeneration regression that mislabeled
  `a11y_generate_declaration`/`a11y_generate_vpat` as read-only, and restores
  the network/not-idempotent signals an agent needs before running
  `a11y_forms` or `a11y_ledger`.
- **`a11y_wcag3_preview` openWorldHint corrected** (pure report→outcomes tool,
  not network) so its label stops lying.
- **Features table** (`What no other a11y tool…` → `## Features`): ✗/✓ replaced
  by No/Yes (screen-reader friendly), two rows added (ACT Rules interop,
  WCAG 3 draft preview), and the "93% of A/AA" vs "~1/3 of WCAG" wording
  reconciled in one sentence.

Tests: `scripts/gen_readme.py --check` (two surfaces) folded into `make test`/
`make fast`/CI; `test_solido.py` now pins both the README table and
`docs/tools.md` entries.

## 5.15.0 — 2026-10-25 — "the whole bible + 100% ACT + WCAG 3 from source"

- **The whole bible: WCAG 2.2 A/AA/AAA ingested from the canonical source**:
  `scripts/wcag22_ingest.py` extracts every success criterion (number, name,
  level) from the w3c/wcag repository (guidelines order gives numbering;
  4.1.1 Parsing numbered then excluded as removed). The catalog now covers
  ALL 86 criteria — the 31 AAA entries authored bilingually (name, what it
  requires, typical failures, how to check — pointing at the right toolkit
  tool where one applies, honest "manual" where none does). `a11y_criterion`
  explains the complete standard with Understanding links; the A/AA set and
  every level are verified against the source snapshot
  (`docs/wcag22-criteria-source.json`), pinned in test_solido (86/86,
  zero level drift).
- **WCAG 3 ingested from the canonical source**: `scripts/wcag3_ingest.py`
  verifies the preview's outcome registry against the w3c/wcag3 repository
  itself (guidelines/groups structure) — 46/46 names verified; the snapshot
  (`docs/wcag3-outcomes-source.json`) is pinned by tests/test_wcag3.py, so
  every future draft re-baseline is a diff against the source, not a guess.
- **README regenerated from the server itself** — the long-standing claim
  is now literal: `scripts/gen_readme.py` builds the tools section from
  `server.TOOLS` between markers, with `--check` (exit 1 when stale) for CI;
  new categories (Knowledge & context, Coverage & evidence) and a tool
  without a category fails the generator. a11y.es is demoted to a two-line
  mention at the end ("The engine behind a11y.es") — the repo is the engine,
  not the service.
- **Naming: `ej` → `example`** across 105 coordinated sites (code kwargs,
  locale placeholders es/en, JS transport keys) and the injected-JS Spanish
  purge (~25 local identifiers). Note for pack consumers: the value key
  rename changes regenerated pack sha256s.
- **EN 301 549 v4.1.1 status note** in every generated statement (both
  frameworks, es/en): adopts WCAG 2.2 and adds the EAA mapping, but not yet
  cited in the Official Journal — presumption of conformity stays with the
  already cited v3.2.1 (WCAG 2.1 AA) until then.
- **Independent adversarial review of the whole wave** (executable reviewer,
  protocol round): 14 real issues the suites missed, all fixed and
  re-verified — contrast symbol-filter exempted all non-Latin text (CJK/
  Cyrillic/Arabic pages measured nothing; now Unicode-property aware);
  role-controls closed on nested same-tag endtags (React icon-button
  pattern produced false unnamed-control highs; close now requires depth
  match); orphan alpha-zone marker burned 30s timeouts per element;
  placeholder+id fields escaped every 3.3.2 signal (placeholder-only now a
  post-parse decision); search inputs never reached the label check; the
  style-rule scan was quadratic (450x overhead with inlined CSS — now
  cached); icon-font exemption required an actual font declaration; the
  ACT runner applicability table carried dead keys (EARL outcomes now
  semantically honest); AAA 2.5.5 documented as 24×24 instead of 44×44;
  later aria-toggles erased earlier real collapse toggles; id-text
  accumulation was quadratic; the 4.1.3 dynamism gate read a post-parse
  flag. Clean probes: hostile HTML, walker JS syntax, glyph-diff sampler,
  deep DOMs, real pages (cross-validated against browser naming).
- **20/20 — 100% consistent with every published ACT rule implemented**.
  The final wave closed every residual: label-in-name implements the full
  2.5.3 algorithm (punctuation removed WITHOUT splitting words — "11×3=33"
  is one token; contiguous word-slice matching — "discover it" does not fit
  "discover italy"; DOM-faithful text concatenation — inline-div letters
  are "ACT", spaced "W C A G" is four words; single symbolic letter exempt);
  icon-font pages exempt buttons (their "text" may be glyphs); <style>-based
  visually-hidden classes excluded from the visible label; bypass = a
  toggle whose function actually collapses (body says `display` inline, or
  the function name does when the JS is external — off-screen/aria toggles
  do not count); element language by effective inheritance incl. img alt
  as text, whitespace lang invalid but empty lang is not. Rendered contrast
  (afw4f7) became fully decisive: aria-hidden/disabled-ancestor/symbol-only
  and single-char text excluded; element+ancestor OPACITY composed into the
  text alpha; text-shadow treated as the effective background (improves or
  fails, no longer deferred); alpha text over gradients measured at BOTH
  composition extremes; and the sampler now measures the background ONLY at
  glyph pixels (two-screenshot diff) — a gradient the text only crosses at
  its light end can no longer fail by its dark end. 34/34 official
  contrast cases, 355/355 overall, zero inconsistencies, published as-is
  in docs/act-report-summary.md.
- **ACT precision wave II — 14/20 rules consistent (was 12/20, originally
  1/20)**: first-`<title>`-in-document model (a body title counts when no
  head title exists, per the case truth table); off-screen focus sentinels
  decided post-parse against the full script text (an unwired sentinel is a
  failure, a wired one is exempt); element language validated by the
  EFFECTIVE language of each text node (nearest ancestor with lang — a
  child with valid lang covers its text even under an invalid ancestor);
  field names per e086e5 semantics (placeholder IS a name for the
  accessibility tree — our separate placeholder_only signal keeps the honest
  3.3.2 review position; label[for] only labels labelable elements;
  role-fields get name-from-content; role=none/disabled/hidden skip);
  aria-value validation skips valueless attributes, accepts tri-state
  "mixed" for pressed/checked, and validates aria-relevant token-wise; a
  button toggling a nav (onclick referencing its id) is a valid bypass
  mechanism (a link toggle is not). Rendered-contrast rule (afw4f7) kept
  static on purpose: the rendered pass caught 5 real fails but added 9
  false positives on indeterminable backgrounds — machinery (file:// +
  Playwright) is in the runner, ready when contrast applicability learns
  gradients/unmeasurable backgrounds.
- **ACT precision wave — 12/20 rules consistent (was 1/20)**: the official
  W3C test cases drove a real engine overhaul. New in the parser: inherited
  visibility model (aria-hidden with `false` re-enabling for accname,
  hidden/display:none/visibility:hidden stacks), an id→text registry
  resolving `aria-labelledby` post-parse (ids can be declared later),
  focusability model for 6cfa84 (native elements + tabindex, `disabled`
  disables, aria-disabled does not, tabindex=-1 does not count, off-screen
  focus sentinels whose id is wired in scripts are exempt, nested
  aria-hidden=false does NOT exempt), the exact ACT/WHATWG autocomplete
  grammar (section-* → shipping|billing → contact modifier only before
  email/impp/tel* → field → webauthn; disabled/hidden/aria-disabled fields
  out of applicability), meta-refresh per the HTML declarative steps (first
  parseable wins — `0:` with a colon does not parse; 0s and >20h exempt),
  zoom blocking on invalid user-scalable/maximum-scale values (negatives
  and device-width do not block), title only in (explicit or implied)
  head and never in templates/bodies, multi-token role validation, and
  name sources for img/input-image/iframe/links/buttons/headings/fields
  (alt, aria-label, resolved labelledby, title, inner image names,
  presentational/hidden exemptions with the focusable exception).
  label-in-name now implements the WCAG 2.5.3 algorithm (parens removed,
  word-level containment, single-symbol visible labels exempt, CSS-hidden
  text is not the visible label) and covers buttons, not just links.
  ARIA 1.2/1.3 roles added (searchfield, comment, suggestion, blockquote).
  Per-rule detail in docs/act-report-summary.md; residuals documented
  there (rendered-only contrast, icon-font labels, bypass heuristics).
- **ACT implementation report (W3C WAI listing play)**: `scripts/act_report.py`
  runs the shipped static engine over the official ACT test cases (single
  w3.org testcases.json, 1211 cases; ours: the rules in ACT_MAP) and emits
  the EARL JSON-LD implementation report (`docs/act-implementation-report.json`,
  act-rules.github.io format) plus an honest per-rule consistency summary
  (`docs/act-report-summary.md`). Outcomes derive from mapped signals —
  failed when a mapped signal fires; passed/inapplicable via a per-signal
  applicability table; never cantTell. Polite crawler (w3.org rate-limits
  bursts: local cache + backoff). Published as-is, inconsistencies included:
  they are the precision backlog. Submission to the W3C implementations
  list = GitHub issue w3c/wcag-act-rules with the permanent raw URL.
- **PDF forms screening (a11y_audit_pdf)**: AcroForm fields without an
  accessible label — `/TU` is what a screen reader announces; without it a
  field is heard as its technical name or as bare "button". Clear-cut case
  (zero /TU in the document) reports by type: inputs/choices/signatures →
  3.3.2 medium, buttons → 4.1.2 high; the partial case reports the honest
  count (N of M) without splitting buttons (radio-group /Parent inheritance
  makes per-field pairing unreliable in an object-parser-free screening).
  The report gains `form_fields` and `form_labels`. Same nobody-automated
  lane as the rest of the PDF screening; public-sector forms are the use
  case.
- **a11y_evidence lang= now covers manual_pending and verified manual rows**:
  the manual-only and agent-verified rows of the criteria matrix used the raw
  English MANUAL_AA strings while the rest of the matrix localized — a pack
  in Spanish reached the client with four English rows. All criterion names
  in the pack now come from the bilingual catalog in the pack's language.
  (Found live at the a11y.es vendor sync: its pack-language test caught it.)

## 5.14.0 — 2026-10-23 — "WCAG 3 preview + EN 301 549 v4.1.1"

- **a11y_wcag3_preview (tool 32) — the WCAG 3 demo nobody ships**: takes any
  audit report and re-groups its WCAG 2.2 findings under the 46 outcomes of
  the WCAG 3 Working Draft (10 September 2026), with the draft's exact
  outcome names. Honest by construction: NO score, NO tier, NO conformance
  claim (the draft's tier thresholds are explicitly TBD); the criterion→
  outcome map is curated by a11y-toolkit and labeled as such — the W3C has
  published no official WCAG 2 → WCAG 3 mapping (transition materials are
  planned). The output carries the Working-Draft disclaimer in es/en, the
  conformance-model summary (single level, core-requirement tags physical
  harm/risk/barrier/friction, reporting tiers 1–6 with tier 3 = conformance,
  per the W3C introduction) and an honest `unmapped` list. Signal-reachable
  criteria are 100% covered (pinned by tests/test_wcag3.py). Re-baseline on
  each W3C draft publication (roughly March/September). CLI:
  `a11ytoolkit wcag3 --from-audit audit.json`.
- **EN 301 549 v4.1.1 status note in every generated statement**: v4.1.1
  (published September 2026) adopts WCAG 2.2 as the web/documents/software
  benchmark, adds six 2.2 requirements, drops obsolete 4.1.1, and is the
  first version built for the EAA (new EAA mapping annex). It is NOT yet
  cited in the Official Journal: presumption of conformity stays with the
  already cited v3.2.1 (WCAG 2.1 AA) until that citation — the note says
  exactly that, in es/en, in both rd1112 and eaa frameworks. Sourced from
  the AccessibleEU Centre (European Commission) announcement.
- Docs sweep: removed a byte-identical duplicate of the a11y_audit_pdf
  entry in README (paste error), and fixed two stale pre-5.11 Spanish
  param names in README/skill (`contenido_no_accesible`, `marco=` →
  `inaccessible_content`, `framework=`).

## 5.13.0 — 2026-10-23 — "locale packs + dictionary-verified English"

- **Community locale packs (the i18n system)**: every user-facing message
  moved out of Python into `a11y_toolkit/locales/<lang>.json` — one file per
  language (es/en ship), namespaced, editable from the GitHub web UI.
  Adding a language = copy `_template.json`, translate keeping `{placeholders}`,
  and `tests/test_locales.py` validates it mechanically: same keys as English,
  same placeholders per message, a working CLDR plural expression, no empty
  values. Zero runtime dependencies (stdlib loader `a11yi18n.py`); English
  fallback chain at runtime; `{"one", "other"}` plural entries supported;
  `use_overlay(path)` lets downstream products layer brand wording without
  forking. The axe-core community-locales model, with the validation layer
  axe-core doesn't pin. Guide: docs/i18n.md.
- **Hardening wave upstreamed** (general engine quality, previously carried
  as downstream patches): `_fetch` reads with a total clock (a dribbling
  server can no longer reset per-operation timeouts forever) and prefers the
  HTTP header charset over body sniffing; `validate_redirect` injection hook
  (callers auditing untrusted URLs can veto each 3xx hop — SSRF boundary);
  `audit_site(budget=seconds)` bounds the crawl and reports
  `budget_exhausted` honestly; disprove handles site-mode reports without
  inventing score 100 (not-rechecked per page); TODAY() computed per call;
  the VPAT document is self-contained and accessible (fixed color-scheme,
  wrapping, keyboard-scrollable table — it must audit clean itself);
  `badge(brand=, palette=, height=)` lets products ship their own seal;
  the evidence pack gains `lang=` (bilingual notice/matrix/criteria names
  via locale packs) and a seal stable across re-emission (sha256 excludes
  the generation clock).
- **Native CLDR plurals**: pack entries may be `{"one", "other"}` resolved
  by the locale's plural rule — "1 pair of links / {n} pairs" is now real
  i18n, not a post-format patch.
- **Identifiers verified against real dictionaries**: every identifier in the
  package is checked against a 613,821-word Spanish-only list (Spanish
  dictionary minus English dictionaries, shipped gzipped) — not a curated
  lexicon. ~530 more Spanish identifiers found and renamed (sitios, pesos,
  firmas, _COLORES, veredicto, flujos…), including three public `a11y_diff`
  output keys (foco_* → focus_*). Both this repo and the a11y.es vendor run
  the dictionary pin. Comments stay Spanish by design (maintainer
  readability) — decision recorded in the naming pins.

## 5.12.0 — 2026-10-23 — "official sources"

- **a11y_criterion now cites the source**: every criterion explanation
  includes `understanding` — the official W3C Understanding WCAG 2.2
  document URL for that criterion (87-entry map extracted from the w3.org
  index). Agents and users get the authoritative text one link away; an
  invariant in test_solido pins that no catalog criterion ever ships
  without its link.
- **a11y_criterion understands signals**: pass `signal=kbd_trap` (the id in
  every finding) instead of a code and it resolves the criterion AND the
  published ACT rule(s) behind it — with official w3.org rule URLs and an
  honest published/proposed status. Criterion answers also list the
  toolkit signals that feed them (`toolkit_signals`). The signal→criterion
  map (115 entries) is derived empirically from the emission points and
  pinned: a new signal without its criterion fails the suite.
- **ACT map verified against the canonical w3c/wcag-act-rules repo**
  (94 rules parsed): all 21 cited rules exist; 6 titles realigned with the
  canonical wording; 5 rules are AG-WG "proposed" (now labeled as such,
  never cited as published). 17 published rules touching our criteria
  remain unmapped — curated candidates analyzed for a future release.
- **WCAG-EM cited in every audit score note** (es/en): the score is
  explicitly framed as WCAG-EM-style sampling, never as a conformance
  evaluation.
- **`a11ytoolkit init` — the agent hook**: writes (or merges, idempotently)
  an AGENTS.md block into any project telling coding agents the rule that
  matters — after any UI change, re-audit before calling the work done —
  with the exact uvx commands, how to act on findings (judgment fixes are
  human calls) and the pre-deploy snapshot+diff loop. Prints the MCP config
  and the optional skill install. `--check` is CI-friendly (exit 1 when the
  hook is missing). The repo itself gains a root AGENTS.md with the
  contribution invariants.
- **README**: the free-analyzer section now points at a11y.es only (single
  brand for the service); stale-reference sweep clean.
- **`a11ytoolkit audit --changed` — the CI gate**: audits ONLY what changed
  since HEAD (or `--base origin/main` for a branch). HTML files audited;
  untracked new files included (a fresh page cannot escape the local gate);
  deleted files skipped; other web-touched files (.css/.jsx/.vue/…) listed
  as not auditable with the reason — the honest boundary: no build, no HTML.
  Exit contract: 0 clean, 2 when high/medium findings in changed files.

## 5.11.0 — 2026-10-22 — "English-only, all the way down" (naming, evidence-driven)

The TDQS registry score (2026-10-17) flagged Naming Consistency 2/5. The
empirical scan behind this release found three layers of Spanish leaking
into the public surface an agent sees — params in the tool schemas, keys in
the returned JSON, and finding signal codes. All renamed to English, with a
permanent test (tests/test_naming.py, seven sections: schema params and
enums, descriptions, dict keys, code identifiers, string-key READS — the
exact hole where four string-reference bugs hid — and phrase-table/JS
placeholder consistency) so Spanish can never slip in again:

- **Schema params** (aliases still accepted, nothing breaks):
  `metodo`→`method`, `fecha_evaluacion`→`evaluation_date`,
  `reclamacion`→`complaints`, `disponibilidad_alternativa`→`alternative_format`
  (a11y_generate_declaration), `fecha`→`date` (a11y_badge),
  `max_pasos`→`max_steps` (a11y_keyboard), `max_tandas`→`max_batches`
  (a11y_scroll). Status enum is now `full | partial | not_conformant`
  (`plena | parcial | no_conforme` still accepted).
- **Output keys**: `aplicados/no_aplicados/por_que_no`→`applied/not_applied/
  why_not` (autofix), `tandas/fin_alcanzado/anuncios_vivos/fuera_de_pantalla/
  alternativa_cargar_mas`→`batches/end_reached/live_announcements/offscreen/
  load_more_alternative` (scroll), `pasos/paradas/ciclo{detectado,
  escape_libera}`→`steps/tab_stops/cycle{detected,escape_releases}` (keyboard),
  `campos_invalidados/detalle`→`invalid_fields/detail` (forms),
  `iframes_anidados/elementos_interactivos`→`nested_iframes/
  interactive_elements` (rendered), `idioma`→`language` (docx),
  `paginas/score_peor/senales_recurrentes/descubrimiento`→`pages/worst_score/
  recurring_signals/discovery` (site), `ultimo_audit/score_peor/score_mejor/
  total_resueltas`→`last_audit/worst_score/best_score/total_resolved` (ledger),
  `guardado_en`→`saved_to`, `accion`→`action`, `mediciones`→`measurements`,
  `razon_rechazo`→`reject_reason`, `criterios_disponibles`→`available_criteria`.
- **Signal codes** (7 renamed, all backward-compatible on ingest):
  `imgs_alt`→`img_no_alt`, `descarga_error`→`fetch_error`,
  `lang_partes`→`element_lang_invalid`, `lang_region_invalida`→
  `lang_region_invalid`, `docx_falsos_encabezados`→`docx_fake_headings`,
  `docx_sin_idioma`→`docx_no_lang`, `docx_sin_tabla_header`→
  `docx_table_no_header`. `normalize_signal()` runs at every ingest point
  (ledger, evidence pack, disprove, SARIF, ACT/EARL, budget), so reports,
  ledgers and budgets saved before 5.11.0 keep comparing correctly.
- **String-reference bugs (found by the independent review, all fixed and
  pinned)**: the injected form-error JS read `F.corto`/`F.patron` after the
  phrase table became `short`/`pattern` (TypeError killed the 3.3.1/3.3.3
  layer); `kbd_trap` messages kept a `{ciclo}` placeholder while the kwarg
  became `cycle` (crash exactly on a real trap); three error paths read dead
  table keys (`carga_error`, `selector_falta`, `color_invalido`…); Spanish
  JS transport keys (`campos`, `ejemplos`, `hayMas`, `svgColoreados`…)
  renamed together with their Python readers — verified live with Playwright.
- **Fixed along the way (found by the same scan)**: contrast guidance text
  pointed agents at output keys that no longer existed (`ratio_peor`,
  `area_pasa_aa_texto_normal`) — both languages now cite the real keys;
  keyboard `limits` and scroll `note` were hardcoded Spanish even with
  `lang=en`; the tab-stop fallback label (`parada N`) was always Spanish;
  `worst_zone.cell` position values (`superior-derecha`…) are now
  `top/middle/bottom-left/center/right`; docs/audit-report.schema.json
  documented keys the code never emitted — rewritten against the real output.
- **Total homogenization (the part earlier passes never reached)**: ~1,900
  Spanish identifiers renamed across all 25 modules via token-level rewrite
  (variables, functions, parser attrs, constants — string literals and
  comments untouched). `declaracion.py` → `a11ystatement.py`. The 2026-09
  v5.0.0 "english on the wire" pass renamed the audit-report keys and a few
  declaration params, and deliberately kept signal IDs Spanish; nothing was
  pinned, so every layer added since (scroll, keyboard, docx outputs, new
  params) shipped Spanish again. v3.9.5 had already caught "4 Spanish-only
  rendered signals shipped since 3.6" — same failure mode, point fix. The
  identifier pin (below) ends the cycle.
- **CLI flags** renamed to English across modules (declaration, vpat, badge,
  keyboard, scroll); Spanish content output (`lang=es`) is untouched.

Breaking: output KEY names changed (renames above). Input params and status
values keep working through aliases. Reports persisted by older versions are
normalized on read everywhere they are consumed. Programmatic imports of
internal functions/renamed modules (a11ystatement.generate, suggest,
build_pack, compute_score…) must switch to the English names.

## 5.10.1 — 2026-10-20 — "painted background"

The PDF contrast check (5.10.0) assumed a white background — but a PDF can
paint one with `re` + `f` before the text. White text on a dark painted rect
was a false positive (the real ratio is high). The parser now tracks the
painted fill as the effective background per text run: same bug, same fix,
same lesson as CSS var() in the HTML audit — resolve the background before
judging contrast.

Also: text-layer detection covers uncompressed content streams (was
Flate-only — legitimate uncompressed PDFs were flagged as scanned).

## 5.10.0 — 2026-10-17 — "PDF contrast + fake links — the next gap"

Two more PDF detections (extending the screening from 5.9.0), verified
with crafted PDFs and validated against the URI-annotation control:

- **`pdf_low_contrast` (1.4.3)**: parses the content stream for `rg` fill
  colors and computes WCAG contrast against the PDF's default white
  background. White-on-white and light-gray text now flagged (medium).
  No cascade, no var() — the operator IS the color, fully measurable.
- **`pdf_fake_link` (2.4.4)**: bluish fill (the classic "looks like a
  link" pattern) with NO URI annotation on the page → flagged. With
  URI annotations present, bluish text is presumed real links (control
  case verified). Screen readers do not announce styled text as links.

Both are review-grade heuristics: a PDF's painted background may exist
(detectable via `re f` operator — queued); default white is the honest
assumption. Full contrast needs the painted-background resolution.

## 5.9.0 — 2026-10-17 — "the details, part two"

The queued detail pass, shipped. Three new tools (31 total) plus precision:

- **a11y_reduced_motion**: does the site HONOR prefers-reduced-motion?
  Counts looping CSS animations, reloads emulating reduce, counts again.
  If the number does not drop, the site ignores the user's preference
  (2.2.2; 2.3.3 AAA). Nobody else automates this.
- **a11y_forced_colors**: does content survive forced-colors: active
  (Windows High Contrast)? Flags SVGs with hardcoded colored fills.
- **a11y_docx_screen**: DOCX accessibility screening — images with no alt
  text, fake headings, document language, tables without header rows.
- **Precision**: bold 700; 2.5.8 spacing exception; 1.3.5 token values vs
  WHATWG section 7.5; reading_level by page language; not_measured in
  static reports; dark-mode contrast.
- Contract tests new — first run caught three live bugs fixed here.

31 MCP tools + 6 prompts; 15 suites green.

## 5.8.0 — 2026-10-16 — "the details nobody saw"

The detail pass over WCAG 2.2 — ten delicate checks verified in code,
three real gaps found and closed, the rest confirmed correct (bold 700 ✓,
region validation now real ✓, muted-autoplay exemption ✓, img-in-link
naming ✓, asterisk+required ✓):

- **2.4.2 generic titles**: "Untitled document", "Inicio", "Page 1" were
  accepted. Now a `title_generic` review finding (low) — the empty case
  stays `title_missing` (medium).
- **3.1.1 invented regions**: `lang="en-ZZ"` passed as valid. The region
  subtag is now validated against ISO 3166-1 alpha-2 + UN M49 numeric
  (es-AR ✓, en-ZZ flags, es-419 ✓) — a `lang_region_invalida` review
  finding (low), because a reader cannot pronounce a region that does not
  exist.
- **2.5.8 spacing exception**: undersized targets pass when the nearest
  neighbor is ≥24px away — no more false positives on isolated small
  controls (the standard’s own exception, never implemented here).
- **1.3.5 autocomplete VALUES validated** against WHATWG §7.5 (one-time-
  code, webauthn, contact schemes, section-* wildcard, on/off), not just
  presence.
- **Bold threshold 700** (spec): semibold no longer gets the large-text
  3:1 pass (three computation sites).
- **reading_level**: Fernández-Huerta for Spanish pages, Flesch for
  English — selected by the page's `lang`, computed over visible prose
  only (script/style/title excluded), never scored (3.1.5 is AAA).

Precision is measured in the replays: every fix above has a live
verification (generic title fires / good title silent / en-ZZ flags /
es-419 passes / isolated 20px button exempt / adjacent 20px buttons
flagged / dark-only contrast failure caught).

## 5.7.0 — 2026-10-16 — "measurement quality + the spaces nobody automated"

The precision pass over every measurement, plus two capabilities that close
real gaps (each verified live, reviewed, and re-reviewed before shipping —
the review caught 2 P1s and 5 P2s in the first draft, all fixed):

**Measurement precision**
- Bold threshold 600→700 everywhere (spec's "bold" is 700: semibold text
  was getting the 3:1 large-text pass it must not).
- 2.5.8 target size implements the **spacing exception**: undersized
  targets pass when the nearest neighbor is ≥24px away (precomputed
  neighbors, early condemnation — no more false positives on isolated
  small controls).
- 1.3.5 validates autocomplete **values** against the WHATWG §7.5 token
  set (incl. one-time-code, webauthn, contact schemes, section-*), not
  just presence.
- Static reports carry `reading_level` (Fernández-Huerta for Spanish
  pages, Flesch for English — chosen by the PAGE's lang, computed over
  visible prose only): informational 3.1.5, never scored.

**New: the spaces nobody automated**
- **`a11y_vtt_check` (tool 27)**: caption CONTENT quality — malformed
  timing, empty cues, overlaps, >21 chars/second (BBC/Netflix standard),
  coverage vs media duration (union of intervals). Everyone stops at
  "<track> exists"; this judges what viewers actually get.
- **`a11y_audit_pdf` (tool 28)**: zero-dep PDF structural screening —
  tagged tree, title, /Lang, outline, /Alt, text layer (scan detection
  requires the image+no-text pattern), encryption at the trailer, zlib-
  bomb-capped stream inspection. axe, pa11y, Lighthouse: HTML only.
- **Dark-mode contrast**: `a11y_audit_dom(color_scheme="dark")` emulates
  prefers-color-scheme — dark themes fail where light passes, and nobody
  (axe included) audits both.
- HTTP fetch gate accepts content-types per caller (text/vtt for
  captions); reading-level and 2.5.8 fixes above.

28 MCP tools + 6 prompts; 15 suites; prefers-reduced-motion check queued
(design note: needs a second page context, not a param).

## 5.6.0 — 2026-10-13 — "contract & usability gates"

Four bets from the quality pass, each tested before, retested after and
reviewed twice (a code-review pass found one P1 and two P2s in the first
draft — all fixed and live-validated before this release):

- **Contract tests** (`tests/test_contract.py`): every tool's schema,
  dispatch and real function signature must agree — verified by parsing the
  dispatch source and cross-checking with `inspect`. First run found three
  live bugs (auth_state silently dropped in a11y_hover and
  a11y_sr_transcript; a11y_autofix's schema missing url/form_errors) and a
  schema-drift family: five stray `browser` entries living OUTSIDE
  `properties` (invisible to every client). Fixed at the source; the
  runtime patch is gone; a shape-guard now rejects orphan inputSchema keys.
- **Journey budgets** (`a11ytoolkit journey-budget`): the usability
  regression gate — rerun the same blindfold task after each deploy and
  only NEW high friction (or a pass degrading) blocks. Keys are stable
  `criterion:signal` (D3); severity collisions resolve to the worst; exit 2
  = NO-GO, exit 1 = usage error, and `--init` refuses to write a poisoned
  baseline.
- **Ledger is crash-safe**: atomic writes (tempfile + fsync + os.replace),
  per-path thread lock plus flock for multi-process, and corrupted files
  are quarantined (.corrupto-TS) instead of crashing the run. Stress-tested
  with 8 threads × 25 records.
- **Precision fixes**: tooltip dismissal judged per-element with real
  visibility (checkVisibility; display:none/visibility:hidden/opacity:0
  hiding now works — live-validated) and forms 3.3.1/3.3.3 only count
  NEW/changed post-submit text (help text no longer masquerades as error
  identification — validated in Chromium with novalidate fixtures).
- **October axe benchmark published**: bench/README.md + results/2026-10.json
  (gov.uk: 5 criteria vs axe's 1, including the 3.91:1 axe marks incomplete).

13 suites green (test_contract new); D14/D15 in the architecture map.

## 5.5.1 — 2026-10-13 — "static honesty"

External critique: a static audit scored 100 while a button failed on
screen — its 1.4.3 check never resolves class-based CSS
(`.btn-primary{background:var(--x)}`), and the report never said so. The
rendered audit always could (that's the gov.uk 3.91:1 finder); the hole
was the static report's silence. Closed three ways:

- **`not_measured` in every static report**: the 17 criteria that require
  the rendered audit, each with its reason — a static 100 can no longer
  read as "contrast is fine".
- **The score note says it out loud** (es/en): "THIS static pass did NOT
  measure contrast (1.4.3), target size or the criteria in not_measured".
- **`RENDERED_ONLY` is now canonical in `a11ycrit`** — one shared set for
  the static reports and the evidence pack's not-run logic (previously a
  private set inside the packer). The MCP routing hint for a11y_audit_url
  states the limit too.

No scoring change: the score still measures what it measures; the report
now says what it doesn't.

## 5.5.0 — 2026-10-12 — "US/ADA + measurement + interop"

Five bets from the ecosystem gap analysis, landed together (no release yet —
`make release` when the author signs off):

- **VPAT 2.5 (WCAG edition) generator** (`a11yvpat.py`, MCP tool
  `a11y_generate_vpat`, CLI `a11ytoolkit vpat`): the US/ADA counterpart of
  the EAA declaration. The full 55-criterion WCAG 2.2 A/AA table with
  Remarks auto-filled from the evidence pack (status, measured values,
  examples, remaining human effort). Honesty rule pinned in `test_vpat.py`:
  every Conformance Level starts at **Not Evaluated**, automated fails force
  Does Not Support, and only a qualified human's `overrides` + a signature
  block referencing `pack.sha256` turn the DRAFT into a claim. The machine
  fills Remarks, never the level.
- **Pixel-sampled contrast over images/gradients in the rendered audit**
  (`a11ydom.py`): text zones the computed-contrast pass could only count as
  "review" are now captured in-browser and measured for real — screenshot
  clip, pure-Python PNG decode (new `decodificar_png`, zero-dep), sampling
  with text pixels excluded (new `sample_rgb(excluir_texto=…)` in
  `contrast.py`). Failures ship as `contrast_image_fail` (high) with the
  worst ratio and % of AA-passing area; what cannot be measured stays an
  honest `contrast_review`. This is the axe gap
  ([dequelabs/axe-core#4628](https://github.com/dequelabs/axe-core/issues/4628)):
  gradient backgrounds, marked "incomplete" there, measured here.
- **`a11y_contrast_dom`** (MCP tool + CLI `a11ytoolkit contrast-dom`): the
  auto-region companion — one selector, and the tool screenshots, decodes and
  samples the element against whatever is behind it. No manual screenshot,
  no region math.
- **ACT Rules interop** (`a11yact.py`, CLI `a11ytoolkit earl`): curated
  signal → ACT rule map (22 signals, 23 published rules, partial by design —
  never invented rules, documented in `ACT_NOTES`) + EARL 1.0 JSON-LD export
  where failures are asserted and absence is never asserted as pass.
- **Screen-reader cross-check scaffold**: `docs/sr-crosscheck.md` (NVDA via
  CI harness + VoiceOver via Caption Panel) and
  `scripts/voiceover-capture.applescript` (experimental, human-driven).
- **Watch loop productized**: the audit → budget → pack → badge loop runs as
  a hosted companion built on this engine (separate codebase, not in this
  repository).

Tests: `tests/test_png.py` (PNG decoder + sampler), `tests/test_vpat.py`
(derivation honesty + overrides + pack hash in the document),
`tests/test_act.py` (canonical ids, no orphan signals, EARL outcomes).
Counts bumped 24 → 26 MCP tools across README, ARCHITECTURE, visuals and the
pinned invariants.

- **a11y.es companion**: the server instructions point to the hosted
  companion (separate private codebase, decoupled from this engine).
  Auditing stays free; the human signature and monitoring are the paid
  part.

## 5.4.2 — 2026-10-11 — "changelog correction"

Release-process note: the tag v5.4.1 was burned — it was cut by hand
(changelog + commit) without the atomic version bump, so its files still
said 5.4.0 and PyPI rightly refused the duplicate wheel. Our own D12 rule,
applied to ourselves: a published id is never edited, it is superseded.

The re-review of v5.4.0 caught something worse than any bug: **five fixes
that our own changelog announced were not in the code.** This release fixes
all five for real, plus the two regressions our own patches introduced, and
pins each one in `tests/test_revision_externa.py` (round 2).

Corrections to 5.4.0’s claims, now actually in the code:

- **autofix and `<script>`**: 5.4.0 said "no longer touches scripts" — false.
  There was no masking; the double-quoted case corrupted the JS (the
  single-quote case survived by accident). Now: real masking of
  `<script>/<style>/<!-- -->` before every transform, restored before
  return. `<textarea>` deliberately stays unmasked — its error layer goes
  after the close (5.2.1) and its content stays intact.
- **rendered contrast and TEXT alpha**: 5.4.0 claimed the main scan composes
  text alpha — the edit never landed. Now it does, with an inline `over_`
  that tolerates alpha-less parses; verified live in Chromium:
  `rgba(255,255,255,.3)` on black reads 2.48:1 (was a silent false 21:1).
- **browser detection chain**: `p` → `pw` in the chrome/msedge lambdas
  (we had "refuted" this by grepping the wrong shape — the bug was
  `lambda pw: p.chromium`, not `lambda p`).
- **focus indicator by border** (2.4.7): `outline:none; border:3px solid`
  no longer reported as invisible.

New regressions from our own 5.4.0 patches, fixed here:

- `_attrs` read single-quoted attributes as empty strings (findall fills
  `''`, not `None`) — the autofix silently stopped applying autocomplete to
  single-quoted HTML. Now `finditer` with true group semantics.
- viewport removal scanned for `>` without respecting quotes
  (`data-note="a>b"` corrupted the document). Quote-aware tag-end scan.

Both external reviewers were right where it counted. The lesson is pinned
next to the tests: **a fix is not shipped when the changelog says so — it is
shipped when the reproduction fails.**

## 5.4.0 — 2026-10-11 — "the second review" (40 findings, verified one by one)

A deeper external review (full module read, all suites executed, browser
verification of rendered failures) reported ~40 findings. Same protocol as
5.3.0: verify first, fix what reproduces, refute what doesn't, pin
everything. Fixed here:

**Critical / high**
- autofix no longer touches `<script>`, `<style>` or `<!-- -->` content in
  its attribute paths (verified clean; masked-tag regex now quote-aware, so
  `value="a>b"` survives autocomplete injection and error-layer placement).
- viewport removal consumed only up to the closing quote, leaving an orphan
  `>` in the page (`<head>></head>`). Now removes the whole tag.
- JSON-RPC 2.0 compliance: parse errors answer `-32700`, non-object
  requests `-32600` (previously the stdio process died on `null`/`[]`/`123`
  and stayed silent on malformed lines).
- `lang` in declarations is HTML-escaped in depth (defense behind the BCP-47
  validation) — the injection path is closed twice.
- rendered audit composes the TEXT color alpha, not only the background:
  `rgba(255,255,255,.3)` on black now reads ≈2.46:1 (was a false 21:1).
- 1.2.2 captions: the `elif` branch was unreachable — every page with a
  `<video>` produced a guaranteed false positive. One merged branch.
- `audit --pages N` (the README's flagship example) crashed on a missing
  `--no-sitemap` argparse flag. Fixed; flag added.
- `fieldset_missing` fired on correctly-wrapped radio groups (final-state
  boolean). Now tracked per group.
- 3.3.2 massive blind spot: checkbox/radio/file/range/color without labels
  were never flagged. Now every input but `hidden` is checked.
- color channels clamped at parse (rgb negatives, hsl >100%) and `hexs`
  defends — `rgb(-10,300,5)` produced invalid hex `#-58a03` and a fake ratio.

**Medium**
- PPM parser: CRLF headers shifted every pixel by one byte — plausible but
  wrong output (red-on-red scored 2.92). Fixed, and `.ppm` now always uses
  our spec-compliant parser (PIL shifts too).
- aria-live monitor: announcement text was interpolated into `innerHTML` —
  DOM XSS from the audited page. Rebuilt with `createElement`/`textContent`;
  embedded module regenerated.
- journey: friction now honors `lang='es'`; outcome booleans are strict
  (`"false"` no longer means true).
- evidence: disprover-rejected findings can't revive (extends 5.3.0);
  `mode: 'static'` present in every static report (SARIF/evidence contract).
- static audit: boolean `required` detected; fieldset tracked per group.

**Low (batch)**: `test_journey` + review suite in `make test` and CI;
`.playwright-mcp/` snapshots out of the repo; `autoplay muted` no longer a
1.4.2 finding; `aria-live="off"` not a status region; `tabindex=" 1"`
detected; badge truncates before escaping.

**Queued for 5.4.x/5.5** (verified real, needs design): rendered tooltip
check by element visibility (not node counts); forms JS distinguishing
help-text from error identification; ledger atomic writes + per-mode scope;
WCAG-EM consistent-navigation by order; es-catalog 27 typical_failures still
in English; hostile-input fuzz table for parse_color/image_contrast.

## 5.3.0 — 2026-10-11 — "the external review"

An external code review (2026-10-11) landed 6 P1/P2 claims and 10 further
findings. Every claim was **verified before acting** — 12 confirmed, 2
refuted (no `p`/`pw` lambda bug; the textarea case needed a `<form>` wrapper
to reproduce, then confirmed). All twelve confirmed findings are fixed and
pinned in `tests/test_revision_externa.py`:

- **`a11y_disprove` crashed on every call** (UnboundLocalError): our 5.1.1
  rename touched the signature but not the body. Fixed; and modes without a
  re-verifier now return `not-rechecked` instead of substituting a static
  audit — `rejected` is reserved for checks that actually disprove.
- **MCP contract**: `prompts/get` (the spec method) implemented — we only
  handled `prompts/call`, and our own test replicated the wrong method. Both
  now work; the test asserts the standard.
- **`auth_state` was accepted and silently dropped** in the dispatch of
  audit_dom, snapshot, scroll, keyboard, reflow and diff_urls — clients got
  unauthenticated audits of login-walled pages. Now transmitted everywhere.
- **`browser` parameter** exposed in the schemas of the rendered tools that
  support it (audit_dom, keyboard, reflow, sr_transcript).
- **autofix no longer corrupts `textarea`/`select`**: the error layer was
  injected INSIDE content-bearing elements, becoming their value. It now
  goes after the close; options and content preserved (regression-tested).
- **`_attrs`** crashed on empty attribute values (`value=""`) — StopIteration.
- **contrast**: modern space syntax with alpha (`rgb(0 0 0 / 50%)`) crashed;
  negative channels now clamp to 0. Focus-state text contrast uses the
  typographic threshold (4.5:1, or 3:1 for genuinely large text) instead of
  a blanket 3:1.
- **`a11y_diff`**: losing a focusable element is now `ok:false` with
  `focus.removed` — the exact regression (tabindex="-1" on the pay button)
  the old common-order comparison let through.
- **evidence pack**: findings marked `rejected`/`not-rechecked` by the
  disprover can no longer revive as failures; `_RENDERED_ONLY` now covers
  the specialized modes (forms, hover, keyboard, scroll) so static-only
  packs say `not-run` instead of implying coverage.
- **declaration**: the default method no longer claims expert manual review,
  axe-core checking and screen-reader testing that nobody performed — it
  states, in both languages, that the document is an unvalidated draft.
- **limits**: gzip responses decompress under a hard cap (61 bytes → 10 KB
  was the reviewer's proof); `_descarga` enforces the http/https-only policy
  for every path (the multi-page crawl skipped it).
- **CI/tests**: the dead `or True` assertion removed; `prompts/get` asserted;
  Playwright + Chromium now installed in CI so the rendered suites run, and
  Python 3.9 (our declared floor) entered the matrix.

Refuted claims are documented in the review-response commit message.

## 5.2.1 — 2026-10-09 — "annotations that tell the truth"

A TDQS audit (Glama's per-tool scoring) caught what the wire already said
about two tools and what the annotations denied:

- **`a11y_ledger`**: `record` mutates a persistent file and is not idempotent
  — `readOnlyHint` and `idempotentHint` were both wrong (scored 1/5 on
  Behavior). Now `false`/`false`.
- **`a11y_forms`**: it REALLY submits forms with invalid data — no longer
  declared read-only, and its description now carries the explicit usage
  guard: test/staging forms or forms you own; never production forms that
  trigger real emails, orders or leads.
- **Every tool description now states its return shape** ("Returns JSON:
  …") — 24 of 24, closing the Completeness penalty on tools like
  `a11y_audit_dom`.
- **`pages` parameter** gains `minimum: 1, maximum: 20` constraints.
- Optional `output_path` writers (badge, autofix, evidence, journey,
  declaration) disclose in-description that they write only when given.

No behavior changes — the wire verbs, schemas and outputs are untouched;
the annotations and descriptions now match what was always true.

## 5.2.0 — 2026-10-05 — "navigate like a screen-reader user"

Blindfold, level two — the research pass:

- **Five new friction patterns** model how real screen-reader users move:
  `journey_heading_nav_broken` (2.4.6) and `journey_landmark_missing`
  (2.4.1) — SR users navigate by headings and landmarks FIRST, Tab second,
  so a Tab-walk alone never sees these; `journey_mode_confusion` (4.1.2,
  keyboard-swallowing custom widgets), `journey_duplicate_targets` (4.1.2,
  ambiguous accessible names), `journey_dynamic_stale` (4.1.3, the tree
  changed under the agent with no announcement). Catalog: 15 patterns,
  parity-tested.
- **The `blindfold-task` prompt now instructs SR-native navigation**: list
  headings and landmarks from every snapshot and jump by them — navigation
  itself is under test.
- **Golden rule added** to the skill: navigate by headings/landmarks first,
  Tab as fallback; broken hierarchies are findings, not inconveniences.
- **Worked example, run for real**: `docs/journey-example.md` — the author
  executed a blindfold journey against a failing fixture strictly by the
  rules (snapshot-only perception, accessible-name actions, gave_up
  protocol). Result: blocked, 0/100, six findings across six criteria.
  The run validated state-preserving perception, the new navigation rules
  and the gave_up protocol in the wild.

## 5.1.1 — 2026-10-05 — "blindfold sees with the right eye"

Functional fix to the blindfold loop: the prompt told the agent to perceive
via `a11y_sr_transcript`, which opens a FRESH page — mid-journey that loses
session state (filled forms, open dialogs). Perception now happens through
the agent's own browser accessibility snapshot at every step (state-
preserving); `a11y_sr_transcript` stays as an optional one-shot at journey
start for the linearized prose. Tool description and skill row updated, plus
four golden rules for running journeys (no vision fallback, same tab,
friction logged at the step it happened, 320px runs for mobile).

Also: the one code comment naming a specific marketplace is now generic.

## 5.1.0 — 2026-10-05 — "blindfold"

The capability no other accessibility tool has: **task-based non-visual
usability testing, where the agent IS the screen-reader user.**

- **New prompt `blindfold-task`**: the agent attempts a REAL task ("sign up",
  "checkout", "password reset") perceiving ONLY the accessibility tree
  (`a11y_sr_transcript` / `a11y_snapshot`) and acting only by accessible name
  and keyboard. Reading HTML, screenshots or CSS is forbidden by the prompt —
  what is not in the tree does not exist. After every action it re-perceives
  and logs friction.
- **New tool `a11y_journey_verdict`**: turns the friction log into a
  deterministic scored verdict — start 100, −25/−12/−5 per high/medium/low
  friction, −15 if the task was only completable via a workaround; verdicts
  pass / partial / fail / blocked (gave_up is a paid outcome, not an agent
  failure). Friction items map to WCAG criteria via a 10-pattern catalogue
  (`journey_unnamed_control` → 4.1.2, `journey_focus_lost` → 2.4.3, …) or raw
  criterion + issue, validated against the 55 A/AA set.
- **Evidence pack integration**: journeys enter as `report:journey`; a high
  friction observed in a real task is an `automated-fail` in the matrix —
  usability evidence with the same hash chain as everything else.
- Honesty guard: the verdict's score_note states a pass means ONE task was
  completable non-visually by an AI agent — not conformance, not a human
  screen-reader user.
- Also: MCP argument `informe` → `report` in `a11y_disprove` (a v5.0.0
  rename leftover), and gen-visuals fully on English keys (GIF regenerated
  at 24 tools · 6 prompts).

## 5.0.0 — 2026-09-23 — "english on the wire"

Every JSON key the toolkit emits is now English. The toolkit was born as a
personal Spanish tool and, when the project went English-first, the prose was
translated but the wire keys froze — `criterios`, `estado`, `esfuerzo`,
`hallazgos`, `minutos`, `severidad`, `senal`… That split is gone.

- **Evidence pack → `a11y-evidence-pack/2`**: every key renamed
  (`criterios`→`criteria`, `estado`→`status`, `esfuerzo`→`effort`,
  `esfuerzo_pendiente`→`effort_pending`, `artefactos`→`artifacts`,
  `evaluador`→`reviewer`, `manual_pendiente`→`manual_pending`,
  `formato`→`format`, `generado`→`generated`, …).
- **MCP arguments**: `informes`→`reports`, `verificados`→`verified`,
  `evaluador`→`reviewer`, `entidad`→`entity`, `marco`→`framework`.
- **Audit reports**: `hallazgos`→`findings`, `severidad`→`severity` with
  values `high`/`medium`/`low`, `senal`→`signal`, `remediacion`→`remediation`,
  `resumen`→`summary`, `score_nota`→`score_note`, `modo`→`mode`.
- **Contrast tools**: `veredictos`→`verdicts`, `ratio_peor`→`worst_ratio`,
  `area_pasa_aa_texto_normal_4_5`→`area_passes_aa_normal_text_4_5`,
  `zona_peor`→`worst_zone`, `sugerencia_aa`→`aa_suggestion`, …
- **Snapshot/diff**: `elementos`→`elements`, `orden_foco`→`focus_order`,
  `aniadidos`→`added`, `eliminados`→`removed`, `renombrados`→`renamed`, …
- **Budget/ledger/criterion tool**: `senales`→`signals`,
  `bloqueantes`→`blocking`, `historial`→`history`, `exige`→`requires`,
  `fallos_habituales`→`typical_failures`, `como_comprobar`→`how_to_check`, …

Coordinated with the Countersignatory exchange before their resolver hardens:
their draft-2 schema referenced the Spanish keys and updates to English in the
same window (their namespace, their rename).

Signal identifiers (stable codes like `img_sin_alt`) are unchanged — they are
IDs, not prose, and renaming them would invalidate existing error budgets.

## 4.0.1 — 2026-09-23 — "aligned with the market"

Docs-only release: the canonical effort-class documents adopt the two rules the
Countersignatory exchange formalized against the published table
(cs-a11y-classes-2026-09-23):

- Rule 1 is now two-sided: confirming a measured `automated-fail` is the MIN
  human class; certifying a PASS always costs the criterion's full table class.
  A MIN confirmation can never become a pass.
- The NA settlement rule: a criterion quoted at its class settles at MIN when
  the human verdict is `not_applicable` with a reason — the buyer does not pay
  for examination that did not happen.

No code changes; `_EFFORT` and the packs it emits are unchanged.

## 4.0.0 — 2026-09-22 — "the package"

The repository grew a proper layout — 37 tracked files sat in the repo root;
now the root is 7 files and 8 directories:

- **`a11y_toolkit/` package**: all 18 Python modules plus `arialive.js` moved
  under one package; intra-package imports are relative. The supported
  surfaces are unchanged: console scripts (`a11ytoolkit`, `a11y-toolkit-mcp`),
  `python3 -m a11y_toolkit.<module>`, and the MCP stdio protocol.
- **`tests/`**: the seven suites moved out of the root; every CLI end-to-end
  test now drives the module (`-m`) path, not a file path.
- **`.github/`**: SECURITY, CODE_OF_CONDUCT and CONTRIBUTING moved there
  (GitHub still surfaces all three).
- **BREAKING (hence the major)**: direct `import a11yaudit` from the
  installed package no longer works — use `from a11y_toolkit.a11yaudit
  import …`. Console scripts and the wire protocol are untouched, so every
  documented client (uvx, pipx, smithery.yaml, server.json package
  arguments) keeps working verbatim.
- `scripts/versionar.py`, the Makefile, CI and the pre-push hook follow the
  new paths; versionar's obsolete test_mcp version bump is gone (the
  assertion derives from `server.VERSION` since 3.21.0).

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

*(3.14–3.20: internal iterations, released without changelog entries — history lives in git)*

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
