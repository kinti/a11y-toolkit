# Per-criterion human-effort class table (WCAG 2.2 A/AA, all 55)

Canonical pricing seed for the human half of a conformance review: what the
**human** still does after this toolkit's best automated signal, per criterion.
This table is data, not prose — `_EFFORT` in [`a11ycrit.py`](../a11y_toolkit/a11ycrit.py) is
the source of truth (this document is generated from it); the evidence pack
emits the class per matrix row and the remaining totals in `esfuerzo_pendiente`.

An outside marketplace maps classes to its own billing; this table prices the
remaining scope honestly, it does not set anyone's price. Provenance: seed by
Jesús Quintana from 20 years of practice plus a monthly axe benchmark; a
counterparty's own published table supersedes it for their engagements.

| Class | Minutes | Criteria | What the human does |
|---|---|---|---|
| **MIN** | 1–3 | 23 | The agent verified with a measured signal; the human reads and confirms. |
| **MED** | 5–10 | 19 | The agent prepares context; the human verifies in the browser. |
| **MAX** | 15–30 | 13 | Real interaction, real judgment, real tooling. |
| | | **55** | Full single-page audit: **313–649 min (≈5–11 h) of human review remaining after the machine.** |

## Normative rules

1. A measured `automated-fail` splits in two. Confirming the measured fail is
   the MIN human class: the evidence is on the table, the human confirms rather
   than recomputes. Certifying a PASS always costs the criterion's full table
   class — on 1.4.3 that means gradients, background images and hover states
   examined. A MIN confirmation can never become a pass.
2. `not-flagged` on a partially-covered criterion never earns a lower class:
   "the machine looked and found nothing" is weaker than a confirmation.
3. The seconds trend down as the machine improves; the MAX rows stay until a
   machine can watch, listen, and remember — i.e., until it stops being a machine.

## The 55 rows

| Criterion | Level | Class | Why the class |
|---|---|---|---|
| 1.1.1 Non-text Content | A | MIN | alt presence is measured; scan for the image the heuristic missed. |
| 1.2.1 Audio-only and Video-only (Prerecorded) | A | MED | media tags detected; play the media and judge the alternative. |
| 1.2.2 Captions (Prerecorded) | A | MIN | caption track presence detected; confirm the captions are real. |
| 1.2.3 Audio Description or Media Alternative | A | MAX | watch the media and judge whether an alternative covers essential visuals. |
| 1.2.4 Captions (Live) | AA | MAX | live captions must be watched and judged; no honest signal. |
| 1.2.5 Audio Description (Prerecorded) | AA | MAX | audio description requires watching and judging the video. |
| 1.3.1 Info and Relationships | A | MED | semantic structure signals (fieldsets, heading skips, lists); navigate with a screen reader. |
| 1.3.2 Meaningful Sequence | A | MED | DOM vs visual order from snapshot and tab walk; spot-check layout exceptions. |
| 1.3.3 Sensory Characteristics | A | MIN | sensory-instruction phrases detected; read the instructions once. |
| 1.3.4 Orientation | AA | MIN | orientation-lock CSS/JS detected; confirm on a device. |
| 1.3.5 Identify Input Purpose | AA | MIN | autocomplete token per input measured; confirm. |
| 1.4.1 Use of Color | A | MED | link-vs-text color ratio computed; verify visually. |
| 1.4.2 Audio Control | A | MIN | autoplay-with-audio detected; confirm. |
| 1.4.3 Contrast (Minimum) | AA | MAX | computed ratios are evidence, not verdicts; gradients, images and hover states still need review. |
| 1.4.4 Resize Text | AA | MIN | viewport zoom block measured; confirm. |
| 1.4.5 Images of Text | AA | MED | images-of-text candidates detected; judge logo and text exceptions. |
| 1.4.10 Reflow | AA | MED | 320px reflow measured with real overflow; navigate the reflowed content. |
| 1.4.11 Non-text Contrast | AA | MED | focus-indicator contrast computed; verify visually. |
| 1.4.12 Text Spacing | AA | MED | text-spacing overrides injected, clipping counted; verify. |
| 1.4.13 Content on Hover or Focus | AA | MED | hover + Escape dismissibility tested; verify. |
| 2.1.1 Keyboard | A | MED | click handlers on non-interactive elements detected; Tab the page. |
| 2.1.2 No Keyboard Trap | A | MAX | real Tab walk plus Escape test per modal and iframe. |
| 2.1.4 Character Key Shortcuts | A | MAX | single-character shortcuts tested by typing in every field. |
| 2.2.1 Timing Adjustable | A | MIN | meta refresh and timing scripts detected; confirm. |
| 2.2.2 Pause, Stop, Hide | A | MED | looping animations computed; verify the pause control. |
| 2.3.1 Three Flashes or Below Threshold | A | MAX | flash threshold needs frame-by-frame analysis; no honest signal. |
| 2.4.1 Bypass Blocks | A | MIN | missing main/skip detected; confirm. |
| 2.4.2 Page Titled | A | MIN | missing or empty title detected; confirm. |
| 2.4.3 Focus Order | A | MIN | positive tabindex detected; confirm. |
| 2.4.4 Link Purpose (In Context) | A | MIN | generic link text detected; read the links in context. |
| 2.4.5 Multiple Ways | AA | MED | nav/sitemap/search presence from the crawl; confirm. |
| 2.4.6 Headings and Labels | AA | MED | vague headings detected; read them in context. |
| 2.4.7 Focus Visible | AA | MAX | focus visibility measured per stop; Tab the whole site. |
| 2.4.11 Focus Not Obscured (Minimum) — NEW in WCAG 2.2 | AA | MED | sticky header vs scroll-padding measured; Tab the page. |
| 2.5.1 Pointer Gestures | A | MED | gesture listeners without alternatives detected; try the gesture. |
| 2.5.2 Pointer Cancellation | A | MIN | down-event-only handlers detected; confirm. |
| 2.5.3 Label in Name | A | MIN | label-in-name mismatch computed; confirm. |
| 2.5.4 Motion Actuation | A | MIN | motion actuation without UI detected; confirm. |
| 2.5.7 Dragging Movements | AA | MED | drag listeners detected; try the click path. |
| 2.5.8 Target Size (Minimum) — NEW in WCAG 2.2 | AA | MED | target rects measured; check the inline/equivalent exceptions. |
| 3.1.1 Language of Page | A | MIN | page lang missing or invalid, measured; confirm. |
| 3.1.2 Language of Parts | AA | MIN | part lang invalid, measured; confirm. |
| 3.2.1 On Focus | A | MIN | focus-triggered navigation detected; confirm. |
| 3.2.2 On Input | A | MIN | select-triggered navigation detected; confirm. |
| 3.2.3 Consistent Navigation | AA | MED | nav consistency compared across crawled pages; confirm the order. |
| 3.2.4 Consistent Identification | AA | MED | consistent identification compared across pages; confirm the icons. |
| 3.2.6 Consistent Help — NEW in WCAG 2.2 | A | MIN | help presence compared across crawled pages; confirm. |
| 3.3.1 Error Identification | A | MAX | invalid submissions fired and the DOM judged; verify with a screen reader. |
| 3.3.2 Labels or Instructions | A | MIN | placeholder-only and unlabeled required fields measured; read each label. |
| 3.3.3 Error Suggestion | AA | MAX | read and judge each correction suggestion. |
| 3.3.4 Error Prevention (Legal, Financial, Data) | AA | MAX | reversible-transaction check requires walking the flow. |
| 3.3.7 Redundant Entry | A | MAX | redundant entry requires a remembered multi-step walk. |
| 3.3.8 Accessible Authentication — NEW in WCAG 2.2 | AA | MIN | captcha detected; confirm an alternative exists. |
| 4.1.2 Name, Role, Value | A | MIN | invalid roles, broken refs and missing state measured; confirm. |
| 4.1.3 Status Messages | AA | MAX | fire each status message and listen for the announcement. |

## Two rows the author would argue about, with his name on them

- **1.4.3 Contrast is both at once.** Confirming the measured failure (the real
  3.91:1 on gov.uk that axe misses) is a MIN confirmation. Certifying a pass is
  MAX: gradients, background images and hover states are outside any computation,
  and the measured value is evidence, not a verdict.
- **1.2.3 / 1.2.4 / 1.2.5 media criteria are MAX for anything that is not stock B-roll.**
  The human watches the video and judges whether essential visual information exists.
  No signal can do this honestly.

