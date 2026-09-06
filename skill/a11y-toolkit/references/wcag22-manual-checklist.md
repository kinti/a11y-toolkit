# WCAG 2.2 manual checklist — what automation cannot check

Automation covers ≈ 1/3 of WCAG. As an agent, YOU can close part of the gap:
these checks are ordered by impact, with how to perform each one. Report PASS/
FAIL/REVIEW per item, with evidence.

## Keyboard (do this first — it is the most common real-world failure)

1. **Tab through the whole page**: every interactive element is reachable and in
   a logical order. Fail: focus jumps unexpectedly, elements skipped, focus
   trapped in a widget (check Esc closes modals/menus — 2.1.2).
2. **Focus is always visible** (2.4.7): you can tell where you are at every stop.
   The rendered audit's focus check approximates this; confirm visually.
3. **All functionality works without a mouse**: menus, sliders, drag-and-drop
   alternatives (2.5.7 — any action draggable must have a click/tap equivalent).
4. **No keyboard traps inside iframes/embeds**.

## Screen reader (NVDA/VoiceOver if available; otherwise reason from the audit)

5. **Page makes sense by headings**: h1 names the page; hierarchy is a real
   outline (the audit catches skips; you judge meaningfulness).
6. **Landmarks exist**: header/nav/main/footer; repeated navs are labeled when
   there are several.
7. **Link text has context out of line** ("click here", "read more" ×14 fail).
8. **Errors are announced**: submit an invalid form; the error must be exposed
   (aria-live / role=alert / focus move) — 3.3.1, 4.1.3.
9. **Dynamic content announces itself**: use the aria-live monitor snippet on
   toasts/loaders/infinite scroll.

## Visual zoom & reflow

10. **200% zoom**: no loss of content or functionality (1.4.4).
11. **320px width (reflow)**: no horizontal scrolling (1.4.10).
12. **Text spacing overrides** (line-height 1.5, paragraph 2em, letter 0.12em):
    nothing clips (1.4.12).

## Content

13. **Alt text QUALITY** (the audit finds missing alt; you judge the text):
    informative images describe content; decorative ones are alt=""; complex
    images have long descriptions nearby.
14. **Language of parts**: foreign-language quotes/terms carry lang= (3.1.2).
15. **Instructions don't rely on shape/position alone** ("click the button on
    the right") — 1.4.1, 1.3.3.
16. **Consistent help** (2.6 — new in 2.2/A): help/phone/contact in the same
    place across pages.
17. **Redundant entry** (3.3.7 — new in 2.2/A): the same info is not asked twice
    in one process (autocomplete/memory is allowed).
18. **Accessible authentication** (3.3.8 — new in 2.2 AA): login has no
    cognitive-function test (puzzle CAPTCHA) without an alternative.

## Contrast (beyond the tools)

19. `a11y_audit_dom` computes computed-color contrast; **text over photos,
    gradients and videos** is exactly where it says "review" — check those
    regions with `a11y_contrast_image` on a screenshot.
20. States: hover/focus/disabled/placeholder colors also need 1.4.3/1.4.11 —
    sample each state.

## Reporting format

```
## A11y report — <url>
Automated: X high / Y medium / Z low (a11y_audit_url [+ a11y_audit_dom])
Manual (agent-verified): <n> pass, <m> fail, <k> review
Top fixes: 1) … (WCAG x.x.x) 2) … 3) …
Scope: automation ≈ 1/3 of WCAG; recommend NVDA/VoiceOver pass for <items marked review>.
```
