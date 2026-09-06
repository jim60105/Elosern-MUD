# Proposal: DA3 — sexual-counter-symmetric-crediting

Change ID: **DA3** (parent design §8 archive order).

## Why

The sexual-act catalogs credit lifetime counters on the actor only — "a
`Monster` target is never credited a lifetime counter"
(`world/skills/sexual_acts/interspecies.py`). The owner decided that a
lifetime counter records what a body underwent, direction-free: every
participant of a participated-act counter's act should carry the record.
The upcoming defeat-aftermath changes credit victims and aggressor monsters
symmetrically; flipping the whole catalog now means both writers share one
convention instead of a permanent, confusing exception.

## What Changes

- **BREAKING** (semantics, no released users): the "actor only" crediting
  convention is retired for direction-free counters. Every act whose counter
  records participation in an act now credits **every participant** the same
  counter it credits the actor:
  - `hostile_act_count` = hostile sexual acts participated in (either side):
    combat seed `combat_tease`, the eight combat-line acts, and
    `shame_provocative_gaze` now mirror to targets.
  - `interspecies_act_count` = acts with a different-species partner (either
    side): the seven interspecies acts now mirror to Monster targets.
- Direction-bound counters stay actor-only because mirroring them would be
  semantically wrong: `exposure_act_count` counts one's own exposure (an
  audience member did not expose), `watched_count` counts one's own
  watched-while-active experience (the observer did not get watched), and
  `masturbation_count` is solo-only. The partner line already mirrors
  `duo_act_count` symmetrically today and is unchanged; the divine line
  declares no counters and is unchanged.
- Mechanism is data-only: `participant_counters` and its
  `sexual_counter:<act_key>` handler already ship (`sexual-act-effects`);
  this change flips 17 act-definition rows and rewrites the module docstrings
  and every regression test that pins the asymmetric expectation.
- Counter semantics are re-documented in the registry module docstrings
  (keys, unlock gates, and thresholds all unchanged).

## Capabilities

### New Capabilities

_None — this change modifies shipped requirements only._

### Modified Capabilities

- `sexual-act-seeds`: "The combat seed credits hostile_act_count on the
  actor only" → credits both participants (requirement renamed).
- `sexual-catalog-combat`: the eight-acts registration requirement now
  declares `participant_counters=("hostile_act_count",)`.
- `sexual-catalog-interspecies`: the seven-acts registration requirement now
  declares `participant_counters=("interspecies_act_count",)`.
- `sexual-catalog-shame`: "shame_provocative_gaze credits hostile_act_count
  on the actor only, never on a target" → credits both participants
  (requirement renamed).

## Impact

- `world/skills/sexual_acts/combat.py`, `interspecies.py`, `shame.py`,
  `solo.py` (combat seed row) — 17 rows' `participant_counters` field plus
  their module docstrings (they currently document the asymmetric
  convention).
- Pinned regression tests rewritten: `test_combat_catalog.py`,
  `test_interspecies_catalog.py`, `test_shame_catalog.py`,
  `test_seed_acts.py`; structural audit of `test_registry_structure.py` for
  asymmetry pins.
- Traceability: the two renamed requirements get new canonical IDs; the
  `covers_requirement` annotations on their tests are updated in the same
  change (`tools.spec_traceability check` green).
- Unlocked-act population effects (both sides' `hostile_act_count` /
  `interspecies_act_count` now grow from any act) are accepted by the owner:
  victims' counts feed the 異種支配/異種共鳴 gates and the title system's
  `COUNTER_THRESHOLD` / `SEXUAL_EXPERIENCE` predicates. Monster-side counts
  are inert for unlocks (monsters do not own catalog acts) and usually
  transient.
- No migration (0 users in the wild); existing characters' historical
  records are not back-derived.
