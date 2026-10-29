# RUNBOOK — the monthly benchmark loop (~30 min, first days of each month)

The CI ([`axe benchmark`](../.github/workflows/bench.yml)) re-measures the
toolkit vs axe-core on day 1 of every month, 07:00 UTC. What CI can't do is
the human half: publish the month's honest reading. This is that loop.

## The loop

1. **Run** — either wait for the cron or trigger it:
   `gh workflow run bench.yml` then `gh run watch`.
2. **Fetch the raw result** (never edit it):
   `gh run download --name axe-benchmark` → save as `bench/results/YYYY-MM.json`.
3. **Write the month's section in `README.md`** — the table + a "reading it
   honestly" block. Rules below are non-negotiable.
4. **Commit direct to main**: `bench: YYYY-MM` (docs-only precedent; this
   isn't release-gated).
5. **(Optional, recommended)** mutant cross-check — see below.
6. **(Optional, human)** a short note on dev.to / a11y.es — Jesús's call,
   never automatic.

## The rules (what makes it credible)

- **Fixed page panel.** The 4 pages in `bench.yml` are the panel; changing
  the panel invalidates month-over-month comparison. If a page dies, replace
  it in `bench.yml` AND say so in the month's section.
- **Raw JSON always lands in the repo.** The README table is a reading, not
  the evidence; `results/YYYY-MM.json` is.
- **Every divergence gets an explanation, not a spin.** "Only toolkit" rows
  must say WHY (review-grade signals, checks axe marks incomplete); "only
  axe" rows must say what we intentionally don't score. The October section
  is the format to follow.
- **The sanity gate is CI's, the honesty gate is yours.** CI asserts the
  toolkit still finds ≥4 signals (a benchmark that could silently go blind
  would be worse than none); the human step is explaining, never hiding.
- **Local mirrors for third-party engines** (house rule): axe-core's MPL
  artifact lives in the user cache (`~/.cache/a11y-bench`), never in the
  tree; no request bursts against third-party services. Extending the panel
  of engines (Alfa, QualWeb — npm, mirrorable; WAVE is API-paid) follows the
  same pattern: add to `compara.py`, one request per page per run.

## Mutant cross-check (the blind-spot number)

The engine's own exam is pinned by the suite (`tests/test_mutants.py`: kill
rate 1.0 on a sealed seed). The monthly extra is examining the OTHER
engine on the same mutants — what axe misses on our bank:

```python
from a11y_toolkit import a11ymutants
from a11y_toolkit.a11ymutants import run_exam, generate
# an external examiner = a callable(html)->findings; wrap axe as compara.py does
report = run_exam(engine=my_axe_wrapper)
```

The number to publish is the external engine's kill rate on the SAME sealed
exam — phrase it exactly that way ("axe kills N of the same 12 mutants the
toolkit's suite pins at 12/12"), never as a general superiority claim.
