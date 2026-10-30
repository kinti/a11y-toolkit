# Cookbook — real recipes, start to finish

Copy-paste workflows for the whole loop: **audit → fix → document → watch**.
Every recipe runs with `uvx` (no clone, no venv) — swap `uvx --from
a11y-toolkit` for `npx -y @kinti/a11y-toolkit` if you live in Node.
Single-page reference: [tools.md](tools.md) · compositions with other MCP
servers: [interop.md](interop.md).

## 1. The health check of a page you own (5 minutes)

```bash
URL=https://example.com
uvx --from a11y-toolkit a11ytoolkit audit --url $URL > audit.json
uvx --from a11y-toolkit a11ytoolkit route --url $URL   # what to run next, and why
```

`audit.json` carries `score`, `findings[]` (each with `criterion`,
`severity`, `remediation`, `examples`) and `not_measured` — the honest list
of what this pass could not see. The router's sequential diagnosis orders
your next moves by what the page actually has (forms? menus? video?).

## 2. The rendered pass: what the browser actually shows

Static HTML is half the truth. Contrast over gradients, keyboard traps,
focus visibility, target sizes — those live in the rendered DOM:

```bash
uvx --from a11y-toolkit a11ytoolkit dom --url $URL --browser chromium > dom.json
```

(First run: `python3 -m playwright install chromium`. The same pass catches
the failures axe marks *incomplete*: e.g. gov.uk's 3.91:1 search button,
criterion 1.4.3.)

## 3. Fixing a contrast failure the honest way

```bash
# measure the pair (verdicts per criterion + nearest passing color)
uvx --from a11y-toolkit a11ytoolkit pair "#767676" "#ffffff"
# text sits on a photo/gradients? sample the REAL background pixels
uvx --from a11y-toolkit a11ytoolkit image hero.jpg --text "#fff" --region 120,40,420,90
```

`pair` composites alpha over the background and suggests the nearest color
that passes; `image` screenshots the region with text made transparent and
measures only the background that was actually behind the glyphs.

## 4. Seal the evidence (the handoff object)

```bash
uvx --from a11y-toolkit a11ytoolkit evidence audit.json dom.json --snapshot snap.json -o pack.json
uvx --from a11y-toolkit python scripts/verify_pack.py pack.json  # or the standalone verifier
```

The pack is `a11y-evidence-pack/2`: the 55-criterion matrix, per-artifact
SHA-256, the whole-pack seal, and the priced human work that remains
(MIN/MED/MAX minutes). Anyone re-verifies it without installing us — that
is the point.

## 5. The documents a human signs

```bash
uvx --from a11y-toolkit a11ytoolkit vpat --reports audit.json dom.json --product "Acme Site" -o vpat.html
uvx --from a11y-toolkit a11ytoolkit openacr --reports audit.json dom.json -o openacr.yaml
uvx --from a11y-toolkit a11ytoolkit declaration --entity "Acme" --url https://acme.example \
     --status partial --framework eaa --lang en --output declaration.html
```

All three start every level at *not-evaluated* (an automated fail forces
*does-not-support*): the machine fills the notes, a qualified human sets the
levels. Drafts, not conformance — by design.

## 6. CI that legacy sites can actually adopt (the ratchet)

```bash
# first run: accept today as the baseline
uvx --from a11y-toolkit a11ytoolkit audit --url $URL | uvx --from a11y-toolkit a11ytoolkit budget --init > budget.json
# every run after: only NEW findings block
uvx --from a11y-toolkit a11ytoolkit budget --budget budget.json --audit audit.json
```

Exit 0 = GO, exit 2 = blocked. Fixes lower the baseline; regressions scream.
Prefer zero-config? The official Action wraps all of this:
[github.com/kinti/a11y-watch](https://github.com/kinti/a11y-watch).

## 7. Only what my PR touched

```bash
uvx --from a11y-toolkit a11ytoolkit audit --changed [--base main]
```

Audits the HTML your branch touched — untracked new pages included, and
non-HTML web files are listed as `not_auditable` instead of silently
passing.

## 8. Hear the page like a screen reader does

```bash
uvx --from a11y-toolkit a11ytoolkit sr --url $URL > transcript.json
```

The linearized announcements (roles, names, states) — what a blind user
actually hears, as data. For the full experience, the blindfold journey
walks a real task perceiving only this:
[journey-example.md](journey-example.md).

## 9. Prove a negative (or catch a liar)

```bash
uvx --from a11y-toolkit a11ytoolkit disprove --file audit.json --url $URL
```

Re-runs every finding against the live page and marks each confirmed or
rejected — regression between runs, stale reports and overeager scanners
all fall here.

## 10. Machine readers: SARIF + EARL

```bash
uvx --from a11y-toolkit a11ytoolkit sarif --from-audit audit.json -o a11y.sarif   # code scanning
uvx --from a11y-toolkit a11ytoolkit earl --from-audit audit.json -o earl.json     # W3C EARL 1.0/ACT
```

SARIF lands in GitHub code scanning (the Action does it for you); EARL
traces every finding to its published ACT rule — and never asserts a
`pass` the machine cannot know.

## 11. A full evaluation, the WCAG-EM way

When the question is "is the WHOLE product accessible" (a tender, an audit,
a regulator), one page is not an answer — a sample is:

```bash
# 1) plan: scope + conformance target + sample set (you choose the sample:
#    structured pages, random picks, complete processes)
cat > plan.json <<'P'
{"product": {"name": "Acme Site", "url": "https://acme.example", "scope": "whole product"},
 "conformance_target": "WCAG 2.2 AA",
 "support_baseline": ["NVDA + Chrome", "VoiceOver + Safari"],
 "sample": [
   {"id": "home", "url": "https://acme.example/", "type": "common-view", "why": "landing"},
   {"id": "checkout", "url": "https://acme.example/checkout", "type": "process", "why": "complete process"}]}
P
# 2) one sealed pack per sample (recipes 1-4)
# 3) the aggregated WCAG-EM report, root-sealed over the pack seals
uvx --from a11y-toolkit a11ytoolkit wcagem --plan plan.json --packs home.json checkout.json
```

The report rolls every criterion up ACROSS the sample (a failure anywhere
is a failure of the report), prices the human work that remains, and never
claims conformance — that signature is a person's, not a tool's.

## 12. From findings to a fix ROUTE (the plan)

A list of 40 findings is an inventory; nobody answers "in what order?".
The plan groups findings by shared cause and orders the batches with a
declared heuristic — infrastructure first (it reprices everything else),
design-system decisions next (one theme change kills many contrast
findings), instances after, pages piling up signals flagged for a redesign
pass:

```bash
uvx --from a11y-toolkit a11ytoolkit plan --report audit.json -o fix-plan.json
# better minutes: price with the evidence pack's effort table
uvx --from a11y-toolkit a11ytoolkit plan --report audit.json --from-pack pack.json
```

Each batch carries its minute range and the running total; grouping savings
are a declared optimistic bound, not a promise. The order is a heuristic —
reorder it, re-seal it, make it yours.

## 13. One audit per template (don't audit 340 twins)

You crawled 500 pages and the report says the same menu is broken 340
times. WCAG-EM Step 3 says audit one page per template — but nothing told
you which pages share a template. Fingerprints hash each page from three
independent views (skeleton / classes / attributes), ignoring text and
per-page noise (ids, urls, tokens), so twins stay twins:

```bash
uvx --from a11y-toolkit a11ytoolkit fingerprints --dir pages/ -o templates.json
# sample_suggestion: one representative per detected template
```

A real run over 4 pages (3 product twins + a contact page):

```
pages: 4   templates: 2
sample: ["pages/contact.html", "pages/product-1.html"]
```

Audit the representatives, not the twins — and the `divergence` list tells
you if a "twin" quietly drifted (`{page, region, view}`: header diverges in
classes while the footer stays identical). Same skeleton does not guarantee
identical findings after rendering: the suggestion feeds the WCAG-EM plan,
the evaluator still owns the sample.
