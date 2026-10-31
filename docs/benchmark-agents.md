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

The IKEA run is the finding this method exists for: live regions correctly
announce "52 products", skip links work, headings are clean — and **not one
product name or price is exposed to the accessibility tree on any page
type**. Every element exists, every widget is individually reachable, every
rule-scanner sees a working store. The commerce layer simply is not there
for a blind user. Verifiable independently: open any accessibility-tree
inspector on the pages and look for a product name.

Update 2026-10-31: **this has been corrected by the site** — the same
journey re-run today, same blindfold protocol, scores **pass, 100** (product
names, prices, ratings and add-to-cart buttons are now in the tree; the task
completes from the results page alone). Independent-witness attempt: an
archive.org capture of the search page from October 5 (09:35 UTC) is
preserved, but the results were client-rendered, so the archive cannot
re-render that day's tree — the October 5 measurement stands as taken, and
the correction stands as measured today.

Full journals: [docs/journey-example.md](journey-example.md).

## The Spanish sample (static sweep, one homepage per sector)

To complement task-based testing with the wide view, we audited the homepage
of the most important Spanish site per sector (v5.15.0 static audit, one
request per site, October 26, 2026; numbers identical on an October 25 re-run):

| Sector | Site | Score | Signature finding |
|---|---|---|---|
| Telecom | Movistar | **92** | best in sample |
| Commerce | Amazon.es | 82 | no page title served to agents |
| Gov | BOE | 78 | unnamed control |
| Rail | Renfe | 80 | no h1, no bypass |
| News | El Mundo | 62 | focusable-but-hidden links |
| Commerce | IKEA Spain | 60 | unlabeled fields, uncaptioned video |
| Gov | Seguridad Social | 58 | zoom capped, focusable-hidden |
| Air | Iberia | **40** | **205 focusable buttons hidden with aria-hidden** |
| Public TV/Radio | RTVE | **26** | **no h1 (only commented out); ~200 focusable elements hidden with aria-hidden; 60+ images without alt are lazy-load placeholders (see Oct-31 notes)** |
| News | El País | — | blocked (403 to agents) |
| Commerce | El Corte Inglés | — | blocked (403) |
| Banking | BBVA | — | blocked (403) |

Read the patterns, not the sites: **focusable-but-hidden** controls
(`aria-hidden="true"` on tab-reachable elements) in five of nine auditable
sites — the keyboard works and the screen reader never announces where it
landed. **Nobody announces changes** (no live regions) in seven of nine.
And three of Spain's biggest sites **block third-party auditing outright**
(403) — the same door every consultant's tool hits.

Update 2026-10-31 (re-runs, every number verified by us unless noted):
Movistar 98 (was 92) — reproduced. RTVE: the score is the most volatile of the
sample because the homepage rotates news content; on October 26 it was 26, and
on October 31 we reproduced both 28 and 16 with the same pinned v5.15.0 and
single-page mode. The signature findings are stable: 60 images without alt
(almost all 1×1 lazy-load data:URI placeholders, not content images), ~200
focusable elements hidden with aria-hidden, and the only h1 of the page
exists inside an HTML comment, not in the rendered tree. The lesson is the
argument of the table itself:
a score is a function of tool version, mode and date — publish all three or publish nothing.
The focusable-but-hidden pattern holds today in El Mundo (203 elements, score 62 unchanged), Iberia
(205, score 40 unchanged) and RTVE — three of nine auditable, from five of
nine on October 26. Sites drift within days — audits belong in CI.

Update 2026-10-31, second addendum — **the "images without alt" signature,
examined to the end.** Against the author's own page source: 830 images, 644
carry informative alt, 126 carry alt="" (declared decorative), and the 60
without the attribute are almost entirely 1×1 transparent lazy-load
placeholder GIFs (data: URIs) plus one JS template artifact — not content
images. In the rendered accessibility tree — the contract a screen reader
consumes — **every image node exposed carries an accessible name**:
the placeholders never surface unnamed. The static rule remains
ACT-true on the served HTML, but under this project's doctrine (WCAG applies
to the rendered experience) it does not reach the user. The image findings
that DO reach the tree: five alts truncated at parse time by unescaped quotes
(including one whose full text — a survivor's quote — is destroyed into empty
attributes) and two mute video links. Consequence for the tool itself: the
static img_no_alt signal must annotate data-URI placeholders as
verify-in-rendered-pass instead of reporting them flat — engine backlog.
The static score above includes that placeholder-driven high finding; the
rendered pass is the authority on experience.

And the key contrast, again: IKEA Spain scores 60 here — "passable" — and
on October 5 the blindfold journey was 0/100 (the site has since corrected it;
the re-run passes 100). **The static sweep approved the shop window; the
blind user could not buy that day.** Task-based and rule-based testing measure

## Scope, honestly

- **The journey verdict is task-usability evidence, not conformance.** WCAG
  is the normative limit and the static audit is what speaks it (IKEA: 60,
  mixed); nothing here claims any site fails WCAG because a task failed.
  The journey measures what a conformance floor cannot see: whether a real
  task is completable non-visually.
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
