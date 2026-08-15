## MODIFIED Requirements

### Requirement: Buff tick is exposed as a plain callable, with no settlement order invented
`world/rules/buffs.py` SHALL expose buff-tick behavior as a plain callable that a caller (change 11's world clock) can invoke explicitly. This change SHALL NOT hardcode, assume, or invent any ordering between buff ticks, trait regen, and sexual-state decay — that fixed settlement order is design doc §6.5's and change 11's exclusive concern. The callable SHALL still apply each active buff's rate modifier on tick, and SHALL additionally return an ordered tuple of damaging tick records — one per applied rate tick whose modifier targets `hp` with a negative delta — each carrying the definition key, the buff cache's `source_pk` (or `None`), the delta, and the entity's HP immediately before that tick applied. A caller that ignores the return value SHALL observe identical state changes to the pre-change callable.

#### Scenario: Buff tick is invokable independently of any clock
- **WHEN** the buff-tick callable is invoked directly in a test, without any `WorldClock` or scheduler present
- **THEN** it applies exactly one tick's worth of each active buff's rate modifier (e.g. `poisoned` reduces `hp` by its configured per-tick delta once) and completes without requiring any other module to exist

#### Scenario: No settlement-order policy is encoded in this change's modules
- **WHEN** `world/rules/buffs.py` and `world/rules/combat_modifiers.py` are inspected
- **THEN** neither contains a reference to trait regen scheduling or sexual-state decay scheduling, and neither module imports or assumes the existence of `world/rules/sexual_state.py` or a `WorldClock` class

#### Scenario: A damaging tick returns one ordered record
- **WHEN** `tick_buffs(entity, 10)` fires both `poisoned` and `fire_scorch` in one call on a living entity
- **THEN** it returns two records in application order, each carrying the definition key, the buff cache's `source_pk` (or `None`), delta `-5`, and the entity's HP immediately before that tick applied

#### Scenario: Non-damaging ticks return no records
- **WHEN** `tick_buffs(entity)` fires only marker buffs or the conferred growth-rate buff
- **THEN** it returns an empty tuple and applies the rate modifier exactly as before

## ADDED Requirements

### Requirement: Damaging rate buffs persist a validated effect-source identity in the buff cache
`_handle_buff_apply` SHALL persist the resolving actor's dbref as `source_pk` in the buff cache whenever the applied definition's `rate` modifier damages HP (target `hp` with a negative delta). The value SHALL be derived from the actor inside the handler; a caller-supplied `source_pk` in `buff_kwargs` SHALL NOT override it, and an actor without a resolvable positive-int dbref SHALL reject the action before commit. Buff instances created outside the handler (for example direct `_add_buff` calls) MAY lack `source_pk`, in which case their rate ticks are unattributed.

#### Scenario: Applying fire_scorch stores the caster's dbref
- **WHEN** `_handle_buff_apply` resolves `buff:fire_scorch` for a target in combat
- **THEN** the target's buff cache entry carries `source_pk` equal to the caster's dbref, readable on the buff instance

#### Scenario: Caller-supplied source identity cannot spoof attribution
- **WHEN** a `buff_kwargs` value supplies `source_pk` naming a different entity than the actor
- **THEN** the cached `source_pk` is the actor's dbref, never the supplied value

#### Scenario: An actor without a resolvable dbref rejects the damaging buff application
- **WHEN** `_handle_buff_apply` stages a damaging buff for an actor with no positive-int pk
- **THEN** the action rejects before commit and no buff is added

#### Scenario: Reapplying a damaging buff replaces the source with the new caster
- **WHEN** the same damaging buff key is re-applied by a different caster before expiry
- **THEN** the buff cache's `source_pk` is the newest caster's dbref, and a refresh that omits `source_pk` retains the previously cached value rather than erasing attribution
