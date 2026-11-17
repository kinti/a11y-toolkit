# Severity data: the user-pain ordering behind the priorities

Severity in this engine is calibrated against expert review (the bench/
directory is the standing panel). Calibration answers "is this finding
REAL?"; it does not answer "how much does it HURT?". For the hurt axis, the
external reference is screen-reader user data, and the most current broad
sample is WebAIM's Screen Reader User Survey #10 (Dec 2023 to Jan 2024,
1,539 valid responses, self-selected sample, webaim.org/projects/
screenreadersurvey10/).

## The survey's "most problematic" list, in order

1. CAPTCHA (most problematic by a notable margin; disabled respondents
   ranked it twice as often)
2. Interactive elements (menus, tabs, dialogs) not behaving as expected
3. Links or buttons that don't make sense
4. Unexpected screen changes
5. Lack of keyboard accessibility
6. Missing or improper alt text
7. Complex or difficult forms
8. Missing or improper headings
9. Too many links / navigation items
10. Complex data tables
11. Inaccessible or missing search
12. Missing skip-to-main-content links

The survey notes this ranking has stayed largely unchanged for 14 years.

## How we use it

- As a TIE-BREAKER and sanity check on severity ordering, never as a
  severity source by itself: a criterion's level (A/AA) and the failure's
  blast radius set the severity; the survey tells us the user-pain rank.
- As a roadmap lens: items 2, 3, 5 and 12 map to rendered checks
  (a11y_keyboard now activates the first real skip link and flags a target
  that lands still hidden, 2.4.1); items 1, 6 and 8 map to static signals.
- For panel ordering in consumer products (Lince), where the question is
  "what hurts the most people first".

## Numbers worth quoting (with their source)

- 71.6% of screen reader users navigate by headings FIRST when looking for
  information on a long page; 88.8% find heading levels very or somewhat
  useful.
- Landmarks: 17.9% use them whenever available, 13.9% often, 31.5%
  sometimes; only 3.7% call landmarks their primary finding method. (Do NOT
  quote the 63% figure from the 2015-era survey 6; the honest current
  picture is cooler.)
- 85.9% say better/more accessible WEBSITES would improve accessibility more
  than better assistive technology (14.1% bet on AT).
- 99.8% of respondents have JavaScript enabled: retire the "no-JS user"
  framing from docs and messages.
- 71.6% use more than one screen reader; JAWS 40.5% and NVDA 37.7% as
  primary, with strong regional variation (NVDA 70.8% in Asia, JAWS 55.5%
  in North America).

## What this document does NOT do

It does not move any score. The engine's severity and score are calibrated
against the expert-review benches; user-pain data informs docs, roadmap and
panel ordering. It also does not claim the survey sample is representative
(WebAIM says so itself in every survey).
