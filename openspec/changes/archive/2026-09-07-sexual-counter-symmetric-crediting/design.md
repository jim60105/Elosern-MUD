# Design: sexual-counter-symmetric-crediting

## Context

`SexualActDef` carries `actor_counters` and `participant_counters`; the
`sexual_counter:<act_key>` handler (`world/rules/action.py`, shipped by
`sexual-act-effects`) already increments `participant_counters` on every
other participant. The partner line uses both fields today (both
participants gain `duo_act_count`); the combat/interspecies/shame lines all
declare `participant_counters=()`, pinning an actor-only convention in both
code docstrings and spec scenarios.

## Goals / Non-Goals

**Goals:**

- One crediting convention for the whole catalog: a participated-act
  counter records every body that underwent the act.
- Data-only flip on existing machinery; no handler or registry-schema work.

**Non-Goals:**

- No new counters, no unlock-gate or threshold changes.
- No back-derivation of historical records on existing characters.
- No change to the partner/divine/solo lines.

## Decisions

**D-1: Flip direction-free counters, keep direction-bound counters
actor-only.**
`hostile_act_count` and `interspecies_act_count` describe the relation
between bodies (a hostile / cross-species act happened between these two),
so both sides qualify. `exposure_act_count` and `watched_count` describe
what one did to oneself / what happened to oneself's gaze budget — crediting
an audience member who merely watched with `exposure_act_count`, or the
observer with `watched_count`, would corrupt the counter's meaning. This
boundary is the difference between "the body underwent it" and "the actor
did it"; the spec deltas encode it.
_Alternative considered_: mirror everything for uniformity — rejected;
`watched_count` on an observer is plainly false.

**D-2: Flip the shame-line `shame_provocative_gaze` only; leave the four
public-exposure acts alone.**
The gaze is a two-body hostile act (target got gazes-at), so it mirrors
`hostile_act_count`. The public acts' counters are direction-bound (D-1);
their `participant_counters` stay `()`.

**D-3: Renamed requirements carry new canonical IDs.**
"The combat seed credits hostile_act_count on the actor only" and
"shame_provocative_gaze credits hostile_act_count on the actor only, never
on a target" would misdescribe the requirement if only the body changed.
Both get renamed with fresh traceability IDs and their `covers_requirement`
annotations move in the same change.

**D-4: Monster-side credit is accepted as inert-but-correct.**
Monsters never own catalog acts, so their counters unlock nothing;
population monsters delete on despawn. The record is written anyway because
the convention is convention, and surviving scene monsters/session
monsters keep meaningful records for Narrator consumption.

## Risks / Trade-offs

- [Both sides' counts now grow, unlocking acts faster] → Accepted by owner;
  gates are relative and apply to both sides equally.
- [Test churn across four catalog test modules could mask a real
  regression] → Each rewritten test keeps its original structure and only
  inverts the target-side expectation; the partner-line tests (already
  symmetric) act as the pattern oracle.
- [Future contributors reintroduce asymmetry from stale docstrings] → All
  module docstrings asserting the old convention are rewritten in the same
  change (tasks list names each file).
