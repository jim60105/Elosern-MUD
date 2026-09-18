## ADDED Requirements

### Requirement: The disguise layer records the provenance of the veil it holds
An entity carrying a disguise layer SHALL also carry a record of that veil's PROVENANCE: divine, when a
divine mystery wrote it at cast time, or mundane, for every other origin (an authored import record,
preset activation, or the companion builder). The provenance record SHALL be stored SEPARATELY from the
display mapping, so the mapping's key set, its import schema and every sanctioned reader are unchanged
and continue to see only trait-key overrides. An entity with no provenance record SHALL read as
mundane. Clearing the disguise layer SHALL clear its provenance in the same operation, and both SHALL
be restored together when a resolution is rolled back.

#### Scenario: A divine cast records divine provenance
- **WHEN** a divine mystery writes a veil onto an entity
- **THEN** that entity's veil reads as divine provenance, and its display mapping contains only
  trait-key overrides

#### Scenario: An authored declaration reads as mundane
- **WHEN** an entity is seeded with a disguise layer by an import record or preset activation, with no
  provenance record written
- **THEN** its veil reads as mundane provenance

#### Scenario: Clearing the veil clears its provenance
- **WHEN** an entity's disguise layer is cleared by any sanctioned path
- **THEN** no stale provenance record remains, and the entity reads as unveiled

#### Scenario: A rolled-back resolution restores both records together
- **WHEN** a resolution that wrote or cleared a veil has a later pending effect fail, restoring the
  action snapshot
- **THEN** both the display mapping and the provenance record are byte-equal to their pre-action values
