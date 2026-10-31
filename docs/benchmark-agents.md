# Can an AI coding agent maintain WCAG 2.2 AA? A task-based benchmark

## The idea

Every scanner scores pages. None of them answers the question a blind user
actually faces: **can I get the task done?** So we benchmarked the other way
around. An AI coding agent attempts a real task on a production site,
perceiving ONLY the accessibility tree of its own browser — no pixels, no
DOM — acting by accessible name and keyboard, exactly like a screen-reader
user. Every obstacle is logged with its WCAG criterion and remediation. A
deterministic verdict closes the journey (start at 100; −25 per high
friction, −12 per medium; giving up means blocked).

The protocol is the open-source `blindfold-task` prompt; the scoring is
`a11y_journey_verdict`; the evidence lands in the same SHA-256-verifiable
pack the audits use. Reproducible end to end.

## The journeys (live, named)

| Journey | Task | Verdict |
|---|---|---|
| GOV.UK | find out how to renew a passport | **pass, 100** |
| IKEA Spain | find a floor lamp under €50 | **blocked, 0** |

The GOV.UK run is the boring one, and that's the point: textbook landmarks,
named controls, answer on the first screen. **The tool must say pass when
the work is good** — an honest pass is worth as much as an honest fail.

**Update 2026-10-31 — the IKEA re-run: pass, 100.** Twenty-six days after the
blocked run, the journey was re-executed blindfold, same protocol: the search
combobox is exposed by name, results expose product names AND prices in the
tree (BARLAST 9,99€, LERSTA 19,99€, LAUTERS 44,99€…), add-to-cart buttons
carry the full product name, and the task completes from the results page
alone. The store changed — for the better — and the benchmark tracked it in
both directions. That is the argument for task-based testing in CI: a point-
in-time audit is a photograph of a moving target. The original October 5
finding (below) is kept as measured, dated.

The IKEA run of October 5 was the finding this method exists for: live
regions correctly announced "52 products", skip links worked, headings were
clean — and **not one product name or price was exposed to the accessibility
tree on any page type**. Every element existed, every widget was individually
reachable, every rule-scanner saw a working store. The commerce layer simply
was not there for a blind user.

Full journals: [docs/journey-example.md](journey-example.md).

## The Spanish sample (static sweep, one homepage per sector)

To complement task-based testing with the wide view, we audited the homepage
of the most important Spanish site per sector (v5.15.0 static audit, one
request per site, October 26, 2026; numbers identical on an October 25
re-run). A third re-run on October 31 kept seven of nine identical and moved
two — Movistar 98 (was 92), RTVE 16 (was 26, 60 images without alt, 202
hidden focusable links) — sites drift within a week, which is exactly why
audits belong in CI instead of in a PDF:

| Sector | Site | Score | Signature finding |
|---|---|---|---|
| Telecom | Movistar | **92 → 98** | best in sample |
| Commerce | Amazon.es | 82 | no page title served to agents |
| Gov | BOE | 78 | unnamed control |
| Rail | Renfe | 80 | no h1, no bypass |
| News | El Mundo | 62 | focusable-but-hidden links |
| Commerce | IKEA Spain | 60 | unlabeled fields, uncaptioned video |
| Gov | Seguridad Social | 58 | zoom capped, focusable-hidden |
| Air | Iberia | **40** | **205 focusable buttons hidden with aria-hidden** |
| Public TV/Radio | RTVE | **26 → 16** | **60 images without alt, 202 hidden focusable links, no h1** |
| News | El País | — | blocked (403 to agents) |
| Commerce | El Corte Inglés | — | blocked (403) |
| Banking | BBVA | — | blocked (403) |

Read the patterns, not the sites: **focusable-but-hidden** controls
(`aria-hidden="true"` on tab-reachable elements) — in five of nine auditable
sites on October 26, three of nine on October 31 (El Mundo, Iberia, RTVE):
the keyboard works and the screen reader never announces where it landed.
**Nobody announces changes** (no live regions) in seven of nine. And three of
Spain's biggest sites **block third-party auditing outright** (403) — the
same door every consultant's tool hits.

And the key contrast, again: IKEA Spain scores 60 here — "passable" — and
0/100 in the blindfold journey. **The static sweep approves the shop window;
the blind user cannot buy.** Task-based and rule-based testing measure
different things, and you need both.

## Scope, honestly

- Two live journeys + one fixture, one task each: a method demonstration,
  not a market survey.
- Static scores are a filter, not a verdict: automation covers about a
  third of WCAG 2.2. The evidence pack prices the human remainder per
  criterion.
- The agent replaces the *absence* of any non-visual check in CI — not the
  screen-reader user, not the qualified human who signs.

## Reproduce

```bash
pip install a11y-toolkit playwright && playwright install chromium
# blindfold protocol with your agent (the friction log is JSON:
# {task, steps, outcome}), then score deterministically:
a11ytoolkit journey journey.json --out verdict.json
```

Version: v5.15.0 (2026-10-25). Journeys run 2026-10-05, re-run 2026-10-31
(pass, 100); Spanish sample run 2026-10-26, re-run 2026-10-31; tables refresh
at each publication.
