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
  toolkit reports 5 — including the rendered contrast failure axe's own
  rule leaves as "incomplete" (the manually-verified **3.91:1** search
  button, criterion 1.4.3) plus text-spacing, focus and target-size checks
  axe does not run.
- **Only axe** on Wikipedia: `landmark-one-main` style rules the static
  pass intentionally does not score (it flags, not fails, partial
  landmark coverage) — the gap list is in the raw JSON, not hidden.

The sanity gate in CI asserts the toolkit still finds things (≥4 signals)
— a benchmark that could silently go blind would be worse than none.
