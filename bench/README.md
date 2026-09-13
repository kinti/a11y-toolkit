# Benchmark: a11y-toolkit vs axe-core 4.10 — real pages

Methodology: on the SAME Chromium page and with the SAME Playwright, we run
(a) a11y-toolkit's static auditor on the served HTML, (b) `a11y_audit_dom`
(rendered) and (c) axe-core 4.10.3 injected. The criteria each reports are
compared. Last run: 2026-09-07, **v3.10.0** (re-measured after the v3.9 criteria wave; re-runs monthly via CI — see `.github/workflows/bench.yml`).

Reproduce it: `python3 bench/compara.py <url…>` (axe.min.js auto-downloads).

## Results

| Page | Toolkit (static/rendered) | Matches axe | axe only | Toolkit only | Triage verdict |
|---|---|---|---|---|---|
| example.com | 94 / 94 | 2.4.1 | — | — | perfect agreement |
| **gov.uk** | 98 / **82** | — | 2.4.1 (`region`, 2 nodes) | **REAL 1.4.3** + 1.3.1 + 2.5.8 | **we found a real failure axe does not report**: "Search GOV.UK" button, `#1d70b8` on `#d2e2f1` at 13px = 3.91:1 < 4.5 (manually verified). axe files contrast under "incomplete"; we compute it |
| es.wikipedia (front page) | 44 / 64 | 1.1.1, 1.3.1, 4.1.2 | 2.4.1 (`region`) | 1.4.3 (review: image backgrounds), 2.1.1/3.3.2/2.4.4/3.1.2 (static pass) | static score dropped 50→44 as the v3.9 criteria landed (3.1.2 lang-of-parts now caught) — raw HTML vs JS DOM: use `a11y_audit_dom` on JS-heavy sites |
| jquin.net | 98 / **88** | — | — | 2.4.4 (static, advisory) + **4.1.2 unnamed footer link** | **the toolkit found a real bug on its author's own site**: an icon-only footer link with no accessible name (caught by the improved rendered collector). Being fixed |

axe's `region` rule (content OUTSIDE landmarks) is a different granularity
from ours (that a bypass mechanism exists: main/skip link) — not a false
negative on our side.

## False positives this benchmark drove out (fixed in v3.4.0)

1. `aria-hidden="true"` on controls with `tabindex="-1"` — not tabbable;
   2.4.7/4.1.2 do not apply. **Fixed** (static + rendered).
2. Hidden **honeypot** container (input with `tabindex="-1"` inside) reported
   as a hidden control. **Fixed**: only reported when a descendant is tabbable.
3. **Hidden skip link** (1×1px clipped) reported by 2.5.8. **Fixed**:
   visually hidden elements are excluded from the target-size check.
4. A **single generic link** reported as 2.4.4 — surrounding sentence context
   usually disambiguates. **Fixed**: only reported on repetition (≥2).
5. Inline links at 20-24px: the 2.5.8 **spacing exception** is not measurable
   without full layout; when all cases are inline the finding drops to "low"
   (review) instead of "medium".

Every case has a regression fixture in `test_dom.py` / `test_audit.py`.

## Known, honest limits

- axe and we draw the violation vs "needs review" line differently; axe
  returns many contrast results as *incomplete* (excluded here) while we
  compute them — hence contrast findings axe does not list.
- The static pass reflects the SERVED HTML (pre-JS): on SPAs and highly
  dynamic sites it is a first-pass filter, not the final truth.
- **Shadow DOM (v3.5.0)**: the collector traverses OPEN shadow roots (up to
  20, depth 6) — contrast, targets, names, images, focus and states. Validated
  with a web-component fixture (all four inner failures detected with
  `mi-tarjeta ::slotted> …` paths) and in production: github.com (5 roots) and
  m3.material.io (2 roots) scan without errors. CLOSED roots are impossible by
  browser design — declared, not hidden.
- `list_structure` rule (1.3.1) added: illegal children of `<ul>/<ol>`
  (axe's `list` rule).
