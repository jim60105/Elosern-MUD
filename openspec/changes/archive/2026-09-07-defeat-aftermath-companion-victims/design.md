# Design: defeat-aftermath-companion-victims

Parent design: `docs/superpowers/specs/2026-09-06-defeat-aftermath-design.md`
§3.1 step 3 (companion pool). Depends on the violation sequence's mechanics;
widens its player-only pool with no change to the resist/clock/delta rails.

## Context

The violation change scoped its pool to the defeated player alone (its
`... first pool cut` requirement) so the mechanics land in one day. The
design's full pool is the player plus knocked-out companions. Companion
`SexualState` mounts exist (bound companion NPC path — `at_post_puppet` /
companion build), and `participant`-keyed crediting already ships symmetric
from `sexual-counter-symmetric-crediting`. The only missing piece is the
pool selection and per-victim writes.

## Goals / Non-Goals

**Goals:**

- Pool = non-fled allied participants (player + knocked-out companions);
  deterministic selection; per-victim own-state/counter/EventLog writes;
  per-companion digest observation + wake line.
- Keep the solo-player baseline byte-identical (regression-pinned).

**Non-Goals:**

- No change to threshold/cap/resist/clock/clamp mechanics (violation
  change owns them). No new state fields. No affinity writes (a companion's
  affinity toward the monster is out of scope; the shipped resist auto-comply
  branch does not fire for NPC-vs-monster either).

## Decisions

**D-P1: Selection is a pure derived draw, not a second RNG.**
Each attempt picks its victim by feeding the state-derived helper an
extra `participant_slot` dimension (session id + violator + attempt index +
purpose="target"). No new RNG state; replay-identical. Fled companions are
filtered out of the candidate list before the draw, so a fled companion can
never be selected even if the hash would have pointed at its slot.

**D-P2: Per-victim writes ride the existing sexual-state path.**
The violator's act applies its declared deltas to the selected victim's
`SexualState` through the same write path the player uses; counters credit
symmetrically (victim's `participant` counter + violator's counter) exactly
as the crediting change defines for combat acts — the defeat path is another
site of the same convention, not a new one. The `interspecies` species gate
(monster-only target) is unchanged, so a companion NPC victim credits the
same way a monster-targeted combat act does.

**D-P3: The digest outcome set is per-participant, keyed by entity.**
`run_violation_sequence` already returns one `ViolationOutcome` (player).
This change returns a mapping `{participant: ViolationOutcome}`; the digest
change consumes the mapping. The player's key keeps the old shape, so the
digest change is unaffected by the widening.

**D-P4: Companion wake line is observation-only.**
A knocked-out companion "wakes" narratively (zh-tw line) with its own counts;
it is NOT re-Hp-floored or state-changed beyond the act deltas it received —
companions already settle through the core's normal survivor/floor path. The
wake line is a read of the outcome, not a new mutation.

## Risks / Trade-offs

- [Companion sexual content may be more sensitive than the player's] →
  single-player, adult-owned project; the content switch (`DEFEAT_ADULT_SCENES`)
  governs the whole violation phase, companions included.
- [Per-victim writes could double-credit the violator across a mixed pool] →
  each attempt credits once against its selected victim; the symmetric
  counter test pins a two-victim sequence's totals.
- [The mapping return widens the violation change's contract] → the player
  key keeps its shape; only the container changes, and the digest change
  (the only consumer) is designed against the mapping in its own proposal.
