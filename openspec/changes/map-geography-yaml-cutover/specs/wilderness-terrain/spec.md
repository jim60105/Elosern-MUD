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

### Requirement: region_for_coordinates is a pure, deterministic function covering the whole bounded map
`world/maps/wilderness_provider.py` SHALL define `region_for_coordinates(x: int, y: int) -> str`,
returning a key that exists in the published region views, for every `(x, y)` pair within the
map's valid coordinate bounds. The function SHALL read the published snapshot's explicit terrain
definition, no database state, no network state, and no random or wall-clock input, and SHALL
return the same value for the same input on every call.

#### Scenario: Same input always returns the same output
- **WHEN** `region_for_coordinates(x, y)` is called twice with the same `(x, y)` in the same process
- **THEN** both calls return the identical string

#### Scenario: Every region key is reachable
- **WHEN** `region_for_coordinates` is evaluated across the full valid coordinate range
- **THEN** every declared region key is returned by at least one coordinate

#### Scenario: The central mountain band spans the full valid Y range
- **WHEN** `region_for_coordinates(x, y)` is evaluated around the declared corridor's X band below
  the northern forest
- **THEN** the mountain region follows the authored bending corridor (its centre shifts per row)
  instead of a fixed rectangular band, and it is never a continuous summit wall: the closed ridge
  is a one-cell cliff wall broken only at the authored passes

#### Scenario: capital_altoria's derived anchor cells resolve to Altoria's own territory
- **WHEN** `region_for_coordinates` is called with `capital_altoria`'s declared cell and with every
  gate's derived `approach_cell`
- **THEN** every call returns `"western_hills_valleys"`, matching `world/lore/nations.py`'s own
  statement that Altoria's territory is "西部丘陵、谷地與西南海岸"

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

#### Scenario: The description matches the coordinate's region
- **WHEN** `terrain_description(x, y)` is called
- **THEN** the returned string is one of the published region view's own `terrain_flavor_zh`
  variants at index `(x * 92821 + y * 68917) % len(variants)`, and that region is
  `region_for_coordinates(x, y)`

#### Scenario: A fixed coordinate produces a literal, spec-pinned string
- **WHEN** `terrain_description(860, 1080)` is called (the `capital_altoria` anchor cell, which
  `region_for_coordinates` resolves to `"western_hills_valleys"`)
- **THEN** the fixed formula selects index `2` of that region's declared variants; the literal prose
  is the continent source's own declaration, preserved by the conversion comparison rather than
  copied into a second approval table

#### Scenario: The constants and flavor text are contract, not discretion
- **WHEN** the formula's constants (`92821`, `68917`) and the continent source's
  `terrain_flavor_zh` text are weighed
- **THEN** the formula constants remain this requirement's contract, and the prose remains the
  authored source contract validated by schema, never an implementation or test-side copy

#### Scenario: No LLM or network dependency exists in the call path
- **WHEN** `world/maps/wilderness_provider.py` is inspected for imports and calls
- **THEN** it references no module under `world/ai/`, no HTTP client, and no `random` module call

### Requirement: WILDERNESS_REGION_REGISTRY is mirrored into LoreRecord Scripts idempotently
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

