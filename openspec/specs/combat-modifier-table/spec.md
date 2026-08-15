# combat-modifier-table Specification

## Purpose
TBD - created by archiving change buffs-rulebook. Update Purpose after archive.
## Requirements
### Requirement: combat_modifiers.yaml is one table evaluated by one condition engine, with no
special-case branch between buff-origin and sexual-origin rows
`world/rules/rulebook/combat_modifiers.yaml` SHALL contain both buff-presence rules (poison, paralysis,
fear) and sexual-field-threshold rules (arousal, climax phase), and `world/rules/combat_modifiers.py`
SHALL evaluate every rule in the table through the identical `evaluate_condition()` function from
`world/rules/rulebook/schema.py`. No function in `combat_modifiers.py` SHALL contain a conditional
branch that distinguishes a sexual-origin condition from a buff-origin condition.

#### Scenario: The seed table contains both condition origins
- **WHEN** `world/rules/rulebook/combat_modifiers.yaml` is loaded
- **THEN** it contains at least one rule whose `when` uses `buff_active` (e.g. `poison_agility_penalty`,
  `paralysis_locks_actions`, `fear_agility_and_accuracy_penalty`) and at least one rule whose `when`
  uses `field`/`gte`/`equals` against a sexual-state field (e.g.
  `high_arousal_agility_accuracy_penalty`, `climax_in_progress_locks_actions`)

#### Scenario: No source-level branching distinguishes rule origin
- **WHEN** `world/rules/combat_modifiers.py`'s source is inspected
- **THEN** it contains no conditional (e.g. `if rule.id.startswith(...)`, `if "arousal" in rule.when`)
  that special-cases a sexual-origin rule differently from a buff-origin rule when evaluating them

### Requirement: evaluate_combat_modifiers() is a pure query that never writes to entity state
`world/rules/combat_modifiers.py` SHALL provide `evaluate_combat_modifiers(entity)`, returning a merged
adjustment bundle (a `dict` of field name to adjustment) computed by evaluating every rule in
`combat_modifiers.yaml` against a context built from the entity's current state. This function SHALL
NOT assign to `entity.traits`, `entity.buffs`, `entity.db.*`, or any other entity attribute.

#### Scenario: Multiple matching rules merge into one bundle
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity with both `poisoned` and `fear`
  active as buffs
- **THEN** the returned bundle includes both rules' adjustments (an `agility` entry reflecting
  `poison_agility_penalty` and `fear_agility_and_accuracy_penalty` together, and an `accuracy` entry
  from `fear_agility_and_accuracy_penalty`)

#### Scenario: No entity state changes as a result of calling the query
- **WHEN** `evaluate_combat_modifiers(entity)` is called any number of times in sequence on the same
  entity with unchanged buff/sexual state
- **THEN** `entity.traits.<key>.value` for every trait key is unchanged after each call, and
  `entity.buffs`'s active buff set is unchanged after each call

#### Scenario: An entity with no matching rules returns an empty bundle
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity with no active buffs and no
  sexual state present
- **THEN** it returns an empty `dict`, not an error

### Requirement: Sexual-field rules degrade to inert until entity.sexual is real, then self-arm
`world/rules/combat_modifiers.py`'s context-building step SHALL tolerate `entity.sexual` being `None`
(change 3's current placeholder value) by omitting sexual-field context keys entirely, causing every
sexual-field rule in `combat_modifiers.yaml` to evaluate as not-satisfied rather than raising. Once
`entity.sexual` is a real object exposing `arousal`/`climax_phase` (change 7's future contribution),
the same rules SHALL evaluate against its real values with no code change to `combat_modifiers.py`.

#### Scenario: Sexual-field rules never match while entity.sexual is the change-3 placeholder
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity whose `entity.sexual` is `None`
- **THEN** the returned bundle contains no adjustment attributable to `high_arousal_agility_accuracy_
  penalty` or `climax_in_progress_locks_actions`, and no exception is raised

#### Scenario: Sexual-field rules fire once entity.sexual is a real object (self-arming)
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity whose `entity.sexual` exposes
  `arousal` at or above the `高度` threshold
- **THEN** the returned bundle includes `high_arousal_agility_accuracy_penalty`'s adjustment
  (`agility: "-20%"`, `accuracy: -15`)

### Requirement: Every rule ID in combat_modifiers.yaml has exactly one corresponding unit test
For every `Rule.id` present in `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/tests/
test_combat_modifiers.py` SHALL define exactly one test function named `test_rule_<id>`. A regression
test SHALL mechanically verify this correspondence rather than relying on reviewer discipline.

#### Scenario: Every seed rule has a matching test function
- **WHEN** the mechanical correspondence check inspects `combat_modifiers.yaml`'s rule IDs against
  `test_combat_modifiers.py`'s test function names
- **THEN** it finds exactly one `test_rule_<id>` function for each of `poison_agility_penalty`,
  `paralysis_locks_actions`, `fear_agility_and_accuracy_penalty`,
  `high_arousal_agility_accuracy_penalty`, and `climax_in_progress_locks_actions`

#### Scenario: Adding a rule without a matching test fails the correspondence check
- **WHEN** a new rule is added to `combat_modifiers.yaml` with no corresponding `test_rule_<id>`
  function added to `test_combat_modifiers.py`
- **THEN** the mechanical correspondence check fails, naming the rule ID missing a test

### Requirement: skill_owned is a first-class condition alongside buff_active and field thresholds
`world/rules/rulebook/schema.py`'s `evaluate_condition()` SHALL support `{"skill_owned":
"<skill_key>"}`, true when `<skill_key>` appears in `entity.skills.owned_keys()`. This condition SHALL
be evaluated by the same `evaluate_condition()` function as `buff_active` and sexual-field-threshold
conditions, with no special-casing by condition type in `combat_modifiers.py`.

#### Scenario: An owned skill's rule matches
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity whose `entity.skills.owned_keys()`
  includes `"defense_instinct"`
- **THEN** the returned bundle includes the `defense_instinct` row's adjustment

#### Scenario: An unowned skill's rule does not match
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity that does not own
  `"defense_instinct"`
- **THEN** the returned bundle does not include that row's adjustment

#### Scenario: skill_owned rows merge with buff-origin and sexual-origin rows identically
- **WHEN** an entity simultaneously owns `defense_instinct`, has the `poisoned` buff active, and has
  high arousal
- **THEN** the returned bundle includes all three rows' adjustments merged together, with no row
  excluded or handled differently because of its condition type

### Requirement: The eight previously-dead passive_buff/combat_prediction skills each grant a real adjustment
`combat_modifiers.yaml` SHALL contain one `skill_owned` row for each of `defense_instinct`,
`blade_art_mastery`, `extreme_endurance`, `magic_circle_comprehension`, `precise_mana_control`,
`retainer_martial_training`, `guardian_instinct`, and `reincarnation_boon_yuka`, each producing a
nonzero adjustment consistent with the skill's Traditional-Chinese flavor description. Each row's
adjustment SHALL surface through the same surfaces as every other combat-modifier row: the merged
bundle returned by `evaluate_combat_modifiers()` and the player-visible WebClient status conditions
(`build_status_read_model()`'s matched-modifier presentation). Every vocabulary key the table
declares SHALL be consumed by the deterministic combat or resource math: `agility` and `accuracy`
in to-hit resolution, `actions_per_turn` as an action lock, `defense` and `atk_phys` as flat
adjustments in damage magnitude, and `mp_cost`/`sp_cost` as percentage adjustments in resource
check and deduction.

#### Scenario: Every one of the eight skills has a corresponding rule row
- **WHEN** `combat_modifiers.yaml` is loaded
- **THEN** it contains a `skill_owned` rule referencing each of the eight listed skill keys, and none
  of the eight produces an empty/no-op adjustment

#### Scenario: An owned skill's adjustment is player-visible in the status panel
- **WHEN** an entity that owns `defense_instinct` is presented through `build_status_read_model()`
- **THEN** the read model's conditions include the `defense_instinct_defense_bonus` condition carrying
  the row's adjustment as its modifiers

#### Scenario: The no-create preview path evaluates skill_owned rows identically
- **WHEN** an entity that owns `defense_instinct` is evaluated through
  `evaluate_combat_modifiers_no_create()`
- **THEN** the returned bundle includes the same `defense_instinct` row adjustment as
  `evaluate_combat_modifiers()`, and the read creates no persistent attribute or handler state

### Requirement: Flat defense and atk_phys bundle values adjust deterministic damage magnitude
Damage resolution in `world/rules/combat.py`'s damage handler SHALL add the actor's flat `atk_phys`
bundle value to the actor's effective physical attack stat before the damage multiplier is applied,
and SHALL add the target's flat `defense` bundle value to the target's effective defense stat before
the defense term is subtracted. The `atk_phys` adjustment SHALL apply only to physical-school
attacks (`attack_key == "atk_phys"`); magic-school attacks (`magic_level`) SHALL NOT receive it. The
`defense` adjustment SHALL apply to both physical and magic attacks, matching defense's existing
dual-school mitigation role. An entity with no matching rows receives unchanged damage math.

#### Scenario: A physical attacker with an atk_phys bonus deals more damage
- **WHEN** an entity owning `retainer_martial_training` (bundle `atk_phys: 5`) lands a physical
  attack whose magnitude would otherwise be `round(effective_atk * multiplier) - defense`
- **THEN** the staged damage amount equals `round((effective_atk + 5) * multiplier) - defense`,
  floored at the configured damage floor

#### Scenario: A magic attack ignores the atk_phys bonus
- **WHEN** the same attacker casts a magic-school spell (damage effect with the magic school)
- **THEN** the staged damage amount is computed from `effective_value("magic_level")` with no
  `atk_phys` bundle value added

#### Scenario: A defender with a defense bonus takes less damage
- **WHEN** an entity owning `guardian_instinct` (bundle `defense: 5`) is the target of a physical
  or magic attack
- **THEN** the staged damage amount equals `round(attack * multiplier) - (effective_defense + 5)`,
  floored at the configured damage floor

### Requirement: Percentage mp_cost and sp_cost bundle values adjust resource checks and deductions
The action resolver's resource check (step 2) and resource deduction (step 6) SHALL apply the
actor's `mp_cost` and `sp_cost` percentage bundle values to the skill's declared MP and SP costs,
and SHALL use the same adjusted integer amount in both steps. The adjusted cost SHALL be computed
with floor rounding and SHALL never be negative: `max(0, floor(amount * (1 + pct/100)))` for a
signed, possibly fractional percentage. The staged deduction and its event-log representation SHALL
report the adjusted amount, and the commit-time recheck SHALL compare against the adjusted amount.
A resource key with no matching `X_cost` bundle entry SHALL use the declared cost unchanged.

#### Scenario: A cost reduction enables a cast the declared cost would reject
- **WHEN** an entity owning `precise_mana_control` (bundle `mp_cost: "-10%"`) has MP exactly equal
  to `floor(declared_cost * 0.9)` but below the declared cost
- **THEN** the action resolves successfully and deducts exactly `floor(declared_cost * 0.9)` MP,
  and the event log reports that adjusted amount

#### Scenario: The adjusted cost clamps at zero, never negative
- **WHEN** percentage adjustments would drive a cost to zero or below
- **THEN** the adjusted cost is exactly zero: the check passes at zero resource and the deduction
  stages no negative amount

#### Scenario: Fractional percentages floor deterministically
- **WHEN** a conferred grant scales a percentage reduction to a fractional value (e.g. `"-5%"`)
  and the declared cost is not divisible by the reduction
- **THEN** the adjusted cost is the integer floor of the scaled amount (e.g. a 10-cost skill with
  `"-5%"` adjusts to 9), identically across the check, the deduction, and the preview

### Requirement: Damage-estimation surfaces mirror the live adjusted damage math
The overwhelm expected-damage estimator (`_expected_damage_per_attack`) and the monster
highest-expected-damage skill-choice metric (`_choose_skill.expected_damage`) SHALL compute their
attack and defense terms through the same adjusted-stat path as live damage resolution: an
entity's `atk_phys` bundle value is added to the physical attack term and its `defense` bundle
value to the defense term, exactly as in live damage. The estimator keeps its existing
conservative base-multiplier shape; only the stat terms SHALL match live resolution. The
overwhelm power-ratio heuristic (`effective_power`) SHALL keep ranking entities by raw effective
stats.

#### Scenario: Overwhelm expected damage includes the bundle adjustments
- **WHEN** `_expected_damage_per_attack` is called on an attacker owning `retainer_martial_training`
  against a defender owning `guardian_instinct`
- **THEN** the estimate uses `effective_atk + 5` for the attack term and `effective_defense + 5`
  for the defense term

#### Scenario: Monster skill choice ranks physical attacks with their atk_phys bonus
- **WHEN** a monster owning (or granted) `retainer_martial_training` chooses between a physical and
  a magic candidate skill
- **THEN** the physical candidate's expected damage includes the flat `atk_phys` bundle value

### Requirement: Preview, preflight, and resolve agree on adjusted resource costs
`action_preview.py`'s skill-wide failure check SHALL apply the same `apply_cost_modifier`
computation as the resolver's step 2 and step 6, using the no-create bundle from
`evaluate_combat_modifiers_no_create()`, so a skill the preview reports enabled is never rejected by
preflight or resolve for the same resource state, and a skill the preview reports
`INSUFFICIENT_RESOURCE` is rejected identically by preflight.

#### Scenario: Preview enables exactly the casts preflight allows under a reduction
- **WHEN** an entity owning `extreme_endurance` (bundle `sp_cost: "-10%"`) has SP at or above the
  adjusted cost of a skill it owns
- **THEN** `preview_skill` reports the skill enabled, `ActionResolver.preflight` succeeds, and
  `ActionResolver.resolve` deducts the adjusted amount

#### Scenario: Preview rejects exactly the casts preflight rejects under a reduction
- **WHEN** the same entity has SP below the adjusted cost
- **THEN** `preview_skill`, `preflight`, and `resolve` all report `INSUFFICIENT_RESOURCE` for the
  same resource key, and no state is written

### Requirement: dual_wield_style grants a combat adjustment while owned
`combat_modifiers.yaml` SHALL contain a `skill_owned` row for `dual_wield_style` producing a nonzero
to-hit and/or damage adjustment, conditioned on actual dual-wielding if the equipment data model
exposes that fact as a queryable condition, or on bare ownership otherwise.

#### Scenario: Owning and dual-wielding grants the adjustment
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity that owns `dual_wield_style` and
  (if the equipment check is implemented) has two weapons equipped
- **THEN** the returned bundle includes `dual_wield_style`'s adjustment

#### Scenario: Not owning the skill never grants the adjustment
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity that does not own
  `dual_wield_style`
- **THEN** the returned bundle does not include this adjustment, regardless of equipped weapons

### Requirement: The no-create preview path resolves the derived arousal level from stored pleasure, not a raw arousal key
`world/rules/combat_modifiers.py::build_no_create_condition_context()` SHALL resolve its `"arousal"`
context entry from the persisted `pleasure` counter's stored value (via the same band lookup
`SexualState.arousal` uses at read time), for any entity whose `sexual_traits` handler has been
materialized, rather than from a raw `"arousal"` key — which SHALL NOT exist in that storage once an
entity's `SexualState` has been built. For an entity whose handler has never been materialized, this
path SHALL still read `"arousal"` as a level string from the entity's frozen import-time baseline
Attribute, unchanged from before this capability's amendment. This resolution SHALL NOT read
`entity.sexual`, construct a `TraitHandler`, or otherwise materialize any persistent state.

#### Scenario: The preview path reflects live pleasure on a materialized entity
- **WHEN** an entity's `SexualState` has been materialized and its `pleasure` has since been raised at
  runtime (through any path) past the `高度` band's floor, and
  `evaluate_combat_modifiers_no_create(entity)` is called without first reading `entity.sexual`
  directly
- **THEN** the returned bundle includes `high_arousal_agility_accuracy_penalty`'s adjustment,
  matching what `evaluate_combat_modifiers(entity)` (the live, handler-based path) reports for the
  same entity at the same moment

#### Scenario: An unmaterialized entity still resolves from its import baseline
- **WHEN** an entity has a populated import-time sexual baseline but no materialized `sexual_traits`
  handler, and `evaluate_combat_modifiers_no_create(entity)` is called
- **THEN** the resolved `"arousal"` context value matches the baseline's `arousal` level string, and
  no `sexual_traits` Attribute is created as a result of the call

#### Scenario: The no-create path never diverges from the live path for the same entity
- **WHEN** `evaluate_combat_modifiers(entity)` (materializing) and
  `evaluate_combat_modifiers_no_create(entity)` (non-materializing) are both called on the same
  already-materialized entity, in either order, with no state change between the two calls
- **THEN** both return the same arousal-driven adjustment bundle

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

#### Scenario: The matched condition is player-visible through the status read model
- **WHEN** `build_status_read_model(entity)` is called on an entity whose `exposure` is at or above
  `高`
- **THEN** the read model's conditions include the `high_exposure_defense_penalty` code carrying
  `{"defense": -15}` as its modifiers with its `status_display.yaml` Traditional Chinese label and
  warning severity, and the entry is absent when `exposure` is below `高` — the row surfaces through
  the same `webclient-status-presentation` matched-condition surface as every other
  `combat_modifiers.yaml` rule

