## ADDED Requirements

### Requirement: The disguise layer records whether the veil verb placed it
An entity carrying a disguise layer MAY also carry a PLACEMENT record: a boolean stating that the
veil verb itself wrote the layer during play. A present, true record means the verb placed the veil;
an ABSENT record means it did not, which covers every authored origin (an import record, preset
activation, or the companion builder) and any entity seeded before the record existed. There is no
false value to write and no third state.

The record SHALL answer exactly one question — may the veil verb lift the veil it is cast over — and
SHALL have exactly one reader, the verb's self-cast branch. No reveal path, display path, or
combat path SHALL read it. It SHALL NOT encode how strong a veil is: this world admits one grade of
veil, because only the bloodline-gated divine mystery can write one.

The record SHALL be stored SEPARATELY from the display mapping, so the mapping's key set, its import
schema and every sanctioned reader are unchanged and continue to see only trait-key overrides.
Clearing the disguise layer SHALL clear the placement record in the same operation, and both SHALL be
restored together when a resolution is rolled back.

#### Scenario: A cast veil records its placement
- **WHEN** the veil verb writes a veil onto an entity
- **THEN** that entity carries a true placement record, and its display mapping contains only
  trait-key overrides

#### Scenario: An authored declaration carries no placement record
- **WHEN** an entity is seeded with a disguise layer by an import record, preset activation, or the
  companion builder
- **THEN** it carries no placement record, and the veil reads as one the verb did not place

#### Scenario: A veil with no record is one the verb did not place
- **WHEN** an entity carries a disguise layer written before the placement record existed
- **THEN** it reads as a veil the verb did not place, with no migration required

#### Scenario: Clearing the veil clears its placement record
- **WHEN** an entity's disguise layer is cleared by any sanctioned path
- **THEN** no stale placement record remains, and the entity reads as unveiled

#### Scenario: A rolled-back resolution restores both records together
- **WHEN** a resolution that wrote or cleared a veil has a later pending effect fail, restoring the
  action snapshot
- **THEN** both the display mapping and the placement record are byte-equal to their pre-action
  values

#### Scenario: Nothing but the self-cast branch reads the record
- **WHEN** production source modules are scanned for the placement record's attribute name or its
  accessor
- **THEN** the only reader is the veil verb's self-cast branch, and no reveal, display, or combat
  module appears

## REMOVED Requirements

### Requirement: The disguise layer records the provenance of the veil it holds
**Reason**: The requirement describes a veil's PROVENANCE — divine or mundane — as a grade that
determines which reveal strength can pierce it. This change establishes that the world has exactly
one grade of veil, because only a bloodline-gated divine mystery can write one, and removes the
reveal strengths that consumed the distinction. What remains is a single yes/no question about
whether the veil verb placed the veil, which the replacement requirement states directly. A two-value
grade vocabulary kept for a one-grade world is what allowed one field to answer two questions and
produced the defect this change fixes.

**Migration**: None required for stored data — the project is pre-release, carries no saves across
builds, and an absent record already means the same thing under both requirements. In code,
`entity.db.disguise_provenance` becomes `entity.db.disguise_placed_by_cast`,
`disguise_provenance_of(entity) == DISGUISE_PROVENANCE_DIVINE` becomes `was_cast_placed(entity)`, and
`record_disguise_provenance(entity, DISGUISE_PROVENANCE_DIVINE)` becomes
`record_cast_placement(entity)`. The `DISGUISE_PROVENANCE_DIVINE` and `DISGUISE_PROVENANCE_MUNDANE`
constants are deleted; no caller may compare against a provenance value afterwards.
