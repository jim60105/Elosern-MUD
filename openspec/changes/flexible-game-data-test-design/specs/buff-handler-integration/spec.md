# Spec Delta

## MODIFIED Requirements

### Requirement: Buff tick is exposed as a plain callable, with no settlement order invented
`world/rules/buffs.py` SHALL expose buff-tick behavior as a plain callable that a caller (change 11's world clock) can invoke explicitly, applying each active buff's rate modifier on tick and returning an ordered tuple of damaging tick records ;  one per applied rate tick whose modifier targets `hp` with a negative delta ;  each carrying the definition key, the buff cache's `source_pk` (or `None`), the delta, and the entity's HP immediately before that tick applied.

#### Scenario: Buff tick is invokable independently of any clock
- **WHEN** the buff-tick callable is invoked directly in a test, without any `WorldClock` or scheduler
  present
- **THEN** it applies exactly one tick's worth of each active buff's rate modifier (e.g. `poisoned`
  reduces `hp` by its configured per-tick delta once) and completes without requiring any other module
  to exist

#### Scenario: No settlement-order policy is encoded in this change's modules
- **WHEN** `world/rules/buffs.py` and `world/rules/combat_modifiers.py` are inspected
- **THEN** neither contains a reference to trait regen scheduling or sexual-state decay scheduling, and
  neither module imports or assumes the existence of `world/rules/sexual_state.py` or a `WorldClock`
  class

#### Scenario: A damaging tick returns one ordered record
- **WHEN** `tick_buffs(entity, 10)` fires both synthetic `t_poisoned` and `t_fire_scorch` in one call on a living entity
- **THEN** it returns two records in application order, each carrying the definition key, the buff cache's `source_pk` (or `None`), its configured rate delta (`-5` and `-8` respectively), and the entity's HP immediately before that tick applied

#### Scenario: Non-damaging ticks return no records
- **WHEN** `tick_buffs(entity)` fires only marker buffs or the conferred growth-rate buff
- **THEN** it returns an empty tuple and applies the rate modifier exactly as before

#### Scenario: No settlement order is invented by this change
- **WHEN** buff ticks coexist with trait regen and sexual-state decay
- **THEN** this change hardcodes, assumes, or invents no ordering between them ;  that fixed settlement order is design doc §6.5's and change 11's exclusive concern

#### Scenario: Ignoring the return value preserves old state behavior
- **WHEN** a caller ignores the returned tuple of damaging tick records
- **THEN** it observes identical state changes to the pre-change callable

#### Scenario: Authored tuning is distinct from mechanism examples
- **WHEN** tests exercise exact numerical band, delta, duration, bias or multiplier examples in this requirement
- **THEN** scoped fixed synthetic rulebook rows provide those numbers and independently known outcomes; production rows receive valid-shape/reference/intentional-invariant checks without a copied expected balance table

