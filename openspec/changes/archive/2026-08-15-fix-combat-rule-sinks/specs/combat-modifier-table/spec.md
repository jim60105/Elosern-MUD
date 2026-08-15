## MODIFIED Requirements

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

## ADDED Requirements

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
