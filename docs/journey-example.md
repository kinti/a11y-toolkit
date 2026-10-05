# Worked example — a blindfold journey, for real

This is a self-test of the blindfold loop (v5.2.0): the fixture page was
authored to fail, the journey was run by the toolkit's own author following
the `blindfold-task` rules strictly — perception from accessibility snapshots
only, actions by accessible name, friction logged at the step it happened.
Six findings, six different criteria, one blocked task.

## The task

"Subscribe to the Acme Weekly newsletter" (`kind: sign-up`) on a fixture
whose seeded failures stay in the appendix of the repository history — the
point is what the TREE shows, not what the HTML says.

## What the snapshots said

**Snapshot 1 (entry).** One heading (`h1 "Acme Weekly"`); the "Latest issue"
section header is styled text, not a heading; zero landmarks — the whole page
is `generic`; a textbox named only by its placeholder; a button whose
accessible name is the arrow emoji.

**Snapshot 2 (after fill + submit).** A bare `generic` node with "Please
enter a valid email address." appeared — no `role="alert"`, no live region,
focus still on the button. A real screen-reader user hears **nothing**.

**Snapshot 3 (second attempt, valid-format email).** Same silent failure —
and a *second* identical error node appended to the DOM. Two reasonable
attempts: per protocol, `gave_up`.

## The friction log (input)

| Step | Pattern | Criterion | Sev |
|---|---|---|---|
| 1 | `journey_heading_nav_broken` | 2.4.6 | high |
| 1 | `journey_landmark_missing` | 2.4.1 | medium |
| 2 | `journey_no_instruction` | 3.3.2 | medium |
| 3 | `journey_unnamed_control` | 4.1.2 | high |
| 4 | `journey_error_silent` | 3.3.1 | high |
| 4 | `journey_status_silent` | 4.1.3 | medium |

## The verdict (output)

```json
{
  "verdict": "blocked", "score": 0,
  "summary": { "high": 3, "medium": 3, "low": 0 },
  "outcome": { "completed": false, "gave_up": true, "workaround_used": false }
}
```

Scoring, deterministically: start 100, −25 per high friction (three: broken
headings, unnamed button, silent error), −12 per medium (three), `gave_up`
→ **blocked at 0/100**. The six findings carry per-step remediations and map
to six distinct criteria — the exact brief a human reviewer needs, and the
exact input a review marketplace prices.

## What this validated

1. Perception via the agent's own browser snapshot preserves session state
   across steps (the filled email was still in the box on snapshot 2).
2. The SR-native navigation rules fire immediately: broken headings and
   missing landmarks were the first two findings — the two things a real
   screen-reader user checks first and a Tab-walk never notices.
3. `gave_up` produced a `blocked` verdict without any special-casing: the
   honest end of an impossible task is a first-class outcome.
4. Friction → criterion → remediation → evidence pack works end-to-end with
   zero manual mapping.
