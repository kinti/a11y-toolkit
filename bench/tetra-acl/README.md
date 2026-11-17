# bench/tetra-acl — calibration against known-good components

[TetraLogical's accessible-components-library](https://github.com/TetraLogical/accessible-components-library)
v1.0.0 (ISC, commit pinned in [ATTRIBUTION.md](./ATTRIBUTION.md)) ships eight
accessible components (accordion, breadcrumbs, dialog, disclosure, pagination,
tabs, text input, textarea) with per-criterion expectations their own
Cucumber/Playwright scenarios enforce. Sixteen example pages are vendored in
[`pages/`](./pages). This engine audits them; the point is measurable
calibration, not a demo.

## First reading (2026-11-17, engine 5.27.0 + lang fix)

- **Static: 13 findings across 16 pages, every one of them
  `no_headings`/`no_h1` (low, 1.3.1).** That is example-page context, not
  component markup: the upstream examples are minimal fragments without page
  headings. Zero findings on the component markup itself — no aria, contrast,
  label or autocomplete noise against implementations a top consultancy
  publishes as correct.
- **Rendered (keyboard walk + 320px reflow, Playwright): 16/16 pages clean.**
  No keyboard trap anywhere, no horizontal scroll at 320px — agreeing with
  the upstream scenarios for 2.1.2-style keyboard behaviour and 1.4.10 reflow.
  Tab-stop counts look right per component (e.g. non-modal dialog: 2 stops;
  pagination default: 10).

Both passes were run before this directory existed and then re-run through
`sweep.py`; the raw evidence is [`results/2026-11-17.json`](./results/2026-11-17.json)
and is never edited by hand.

## Rules

- **The reviewed allowlist is the invariant.** `tests/test_tetra_acl.py`
  pins that static findings on these pages may only be the two reviewed
  1.3.1 page-context signals. A new signal firing here fails the suite: the
  engine either learned something real on known-good markup (double-check
  it, then extend the allowlist with a comment) or grew a false positive
  (fix the engine, not the allowlist).
- **Rendered degrades to static without Playwright**, exactly like
  `tests/test_engines.py` — CI without a browser still guards the static
  panel; the rendered half runs where a browser exists.
- **Upstream moves on purpose.** Re-pin the commit, re-copy, re-run
  `sweep.py`, re-triage every finding, re-pin the allowlist, and say so
  here with the date. A silent page swap would hollow out the panel.
- **This bench is documentation-grade, not release-gated** — same precedent
  as the monthly axe benchmark in the parent directory.
