## MODIFIED Requirements

### Requirement: Key charset is checked at import validation

The import validator SHALL apply the entity-key character-set and length rules as structural checks shared with the schema, so no key that could corrupt downstream `|`-delimited effect serialization reaches the loader. The validator SHALL additionally reject digit-only keys through the shared reservation predicate (`is_reserved_player_stable_key`, hosted in `world/art/subjects.py`), mirroring the schema pattern: the digit-only region of the character-portrait keyspace is reserved for player characters, so an imported entity key can never collide with a player's `str(pk)` portrait stable key.

#### Scenario: Separator key is a structural issue

- **WHEN** any record's key contains a structural separator
- **THEN** the record is flagged as a structural issue and excluded from instantiation

#### Scenario: A digit-only key is a structural issue

- **WHEN** a character or world-entry record's key consists only of ASCII digits
- **THEN** the record is flagged with a rejection naming the reserved digit-only region and excluded from instantiation, so the loader never creates an entity whose portrait stable key could equal a player's pk
