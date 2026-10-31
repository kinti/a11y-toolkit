# Security policy — declared capabilities

Zero telemetry is a product promise: this engine never sends anything
anywhere, except to the URLs the operator explicitly asks it to audit.
This file declares every capability a supply-chain scanner may flag, so a
reviewer reads a verdict instead of guessing from heuristics.

## What the package does, and why

| Capability | Where | Why it exists |
|---|---|---|
| Filesystem read/write | Reads the inputs you pass (HTML, PDFs, packs) and writes the artifacts you request (reports, evidence packs, VPAT/OpenACR, badges) to the paths you pass — or their documented defaults in your working directory. **Verified and pinned by the suite: the engine opens ZERO hardcoded absolute paths and NEVER touches the user's home**; the only self-opened files are its packaged locale catalogs, plus three standard tempfiles (atomic ledger writes, the macOS `sips` image fallback, the once-per-machine star-nudge marker in the system temp dir) | It is a local CLI tool; its file surface is exactly its arguments |
| Network fetch (http/https only) | The audit/validate tools fetch **user-supplied URLs**; `a11y_html_validate` calls validator.w3.org when invoked. Anti-SSRF by construction: scheme allow-list, per-hop redirect validation hook, total-clock reads | It is a web accessibility scanner. The w3.org URLs in the knowledge catalog are static documentation links shown in findings. The namespace-looking URIs (`w3.org/ns/earl#`, `purl.org/dc/terms/`, `w3.org/2000/svg`, OpenXML schemas, the SARIF `$schema`) are format identifiers REQUIRED by those specifications — they are names, never fetched |
| subprocess (list-argv, never a shell) | `git ls-files`/`git diff` **only** under the explicit `audit --changed` flag; `sips` (macOS system binary) as an image-conversion fallback when Pillow is absent | No `shell=True` anywhere; no command is ever built from a string. The npm launcher spawns `python3 -m <module>` with a fixed argv |
| Environment variables | **None in the runtime engine.** (Development tests set PYTHONPATH/PYTHONHASHSEED to launch subprocess boundary checks; the tests are not shipped in the sdist — run them from the release tag) | The engine itself never reads the environment. The one shipped `.js` file (`arialive.js`, the aria-live monitor snippet returned by a tool) is browser-only UI — `window`/`document`/`navigator.clipboard`, zero references to `env`/`process` — and runs only when deliberately injected into the page being audited |
| Dynamic code execution | **None.** Since 5.25.0 the CLDR plural rules in locale packs are parsed by an AST whitelist (`a11yi18n.eval_plural_rule`), not eval'd: a locale pack — including third-party `use_overlay()` packs — is data, and data never becomes code (pinned by test) | Locale packs are community-editable by design |

## What it never does

- No telemetry, no phone-home, no analytics, no post-install scripts.
- No code execution from fetched or downloaded content (findings are data).
- No shell interpolation of user input, ever.
- The self-contained npm package runs the same pure-stdlib engine locally;
  its only fallback download is a version-pinned `uvx` invocation, declared
  in `npm/lib/runner.cjs`.

## Reporting a vulnerability

Open a private GitHub security advisory at
`https://github.com/kinti/a11y-toolkit/security/advisories`
(or an issue if non-sensitive). Expect a fix release, not an argument: this
engine's own thesis is verifiable evidence, and that starts with itself.
