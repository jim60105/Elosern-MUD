## ADDED Requirements

### Requirement: The disguise layer has a provenance-scoped reveal primitive
A deterministic-core reveal primitive SHALL exist in the same module as the disguise write, clearing a
target's disguise layer and its provenance record only when the veil's provenance falls within the
strength the caller declares. It SHALL be reachable from a skill through a `reveal_disguise` effect
prefix whose handler declares the `traits` surface, with exactly two strengths: MUNDANE-ONLY, which
clears a mundane veil and leaves a divine veil untouched, and ANY-PROVENANCE, which clears a veil of
either provenance. A reveal that cannot pierce its target's veil SHALL be a reported no-op rather than
a rejection, so the attempt neither leaks the existence of the veil through a rejection reason nor
fails the action. The primitive SHALL NOT expose true trait values, identity, or persona; its only
effect is removing a veil.

#### Scenario: The mundane strength lifts an authored veil
- **WHEN** a mundane-only reveal resolves against a target whose veil reads as mundane provenance
- **THEN** the target's disguise layer and provenance record are cleared and `get_display_value`
  returns true values

#### Scenario: The mundane strength cannot pierce a divine veil
- **WHEN** a mundane-only reveal resolves against a target whose veil reads as divine provenance
- **THEN** the target stays veiled, no state changes, and the action completes as a reported no-op
  rather than a rejection

#### Scenario: The true-name strength pierces a divine veil
- **WHEN** an any-provenance reveal resolves against a target whose veil reads as divine provenance
- **THEN** the target's disguise layer and provenance record are cleared

#### Scenario: A reveal against an unveiled target is a clean no-op
- **WHEN** either strength resolves against a target carrying no disguise layer
- **THEN** the action completes without raising and changes no stored state

#### Scenario: A reveal never exposes anything but the veil's removal
- **WHEN** any reveal resolves
- **THEN** the only state it touches is the target's disguise layer and provenance record; no true
  trait value, identity field, or persona record is read or written
