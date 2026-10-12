# Screen-reader cross-check — validating the transcript against the real thing

`a11y_sr_transcript` linearizes the accessibility tree: it says what a screen
reader *should* announce, not what one *did* announce. Real screen readers
(and their browsers) have their own quirks — virtual buffer order, name
computation differences, heuristics for links and headings. The roadmap item
"cross-checks against NVDA and VoiceOver output" is the honest close of that
gap. This document is the design; `scripts/voiceover-capture.applescript` is
the first working scaffold (macOS).

## What we compare

| Field | Transcript (toolkit) | Capture (real SR) |
|---|---|---|
| role + name per node | accessibility tree snapshot | announced text per step |
| reading order | tree walk order | VO/NVDA cursor order |
| states (expanded, checked…) | tree states | spoken state |

A diff engine compares **sequences of (role, name, state)** normalized to
lowercase, whitespace-collapsed text. Mismatches are triaged into:

1. **Tree bug** (our linearization wrong) — fix the collector.
2. **SR quirk** (announced name differs from computed) — document as a known
   quirk, optionally add a `known_quirks` note to the transcript tool.
3. **Page bug** (neither announced what the page visually shows) — the real
   finding; flows into the evidence pack as a journey/review artifact.

## NVDA (Windows — CI-able)

NVDA exposes a controller API (`nvdaControllerClient32.dll`). A Python
harness (ctypes) can:

1. Launch NVDA (`nvda.exe --minimal`), start Firefox/Chrome.
2. Drive the page: `Tab`, headings by letter, landmarks by key.
3. Capture speech: enable NVDA's log (`--log-level=DEBUGSPEECH`), read the
   speech lines from `%TEMP%/nvda.log`.

CI recipe (GitHub Actions `windows-latest`): silent-install NVDA from
[nvaccess.org](https://www.nvaccess.org/download/), run the harness against
staging, diff against the transcript, upload the diff as an artifact.
Windows + NVDA in CI is the battle-tested path (axe-core's own lab does
this); the harness is the missing piece, not the platform.

## VoiceOver (macOS — this scaffold)

VoiceOver has no public API for speech; the trick is its **Caption Panel**
(VO-F10): VoiceOver renders its spoken output as on-screen text, readable
through the accessibility APIs. `scripts/voiceover-capture.applescript`:

1. Opens a URL in Safari.
2. Activates VoiceOver (requires the terminal/host app to have
   *Accessibility* permission).
3. Toggles the Caption Panel.
4. Drives VO navigation (VO+Right/Left, heading jumps) via System Events
   keystrokes.
5. Reads the Caption Panel text after each step and writes a JSONL transcript
   (`{step, text}`).

Caveats, stated honestly: keystroke injection needs Accessibility +
Automation permissions; timing varies by VoiceOver speech rate (set a fixed
rate first); the caption text lags speech by a fraction. It is a scaffold
for a human-driven cross-check on a Mac, not a CI gate.

## Where the diff lives

`a11y_diff` compares accessibility snapshots, not transcripts. The
cross-check adds a small normalizer (`normalize(announcement) → role|name|state`)
on both sides and reuses the diff shape (`added/removed/renamed/first_differences`).
When a run exists, the transcript enters the evidence pack as
`sr_transcript` with a `crosscheck` block (source: nvda|voiceover, date,
mismatch count) — evidence a reviewer can see and re-run.

## Do not promise, yet

Until NVDA capture runs in CI at least once a month, the transcript tool
keeps saying "linearized reading order — approximation". The day the
cross-check lands in CI, that sentence gets a measured qualifier. Same
honesty rule as every other signal in this toolkit.
