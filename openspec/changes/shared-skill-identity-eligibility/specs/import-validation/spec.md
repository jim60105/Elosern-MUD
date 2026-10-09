# Spec Delta

## MODIFIED Requirements

### Requirement: Skill ownership requiring divine arts is rejected for a non-divine record
`validate.py` SHALL reject a character record whose `skills` or `passives` name a registry entry that
fails the shared actor-kind and authored race/subrace identity qualification, including a required
divine capability whose race is missing or incapable. The issue SHALL name the offending field and key, matching the shape of the
existing unknown-key issue for the same fields.

#### Scenario: A non-divine record owning a divine-arts skill is rejected
- **WHEN** a character record declares a race that cannot use divine arts and lists a divine-arts
  skill in `skills`
- **THEN** validation reports a rejection naming the field and the key, and the batch does not load

#### Scenario: The same rule applies to passives
- **WHEN** such a record lists a divine-arts skill in `passives` instead
- **THEN** validation reports the equivalent rejection

#### Scenario: A divine-capable record owning a divine-arts skill is accepted
- **WHEN** a character record declares a race that can use divine arts and lists a divine-arts skill
- **THEN** validation reports no issue for that entry

#### Scenario: A non-divine skill is unaffected
- **WHEN** a record on a non-divine race lists a registry skill that has no identity restriction
- **THEN** validation reports no issue for that entry

#### Scenario: The check degrades with the skill registry
- **WHEN** the skill registry is unavailable and the existing degraded-state reporting is in effect
- **THEN** the identity check reports nothing rather than rejecting, exactly as the unknown-key check
  does in the same state

#### Scenario: The rule mirrors the preset registry's load-time stance
- **WHEN** this rejection rule is designed against the authored-content paths
- **THEN** it mirrors the load-time stance the preset registry already takes for authored preset cards, so the two authored-content paths agree on what a bloodline permits

## ADDED Requirements

### Requirement: Imports validate complete closed kits against authored identity
Character import validation SHALL reject identity-ineligible active or passive ownership, including prerequisite closure additions, using authored intended actor kind and identity without entity construction. Registry-unavailable degraded reporting SHALL remain unchanged.

#### Scenario: Identity errors name authored fields
- **WHEN** a player or NPC record includes a monster-only skill, wrong subrace or incapable prerequisite
- **THEN** batch validation names the offending skills/passives field and key and persists no entity

