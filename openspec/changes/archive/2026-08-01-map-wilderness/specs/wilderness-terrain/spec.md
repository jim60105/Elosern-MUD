## ADDED Requirements

### Requirement: WILDERNESS_REGION_REGISTRY covers exactly the seven world_info.md terrain regions
`world/lore/wilderness_regions.py` SHALL define a frozen `WildernessRegion` dataclass (`key`,
`display_name_zh`, `nation_key: str | None`, `terrain_flavor_zh: tuple[str, ...]` with at least two
entries) and a module-level `WILDERNESS_REGION_REGISTRY: dict[str, WildernessRegion]` containing
exactly seven entries, one per terrain region named in `world_info.md`'s geography section (中央山脈,
東部大平原, 東南海岸, 西部丘陵與谷地, 西南海岸, 西北高地森林, 北部深林).

#### Scenario: The registry has exactly seven entries
- **WHEN** `WILDERNESS_REGION_REGISTRY` is inspected
- **THEN** it contains exactly seven entries, and every entry's `display_name_zh` matches one of the
  seven terrain region names in `world_info.md`'s geography section, with no duplicates

#### Scenario: Every region carries at least two description variants
- **WHEN** every entry in `WILDERNESS_REGION_REGISTRY` is inspected
- **THEN** each entry's `terrain_flavor_zh` tuple has at least two elements

### Requirement: region_for_coordinates is a pure, deterministic function covering the whole bounded map
`world/maps/wilderness_provider.py` SHALL define `region_for_coordinates(x: int, y: int) -> str`,
returning a key that exists in `WILDERNESS_REGION_REGISTRY`, for every `(x, y)` pair within the
map's valid coordinate bounds. The function SHALL read no database state, no network state, and no
random or wall-clock input, and SHALL return the same value for the same input on every call.

#### Scenario: Same input always returns the same output
- **WHEN** `region_for_coordinates(x, y)` is called twice with the same `(x, y)` in the same process
- **THEN** both calls return the identical string

#### Scenario: Every region key is reachable
- **WHEN** `region_for_coordinates` is evaluated across the full valid coordinate range
- **THEN** every one of the seven keys in `WILDERNESS_REGION_REGISTRY` is returned by at least one
  coordinate

#### Scenario: The central mountain band spans the full valid Y range
- **WHEN** `region_for_coordinates(x, y)` is called with `x` inside the central mountain band and `y`
  at both the minimum and maximum valid values (excluding the northern deep-forest band, which is
  checked first)
- **THEN** both calls return `"central_mountains"`

#### Scenario: capital_altoria's registered wilderness entry point resolves to Altoria's own territory
- **WHEN** `region_for_coordinates` is called with `WILDERNESS_ENTRY_REGISTRY["capital_altoria"].
  wilderness_xy`
- **THEN** it returns `"western_hills_valleys"`, matching `world/lore/nations.py`'s own statement that
  Altoria's territory is "西部丘陵、谷地與西南海岸"

### Requirement: terrain_description is a pure, deterministic function with no LLM or randomness
`world/maps/wilderness_provider.py` SHALL define `terrain_description(x: int, y: int) -> str`,
selecting one of `region_for_coordinates(x, y)`'s region's `terrain_flavor_zh` variants via the fixed
arithmetic formula `index = (x * 92821 + y * 68917) % len(variants)` over `(x, y)` alone. The function
SHALL call no LLM client, no random-number generator, and no wall-clock read, satisfying the design
doc's offline-playability criterion. The formula's constants (`92821`, `68917`) and
`WILDERNESS_REGION_REGISTRY`'s exact `terrain_flavor_zh` text are both part of this requirement's
contract, not implementation detail left to the implementer's discretion — see the literal-pin
scenario below.

#### Scenario: Same coordinates always produce the same description
- **WHEN** `terrain_description(x, y)` is called twice with the same `(x, y)`
- **THEN** both calls return the identical string, including across separate process invocations
  (same input, same output, with no persisted state required to reproduce it)

#### Scenario: The description matches the coordinate's region
- **WHEN** `terrain_description(x, y)` is called
- **THEN** the returned string is one of `WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].
  terrain_flavor_zh`'s own variants

#### Scenario: A fixed coordinate produces a literal, spec-pinned string
- **WHEN** `terrain_description(60, 100)` is called (`capital_altoria`'s registered wilderness entry
  point, which `region_for_coordinates` resolves to `"western_hills_valleys"`)
- **THEN** it returns exactly `"谷地間河流蜿蜒，兩岸散落著手工業者的作坊與磨坊。"` — the literal second
  (index `1`) entry of `WILDERNESS_REGION_REGISTRY["western_hills_valleys"].terrain_flavor_zh`, per
  `(60 * 92821 + 100 * 68917) % 3 == 1`. A reimplementation using different formula constants or
  reworded flavor text — either of which would still satisfy every other scenario in this
  requirement — SHALL fail this scenario, which is the point: it is what pins the formula and the
  registry text together against silent drift, the same concern that ruled out a `hash()`-based
  formula in this capability's own design rationale

#### Scenario: No LLM or network dependency exists in the call path
- **WHEN** `world/maps/wilderness_provider.py` is inspected for imports and calls
- **THEN** it references no module under `world/ai/`, no HTTP client, and no `random` module call

### Requirement: WILDERNESS_REGION_REGISTRY is mirrored into LoreRecord Scripts idempotently
`world/lore/sync.py::_ALL_REGISTRIES` SHALL include `WILDERNESS_REGION_REGISTRY` under the category
key `"wilderness_regions"`, so `sync_all()` mirrors it into `LoreRecord` Scripts exactly as it mirrors
every other lore registry, including idempotency across repeated calls.

#### Scenario: sync_all mirrors wilderness regions
- **WHEN** `sync_all()` runs
- **THEN** a `LoreRecord` Script exists for each of the seven region keys, keyed
  `"lore:wilderness_regions:<key>"`, with `db.fields` matching the corresponding
  `WildernessRegion` entry

#### Scenario: Repeated sync creates no duplicate region records
- **WHEN** `sync_all()` is called twice in succession
- **THEN** exactly seven `LoreRecord` Scripts exist under the `"wilderness_regions"` category after
  the second call
