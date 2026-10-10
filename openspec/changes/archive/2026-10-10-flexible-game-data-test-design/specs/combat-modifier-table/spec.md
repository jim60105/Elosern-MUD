# Spec Delta

## MODIFIED Requirements

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
