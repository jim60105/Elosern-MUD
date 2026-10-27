# Spec Delta

## MODIFIED Requirements

### Requirement: WILDERNESS_REGION_REGISTRY covers the authored terrain regions
Game terrain views SHALL expose immutable schema-valid region values loaded from the continent source, with every classifier result resolving to a declared region.

#### Scenario: Complete region references
- **WHEN** a synthetic continent classifier returns a missing region or a region lacks required typed prose
- **THEN** the candidate is rejected before replacing published terrain values

#### Scenario: Round-trip derived view
- **WHEN** a supported region document is loaded twice and mirrored by lore synchronization
- **THEN** both reads are immutable and synchronization remains idempotent

#### Scenario: The registry covers the declared regions without duplicate names
- **WHEN** a synthetic continent supplies region declarations and classifier references
- **THEN** every classifier target resolves, identities/display names satisfy the existing uniqueness rule and duplicate declarations reject

#### Scenario: Every region carries at least two description variants
- **WHEN** a region has fewer than two typed nonblank description variants
- **THEN** authoring validation rejects that region rather than coercing or fabricating prose

### Requirement: terrain_description is a pure, deterministic function with no LLM or randomness
`world/maps/wilderness_provider.py` SHALL define `terrain_description(x: int, y: int) -> str`,
selecting one of `region_for_coordinates(x, y)`'s region's declared `terrain_flavor_zh` variants via
the fixed arithmetic formula `index = (x * 92821 + y * 68917) % len(variants)` over `(x, y)` alone.
The function SHALL call no LLM client, no random-number generator, and no wall-clock read, satisfying
the design doc's offline-playability criterion. The formula's constants are part of this
requirement's contract; the authored prose itself is a source-document declaration, so the checks
pin the selection mechanism and its agreement with the loaded region, never a copied literal string.

#### Scenario: Same coordinates always produce the same description
- **WHEN** `terrain_description(x, y)` is called twice with the same `(x, y)`
- **THEN** both calls return the identical string, including across separate process invocations
  (same input, same output, with no persisted state required to reproduce it)

#### Scenario: The description matches the coordinate's region and the fixed formula
- **WHEN** `terrain_description(x, y)` is called for sampled coordinates after a reload
- **THEN** the returned string is the published region view's own variant at index
  `(x * 92821 + y * 68917) % len(variants)`, so both the region resolution and the selection
  mechanism follow the loaded source rather than an old registry

#### Scenario: No LLM or network dependency exists in the call path
- **WHEN** `world/maps/wilderness_provider.py` is inspected for imports and calls
- **THEN** it references no module under `world/ai/`, no HTTP client, and no `random` module call

### Requirement: The published terrain regions are mirrored into LoreRecord Scripts idempotently
`world/lore/sync.py::sync_all()` SHALL mirror the published geography's composed region views under
the category key `"wilderness_regions"`, so the mirror follows the loaded continent source exactly as
it follows every other lore registry, including idempotency across repeated calls.

#### Scenario: sync_all mirrors wilderness regions
- **WHEN** `sync_all()` runs after geography publication
- **THEN** a `LoreRecord` Script exists for each published region key, keyed
  `"lore:wilderness_regions:<key>"`, with `db.fields` matching the corresponding region view

#### Scenario: Repeated sync creates no duplicate region records
- **WHEN** `sync_all()` is called twice in succession
- **THEN** exactly one `LoreRecord` Script per published region key exists under the
  `"wilderness_regions"` category after the second call

