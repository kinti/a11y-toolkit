# Cookbook — real recipes, start to finish

Copy-paste workflows for the whole loop: **audit → fix → document → watch**.
Define the runner once and every recipe stays short (swap the uvx line for
`npx -y @kinti/a11y-toolkit` if you live in Node):

```bash
at() { uvx --from a11y-toolkit a11ytoolkit "$@"; }   # bash/zsh, this session
```

Single-page reference: [tools.md](tools.md) · compositions with other MCP
servers: [interop.md](interop.md).

## 1. The health check of a page you own (5 minutes)

```bash
URL=https://example.com
at audit --url $URL > audit.json
at route --url $URL        # what to run next, and why
```

`audit.json` carries `score`, `findings[]` (each with `criterion`,
`severity`, `remediation`, `examples`) and `not_measured` — the honest list
of what this pass could not see. The router's sequential diagnosis orders
your next moves by what the page actually has (forms? menus? video?).

## 2. The rendered pass: what the browser actually shows

Static HTML is half the truth. The rendered checks are one subcommand each
(first run: `python3 -m playwright install chromium`; any browser you have —
Chromium, Firefox, WebKit, Chrome, Edge):

```bash
at kbd $URL            > kbd.json        # keyboard traps (2.1.2)
at contrast-dom $URL --selector "a, button"   # real text-over-anything contrast
at reflow $URL         > reflow.json     # 320px sideways scroll (1.4.10)
at forms $URL/contact  > forms.json      # error identification (3.3.1/3.3.3)
```

The same pass catches the failures axe marks *incomplete*: e.g. gov.uk's
3.91:1 search button, criterion 1.4.3.

## 3. Fixing a contrast failure the honest way

```bash
# measure the pair (verdicts per criterion + nearest passing color)
at pair "#767676" "#ffffff"
# text sits on a photo/gradient? sample the REAL background pixels
at image hero.jpg --text "#fff" --region 120,40,420,90
```

`pair` composites alpha over the background and suggests the nearest color
that passes; `image` measures only the background that was actually behind
the glyphs.

## 4. Seal the evidence (the handoff object)

```bash
at evidence audit.json kbd.json --snapshot snap.json -o pack.json
curl -sLO https://raw.githubusercontent.com/kinti/a11y-toolkit/main/scripts/verify_pack.py
python3 verify_pack.py pack.json     # 0 = the seal holds; needs no toolkit
```

The pack is `a11y-evidence-pack/3`: the 55-criterion matrix, per-artifact
SHA-256, the whole-pack seal, and the priced human work that remains
(MIN/MED/MAX minutes). Anyone re-verifies it without installing us — that
is the point (the verifier is one standalone stdlib file).

## 5. The documents a human signs

```bash
at vpat --reports audit.json --product "Acme Site" -o vpat.html
at openacr --reports audit.json --product "Acme Site" -o openacr.yaml
at declaration --entity "Acme" --url https://acme.example \
     --status partial --framework eaa --lang en --output declaration.html
```

The two conformance reports start every level at *not-evaluated* (an automated fail forces
*does-not-support*): the machine fills the notes, a qualified human sets the
levels. Drafts, not conformance — by design.

## 6. CI that legacy sites can actually adopt (the ratchet)

```bash
# first run: accept today as the baseline
at audit --url $URL | at budget --init > budget.json
# every run after: only NEW findings block
at budget --budget budget.json --audit audit.json
```

Exit 0 = GO, exit 2 = blocked. Fixes lower the baseline; regressions scream.
Prefer zero-config? The official Action wraps all of this:
[github.com/kinti/a11y-watch](https://github.com/kinti/a11y-watch).

## 7. Only what my PR touched

```bash
at audit --changed [--base main]
```

Audits the HTML your branch touched — untracked new pages included, and
non-HTML web files are listed as `not_auditable` instead of silently
passing.

## 8. Hear the page like a screen reader does

The linearized announcements (roles, names, states) are the MCP tool
`a11y_sr_transcript` — ask your agent: *"transcribe what a screen reader
announces on $URL"*. For the full experience, the blindfold journey walks a
real task perceiving only that: [journey-example.md](journey-example.md).

## 9. Prove a negative (or catch a liar)

```bash
at disprove --file audit.json --url $URL
```

Re-audits the same page and returns its current score, coverage and findings.
It confirms matching findings, records earlier findings that disappeared and
keeps ambiguous historical matches for review.

## 10. Machine readers: SARIF + EARL

```bash
at sarif --from-audit audit.json -o a11y.sarif   # code scanning
at earl --from-audit audit.json -o earl.json     # W3C EARL 1.0/ACT
```

SARIF lands in GitHub code scanning. EARL emits assertions for findings with
an ACT mapping. Both exporters return exit 1 for failed or incomplete
audits. [Document and export quality review](document-and-export-quality.md)

## 11. Use fingerprints to select representative pages

Fingerprints group pages by DOM structure, classes and attributes. Start
with the suggested representatives and include relevant differences in
content and interaction when selecting the pages to audit.

```bash
at fingerprints --dir pages/ -o templates.json
# sample_suggestion: one representative per detected template
```

A real run over 4 pages (3 product twins + a contact page):

```
pages: 4   templates: 2
sample: ["pages/contact.html", "pages/product-1.html"]
```

The `divergence` list identifies regions that differ structurally. Pages in
the same group can still have different labels, alternative text or findings.

## 12. Score ANY engine against the frozen corpus

You want to know how another evaluator (a competitor's, a new LLM agent's,
your own fork) behaves on KNOWN ground truth — not on pages where nobody
knows the answer. The corpus is the sealed exam frozen as a dataset: pages
with one injected violation each, placebo controls where any finding is a
false positive by construction.

```bash
at corpus verify corpus   # every hash + the seal
# run YOUR evaluator on corpus/pages/*.html, then one JSON line per case:
# {"case_id": "m7-0", "criteria_found": ["1.1.1"]}
at corpus evaluate --submission mine.jsonl corpus
```

The reference baseline ships with the dataset (`results/reference.json`:
this engine, kill 1.0, zero false positives). A submission that flags
nothing scores exactly 0.0 — and one that invents criteria on the placebo
pages is exposed by construction. The contract is criterion codes, not
tool rule ids: axe, Lighthouse or a human with a checklist can all play.

## 13. Locate a broken table header in the original HTML

```bash
at audit --file table.html > table-audit.json
at annotate table.html --report table-audit.json -o marked.html --marks marks.json
```

For a cell such as `<td headers="quarter total">…</td>`, the static audit
checks both IDs against header cells in that data table. A broken reference
emits `headers_attr_bad` with the referring cell's CSS path. Nested tables
have independent header sets. Both commands read the file as UTF-8 text.
Annotation preserves that text outside the injected `data-a11y-id`
attributes, including when the route contains a browser-implied `tbody`.
`marks.json` links those IDs to the findings.

Annotate the same HTML you audited. If the audit's `source_sha256` differs,
the CLI reports `source_mismatch: true`, writes the original HTML as the
output, and counts the findings as unplaced. Re-audit the edited source to
place fresh marks.

## 14. Gate a keyboard journey in CI

Save the same actions for both runs, for example in `journey.json`.

```json
[
  {"kind": "click", "selector": "#open-dialog"},
  {"kind": "press", "key": "Escape"}
]
```

```bash
at trace "$BASELINE_URL" --script journey.json --capture-dialog-state -o before.json &&
at trace "$CANDIDATE_URL" --script journey.json --capture-dialog-state -o after.json &&
at trace diff before.json after.json --gate-dialog-state
```

| Exit | Meaning |
|---|---|
| `0` | The available evidence shows no blocking regression. |
| `1` | A capture failed or the diff input could not be read or validated. An HTTP 4xx/5xx during the initial load or a scripted `goto` is a capture failure. |
| `2` | Focus was lost or reordered, or the optional gate found a difference in dialog state on comparable steps. |

When comparing dialogs, read `dialog_gate.status` as well as the exit code.
Empty steps, missing or invalid dialog state, and different action
sequences yield `inconclusive`. In that case the focus verdict determines
the exit code. A passing dialog comparison is explicit as
`dialog_gate.status: "pass"`.
