# The real WCAG failure on gov.uk that axe doesn't report

*(Publish-ready article. TL;DR variants for Hacker News and LinkedIn at the
end — pick per audience. Data verified live on 2026-09-15 with
a11y-toolkit 3.13; every claim below is reproducible with two commands.)*

---

The UK government's site is the most cited accessibility reference on earth.
GOV.UK's design system is studied, copied, and praised. And its search button
fails WCAG 2.2 AA — in a way the industry's default scanner does not report.

## The finding

The "Search GOV.UK" button renders its label in `#1d70b8` on a
`#d2e2f1` background at 13px. That is a contrast ratio of **3.91:1**. Normal
text at that size needs **4.5:1** (criterion 1.4.3, level AA). It fails —
and it fails for every low-vision user in a glare-lit room, which is the
user WCAG writes for.

I know because my tool computed it. Not sampled, not estimated: the rendered
audit loads the page in Chromium, resolves the effective colors (including
transparency stacks), applies the official relative-luminance formula, and
compares against the threshold at the element's actual size and weight.

## Why axe doesn't tell you this

Run axe-core on GOV.UK's homepage and the color-contrast rule lands in
**"incomplete"**, not "violations". That is a defensible engineering choice —
contrast is genuinely hard to compute in the general case (gradients,
background images, z-stacks), and axe would rather say "needs review" than
guess. On today's run, axe reports one violation type (`region`); contrast
isn't in the list.

But here's the thing about "incomplete": **agents don't read it as a task.
They read it as noise.** An AI coding assistant running the default pipeline
gets a violations list, and an incomplete list, and acts on the first. The
failure mode isn't that axe is wrong — it's that the honest shrug gets
dropped on the floor.

So a11y-toolkit makes the opposite bet: **compute it.** Resolve the real
background through every alpha layer, apply the formula, and say the number.
Where it truly can't be computed (text over photos), it says so in the
findings and points you at pixel-sampling instead of pretending.

## Reproduce it yourself

```bash
uvx --from a11y-toolkit a11ytoolkit-mcp &
# then ask your agent: use a11y_audit_dom on https://www.gov.uk
# or, CLI:
pip install playwright && playwright install chromium
uvx --from a11y-toolkit a11ytoolkit reflow https://www.gov.uk
```

The audit returns the ratio, the two colors, and the exact element — plus 37
other criteria signals (target sizes, focus traps, shadow DOM, 320px reflow,
the works).

## The uncomfortable general point

Automation covers roughly a third of WCAG. Everyone says it; almost no tool
behaves as if it were true. The two honest failure modes are:

1. **Overclaiming** — the overlay vendors, one of which took a $1M FTC fine
   for it.
2. **Under-delivering the checkable part** — filing computable facts as
   "incomplete" and letting them vanish.

The first is a lie. The second is a shrug. Users with low vision are failed
by both. We built a toolkit that does neither: it computes everything
computable, refuses to compute what isn't, prints the boundary between them,
and hands you a hash-verified evidence pack for the human who signs the
rest.

That last part matters most. A conformance claim needs a person behind it —
reachable, attributable, dated. The machine's job is to shrink and sharpen
that person's work to exactly what judgment it actually requires.

---

*a11y-toolkit: 17 MCP tools + 5 prompts, zero dependencies at the core,
es/en, MIT, benchmarked against axe-core monthly on real pages — including
the finding above, with dates.*
[github.com/kinti/a11y-toolkit](https://github.com/kinti/a11y-toolkit) ·
`uvx --from a11y-toolkit a11y-toolkit-mcp`

---

## Hacker News variant

**Show HN: I found a real WCAG AA failure on GOV.UK that axe-core doesn't
report**

The "Search GOV.UK" button is #1d70b8 on #d2e2f1 at 13px = 3.91:1. Normal
text needs 4.5:1. axe files contrast as "incomplete" (defensible — contrast
is hard in general), and "incomplete" is where agent pipelines drop things.
So I built an MCP toolkit that computes it: resolved backgrounds through
alpha stacks, official luminance formula, exact ratio per element. 17 tools,
zero-dep core, es/en. It also walks real Tab presses for keyboard traps,
reflows at 320px, traverses open shadow DOM, and emits a countersignature-
ready evidence pack (hash-verified, human homework list printed) because a
conformance claim needs a person behind it. Benchmarked against axe monthly
on real pages — the gov.uk finding and the methodology are in the repo.
MIT: github.com/kinti/a11y-toolkit

## LinkedIn variant

The most accessibility-famous website in the world has a search button that
fails WCAG AA — and the industry's default scanner doesn't mention it.

#1d70b8 sobre #d2e2f1 a 13px: 3.91:1. Se necesitan 4.5:1.

Not because axe is broken — because axe honestly files contrast as
"incomplete", and incomplete is where attention goes to die. My MCP toolkit
for AI agents computes it instead (real backgrounds, official formula,
exact element). The finding above is reproducible with two commands; the
monthly axe-comparison methodology is public in the repo.

The bigger point for the EAA era: machines should compute everything
computable, refuse to compute what they can't, and hand a named, dated human
exactly the judgment work that remains. That's what a11y-toolkit does — and
why its audit output ends in a hash-verified evidence pack rather than a
conformance claim.

A scan is not a defence. The machine finds; the human signs.
