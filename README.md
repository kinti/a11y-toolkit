# a11y-toolkit

**WCAG 2.2 accessibility checks for coding agents, developers and CI.**

Audit an HTML file or a live page, find out how to fix each issue, and check
what changed before you ship. When a human needs to review the result,
export a verifiable evidence pack with the findings and the checks that
still need attention.

[English](README.md) · [Español](README.es.md)

[![CI](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/kinti/a11y-toolkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![npm](https://img.shields.io/npm/v/%40kinti%2Fa11y-toolkit)](https://www.npmjs.com/package/@kinti/a11y-toolkit)
[![Downloads](https://img.shields.io/pypi/dm/a11y-toolkit)](https://pypistats.org/packages/a11y-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-server-purple)](https://modelcontextprotocol.io)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink)](https://github.com/sponsors/kinti)
[![Socket score](https://socket.dev/api/badge/pypi/package/a11y-toolkit)](https://socket.dev/pypi/package/a11y-toolkit/overview)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/kinti/a11y-toolkit/badge)](https://scorecard.dev/viewer/?uri=github.com/kinti/a11y-toolkit)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/16107/badge)](https://www.bestpractices.dev/en/projects/16107)
[![ACT Rules](https://img.shields.io/badge/ACT%20Rules-134%2F134%20failures%20detected-brightgreen)](https://github.com/kinti/a11y-toolkit/blob/main/docs/act-report-summary.md)
[![Releases](https://img.shields.io/badge/releases-OIDC%20provenance%20signed-blue)](.github/workflows/publish.yml)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-blue)](pyproject.toml)
[![Python Versions](https://img.shields.io/pypi/pyversions/a11y-toolkit)](https://pypi.org/project/a11y-toolkit/)
[![GitHub Release](https://img.shields.io/github/v/release/kinti/a11y-toolkit)](https://github.com/kinti/a11y-toolkit/releases)

<p align="center">
  <a href="https://madebyhuman.iamjarl.com"><img src="https://madebyhuman.iamjarl.com/badges/loop-white.svg" alt="Human in the Loop" height="34"></a>
</p>

Python 3.9+ · Zero dependencies at the core · Zero telemetry · English and Spanish output

## Quickstart

### Try the CLI

Run a local contrast check with `uvx`. The expected ratio is **4.54:1**.
[uv tool guide](https://docs.astral.sh/uv/guides/tools/)

```sh
uvx --from a11y-toolkit a11ytoolkit pair "#767676" "#ffffff"
```

Install the CLI with `uv tool install a11y-toolkit` or run
`python -m pip install a11y-toolkit` in your project's Python environment.
Then audit a public page or pass `--file page.html` to audit local HTML.

```sh
a11ytoolkit audit --url https://example.com
```

Each finding includes a WCAG criterion, severity and remediation. Check
`not_measured` for the criteria that this audit did not measure. Run
`a11ytoolkit route --url https://example.com` to see what to check next.
The CLI writes UTF-8 on every platform, so a report sent to a file or a pipe
(`> report.json`) is a valid file on Windows too.

<details>
<summary>Watch an audit, a contrast fix and a re-audit</summary>

![An audit flags a text contrast failure. The toolkit suggests a darker text color and the re-audit shows the improvement.](docs/demo.gif)

</details>

### Connect your coding agent

> mcp-name: io.github.kinti/a11y-toolkit

Register a **stdio** MCP server with the command and arguments below. Use
the configuration format supported by your client. [Client setup guide](docs/clients.md)

```text
command: uvx
args: --from a11y-toolkit a11y-toolkit-mcp
```

For the npm launcher, use `npx -y -p @kinti/a11y-toolkit a11y-toolkit-mcp`.
It bundles the engine and uses a local Python 3.9+ interpreter. [Install options](llms-install.md)

Once connected, ask your agent to call `a11y_contrast_pair` for `#767676` on
`#ffffff`. The expected contrast ratio is **4.54:1**.

### Enable browser checks

Use the same Python environment for Playwright and the CLI or MCP server.
Install Chromium for browser checks and Pillow for image decoding in
pixel-based contrast checks.

```sh
python -m pip install a11y-toolkit playwright pillow
python -m playwright install chromium
a11ytoolkit dom https://example.com
```

The CLI has no browser option and uses the first engine it finds. Choose the
engine with the `browser` argument of the MCP tools. If your MCP client uses
an isolated `uvx` environment, launch it from the
browser-enabled environment instead. Set its command to that environment's
`a11y-toolkit-mcp` executable. Rendered checks also support installed Firefox,
WebKit, Chrome and Edge.

Closed `<details>` content is no longer reported as unnamed or unfocusable.
`a11y_snapshot` can run right after a browser audit in the same session, and
`a11y_contrast_dom` returns a load timeout as an error object. When `load`
exceeds the timeout but the DOM is complete, `a11y_audit_dom` audits the
rendered page and lists it in `page_errors`; raise `timeout` for slow sites.
Rendered findings carry `count`, the total number of instances (examples are
capped at 6).

## From a finding to a verified fix

### Locate the issue and recheck it

Run these commands on the same local HTML file. The annotated copy marks
the elements the report can locate in the original source, and
`marks.json` lists the path of each marked element.

```sh
a11ytoolkit audit --file page.html > audit.json
a11ytoolkit annotate page.html --report audit.json -o annotated.html --marks marks.json
```

Apply the remediation in `page.html`, then repeat the audit. For text contrast,
`a11ytoolkit pair "#767676" "#ffffff"` measures the color pair and reports the
thresholds. Use a rendered check for text over images and gradients.

### Block regressions in CI

Start with an audit of the page you want to track. The budget records the
findings you have already accepted. Commit the budget so CI can use it as a
baseline.

```sh
a11ytoolkit budget --init --audit audit.json > budget.json
```

After the next change, audit the **same** file again and compare it with the saved budget.

```sh
a11ytoolkit audit --file page.html > next.json
a11ytoolkit budget --budget budget.json --audit next.json
```

| Exit | Result |
| --- | --- |
| `0` | The measured changes are within budget. |
| `1` | The capture failed or the reports could not be compared. |
| `2` | At least one finding exceeded the budget. |

Keep browser, color scheme and session type consistent when comparing live
captures. To check changed HTML in a Git branch, use
`a11ytoolkit audit --changed --base origin/main`. To compare focus order in a
scripted journey, use `trace`. [CI and keyboard recipes](docs/cookbook.md)

```sh
a11ytoolkit trace https://mysite --script journey.json --capture-dialog-state -o after.json
a11ytoolkit trace diff before.json after.json --gate-dialog-state
```

`--capture-dialog-state` records, after each step, whether a dialog is open
and whether focus is inside it. `trace diff --gate-dialog-state` compares that
state when both traces carry it.

Budgets match instances by `stable_paths` (id, `data-testid`, ARIA name)
before positional paths. In a crawl, failed URLs do not spend the page
quota; the crawl stops after failures reach twice the quota and the report
says so with `failed_pages_capped`.

`a11ytoolkit init` also installs a write-time gate in `.claude/settings.json`.
`guard` fails closed: a save the engine cannot audit (over 3 MB,
unparseable) returns `decision: "error"` and exit 1 instead of `allow`;
`A11Y_GATE=off` bypasses the hook and `--lang es` answers in Spanish. `fix`
returns `error` when its final audit fails. To re-verify a report,
`a11y_disprove` checks each earlier finding on the live page; with fewer
saved paths than instances it confirms only a signal still on the same page
and rejects only with complete proof.

### Hand off the evidence

```sh
a11ytoolkit evidence next.json -o evidence-pack.json
```

An evidence pack includes the source reports, a 55-criterion matrix and the
review still required on the sample. From a checkout of this repository,
run `python3 scripts/verify_pack.py /path/to/evidence-pack.json` to check
the SHA-256 seal and embedded reports. An auditor can review the pack and take
responsibility for the conformance decision. [Pack format and verifier](docs/evidence-pack-schema.md)

## Choose the right check

| If you need to… | Start with… |
| --- | --- |
| Scan a page, local HTML or a small site | `audit --url`, `audit --file` or `audit --url … --pages 5` |
| Check rendered contrast, focus or small targets | `dom` or `contrast-dom` |
| Walk a keyboard route or check a layout at 320 CSS pixels | `kbd`, `trace` or `reflow` |
| Check interactive behavior such as errors, hover or infinite scroll | `forms`, `hover`, `scroll` or `patterns` |
| Inspect what a browser exposes to assistive technology | MCP tool `a11y_sr_transcript` or prompt `blindfold-task` |
| Screen documents or captions | `pdf`, `python -m a11y_toolkit.a11ydocx` or `vtt` |
| Prepare a human review or an interoperability export | `evidence`, `scope`, `sarif`, `earl`, `vpat` or `openacr` |

Form checks can submit test data. Run them against a test site or an
environment where submissions are expected. [Examples and command options](docs/cookbook.md)

## Coverage and validation

**48 of 55 A/AA criteria carry at least one automated signal (87%)** in
the supported WCAG 2.2 check modes. A signal covers a specific condition
within a criterion. Any signal counts, even a partial one: a criterion
appears in this count as soon as one of its conditions is checked, which
says nothing about the others. The sample, the selected checks and the
manual review determine what a reviewer can conclude about conformance.
The evidence pack
shows those distinctions criterion by criterion. [Manual review checklist](skills/a11y-toolkit/references/wcag22-manual-checklist.md) · [Standards and mappings](docs/standards-coverage.md)

| Evidence | What it measures |
| --- | --- |
| [ACT implementation report](docs/act-report-summary.md) | 134 of 134 expected failures were detected across 355 cases and 20 rules. Exact outcome agreement was 273 of 355 (77%). The other outcomes differed between `passed` and `inapplicable`. |
| [Frozen corpus](corpus/README.md) | The toolkit detected all 18 injected faults and flagged none of the three controls. These cases come from the toolkit's own mutation bank. Other engines can submit results to the same scorer. |
| [Live axe-core benchmark](bench/README.md) | Four public pages compared across static, rendered and axe passes. Differences identify cases for manual review. Raw results and the validation procedure are public. |

For browser-based transcripts, the browser's accessibility tree is the
source. Use a real screen reader for spoken-output verification. [Screen-reader cross-check](docs/sr-crosscheck.md)

## MCP tools and prompts

The project ships 37 MCP tools, 5 prompts and a skill for repeatable
audits and review. The CLI also includes regression and corpus commands.
[Agent skill](skills/a11y-toolkit/SKILL.md) · [Agent documentation index](llms.txt)

<details>
<summary>Browse the 37-tool catalog</summary>

<!-- TOOLS:BEGIN -->
## The tools (37)

Full reference — descriptions, arguments, return shapes and behavior — in [docs/tools.md](docs/tools.md). All tools accept `lang` (`en`|`es`) unless noted; output is JSON unless noted. Generated from `server.TOOLS` by `scripts/gen_readme.py`.

| Tool | Category | What it does |
|---|---|---|
| [`a11y_audit_url`](docs/tools.md#a11y_audit_url) | Audit | Express WCAG audit |
| [`a11y_audit_dom`](docs/tools.md#a11y_audit_dom) | Audit | Rendered WCAG audit |
| [`a11y_audit_pdf`](docs/tools.md#a11y_audit_pdf) | Audit | PDF accessibility screening |
| [`a11y_docx_screen`](docs/tools.md#a11y_docx_screen) | Audit | DOCX accessibility screening |
| [`a11y_locate`](docs/tools.md#a11y_locate) | Locate | Locate element by accessible name |
| [`a11y_journey_verdict`](docs/tools.md#a11y_journey_verdict) | Blindfold testing | Blindfold journey verdict |
| [`a11y_autofix`](docs/tools.md#a11y_autofix) | Fix & contrast | Deterministic safe auto-fixes |
| [`a11y_patches`](docs/tools.md#a11y_patches) | Fix & contrast | Sealed patch-set (sha-keyed) |
| [`a11y_contrast_pair`](docs/tools.md#a11y_contrast_pair) | Fix & contrast | Contrast ratio + verdicts |
| [`a11y_contrast_image`](docs/tools.md#a11y_contrast_image) | Fix & contrast | Text-over-image contrast |
| [`a11y_contrast_dom`](docs/tools.md#a11y_contrast_dom) | Fix & contrast | Live-element contrast sampling |
| [`a11y_suggest_color`](docs/tools.md#a11y_suggest_color) | Fix & contrast | Nearest passing color |
| [`a11y_generate_declaration`](docs/tools.md#a11y_generate_declaration) | Document | Accessibility statement (EAA/RD 1112) |
| [`a11y_generate_vpat`](docs/tools.md#a11y_generate_vpat) | Document | VPAT 2.5 report (WCAG edition) |
| [`a11y_generate_openacr`](docs/tools.md#a11y_generate_openacr) | Document | OpenACR YAML report (GSA) |
| [`a11y_badge`](docs/tools.md#a11y_badge) | Document | Honest SVG badge |
| [`a11y_snapshot`](docs/tools.md#a11y_snapshot) | Watch (regressions) | A11y snapshot + tab order |
| [`a11y_diff`](docs/tools.md#a11y_diff) | Watch (regressions) | Snapshot regression diff |
| [`a11y_diff_urls`](docs/tools.md#a11y_diff_urls) | Watch (regressions) | Staging vs production diff |
| [`a11y_aria_live_snippet`](docs/tools.md#a11y_aria_live_snippet) | Watch (regressions) | aria-live monitor snippet |
| [`a11y_criterion`](docs/tools.md#a11y_criterion) | Knowledge & context | WCAG criterion explained |
| [`a11y_html_validate`](docs/tools.md#a11y_html_validate) | Knowledge & context | W3C Nu validation |
| [`a11y_keyboard`](docs/tools.md#a11y_keyboard) | Interactions | Keyboard-trap + skip-link landing detector |
| [`a11y_forms`](docs/tools.md#a11y_forms) | Interactions | Form error testing |
| [`a11y_hover`](docs/tools.md#a11y_hover) | Interactions | Hover dismissibility (1.4.13) |
| [`a11y_reflow`](docs/tools.md#a11y_reflow) | Interactions | 320px reflow check |
| [`a11y_scroll`](docs/tools.md#a11y_scroll) | Interactions | Infinite-scroll audit (passive by default; interactive=true clicks the exact control you name) |
| [`a11y_sr_transcript`](docs/tools.md#a11y_sr_transcript) | Interactions | Screen reader transcript |
| [`a11y_reduced_motion`](docs/tools.md#a11y_reduced_motion) | Interactions | prefers-reduced-motion honored? |
| [`a11y_forced_colors`](docs/tools.md#a11y_forced_colors) | Interactions | forced-colors survival heuristic |
| [`a11y_vtt_check`](docs/tools.md#a11y_vtt_check) | Interactions | WebVTT caption quality |
| [`a11y_evidence`](docs/tools.md#a11y_evidence) | Coverage & evidence | Evidence pack (verifiable handoff) |
| [`a11y_disprove`](docs/tools.md#a11y_disprove) | Coverage & evidence | Disprover: re-verify findings |
| [`a11y_ledger`](docs/tools.md#a11y_ledger) | Coverage & evidence | Coverage ledger (persistent) |
| [`a11y_wcag3_preview`](docs/tools.md#a11y_wcag3_preview) | Coverage & evidence | WCAG 3 draft preview (no score) |
| [`a11y_scope`](docs/tools.md#a11y_scope) | Coverage & evidence | Applicability scope (semi-automatic) |
| [`a11y_route`](docs/tools.md#a11y_route) | Routing | Tool router (goal or page to steps) |
<!-- TOOLS:END -->

</details>

### The 5 prompts

| Prompt | Use it to… |
| --- | --- |
| `audit-page` | Audit a page and plan keyboard, screen-reader and zoom checks. |
| `fix-contrast` | Find and apply a passing text color for the measured background. |
| `pre-deploy-check` | Audit a URL and compare it with a saved accessibility snapshot. |
| `declaration-eaa` | Draft an accessibility statement for human review. |
| `blindfold-task` | Attempt a task using accessible names and keyboard actions, then record the friction. |

## Data and security

The toolkit runs as your local user. Local file arguments can read or write
files that user can access. URL and browser checks contact the pages you
specify. The optional Nu HTML validation tool sends the selected URL or
HTML to its configured validator. Keep authenticated browser session
files local. [Security policy and private reporting](SECURITY.md)

## Contribute

Run `make test` from the repository root. Install Playwright and Chromium
to exercise the browser suites. The tool inventory and agent index derive
from the MCP definitions, and CI checks that they stay in sync.
[Architecture](docs/ARCHITECTURE.md) · [Changelog](CHANGELOG.md)

Fix a bug, improve a recipe or add a locale. Locale packs can be validated
with `python3 tests/test_locales.py`. [Translation guide](docs/i18n.md) ·
[Good first issues](https://github.com/kinti/a11y-toolkit/issues?q=is%3Aissue+is%3Aopen+label%3A%22good%20first%20issue%22) ·
[Discussions](https://github.com/kinti/a11y-toolkit/discussions)

## About

I have been auditing websites for accessibility since 2003. I built this
toolkit so the person fixing an issue can find it and the person reviewing
the fix can check the evidence. If a result surprises you, share the smallest
page that reproduces it. [Jesús Quintana Fernández](https://jquin.net/) ·
[Report an issue](https://github.com/kinti/a11y-toolkit/issues/new/choose)

The toolkit is used by a11y.es for hosted accessibility monitoring. [a11y.es](https://a11y.es)

The code is MIT-licensed. Modified distributions use their own name and
branding. [License](LICENSE)
