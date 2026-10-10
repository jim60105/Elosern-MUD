# combat-modifier-table Specification

## Purpose
Keeps combat_modifiers.yaml one table — buff-origin and sexual-origin rules alike — evaluated by the identical shared condition engine with no origin-specific branch, exposed through the pure query evaluate_combat_modifiers(). Defines bundle value semantics (flat defense/atk_phys magnitude adjustments, percentage mp/sp cost adjustments, non-negative adjusted agility), condition kinds such as skill_owned and worn-equipment facts, and the requirement that preview, preflight, and resolve agree on adjusted values.

## Requirements

### Requirement: combat_modifiers.yaml is one table evaluated by one condition engine, with no
special-case branch between buff-origin and sexual-origin rows
`world/rules/rulebook/combat_modifiers.yaml` SHALL contain both buff-presence rules and
sexual-field-threshold rules, and `world/rules/combat_modifiers.py`
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

#### Scenario: A newly added lock-marker row locks through the shared mechanism
- **WHEN** a synthetic entity holds a marker buff whose only mechanical row is a new
  `buff_active`-conditioned `actions_per_turn: 0` rule
- **THEN** the merged bundle reports the zero exactly as `paralysis_locks_actions` does, the existing
  turn-skip and cast-gate consumers observe it with no code change, and expiry restores action

#### Scenario: New leaf values ride the same merge without defaulting
- **WHEN** `evaluate_combat_modifiers(entity)` runs for an entity holding only a regen-lock marker,
  only a share-bonus marker, and neither
- **THEN** each bundle contains exactly its one new leaf value from its row, the third bundle lacks
  both keys entirely (absent, not zero, for `regen_scale`), and every pre-existing leaf value is
  merged unchanged

#### Scenario: Fear locks actions and stays key-independent of physical stillness
- **WHEN** one synthetic entity holds `fear` and another holds an ice physical-still marker, and each
  key is cleansed separately
- **THEN** the feared entity's merged bundle reports `actions_per_turn: 0` through the ordinary
  `buff_active` row while the feared entity still also carries its agility/accuracy values, removing
  either key restores exactly that entity's action without touching the other key's state, and no
  table row matches one key against the other's condition

#### Scenario: The rule origins covered by the table's seed rows
- **WHEN** the buff-presence and sexual-field-threshold origins are enumerated
- **THEN** buff-presence covers poison, paralysis, and fear, and sexual-field-threshold
  covers arousal and climax phase

#### Scenario: Reaction-wave lock markers join as ordinary rows
- **WHEN** the action-locking marker buffs added by the MP-depletion reaction wave — a
  suffocation marker, and the bind marker the water wave binds through the table — join the
  table
- **THEN** each joins as an ordinary `buff_active`-origin row carrying the existing
  `actions_per_turn: 0` bundle value — no new bundle key, no marker-specific consumer code
- **AND** every new rule ID keeps the one-unit-test correspondence the table already
  enforces

#### Scenario: Gauge-transfer leaf values are generic and single-consumer
- **WHEN** the gauge-transfer wave extends the merged bundle
- **THEN** it adds exactly two further generic leaf values following the existing
  heterogeneous-value posture: `{gauge}_regen_scale` (a per-gauge regen multiplier consumed
  only by the world-clock regen stage) and `recovery_share_bonus` (an additive
  drain-recovery share bonus consumed only by the gauge-transfer caster-share read site,
  folded gauge-agnostically)
- **AND** both are produced by ordinary `buff_active`-origin rows and are absent-by-default
  rather than defaulted in table code
- **AND** neither introduces a marker-specific consumer, an element name, or a skill key
  anywhere in the table or its evaluation module

#### Scenario: The fear marker ships its lock through the ordinary mechanism
- **WHEN** the dark wave's psychological-stillness marker joins the table the same way
- **THEN** the `fear` marker's 「無法行動」 clause ships as one ordinary `buff_active: fear`
  row carrying `actions_per_turn: 0` alongside the pre-existing `fear` agility/accuracy row
- **AND** `fear` remains an buffs key INDEPENDENT of the ice wave's physical-still keys — no
  row, condition or consumer may equate, alias, or cross-match `fear` with any ice stillness
  key; their distinction is authoring-side narrative only

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
by omitting sexual-field context keys entirely, causing every
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
- **THEN** the returned bundle includes `t_high_arousal_agility_accuracy_penalty`'s adjustment
  (`agility: "-20%"`, `accuracy: -15`)

#### Scenario: The tolerated None is change 3's current placeholder
- **WHEN** the context-building step runs while the table is still ahead of the sexual-state
  implementation
- **THEN** `entity.sexual` is `None` as change 3's current placeholder value, and the inert
  degradation applies to it

#### Scenario: Numerical mechanism examples are synthetic
- **WHEN** the numerical examples above are exercised
- **THEN** file-local fixed synthetic rows grant those values with independently known results; shipped-content checks retain real reference/predicate/shape/polarity validation without fixing the production adjustment amounts

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
nonzero adjustment consistent with the skill's Traditional-Chinese flavor description.

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

#### Scenario: The eight rows surface through the same surfaces as every other row
- **WHEN** one of the eight rows' adjustments is produced
- **THEN** it surfaces through the same surfaces as every other combat-modifier row: the merged
  bundle returned by `evaluate_combat_modifiers()` and the player-visible WebClient status
  conditions (`build_status_read_model()`'s matched-modifier presentation)

#### Scenario: Every declared vocabulary key is consumed by deterministic math
- **WHEN** the table's vocabulary keys are checked against consumers
- **THEN** each is consumed by the deterministic combat or resource math: `agility` and
  `accuracy` in to-hit resolution, `actions_per_turn` as an action lock, `defense` and
  `atk_phys` as flat adjustments in damage magnitude, and `mp_cost`/`sp_cost` as percentage
  adjustments in resource check and deduction

### Requirement: Flat defense and atk_phys bundle values adjust deterministic damage magnitude
Damage resolution in `world/rules/combat.py`'s damage handler SHALL add the actor's flat `atk_phys`
bundle value to the actor's effective physical attack stat before the damage multiplier is applied,
and SHALL add the target's flat `defense` bundle value to the target's effective defense stat before
the defense term is subtracted.

#### Scenario: A physical attacker with an atk_phys bonus deals more damage
- **WHEN** an entity owning `t_retainer_martial_training` (bundle `atk_phys: 5`) lands a physical
  attack whose magnitude would otherwise be `round(effective_atk * multiplier) - defense`
- **THEN** the staged damage amount equals `round((effective_atk + 5) * multiplier) - defense`,
  floored at the configured damage floor

#### Scenario: A magic attack ignores the atk_phys bonus
- **WHEN** the same attacker casts a magic-school spell (damage effect with the magic school)
- **THEN** the staged damage amount is computed from `effective_value("magic_power")` with no
  `atk_phys` bundle value added

#### Scenario: A defender with a defense bonus takes less damage
- **WHEN** an entity owning `t_guardian_instinct` (bundle `defense: 5`) is the target of a physical
  or magic attack
- **THEN** the staged damage amount equals `round(attack * multiplier) - (effective_defense + 5)`,
  floored at the configured damage floor

#### Scenario: The atk_phys adjustment is physical-school only
- **WHEN** the actor's `atk_phys` bundle value is applied during damage resolution
- **THEN** it applies only to physical-school attacks (`attack_key == "atk_phys"`);
  magic-school attacks (`magic_power`) do not receive it

#### Scenario: The defense adjustment keeps its dual-school role
- **WHEN** the target's `defense` bundle value is applied during damage resolution
- **THEN** it applies to both physical and magic attacks, matching defense's existing
  dual-school mitigation role

#### Scenario: No matching rows leaves damage math unchanged
- **WHEN** an entity with no matching rows is involved in damage resolution
- **THEN** it receives unchanged damage math

#### Scenario: Numerical mechanism examples are synthetic
- **WHEN** the numerical examples above are exercised
- **THEN** file-local fixed synthetic rows grant those values with independently known results; shipped-content checks retain real reference/predicate/shape/polarity validation without fixing the production adjustment amounts

### Requirement: Percentage mp_cost and sp_cost bundle values adjust resource checks and deductions
The action resolver's resource check (step 2) and resource deduction (step 6) SHALL apply the
actor's `mp_cost` and `sp_cost` percentage bundle values to the skill's declared MP and SP costs,
and SHALL use the same adjusted integer amount in both steps, computed with floor rounding and
never negative: `max(0, floor(amount * (1 + pct/100)))` for a signed, possibly fractional
percentage.

#### Scenario: A cost reduction enables a cast the declared cost would reject
- **WHEN** an entity owning `t_precise_mana_control` (bundle `mp_cost: "-10%"`) has MP exactly equal
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

#### Scenario: Reporting and the commit-time recheck use the adjusted amount
- **WHEN** a cost adjustment is applied
- **THEN** the staged deduction and its event-log representation report the adjusted amount,
  and the commit-time recheck compares against the adjusted amount

#### Scenario: A key without an X_cost entry keeps its declared cost
- **WHEN** a resource key has no matching `X_cost` bundle entry
- **THEN** it uses the declared cost unchanged

#### Scenario: Numerical mechanism examples are synthetic
- **WHEN** the numerical examples above are exercised
- **THEN** file-local fixed synthetic rows grant those values with independently known results; shipped-content checks retain real reference/predicate/shape/polarity validation without fixing the production adjustment amounts

### Requirement: Damage-estimation surfaces mirror the live adjusted damage math
The overwhelm expected-damage estimator (`_expected_damage_per_attack`) and the monster
highest-expected-damage skill-choice metric (`_choose_skill.expected_damage`) SHALL compute their
attack and defense terms through the same adjusted-stat path as live damage resolution: an
entity's `atk_phys` bundle value is added to the physical attack term and its `defense` bundle
value to the defense term, exactly as in live damage.

#### Scenario: Overwhelm expected damage includes the bundle adjustments
- **WHEN** `_expected_damage_per_attack` is called on an attacker owning `t_retainer_martial_training`
  against a defender owning `t_guardian_instinct`
- **THEN** the estimate uses `effective_atk + 5` for the attack term and `effective_defense + 5`
  for the defense term

#### Scenario: Monster skill choice ranks physical attacks with their atk_phys bonus
- **WHEN** a monster owning (or granted) `t_retainer_martial_training` chooses between a physical and
  a magic candidate skill
- **THEN** the physical candidate's expected damage includes the flat `atk_phys` bundle value

#### Scenario: Only the stat terms mirror live resolution
- **WHEN** the estimator computes an expected damage
- **THEN** it keeps its existing conservative base-multiplier shape; only the stat terms
  match live resolution

#### Scenario: The power-ratio heuristic keeps ranking on raw stats
- **WHEN** the overwhelm power-ratio heuristic (`effective_power`) ranks entities
- **THEN** it keeps ranking by raw effective stats

#### Scenario: Numerical mechanism examples are synthetic
- **WHEN** the numerical examples above are exercised
- **THEN** file-local fixed synthetic rows grant those values with independently known results; shipped-content checks retain real reference/predicate/shape/polarity validation without fixing the production adjustment amounts

### Requirement: Preview, preflight, and resolve agree on adjusted resource costs
`action_preview.py`'s skill-wide failure check SHALL apply the same `apply_cost_modifier`
computation as the resolver's step 2 and step 6, using the no-create bundle from
`evaluate_combat_modifiers_no_create()`, so a skill the preview reports enabled is never rejected by
preflight or resolve for the same resource state, and a skill the preview reports
`INSUFFICIENT_RESOURCE` is rejected identically by preflight.

#### Scenario: Preview enables exactly the casts preflight allows under a reduction
- **WHEN** an entity owning `t_extreme_endurance` (bundle `sp_cost: "-10%"`) has SP at or above the
  adjusted cost of a skill it owns
- **THEN** `preview_skill` reports the skill enabled, `ActionResolver.preflight` succeeds, and
  `ActionResolver.resolve` deducts the adjusted amount

#### Scenario: Preview rejects exactly the casts preflight rejects under a reduction
- **WHEN** the same entity has SP below the adjusted cost
- **THEN** `preview_skill`, `preflight`, and `resolve` all report `INSUFFICIENT_RESOURCE` for the
  same resource key, and no state is written

#### Scenario: Numerical mechanism examples are synthetic
- **WHEN** the numerical examples above are exercised
- **THEN** file-local fixed synthetic rows grant those values with independently known results; shipped-content checks retain real reference/predicate/shape/polarity validation without fixing the production adjustment amounts

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
context entry from the persisted `pleasure` counter's stored value, when the entity's
`sexual_traits` handler is materialized, rather than from a raw `"arousal"` key. With an
unmaterialized handler it still reads `"arousal"` as a level string from the baseline Attribute,
and SHALL NOT read `entity.sexual`, construct a `TraitHandler`, or otherwise materialize any
persistent state.

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

#### Scenario: The band lookup matches the live property
- **WHEN** the preview path derives the `"arousal"` level from the stored `pleasure` value
- **THEN** it uses the same band lookup `SexualState.arousal` uses at read time

#### Scenario: No raw arousal key survives a built SexualState
- **WHEN** an entity's `SexualState` has been built
- **THEN** a raw `"arousal"` key does not exist in that storage

#### Scenario: The baseline read is unchanged from before the amendment
- **WHEN** the unmaterialized-entity path reads `"arousal"` from the frozen import-time
  baseline Attribute
- **THEN** the read is unchanged from before this capability's amendment

### Requirement: high_exposure_defense_penalty prices raised exposure as a combat cost
The authored high_exposure_defense_penalty row SHALL match exposure at or above 高, the second-highest vocabulary level, and grant a negative flat integer defense adjustment through the common condition engine. Below 高 it SHALL be absent. Its status display SHALL retain a Traditional Chinese label and warning severity. Exact negative magnitude SHALL be tunable data; percentage defense SHALL remain invalid for its flat-integer consumer.

#### Scenario: Synthetic negative adjustment reaches real damage
- **WHEN** a fixed synthetic exposure row gives defense -15 and a synthetic passive gives defense +5
- **THEN** the merged flat defense is -10, both physical and magic damage observe it, and changing exposure below 高 removes only the exposure contribution

#### Scenario: Production status projection has a distinct boundary
- **WHEN** the actual exposure row matches an entity above 高
- **THEN** the status read model carries the current authored flat negative adjustment and warning label; neither appears below 高, without a duplicated literal adjustment table

#### Scenario: An entity at or above 高 exposure takes the defense penalty
- **WHEN** actual exposure reaches 高 or above
- **THEN** the authored negative flat defense row matches through the common engine

#### Scenario: The penalty applies correctly through real damage resolution, not only the raw bundle
- **WHEN** a fixed synthetic exposure row grants defense -15 during real physical and magic damage resolution
- **THEN** independently known damage outcomes reflect defense reduced by 15 rather than merely echoing the raw bundle

#### Scenario: An entity below 高 exposure is unaffected
- **WHEN** actual exposure is below 高
- **THEN** no adjustment attributable to the exposure row appears

#### Scenario: The row merges with buff-origin and skill-owned rows identically
- **WHEN** fixed synthetic buff, passive and exposure rows contribute agility -10%, defense +5 and defense -15
- **THEN** agility stays -10% and defense merges to -10 without condition-origin special casing

#### Scenario: The matched condition is player-visible through the status read model
- **WHEN** the authored exposure row matches
- **THEN** the status condition carries its current authored modifier, Traditional Chinese label and warning severity, absent below 高

#### Scenario: The defense adjustment is a merge-safe flat integer
- **WHEN** the authored adjustment is validated
- **THEN** negative flat integer shape is required and percentage defense is rejected

#### Scenario: The threshold position mirrors the arousal penalty's
- **WHEN** exposure and arousal penalty thresholds are located in their vocabularies
- **THEN** both remain second-highest, without fixing the adjustment magnitudes

### Requirement: Worn equipment merges into the merged bundle of both evaluation paths

The deterministic core SHALL expose one pure equipment-adjustment accessor
that reads the fail-closed normalized equipment mapping and folds each worn
item's rulebook combat values into a single adjustment bundle. Both
`evaluate_combat_modifiers()` and the no-create preview variant SHALL append
that bundle after rule-table matching, so to-hit, damage, estimation,
preview, cost, and resist consumers share one effective bundle.

#### Scenario: Worn gear lands in combat resolution

- **WHEN** an actor wearing an item granting `atk_phys +5` strikes under a
  fixed seed
- **THEN** the damage magnitude reflects the merged bundle including the
  equipment contribution, identical to what the preview path predicted

#### Scenario: Malformed equipment storage falls back to base stats

- **WHEN** equipment storage is malformed and a combat resolution evaluates
  the actor
- **THEN** the evaluation returns the rule-table bundle unchanged (no
  equipment contribution, no error raised) while every equipment mutation
  still fails preflight

#### Scenario: Preview and revalidation agree on equipment costs

- **WHEN** an actor wearing an `mp_cost −10%` accessory previews a cast and
  then resolves it without state change between the two reads
- **THEN** both paths apply the identical adjusted cost

#### Scenario: Malformed equipment storage yields an empty bundle
- **WHEN** equipment storage is malformed
- **THEN** the accessor yields an empty bundle: resolution proceeds on base stats
  while mutation stays blocked by the existing preflight

#### Scenario: The accessor and both paths never write entity state
- **WHEN** the accessor or either evaluation path runs
- **THEN** none of them writes any entity state

#### Scenario: Numerical mechanism examples are synthetic
- **WHEN** the numerical examples above are exercised
- **THEN** file-local fixed synthetic rows grant those values with independently known results; shipped-content checks retain real reference/predicate/shape/polarity validation without fixing the production adjustment amounts

### Requirement: Adjusted agility never resolves negative

Every consumer path that derives a modifier-adjusted effective agility for
to-hit, overwhelm estimation, resist scoring, or the flee contest SHALL share
one accessor that applies both agility components of the merged bundle in
order and clamps the adjusted value at 0.

#### Scenario: Heavy gear cannot invert the to-hit inequality

- **WHEN** a defender's equipment and rules drive raw modifier-adjusted
  agility below zero
- **THEN** the to-hit formula consumes agility 0, and the required roll is
  identical to the one computed for a defender with base agility 0

#### Scenario: Negative agility cannot speed a flee attempt

- **WHEN** a fleeing actor's modifiers drive raw adjusted agility below zero
- **THEN** the flee contest scores the actor with agility 0

#### Scenario: Percentage scales first, then the flat addend
- **WHEN** the shared accessor applies the merged bundle's agility components
- **THEN** the `agility` percentage string (rule-table rows and percent-shaped gear)
  scales the effective skill value first, then the flat `agility_flat` addend (flat
  gear such as `shadow_blade`) is added

#### Scenario: Initiative keeps its raw-agility exception
- **WHEN** initiative order is computed
- **THEN** it keeps its documented raw-agility exception unchanged

### Requirement: Condition contexts match on effective exposure

Both combat-modifier condition-context builders (the handler path and the
no-create path) SHALL fill the exposure condition field from the effective
(stored + equipment bias, clamped) ordinal, exposed as one shared immutable
level view with `gte`/`lte`/equality comparison parity across both paths.

#### Scenario: Revealing habit earns the exposure defense penalty with little written

- **WHEN** an actor with stored exposure 中等 wearing t_修女聖袍 (bias +1,
  effective 高) is evaluated for combat modifiers
- **THEN** the shipped 露出 ≥ 高 defense adjustment is present in the merged
  bundle

#### Scenario: Penalty round-trips with the equipment

- **WHEN** the actor unequips t_修女聖袍 mid-itinerary and modifiers are
  re-evaluated
- **THEN** the exposure defense adjustment is gone in both paths and the
  stored trait never moved

#### Scenario: Non-create preview agrees with live resolution

- **WHEN** the same actor's modifiers are evaluated through the no-create
  path and through the handler path
- **THEN** both bundles are identical, the exposure fields are the same
  view type, and all three comparison styles agree

#### Scenario: No equipment reproduces shipped matching

- **WHEN** an unequipped entity's contexts are built
- **THEN** exposure conditions match on the stored value exactly as before

#### Scenario: Revealing gear fires exposure rules without writing state
- **WHEN** revealing equipment raises a wearer's effective exposure past a rule
  threshold
- **THEN** the exposure-gated rule fires on the effective level while written state
  and stored values never change

#### Scenario: The no-create builder stays neutral and write-free
- **WHEN** the no-create context builder resolves stored sexual levels
- **THEN** it remains handler-free and write-free, reading stored sexual levels
  through one neutral shared reader that imports no rules modules

#### Scenario: Numerical mechanism examples are synthetic
- **WHEN** the numerical examples above are exercised
- **THEN** file-local fixed synthetic rows grant those values with independently known results; shipped-content checks retain real reference/predicate/shape/polarity validation without fixing the production adjustment amounts

### Requirement: Equipment-worn conditions match a shared worn-item fact

The rulebook condition vocabulary SHALL include `equipment_worn:
<item_key>` matching iff the entity currently wears that item key. The
worn-item-keys fact SHALL come from one pure stored-equipment read and
SHALL be present in the handler context, the no-create context, and the
shared matcher's partial-context defaults, so live resolution, preview,
resist scoring, and presentation all match identically.

#### Scenario: Sister's grace fires while the habit is worn

- **WHEN** an actor wearing t_修女聖袍 with arousal 中等 is evaluated for
  combat modifiers
- **THEN** the merged bundle includes `t_sister_vestment_grace`'s defense +4

#### Scenario: Same rule silent without the item or the arousal

- **WHEN** the arousal is 平靜, or the habit is not worn
- **THEN** no grace adjustment is present

#### Scenario: Preview agrees with resolution

- **WHEN** a grace-wearing actor's modifiers are evaluated through the
  no-create path and rendered through a partial presentation context
- **THEN** both include the same grace adjustment as live resolution

#### Scenario: Malformed equipment confers no grace

- **WHEN** worn-equipment storage is malformed during evaluation
- **THEN** the worn-item fact is empty and no `equipment_worn` rule matches

#### Scenario: Multi-accessory devotion stack merges as declared

- **WHEN** an actor simultaneously wears t_聖女聖袍, t_光輝聖徽, and t_朝聖者銅符
  (within the shipped accessory slot budget) with arousal 高度
- **THEN** the merged bundle carries the combined defense +8 and the
  emblem's heal_gain +10%, and the display layer lists all three matched
  grace rules

#### Scenario: Grace rules carry display labels

- **WHEN** the shipped display-coverage test runs against the rulebook
- **THEN** every authored grace rule has its Traditional-Chinese label and
  severity entry in the status display rulebook

#### Scenario: The worn-item read is pure and fail-safe
- **WHEN** the worn-item-keys fact is read from stored equipment
- **THEN** the read is pure ;  malformed storage yields an empty set, no writes, and
  no handler materialization

#### Scenario: A missing fact fails the condition closed
- **WHEN** a condition context lacks the worn-item fact
- **THEN** the `equipment_worn` condition fails (fail-closed)

#### Scenario: equipment_worn composes with existing conditions
- **WHEN** an `equipment_worn` condition is authored alongside other conditions
- **THEN** it AND-composes with all existing conditions

#### Scenario: Numerical mechanism examples are synthetic
- **WHEN** the numerical examples above are exercised
- **THEN** file-local fixed synthetic rows grant those values with independently known results; shipped-content checks retain real reference/predicate/shape/polarity validation without fixing the production adjustment amounts

