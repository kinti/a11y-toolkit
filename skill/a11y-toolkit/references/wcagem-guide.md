# WCAG-EM conformance ladder — from screening to a defensible report

Three named tiers. Escalate one at a time. **Tiers 1 and 2 are NEVER
conformance claims** — that honesty is the product.

## Tier 1 — EXPRESS (automated screening)

- `a11y_audit_url` on the root + 4-5 key pages (or the `pages` crawl).
- `a11y_audit_dom` where Playwright exists (computed contrast, 2.5.8, focus).
- Output: scores + findings by severity with remediation.
- Time: minutes. What it is: a filter, ≈1/3 of WCAG.

## Tier 2 — GUIDED (agent-verified evaluation)

Based on WCAG-EM (W3C Website Accessibility Conformance Evaluation Methodology):
structured + random sampling, human-verified results.

1. **Sample** (WCAG-EM step 3-4): include the structured pages — home,
   contact, login/signup, one content page, one complete form flow, one page
   with rich interaction — plus 1-2 random pages from the crawl. Minimum ~10
   pages for a small site.
2. **Per sample page**, run the tools AND verify manually what automation
   cannot (agent does the keyboard walk, checks focus visibility, 200% zoom,
   submits a form with errors and checks the announcement):
   use `references/wcag22-manual-checklist.md`.
3. **Mark every result**: `automated` / `agent-verified` / `needs-human`
   (screen reader pass, cognitive, domain judgment). This triple is what makes
   the report trustworthy.
4. Output: per-page PASS/FAIL/REVIEW against the checklist + consolidated
   findings. Still NOT conformance.

## Tier 3 — CONFORMANCE (human in the loop)

- Compile the WCAG-EM report: scope, sample (structured + random), all
  results with the triple above, dates, evaluator names — a human evaluator
  signs it. The toolkit compiles; the human certifies.
- Feed the non-accessible content list into `a11y_generate_declaration`
  (marco="eaa" or "rd1112").
- State the refresh cadence: re-run Tier 1 monthly (see `examples/a11y-watch.yml`),
  full Tier 2-3 yearly or after major changes.

## Report skeleton (Tier 2-3)

```
## Accessibility evaluation — <site> (WCAG-EM based)
Scope & sample: N pages — structured: …, random: …
Tier: guided (agent-verified) | conformance (evaluator-signed)
Results: <n> automated · <m> agent-verified · <k> needs-human
Findings: severity × criterion × evidence × remediation
Out of scope: <anything not sampled>
Honesty line: screening + sample-based evaluation; not a certification.
```
