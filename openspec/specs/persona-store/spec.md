# persona-store Specification

## Purpose
Define the read-only `PersonaStore` handler that exposes an entity's verbatim persona record
(keyed retrieval and bounded prompt-block flattening) and its mount on `LivingEntity.persona`.
## Requirements
### Requirement: PersonaStore is a read-only handler over the verbatim persona record
`world/rules/persona.py` SHALL provide a `PersonaStore` class constructed from a `LivingEntity`
that reads the raw record from `entity.db.persona` and exposes keyed retrieval plus prompt-block
flattening. The handler SHALL have no write API, SHALL import no state-mutating module, and SHALL
never modify traits, attributes beyond the single persona record, or the world clock.

#### Scenario: The handler reads the verbatim record
- **WHEN** a `PersonaStore` is constructed for an entity whose `entity.db.persona` is a dict with
  the fields `personality`, `life_story`, and `habit`
- **THEN** the handler's retrieval returns those field values exactly as stored, with no
  transformation, addition, or removal of content

#### Scenario: Keyed retrieval follows a defined contract
- **WHEN** `get(field)` is called for a field that exists in the record
- **THEN** the handler returns that field's value verbatim (the raw stored value, whether text,
  number, or container); `get(field)` for a missing key, a non-mapping record, or a missing
  record SHALL return `None` and never raise

#### Scenario: The handler has no write surface
- **WHEN** the public surface of `PersonaStore` is inspected
- **THEN** it contains no method that assigns `entity.db.persona`, traits, or any other persistent
  attribute, and the module's source contains no import of a state-mutating module

### Requirement: Flatten produces one bounded, labeled prompt block
`PersonaStore.flatten(fields=("personality", "life_story", "habit"))` SHALL return a single string
with one labeled section per present field in the declared field order (e.g. 性格：… /
人生經歷：… / 習慣：…), each field string capped and the combined block capped at a total bound.
A missing record, a non-mapping record, or a record with none of the requested fields present
SHALL return `None` and never raise.

#### Scenario: Three present fields flatten in declared order with labels
- **WHEN** a record contains all three fields and `flatten()` is called with the default fields
- **THEN** the result is one string containing exactly three labeled sections in the order
  `personality`, `life_story`, `habit`, each label prefix present once

#### Scenario: Absent fields are omitted
- **WHEN** a record contains only `personality` and `habit`
- **THEN** the flattened block contains exactly two labeled sections and no placeholder or empty
  section for `life_story`

#### Scenario: Non-string fields are treated as absent
- **WHEN** a record field such as `habit` is `None`, a number, or a container rather than text
- **THEN** that field produces no section and no exception is raised; only non-empty string
  fields produce sections

#### Scenario: Missing or malformed records return None
- **WHEN** `flatten()` is called for an entity with no persona record, a non-mapping persona
  value, or a mapping with none of the requested fields
- **THEN** the result is `None` and no exception is raised

#### Scenario: Field and block caps are enforced deterministically
- **WHEN** a field string or the combined block exceeds the configured bounds
- **THEN** the result is truncated to the bound; the truncation is deterministic and never raises

### Requirement: LivingEntity.persona mounts the PersonaStore handler
`LivingEntity.persona` SHALL be a `lazy_property` returning a `PersonaStore` instance, replacing
the placeholder `AttributeProperty(default=None)`. Raw storage SHALL remain at `entity.db.persona`,
and `world/imports/loader.py` SHALL continue to write it verbatim without modification.

#### Scenario: The persona attribute returns a handler
- **WHEN** a freshly created `LivingEntity` (or any subclass) is inspected
- **THEN** `entity.persona` is a `PersonaStore` instance backed by the `entity.db.persona` record

#### Scenario: The loader storage path is unchanged
- **WHEN** a validated import record's persona is stored
- **THEN** it lands verbatim at `entity.db.persona` through the existing loader code, with no
  change to `world/imports/loader.py`

#### Scenario: An entity without persona behaves like the former placeholder
- **WHEN** a freshly created character without any persona record calls `flatten()`
- **THEN** the result is `None` and no game behavior differs from the pre-change state
