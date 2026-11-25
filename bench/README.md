# Benchmark: a11y-toolkit vs axe-core (monthly, real pages)

Methodology: [`compara.py`](compara.py) runs the toolkit's static + rendered
audits and axe-core 4.10 on the same live pages, then compares criteria
found. Scheduled monthly via CI (first run: **2026-10-01**, run
[36874832232](https://github.com/kinti/a11y-toolkit/actions/runs/36874832232));
raw JSON in `results/` per month.

## October 2026

| Page | Toolkit static | Toolkit rendered | Toolkit criteria | axe violations | axe criteria | Both | Only toolkit | Only axe |
|---|---|---|---|---|---|---|---|---|
| example.com | 88 | 86 | 3 | 9 | 2 | 2 | 1 | 0 |
| www.gov.uk | 98 | 74 | 5 | 2 | 1 | 0 | 5 | 1 |
| es.wikipedia.org/wiki/Wikipedia:Portada | 42 | 56 | 12 | 14 | 4 | 3 | 9 | 1 |
| www.jquin.net | 98 | 100 | 1 | 0 | 0 | 0 | 1 | 0 |

Reading it honestly:

- **Overlap where both look** (example.com: 2/3, Wikipedia: 3/12) — the
  core signals agree. "Only toolkit" rows are mostly review-grade signals
  (DOM-vs-visual order, heading quality) and the rendered checks axe marks
  *incomplete*.
- **gov.uk is the showcase**: axe reports 1 criterion (`region`), the
  toolkit reports 5 — including a rendered contrast finding axe's own
  rule leaves as "incomplete" (the **3.91:1** search button). Manual
  review corrected that finding: the button's visible content is an icon
  that passes the 3:1 non-text threshold, and its label is visually hidden,
  so it is not a conformance failure. The detector now distinguishes
  visible text from visually-hidden text.
- **Only axe** on Wikipedia: `landmark-one-main` style rules the static
  pass intentionally does not score (it flags, not fails, partial
  landmark coverage) — the gap list is in the raw JSON, not hidden.

The gate in CI is `python3 bench/compara.py --check bench/results.json
--expect 4`. A row only counts as evidence with results from the three
engines (toolkit static, toolkit rendered, axe) on the same page: the check
rejects a failed row, a row missing an engine, a row where axe executed no
rules, a row where axe's own page load was an error response (4xx or 5xx) and
a row where any of the three passes ended on a different final URL. It still
requires the toolkit to find things across the pages (4 criteria or more).
The previous gate looked at the toolkit alone, so a run could go green with
axe not running, and later with axe auditing a 404 the browser had loaded
without complaint. Rows record `axe.http_status`, both rendered `url_final`
values and `toolkit.url_final_static`. Earlier result files are historical
records and lack fields needed by `--check`. The comparison uses each axe
rule's numeric WCAG tags. Rules without a criterion tag remain in the raw
violations and are excluded from the WCAG divergence lists.

The scripts never open a Playwright session of their own. The rendered audit
keeps the engine's browser pool alive for the rest of the process, and a
second sync session in the same thread fails with "Sync API inside the
asyncio loop". `bench/browser.py` lends them a page from that same pool,
which is why the benchmark runs with the default configuration and with
`A11Y_BROWSER_POOL=0` alike.

## Regression flow (`pr-flow.py`)

Give it two snapshots of one page and it reports, per tool, which findings
appeared and which disappeared:

    python3 bench/pr-flow.py before.html after.html [--rendered] [--axe]

- Toolkit static always runs. `--rendered` adds the Playwright pass when
  Playwright is installed. `--axe` adds axe-core when a local copy exists
  (`bench/axe.min.js` or the user cache the monthly benchmark fills). An
  opt-in that cannot run is reported as `skipped` with the reason.
- Findings are compared instance by instance: by element route in the static
  pass, by example text in the rendered one, and in axe by failing node
  (rule plus target). A failure that moves from element A to element B is
  one new and one fixed.
- A finding that is not tied to an element (a missing `title`, a missing
  `lang`) counts as one page-level instance, reported with a `null` element:
  a page that loses its title reports one new finding.
- A finding aggregates many elements and carries only the first ones (5 in
  the static pass). At or past that number the report cannot back an
  element-level verdict, so the signal is listed under
  `insufficient_evidence` with the measured count delta (read from the
  message for older reports): a page
  going from 6 to 7 images without alt reports 1 new finding that cannot be
  located. `summary.inconclusive` names the affected tools and signals.
- Routes are positional: inserting an element shifts the routes of its later
  siblings, which then read as moved instances.
- Exit code 0 means every requested pass measured, new findings or not (the
  budget gate decides elsewhere). Exit code 1 means a pass failed to run.
  A failed measurement is never reported as zero findings.

`tests/test_bench_flow.py` pins all of the above against a local page, under
the default pool configuration.

## Local parser and annotation measurements

Both runs used CPython 3.12 on the same machine, with commit `d330539`
as the baseline. Inputs were synthetic HTML and reports.

| Operation | Input and measurement | Baseline | Parent-linked routes and one-pass annotation |
|---|---|---:|---:|
| `audit_html` | 3,200 nested `div` elements and one image without alt text, peak Python allocations via `tracemalloc` | 95.2 MiB | 2.6 MiB |
| `annotate` | 4,000 images with 230-character sources and one path per image, median of five elapsed times | 147 ms | 12 ms |

The first case checks that the emitted selector still includes all 3,200
ancestors. The second checks that every submitted path produces a mark.
These inputs isolate deep nesting and large mark counts. Times will vary
with the input, Python version and hardware.

In a separate CPython 3.12 run with 3,200 wrappers and 400 explicit
`listitem` roles, the parent-linked ARIA check reduced peak Python
allocations from 81.07 MiB to 2.58 MiB. A role after the first 400 is now
checked as well.
