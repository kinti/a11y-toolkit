# Benchmark: a11y-toolkit vs axe-core (monthly, real pages)

Methodology: [`compara.py`](compara.py) runs the toolkit's static + rendered
audits and axe-core 4.10 on the same live pages, then compares criteria
found. Scheduled monthly via CI (first run: **2026-10-01**, run
[36874832232](https://github.com/kinti/a11y-toolkit/actions/runs/36874832232));
raw JSON in `results/` per month.

## October 2026

| Page | Toolkit static | Toolkit rendered | Toolkit criteria | axe node hits | axe criteria | Both | Only toolkit | Only axe |
|---|---|---|---|---|---|---|---|---|
| example.com | 88 | 86 | 3 | 9 | 2 | 2 | 1 | 0 |
| www.gov.uk | 98 | 74 | 5 | 2 | 1 | 0 | 5 | 1 |
| es.wikipedia.org/wiki/Wikipedia:Portada | 42 | 56 | 12 | 14 | 4 | 3 | 9 | 1 |
| www.jquin.net | 98 | 100 | 1 | 0 | 0 | 0 | 1 | 0 |

The table uses the historical mapping recorded in the October JSON.
That version mapped axe's `region` rule to 2.4.1. The current comparator
uses axe's numeric WCAG tags for criterion counts and keeps untagged
rules in the raw violations.

Live-page counts show agreement and suggest cases for manual review.
For example, the toolkit raised a 3.91:1 search button on GOV.UK for text
contrast review. The visible icon passed the 3:1 non-text threshold and
the label was visually hidden. The detector now checks those cases
separately. Precision and recall require independently labelled cases
and a declared scope.

## Validating a run

```bash
python3 bench/compara.py --check results.json --expect 4
python3 bench/compara.py --check results.json https://example.com https://www.gov.uk https://es.wikipedia.org/wiki/Wikipedia:Portada https://www.jquin.net
```

CI uses the second form with the same page list for capture and
validation. Each declared URL must appear once and resolve to a distinct
final page. A valid row contains completed toolkit static, toolkit
rendered and axe passes, a successful axe page load and the same final
URL in all three passes. The suite expects at least four toolkit
criterion hits across the panel, with each criterion counted once per
page. Rows record `axe.http_status`, both rendered `url_final` values and
`toolkit.url_final_static`. Use current captures to exercise the gate.

Both comparison scripts borrow pages from the engine's browser pool
through `bench/browser.py`. Sharing the pool keeps Playwright's sync API
on one driver. The same scripts work with `A11Y_BROWSER_POOL=0`.

## Frozen corpus cross-check

On corpus `2026.11.0`, the toolkit detected 18 of 18 injected failures.
axe-core 4.10.3 detected the expected criterion on 9 of 18 pages. Both
covered all three placebo controls with zero flags. To reproduce the axe
submission, open each HTML file from `cases.jsonl` in Chromium (this run
used 147.0.7727.15). Use `axe_en_pagina` and `axe_a_criterios` from
`compara.py` to write one row of criterion codes per case and score it
with `corpus evaluate`. The static toolkit reference uses that same
scorer. [Corpus scoring guide](../docs/cookbook.md#12-score-any-engine-against-the-frozen-corpus)

The corpus derives from the toolkit's mutation operators. The measured
detection rate covers the expected criterion tags in these 18 cases.
An independent corpus with broader coverage would support a stronger
comparison.

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
