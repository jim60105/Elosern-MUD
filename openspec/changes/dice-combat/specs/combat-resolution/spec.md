## ADDED Requirements

### Requirement: To-hit uses a recalibrated defender constant of 51, not the design doc's original 60
`world/rules/rulebook/combat.yaml` SHALL declare `to_hit.defender_constant: 51`. A hit SHALL occur when
`roll_d100() + attacker_effective_agility >= defender_constant + defender_effective_agility`, where both
agility values are read through `SkillHandler.effective_value("agility")` (change 5), adjusted by any
`agility` percentage modifier `evaluate_combat_modifiers()` (change 6) returns for that entity, plus any
`accuracy` modifier the attacker's own bundle returns.

#### Scenario: Exact agility parity yields a 50% hit chance
- **WHEN** attacker and defender have identical effective agility (after modifiers) and 10,000
  `roll_d100()`-driven to-hit checks are run
- **THEN** the observed hit rate is within a small statistical tolerance of 50%, matching
  `(50 + 0) / 100` from design.md D-2's derivation

#### Scenario: A cross-race agility gap saturates to a guaranteed outcome
- **WHEN** a to-hit check is run with an attacker/defender effective-agility difference of 48 or more
  in either direction (the smallest possible human/elf gap given `STATIC_TIER_REGISTRY`'s bands)
- **THEN** the hit rate is exactly 0% (attacker's agility deficit) or exactly 100% (attacker's agility
  surplus), with no roll capable of changing the outcome

#### Scenario: A same-tier or adjacent-tier agility gap never fully saturates
- **WHEN** a to-hit check is run with an attacker/defender effective-agility difference within the
  range any two `STATIC_TIER_REGISTRY` entries for the same race produce (at most 30 points)
- **THEN** the resulting hit rate is strictly between 0% and 100%

#### Scenario: A natural roll of 100 does not override a saturated miss
- **WHEN** an attacker whose effective-agility deficit against the defender is 50 or more rolls the
  maximum possible value on `roll_d100()`
- **THEN** the action still misses — no natural-roll override exists that can defeat the deliberate,
  calibrated saturation from design.md D-2

### Requirement: Damage multiplier is banded by margin of success, with a magnitude-only critical on a
natural 100
`world/rules/rulebook/combat.yaml`'s `damage` section SHALL declare `crit_multiplier`,
`solid_hit_margin`, `solid_hit_multiplier`, `base_multiplier`, and `floor`. Damage SHALL be computed as
`max(round(effective_attack_stat * roll_multiplier) - effective_defense, floor)`, where
`roll_multiplier` is `crit_multiplier` if the raw, unmodified `roll_d100()` result equals 100,
`solid_hit_multiplier` if the margin of success is at least `solid_hit_margin`, and `base_multiplier`
otherwise. This calculation SHALL only run when the to-hit check (above) already succeeded — a natural
100 SHALL NOT cause a miss to become a hit.

#### Scenario: A bare hit uses the base multiplier
- **WHEN** an attack hits with a margin of success below `solid_hit_margin` and the raw roll is not 100
- **THEN** damage is computed using `base_multiplier`

#### Scenario: A comfortable hit uses the solid-hit multiplier
- **WHEN** an attack hits with a margin of success at or above `solid_hit_margin`
- **THEN** damage is computed using `solid_hit_multiplier`

#### Scenario: A natural 100 always applies the critical multiplier regardless of margin
- **WHEN** an attack's raw, unmodified `roll_d100()` result is exactly 100 and the attack hits
- **THEN** damage is computed using `crit_multiplier`, even if the margin of success would otherwise
  have qualified only for `base_multiplier`

#### Scenario: Damage never drops below the floor
- **WHEN** `effective_attack_stat * roll_multiplier - effective_defense` computes to a value at or
  below zero
- **THEN** the applied damage equals `damage.floor`, never zero or negative

#### Scenario: A miss deals no damage and applies no floor
- **WHEN** the to-hit check fails
- **THEN** no damage is applied to the target's `hp`, and the damage floor does not apply (a miss is
  not a "zero-damage hit")

### Requirement: effective_power combines four effective stats multiplied by current hp
`world/rules/combat.py` SHALL provide `effective_power(entity) -> float`, computed as the sum of
`SkillHandler.effective_value()` for `atk_phys`, `agility`, `defense`, and `magic_level`, multiplied by
`max(entity.traits.hp.value, 0)`. This function SHALL NOT write to any entity attribute.

#### Scenario: effective_power reads every stat through effective_value, never raw traits
- **WHEN** an entity has an active stat-multiplier skill (e.g. 身體強化) affecting `atk_phys`
- **THEN** `effective_power()`'s result reflects the multiplied value, not `entity.traits.atk_phys.value`

#### Scenario: An elf's effective_power vastly exceeds a human elite's, driven by hp
- **WHEN** `effective_power()` is computed for an elf reference character (e.g. stats matching Yuka,
  88/92/90, hp 10000) and a human-elite reference character (e.g. stats matching Lidzia, 8/9/7, hp 120)
- **THEN** the ratio of the elf's `effective_power()` to the human's is at least 100 — large enough
  that a downstream overwhelm check (change 10) could treat this matchup as overwhelming, unlike a
  stat-only ratio which would understate the gap to roughly 10

#### Scenario: A mid-tier monster's effective_power exceeds a human elite's without becoming overwhelming
- **WHEN** `effective_power()` is computed for a mid-tier monster (`MonsterTier["mid"]`'s band, e.g.
  16/16/16, hp 300) and a human elite (Lidzia-equivalent, hp 120)
- **THEN** the ratio of the monster's `effective_power()` to the human's is greater than 1 but well
  below 100, reflecting a fight that requires a party rather than one that is mathematically decided

#### Scenario: effective_power drops as an entity's current hp drops, mid-fight
- **WHEN** `effective_power()` is computed for the same entity at full current hp and again after its
  `entity.traits.hp.value` has been reduced (but not to zero)
- **THEN** the second computation returns a strictly smaller value, reflecting design doc §6.3's
  requirement that the overwhelm ratio be recomputable every round to catch mid-fight shifts

#### Scenario: A dead entity has zero effective_power
- **WHEN** `effective_power()` is computed for an entity whose `entity.traits.hp.value` is 0
- **THEN** it returns `0`, not a negative or undefined value

### Requirement: Initiative order is agility-dominant with d100 jitter
`world/rules/combat.py` SHALL provide `roll_initiative(battlefield) -> list[str]`, returning roster
keys ordered to act, computed as `effective_agility * initiative.agility_weight + roll_d100()` per
entity, sorted descending. `rulebook/combat.yaml` SHALL declare `initiative.agility_weight`.

#### Scenario: A large agility gap guarantees turn order regardless of the jitter roll
- **WHEN** two combatants' effective agility differs by at least `agility_weight` (10)
- **THEN** the higher-agility combatant's initiative score is greater than the lower-agility
  combatant's for every possible pair of `roll_d100()` outcomes

#### Scenario: A small agility gap can be reordered by the jitter roll
- **WHEN** two combatants' effective agility differs by less than `agility_weight`
- **THEN** there exists at least one pair of `roll_d100()` outcomes for which the lower-agility
  combatant's initiative score exceeds the higher-agility combatant's

### Requirement: The turn loop reports elapsed time as rounds times 6 seconds and never advances a clock
`world/rules/combat.py`'s `run_battle()` SHALL return a `total_seconds` value equal to
`rounds_elapsed * 6` (design doc §6.3). No function in `world/rules/combat.py` SHALL call
`WorldClock.advance()` or any equivalent — this change reports a time cost and does not itself cause
time to pass.

#### Scenario: A three-round battle reports 18 seconds
- **WHEN** `run_battle()` completes after exactly 3 rounds
- **THEN** `total_seconds == 18`

#### Scenario: No WorldClock call exists anywhere in this change's code
- **WHEN** `world/rules/combat.py`'s and `world/rules/dice.py`'s source is inspected
- **THEN** neither file references `WorldClock` or calls anything named `advance()`

### Requirement: Per-round upkeep ticks buffs unconditionally and self-arms sexual decay
`world/rules/combat.py`'s per-round upkeep SHALL call change 6's `tick_buffs(entity)` for every living
roster member unconditionally (change 6 is a transitive dependency of this change via change 8).
Sexual-state decay SHALL be attempted via a lazy import of `world.rules.sexual_transitions`, degrading
to a no-op — never raising — while that module does not exist, and self-arming once it does.

#### Scenario: Buff ticks run every round with no self-arming guard
- **WHEN** a round completes with a poisoned combatant present
- **THEN** `tick_buffs()` is called for that combatant exactly once, unconditionally, with no
  try/except around the call

#### Scenario: Sexual decay is a no-op while sexual-transitions does not exist
- **WHEN** a round completes and `world.rules.sexual_transitions` is not importable
- **THEN** the round completes successfully with no exception raised, and no sexual-state field on any
  entity is touched

#### Scenario: Sexual decay fires once sexual-transitions exists (self-arming)
- **WHEN** a round completes and `world.rules.sexual_transitions.decay_tick` is importable and callable
- **THEN** it is called once per living roster member as part of that round's upkeep

### Requirement: actions_per_turn: 0 skips a combatant's turn before ActionResolver is called
`world/rules/combat.py`'s `run_round()` SHALL read `evaluate_combat_modifiers(entity)` for each acting
combatant and, if the bundle's `actions_per_turn` key equals `0`, skip that combatant's turn entirely —
producing an `EventLog` with kind `"action_skipped"` — without calling `ActionResolver.resolve()`. This
check SHALL read the combat-modifier bundle's output keys only, with no branch distinguishing which
underlying rule (poison, paralysis, arousal, climax phase) produced the value.

#### Scenario: A climax-in-progress combatant's turn is skipped, not attempted
- **WHEN** `evaluate_combat_modifiers(entity)` returns `{"actions_per_turn": 0}` for the acting
  combatant
- **THEN** `ActionResolver.resolve()` is never called for that combatant this round, and the round's
  event list contains an `"action_skipped"` entry naming that combatant

#### Scenario: No source-level branch distinguishes the modifier's origin
- **WHEN** `world/rules/combat.py`'s source is inspected
- **THEN** it contains no conditional that special-cases a sexual-origin `actions_per_turn` modifier
  differently from a buff-origin one — both are read from the identical bundle key

### Requirement: Golden fixed-seed tests cover a normal exchange and a lopsided exchange
`world/rules/tests/` SHALL contain a fixed-seed golden test for a same-tier ("normal") combat exchange
and a separate fixed-seed golden test for a cross-race ("lopsided") exchange, per design doc §10.

#### Scenario: The normal-exchange golden test asserts an exact hit/miss/damage sequence
- **WHEN** the normal-exchange golden test runs under its fixed seed
- **THEN** it asserts the exact sequence of hit/miss outcomes and damage values `roll_d100()` produces
  for that seed, failing if the to-hit constant, damage bands, or initiative weight are ever changed
  without updating the fixture

#### Scenario: The lopsided-exchange golden test asserts full saturation for the entire fixture
- **WHEN** the lopsided-exchange golden test (elf attacker vs. human-elite defender, and the reverse)
  runs under its fixed seed for multiple rounds
- **THEN** every attack from the elf attacker hits and every attack from the human attacker misses,
  regardless of the specific roll values the seed produces
