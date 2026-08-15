## ADDED Requirements

### Requirement: high_exposure_defense_penalty prices raised exposure as a combat cost
`world/rules/rulebook/combat_modifiers.yaml` SHALL declare a `high_exposure_defense_penalty` row
whose condition is `{field: exposure, gte: 高}` and whose adjustment is `{defense: -15}` — a flat
integer, matching every other `defense`-bundle row in this table (`defense` has no percentage-aware
consumer anywhere in this codebase; only a flat integer is safe to merge and to consume in damage
resolution) — evaluated by the same `evaluate_condition()` function as every other row in the table
with no special-casing by condition origin. This row's threshold position (the second-highest of
`EXPOSURE_LEVELS`' five levels) mirrors `high_arousal_agility_accuracy_penalty`'s threshold
position on `AROUSAL_LEVELS`.

#### Scenario: An entity at or above 高 exposure takes the defense penalty
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity whose `entity.sexual.exposure`
  is at or above `高`
- **THEN** the returned bundle includes `defense: -15`

#### Scenario: The penalty applies correctly through real damage resolution, not only the raw bundle
- **WHEN** an entity whose `exposure` is at or above `高` is the target of a physical or magic attack,
  resolved through `world/rules/combat.py::_adjusted_defense`
- **THEN** the staged damage amount reflects the target's effective defense reduced by exactly `15`
  (i.e. `_adjusted_defense` returns `effective_value("defense") - 15`), with no exception raised —
  proving the adjustment's shape is one `_adjusted_defense`'s numeric-addition consumer can actually
  apply, not merely one `evaluate_combat_modifiers()` can report in isolation

#### Scenario: An entity below 高 exposure is unaffected
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity whose `entity.sexual.exposure`
  is below `高` (`極低` or `低`)
- **THEN** the returned bundle contains no adjustment attributable to
  `high_exposure_defense_penalty`

#### Scenario: The row merges with buff-origin and skill-owned rows identically
- **WHEN** an entity simultaneously has `exposure` at or above `高`, has the `poisoned` buff active,
  and owns `defense_instinct`
- **THEN** the returned bundle includes `agility: "-10%"` (from `poisoned`) and `defense: -10`
  (`defense_instinct`'s `+5` and `high_exposure_defense_penalty`'s `-15` summed by
  `_merge_adjustments`'s numeric-addition path — both being flat integers is what makes this
  genuine merge possible; see design.md D-2), with no row excluded or handled differently because of
  its condition origin
