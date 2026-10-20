# Spec Delta

## ADDED Requirements

### Requirement: Every elemental spell has its own action narration

Each ACTIVE elemental-magic skill SHALL declare its own authored action narration, in its
element's register and shaped by the spell's own form, and SHALL render that line as the
opening of its resolved action instead of the element-and-shape line. The catalog's
pending-family set SHALL no longer contain elemental magic.

#### Scenario: Two fire spells open differently

- **WHEN** two ACTIVE fire spells resolve against the same target under the same narration
  scope
- **THEN** each log's opening line comes from that spell's own row and the two lines differ

#### Scenario: An area spell addresses the field, not one body

- **WHEN** an ACTIVE area spell resolves against several targets
- **THEN** its opening line is rendered once for the whole cast and does not read as a
  single-target strike

#### Scenario: A newly added spell fails at import without a row

- **WHEN** an ACTIVE elemental-magic skill exists in the shipped registry with no authored
  narration row
- **THEN** catalog loading raises a named narration-catalog error naming that spell

#### Scenario: The pending-family set now names only sexual acts

- **WHEN** the catalog loads after this change
- **THEN** the declared pending-family set contains the sexual-act family alone and the
  pinning test asserts exactly that set
