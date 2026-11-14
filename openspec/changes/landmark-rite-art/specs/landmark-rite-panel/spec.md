# Spec Delta

## ADDED Requirements

### Requirement: The rite panel carries the archetype's scene artwork
An available `rite` panel SHALL carry the artwork descriptor that the existing scene resolution produces for the landmark's archetype subject, and SHALL carry no artwork, while staying available, when that descriptor cannot be produced.

#### Scenario: Descriptor present
- **WHEN** the scene resolution returns a valid descriptor for the archetype's subject
- **THEN** the panel's artwork equals that descriptor and the panel passes its validator

#### Scenario: Descriptor unavailable
- **WHEN** the scene resolution raises
- **THEN** the panel is available with no artwork and one warning is logged
