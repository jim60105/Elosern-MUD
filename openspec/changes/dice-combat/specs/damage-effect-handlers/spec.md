## ADDED Requirements

### Requirement: damage:* is registered into change 8's effect-handler registry, declaring the traits
surface
`world/rules/combat.py` SHALL call change 8's `register_effect_handler("damage", _handle_damage,
surfaces=frozenset({"traits"}))` at import time. This SHALL be the first and only registration this
change performs, and it SHALL use change 8's public registration function — no direct write to
`_EFFECT_HANDLERS` or `_EFFECT_HANDLER_SURFACES`.

#### Scenario: A skill with a damage:* effect resolves once this change is imported
- **WHEN** a `SkillDef` whose `effects` includes a `damage:physical` or `damage:magic:<element>`-shaped
  ID is resolved via `ActionResolver.resolve()` after `world/rules/combat.py` has been imported
- **THEN** the action no longer rejects with `RejectReason.UNKNOWN_EFFECT_ID`

#### Scenario: The registration declares only the traits surface
- **WHEN** `register_effect_handler` is called for the `"damage"` prefix
- **THEN** it declares `surfaces=frozenset({"traits"})`, and this is a genuine subset of change 8's
  `SNAPSHOTTED_SURFACES` — no `UnsnapshottedSurfaceError` is raised at registration time

### Requirement: damage:<school>[:<element>] is the defined convention for this prefix
`_handle_damage` SHALL parse `effect_id` as `damage:<school>[:<element>]`, where `school` is either
`"physical"` (reading `atk_phys`) or `"magic"` (reading `magic_level`) as the attacking stat, and
`element` is an optional reference into `world.lore.elements.ELEMENT_REGISTRY`.

#### Scenario: A physical damage effect reads atk_phys
- **WHEN** `_handle_damage` processes an effect ID of `"damage:physical"`
- **THEN** the attacking stat is `SkillHandler.effective_value("atk_phys")` for the acting entity

#### Scenario: A magic damage effect reads magic_level
- **WHEN** `_handle_damage` processes an effect ID of `"damage:magic:fire"`
- **THEN** the attacking stat is `SkillHandler.effective_value("magic_level")` for the acting entity

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
`_handle_damage` SHALL read `atk_phys`/`magic_level`, `agility`, and `defense` exclusively through
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
