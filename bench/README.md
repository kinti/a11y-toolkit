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

The sanity gate in CI asserts the toolkit still finds things (≥4 signals)
— a benchmark that could silently go blind would be worse than none.

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
