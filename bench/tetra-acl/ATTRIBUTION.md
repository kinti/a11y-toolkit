# Attribution — bench/tetra-acl

Vendored material: the 8 component example pages plus their CSS/JS from
[TetraLogical's accessible-components-library](https://github.com/TetraLogical/accessible-components-library)
v1.0.0, pinned at commit `214baddf9a0500fd067a37c83583bd288f5a4f72`
(clone of 2026-11-17). Upstream license: **ISC** — its full text ships
verbatim in [`LICENSE`](./LICENSE) as the ISC notice requires.

What we took: `dist/<component>/examples/*.html` + the component CSS/JS
next to them (needed so the rendered pass reproduces with styles in place).
What we did NOT take: their Gherkin scenarios, step definitions, docs and
site — those remain upstream's; we reference their published expectations
in `README.md` instead of copying them.

Purpose: known-good implementations as a calibration panel. This engine
audits these pages; every finding is reviewed by hand and pinned in
`tests/test_tetra_acl.py`. A new signal firing here is a regression signal
in itself (either our engine learned something worth double-checking, or
it just grew a false positive — either way it gets reviewed before it
ships). To move to a newer upstream: update the commit above, re-copy the
pages, re-run `sweep.py`, re-triage, re-pin.
