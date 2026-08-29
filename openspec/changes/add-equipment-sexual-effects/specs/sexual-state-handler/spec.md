## ADDED Requirements

### Requirement: Equipment exposure bias never touches stored state

Equipment bias SHALL be an overlay at read time only: stored exposure
traits, act-driven transitions, transition rule matching, snapshots, and
persistence SHALL operate on the stored ordinal alone, and bias SHALL never
raise an exposure field-change event. Every player-facing read surface
(status read model and the status web payload alike) SHALL render the same
effective ordinal with unchanged row/payload schemas. Every shipped consumer
of stored exposure SHALL be classified (stored vs effective) in a structural
allowlist test, and a new raw consumer outside the allowlist SHALL fail it.

#### Scenario: Progression ignores what is worn

- **WHEN** an exposure-raising act resolves for an actor wearing a bias +2
  item and then the item is removed
- **THEN** the stored ordinal advanced exactly as with no equipment, no
  exposure field-change event was raised by equipping or unequipping, and
  effective exposure drops back to the stored value

#### Scenario: Status row and web payload agree on the effective band

- **WHEN** the status read model and the web status payload render an actor
  wearing bias-granting equipment
- **THEN** both show the same effective ordinal, schemas unchanged, while
  the stored trait remains as-is

#### Scenario: New raw consumer is rejected by the allowlist

- **WHEN** a new module reads the stored exposure trait outside the
  stored-classified allowlist
- **THEN** the structural test fails until it is classified
