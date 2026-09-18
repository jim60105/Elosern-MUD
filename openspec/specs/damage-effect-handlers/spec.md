# damage-effect-handlers Specification

## Purpose
Registers the damage:* prefix into change 8's effect-handler registry declaring the traits surface, fixes the damage:<element>:<school> naming convention, and requires the to-hit roll and damage number to be computed during effect resolution — never inside handlers — reading every stat through effective_value() with combat modifiers applied uniformly regardless of origin.
## Requirements
### Requirement: damage:* is registered into change 8's effect-handler registry, declaring the traits
surface
`world/rules/combat.py` SHALL call change 8's `register_effect_handler("damage", _handle_damage,
surfaces=frozenset({"traits"}))` at import time. This SHALL be the first and only registration this
change performs, and it SHALL use change 8's public registration function — no direct write to
`_EFFECT_HANDLERS` or `_EFFECT_HANDLER_SURFACES`.

#### Scenario: A skill with a damage:* effect resolves once this change is imported
- **WHEN** a `SkillDef` whose `effects` includes a `damage:<element>:physical` or
  `damage:<element>:magic`-shaped
  ID is resolved via `ActionResolver.resolve()` after `world/rules/combat.py` has been imported
- **THEN** the action no longer rejects with `RejectReason.UNKNOWN_EFFECT_ID`

#### Scenario: The registration declares only the traits surface
- **WHEN** `register_effect_handler` is called for the `"damage"` prefix
- **THEN** it declares `surfaces=frozenset({"traits"})`, and this is a genuine subset of change 8's
  `SNAPSHOTTED_SURFACES` — no `UnsnapshottedSurfaceError` is raised at registration time

### Requirement: damage:<element>:<school> is the defined convention for this prefix
`_handle_damage` SHALL parse `effect_id` as `damage:<element>:<school>`, matching the change-5 seed
registry, where `school` is either `"physical"` (reading `atk_phys`) or `"magic"` (reading
`magic_power`) as the attacking stat, and `element` either references
`world.lore.elements.ELEMENT_REGISTRY` or is the reserved token `none`, which denotes the absence of
an element rather than a registry lookup. The reserved token SHALL change nothing about settlement:
the school segment alone selects the attacking stat, and an elementless damage effect resolves
through the same to-hit roll, defense subtraction, policy application and projection as an
element-bearing one.

#### Scenario: A physical damage effect reads atk_phys
- **WHEN** `_handle_damage` processes an effect ID of `"damage:dark:physical"`
- **THEN** the attacking stat is `SkillHandler.effective_value("atk_phys")` for the acting entity

#### Scenario: A magic damage effect reads magic_power
- **WHEN** `_handle_damage` processes an effect ID of `"damage:fire:magic"`
- **THEN** the attacking stat is `SkillHandler.effective_value("magic_power")` for the acting entity

#### Scenario: An elementless physical effect settles identically to an element-bearing one
- **WHEN** a synthetic actor strikes a target with an elementless physical damage effect, and a twin
  actor strikes an identical target with an element-bearing physical damage effect of the same
  coefficient and policy under the same fixed roll
- **THEN** both attacks read `atk_phys`, subtract the same defense, apply the same policy terms and
  commit the same hp delta, and neither the attacker's nor the target's elemental affinity changes
  either result

### Requirement: The to-hit roll and damage number are computed during effect resolution, never inside
apply()
`_handle_damage` SHALL compute the to-hit roll, the hit/miss determination, and the resulting damage
number as part of building each `PendingEffect`, before any effect is committed. The `apply` callable
stored on each `PendingEffect` SHALL only write the already-computed damage to `entity.traits.hp`; it
SHALL NOT perform any roll, randomness, or hit-determination logic itself.

#### Scenario: A rejected action after staging leaves hp untouched
- **WHEN** a `damage:*` effect is staged successfully (steps 1-5 succeed) but a later pipeline step
  (6, 7, or 8) raises `RejectedAction`
- **THEN** no target's `entity.traits.hp.value` changes, even though a to-hit roll was already computed
  during staging

#### Scenario: apply() contains no call to the dice roller
- **WHEN** the `apply` callable constructed by `_handle_damage` is inspected
- **THEN** it performs no call to `roll_d100()` or any other randomness source — it only writes a
  precomputed integer delta to `entity.traits.hp`

### Requirement: Damage reads every stat through effective_value(), never raw entity.traits
`_handle_damage` SHALL read `atk_phys`/`magic_power`, `agility`, and `defense` exclusively through
`SkillHandler.effective_value()` for both the acting entity and every target — never
`entity.traits.<key>.value` directly — so that an active stat-multiplier skill's ×10/×100/×1000
applies at resolution time.

#### Scenario: An active body-enhancement skill changes computed damage without changing stored stats
- **WHEN** an attacker with an active ×100 body-enhancement skill casts a `damage:physical` skill
- **THEN** the resulting damage reflects the multiplied `atk_phys`, while
  `entity.traits.atk_phys.value` is unchanged before and after the action

### Requirement: Combat modifiers apply uniformly regardless of origin
`_handle_damage` SHALL read `evaluate_combat_modifiers()` for both the acting entity and each target,
applying any returned `agility` percentage adjustment to that entity's own effective agility and any
`accuracy` adjustment to the attacker's side of the to-hit calculation. No branch in `_handle_damage`
SHALL distinguish a poison-sourced adjustment from an arousal-sourced or fear-sourced one.

#### Scenario: A poisoned attacker's reduced agility lowers their own hit chance
- **WHEN** an attacker has an active `poisoned` buff (per `combat_modifiers.yaml`'s
  `poison_agility_penalty` rule) and casts a `damage:*` skill
- **THEN** the to-hit calculation uses the attacker's agility reduced by that rule's percentage,
  identically to how a high-arousal penalty would be applied

#### Scenario: No source-level branch distinguishes modifier origin
- **WHEN** `_handle_damage`'s source is inspected
- **THEN** it contains no conditional keyed on which `combat_modifiers.yaml` rule produced an
  `agility`/`accuracy` adjustment — only the bundle's output keys are read

