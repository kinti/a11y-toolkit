# a11y corpus 2026.10.0

Frozen pages with sealed ground truth for evaluation-benchmarking ANY
accessibility engine. Version 2026.10.0, 21 cases (18
sealed mutants + 3 placebo controls). Format `a11y-corpus/1`.

## The contract (engine-neutral)

One JSON line per case in your submission file:

{"case_id": "m7-0", "criteria_found": ["1.1.1"]}

`criteria_found` = the WCAG 2.x criteria YOUR evaluator reports as failing
on that page (criterion codes, e.g. "1.4.4" — not tool-specific rule ids).
Placebo cases accept the same shape; anything you flag on them counts as a
false positive by construction (no violation was injected).

Score it:

    a11ytoolkit corpus evaluate --submission my-submission.jsonl corpus

## Verify this corpus (no toolkit needed)

Every file hash and the manifest seal are plain sha256:

    cd corpus && shasum -a 256 -c <(python3 -c \
      "import json;m=json.load(open('MANIFEST.json'));[print(v+'  '+k) for k,v in m['files'].items()]")

The seal `MANIFEST.json.sha256` covers the canonical manifest without the
seal itself — recompute and compare (see a11ycorpus.py `verify`).

## Baseline

`results/reference.json` is this engine's own submission scored by the same
harness (published WITH the dataset, LSVD-style). A published corpus
version is never edited; changes ship as a new version + changelog entry.
