# Contributing to a11y-toolkit

Thanks for helping make agents accessibility-aware. Three golden rules govern
every contribution — they are what makes this toolkit different:

1. **Zero dependencies at the core.** The static audit, contrast math and
   declarations run on the Python standard library alone. Playwright and Pillow
   are optional *enhancements*, never requirements. If your feature needs a
   dependency, it goes behind an import guard with a graceful fallback.
2. **es/en everywhere.** Every user-facing string (findings, remediations,
   errors, prompts) exists in both languages, selected by the `lang` argument.
   Follow the `T` / `CRIT` dictionary pattern in `a11yaudit.py`.
3. **Honesty is a feature.** Automation covers ≈1/3 of WCAG. Never weaken a
   scope note, never imply conformance from an automated pass, mark
   unmeasurable cases as "review" instead of guessing.

## Setup

```bash
git clone https://github.com/kinti/a11y-toolkit && cd a11y-toolkit
python3 test_contrast.py && python3 test_audit.py   # core suites, no deps
pip install playwright && playwright install chromium
python3 test_dom.py && python3 test_mcp.py          # full suites
```

## What help is wanted

- **More WCAG signals** for `a11yaudit.py` / `a11ydom.py` — each must map to a
  specific WCAG 2.2 criterion, carry a remediation string, and have a test
  fixture in `test_audit.py`. When in doubt, look at how axe-core names the
  rule and what makes it a *violation* vs "needs review".
- **The rendered audit** (`a11ydom.py`): fewer "review" cases, better
  selectors, state-contrast checks.
- **Translations**: the output catalogs are plain dictionaries — adding
  languages is welcome (open an issue first to agree on the code).
- **Docs and real-world reports**: audits of real sites that found real issues
  (redact as needed) are the best marketing this project can have.

## Commit and release style

- Commits: imperative, one logical change (`fix: …`, `feat: …`, `docs: …`).
- Bump `pyproject.toml` + `server.VERSION` together; `CHANGELOG.md` entry per
  release. Tags `vX.Y.Z` trigger the PyPI publish workflow.
- The 4-space, single-quote, no-magic style of the existing modules is the
  style. No linters enforced — readable beats fashionable.
