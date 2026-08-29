## ADDED Requirements

### Requirement: Equipment-worn condition values are referentially validated at load

The combat-modifier rulebook SHALL preflight every `equipment_worn`
condition at its own load site, before any rule matching or startup
mirroring: the value must be a string naming an `ITEM_REGISTRY` member that
carries an equipment slot. Unknown keys, consumable/non-slot items, and
non-string values SHALL fail loading with an identifying error; the shared
evaluator SHALL additionally raise `ValueError` on a non-string value
rather than silently mis-matching, and a condition context that lacks the
worn-item fact SHALL fail the condition closed.

#### Scenario: Typo in a grace rule fails the preflight

- **WHEN** a combat-modifier rule declares `equipment_worn:
  sister_vestmenst`
- **THEN** the combat rulebook preflight rejects it with an identifying
  error before any matching occurs

#### Scenario: Non-slot item rejected

- **WHEN** a rule declares `equipment_worn` naming a consumable item key
- **THEN** loading fails

#### Scenario: Direct evaluator misuse raises

- **WHEN** `evaluate_condition` is called directly with a non-string
  `equipment_worn` value
- **THEN** it raises `ValueError` instead of returning a match result

#### Scenario: Valid authored grace rules load

- **WHEN** the shipped rulebook with the four authored grace rules loads at
  startup
- **THEN** preflight passes and the rules are queryable through the
  matcher
