## ADDED Requirements

### Requirement: The power-ratio signal is computed from team-summed effective_power, checked in both
directions independently
`world/rules/overwhelm.py` SHALL provide `team_effective_power(battlefield, team_key) -> float`,
summing `combat.effective_power()` (change 9, unmodified) over every living, non-fled member of the
named team, and `power_ratio_verdict(battlefield, team_a, team_b) -> str | None`, returning `team_a`
when `team_effective_power(team_a) / team_effective_power(team_b) >= power_ratio_threshold`, `team_b`
when the reverse division meets the same threshold, and `None` otherwise. `world/rules/rulebook/
overwhelm.yaml` SHALL declare `power_ratio_threshold: 100`.

#### Scenario: A team whose aggregate effective_power is 100x or more the other team's is the ratio verdict
- **WHEN** `power_ratio_verdict()` is called for two teams where one team's summed `effective_power()`
  is at least 100 times the other's
- **THEN** it returns the stronger team's key

#### Scenario: Comparable aggregate power returns no ratio verdict
- **WHEN** `power_ratio_verdict()` is called for two teams whose summed `effective_power()` ratio is
  under 100 in both directions
- **THEN** it returns `None`

#### Scenario: Both directions are checked as independent divisions, not one division and its reciprocal
- **WHEN** `power_ratio_verdict()`'s implementation is inspected
- **THEN** it computes `power_a / power_b` and `power_b / power_a` as two separate divisions, never
  deriving the reverse-direction check from `1 / ratio`

#### Scenario: A team with zero living, non-fled members yields an automatic ratio verdict for the other side
- **WHEN** `power_ratio_verdict()` is called for a matchup where one team has no living, non-fled
  members and the other has at least one
- **THEN** it returns the other team's key, without dividing by zero

#### Scenario: A dead or fled team member contributes nothing to their team's aggregate, without affecting their own effective_power
- **WHEN** `team_effective_power()` is computed for a team with one dead member and one living member
- **THEN** the result equals the living member's own `effective_power()` value exactly, and this does
  not depend on reading the dead member's current hp anywhere in `team_effective_power()`'s own logic
  beyond the liveness check itself

### Requirement: The hit-rate signal detects to-hit saturation without rolling dice, checked over every
cross-team pair
`world/rules/overwhelm.py` SHALL provide `hit_rate_verdict(battlefield, team_a, team_b) -> str | None`,
returning `team_a` only if every living, non-fled member of `team_a` has a guaranteed-hit (effective-
agility difference `>= 50`) relationship against every living, non-fled member of `team_b`, **and**
every member of `team_b` has a guaranteed-miss (effective-agility difference `<= -50`) relationship
against every member of `team_a` — both checked as independent conditions, reusing change 9's
`defender_constant` (`combat.COMBAT_YAML["to_hit"]["defender_constant"]`) and the same
`effective_value("agility")`/`evaluate_combat_modifiers()` reads `dice-combat`'s to-hit formula already
performs, without calling `roll_d100()`.

#### Scenario: A team that always hits and is never hit is the hit-rate verdict
- **WHEN** every member of `team_a` has an effective-agility advantage of 50 or more over every member
  of `team_b`
- **THEN** `hit_rate_verdict(battlefield, team_a, team_b)` returns `team_a`

#### Scenario: A non-saturated pair anywhere yields no hit-rate verdict
- **WHEN** at least one cross-team pair's effective-agility difference is strictly between -50 and 50
- **THEN** `hit_rate_verdict()` returns `None`

#### Scenario: No roll_d100 call is made while computing this signal
- **WHEN** `hit_rate_verdict()`'s and `power_ratio_verdict()`'s implementations are inspected
- **THEN** neither calls `roll_d100()` or stages a `PendingEffect` — this signal is computed from
  agility reads and modifier lookups alone

#### Scenario: Attacker and defender saturation are checked as independent conditions, not one derived from the other's negation
- **WHEN** a combat-modifier bundle supplies an `accuracy` adjustment to only one side of a pair
- **THEN** `hit_rate_verdict()` evaluates that pair's "always hits" and "never hits" conditions as two
  separate boolean checks, and does not assume one follows automatically from the other's negation

### Requirement: A decided direction is computed by combining the ratio and hit-rate signals by
agreement, falling back to contested on disagreement
`world/rules/overwhelm.py` SHALL provide an internal decided-direction computation combining
`power_ratio_verdict()`/`hit_rate_verdict()`. When exactly one of the two returns a non-`None` team
key, that key SHALL be the decided direction. When both return the same non-`None` team key, that key
SHALL be the decided direction. When both return non-`None` but different team keys, the decided
direction SHALL be `None`. When both return `None`, the decided direction SHALL be `None`.

#### Scenario: Ratio fires alone (both sides can still land blows)
- **WHEN** `power_ratio_verdict()` returns a team key and `hit_rate_verdict()` returns `None` for the
  same battlefield, and that direction's `estimated_rounds_to_conclude()` is within
  `max_estimated_rounds`
- **THEN** `classify_overwhelm()` returns the ratio's team key

#### Scenario: Hit-rate fires alone (a comparable-power, saturated-agility matchup)
- **WHEN** `hit_rate_verdict()` returns a team key and `power_ratio_verdict()` returns `None` for the
  same battlefield, and that direction's `estimated_rounds_to_conclude()` is within
  `max_estimated_rounds`
- **THEN** `classify_overwhelm()` returns the hit-rate's team key

#### Scenario: Both signals agree
- **WHEN** `power_ratio_verdict()` and `hit_rate_verdict()` both return the same team key, and that
  direction's `estimated_rounds_to_conclude()` is within `max_estimated_rounds`
- **THEN** `classify_overwhelm()` returns that team key

#### Scenario: Signals disagree on direction
- **WHEN** `power_ratio_verdict()` returns one team's key and `hit_rate_verdict()` returns the other
  team's key for the same battlefield
- **THEN** `classify_overwhelm()` returns `None`, leaving the encounter contested rather than asserting
  either direction — this is decided by the disagreement alone; the round-bound signal is never
  consulted when there is no decided direction to bound

#### Scenario: Neither signal fires
- **WHEN** both `power_ratio_verdict()` and `hit_rate_verdict()` return `None`
- **THEN** `classify_overwhelm()` returns `None`

### Requirement: A decided direction is further gated by an estimated-round-count bound — overwhelm
means decided AND quick, not merely decided
`world/rules/overwhelm.py` SHALL provide `estimated_rounds_to_conclude(battlefield, overwhelming_team,
overwhelmed_team) -> float`, a conservative (never-underestimated) estimate of how many more rounds it
would take the overwhelming team to reduce the overwhelmed team's **current**, not max, total hp to
zero, using each attacker's actual to-hit probability and only `combat.COMBAT_YAML["damage"]
["base_multiplier"]` (never the solid-hit or critical bonus), without calling `roll_d100()`.
`world/rules/rulebook/overwhelm.yaml` SHALL declare `max_estimated_rounds: 5`. Once a decided direction
exists (per the prior requirement), `classify_overwhelm()` SHALL return `None` instead of that
direction whenever `estimated_rounds_to_conclude()` for that direction exceeds `max_estimated_rounds`.

#### Scenario: A genuine curbstomp within the round bound is accepted as overwhelm
- **WHEN** a decided direction's `estimated_rounds_to_conclude()` is at or below `max_estimated_rounds`
  (e.g. the elf-vs-human-elite reference matchup, estimated at roughly 1.5 rounds, or an elf against a
  multi-member low-tier-monster party, estimated at roughly 3.3 rounds)
- **THEN** `classify_overwhelm()` returns that decided direction

#### Scenario: A decided-but-grinding matchup is excluded even though a direction is certain
- **WHEN** a decided direction's `estimated_rounds_to_conclude()` exceeds `max_estimated_rounds` (e.g.
  an overwhelming ratio driven by a large max-hp gap, but the overwhelmed side's current hp is large
  and the overwhelming side's per-hit damage is floored at `damage.floor`, so `remaining_hp / dmg_per_
  round` is in the thousands)
- **THEN** `classify_overwhelm()` returns `None`, even though `power_ratio_verdict()` alone would have
  returned a non-`None` team key for the same battlefield

#### Scenario: estimated_rounds_to_conclude uses current hp, not max hp, deliberately
- **WHEN** `estimated_rounds_to_conclude()` is computed for the same overwhelmed team before and after
  one of its members takes combat damage (current hp decreases, max hp and every `effective_value()`
  output unchanged)
- **THEN** the estimate decreases (fewer rounds remain), unlike `team_effective_power()`
  (`overwhelm-threshold`'s own power-ratio requirement), which is unaffected by the identical change —
  the two functions deliberately answer different questions and are not required to agree

#### Scenario: estimated_rounds_to_conclude never calls roll_d100
- **WHEN** `estimated_rounds_to_conclude()`'s implementation is inspected
- **THEN** it contains no call to `roll_d100()` — it is computed from stat reads, the actual to-hit
  probability formula, and `COMBAT_YAML["damage"]` values alone

#### Scenario: The round-bound gate is not consulted when there is no decided direction
- **WHEN** `power_ratio_verdict()` and `hit_rate_verdict()` both return `None`, or return conflicting
  team keys
- **THEN** `classify_overwhelm()` returns `None` without needing to call `estimated_rounds_to_conclude()`
  at all (there is no direction to bound)

### Requirement: classify_overwhelm is a pure query, recomputable every round with no stale state
`classify_overwhelm()` SHALL be a pure function of the `Battlefield`'s current state — it SHALL NOT
write to any entity attribute, cache a previous result, or require being called in any particular
sequence relative to other calls.

#### Scenario: Recomputation after a mid-fight power-tier shift changes the verdict
- **WHEN** `classify_overwhelm(battlefield)` is called, a combatant's `effective_value()` output then
  changes (e.g. a disguise drops, revealing higher true stats, or an agility-multiplying buff expires),
  and `classify_overwhelm(battlefield)` is called again on the same battlefield object
- **THEN** the second call reflects the changed state and may return a different result than the first,
  with no special reset or invalidation step required between the two calls

#### Scenario: effective_power's own max-hp discipline is not bypassed by team aggregation
- **WHEN** `team_effective_power()` is computed for the same still-living team member before and after
  their `entity.traits.hp.value` (current hp, not max) decreases from combat damage, with no change to
  their `effective_value()` outputs
- **THEN** the team aggregate is unchanged — current-hp attrition of a still-living member never moves
  `classify_overwhelm()`'s verdict, matching `effective_power()`'s own established discipline
  (dice-combat design.md D-4)

#### Scenario: A round whose real progress falls behind the round-bound estimate self-corrects on the next call
- **WHEN** `classify_overwhelm()` returns a decided direction because `estimated_rounds_to_conclude()`
  was within bound, one round of real combat resolution then produces less progress than the estimate
  assumed (e.g. the overwhelming side's actual rolls miss more often than the estimate's conservative
  hit-probability figure predicted), and `classify_overwhelm()` is called again on the resulting
  battlefield state
- **THEN** the second call's `estimated_rounds_to_conclude()` reflects the reduced progress and may now
  exceed `max_estimated_rounds`, returning `None` — no separate invalidation step is needed for the
  round-bound signal to correct itself round over round
