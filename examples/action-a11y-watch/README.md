# <img src="logo.svg" width="64" alt="a11y.es symbol: a gear with a green check" valign="middle"> a11y-watch — the official GitHub Action

One line in a workflow and your repo watches its site's accessibility every
week: WCAG 2.2 audit, SARIF to code scanning, and the error-budget ratchet —
**only NEW findings block**, so a site with legacy debt can adopt CI today
and improve without failing every build.

```yaml
# .github/workflows/a11y-watch.yml in YOUR repo
name: a11y-watch
on:
  schedule:
    - cron: '0 6 * * 1'   # Mondays 06:00 UTC
  workflow_dispatch: {}
permissions:
  security-events: write   # for the SARIF upload
jobs:
  watch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4        # checks out budget.json
      - uses: kinti/a11y-watch@v1        # ← this action, published
        with:
          site-url: https://example.com
```

## First run: adopting the ratchet

Run it once without `budget.json` — the action generates the accepted
baseline, fails with instructions, and uploads it as an artifact. Review it,
commit it as `budget.json`, done: from then on every fix lowers the bar and
every regression screams. Baselines carry a 90-day review date.

## Inputs

| input | default | what |
|---|---|---|
| `site-url` | — (required) | homepage URL; the audit samples from there |
| `budget-file` | `budget.json` | accepted-baseline path (ratchet) |
| `lang` | `en` | report language (`en` / `es`) |
| `pages` | `5` | pages audited per run |
| `sarif` | `true` | upload SARIF to code scanning (needs `security-events: write`) |

Blocking severities live in the budget file itself (`blocking` key) — policy
travels with the baseline, not with the workflow.

## Versioning

`v1` tracks the latest major (append-only fixes); pin a tag for exact
reproducibility. The action has no dependencies of its own — it installs
[a11y-toolkit](https://github.com/kinti/a11y-toolkit) (MIT, stdlib-only) from
PyPI at run time. Source of truth for the action lives HERE; the toolkit repo
carries a mirrored copy under `examples/action-a11y-watch/` for reference.
