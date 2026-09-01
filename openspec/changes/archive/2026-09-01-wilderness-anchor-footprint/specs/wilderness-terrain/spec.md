# Delta: wilderness-terrain (wilderness-anchor-footprint)

## MODIFIED Requirements

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

#### Scenario: capital_altoria's derived anchor cells resolve to Altoria's own territory
- **WHEN** `region_for_coordinates` is called with the `"capital_altoria"` entry's derived
  `anchor_cell` `(60, 100)` and with every gate's derived `approach_cell` (`(60, 97)` and
  `(60, 103)`)
- **THEN** every call returns `"western_hills_valleys"`, matching `world/lore/nations.py`'s own
  statement that Altoria's territory is "西部丘陵、谷地與西南海岸"

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
- **WHEN** `terrain_description(60, 103)` is called (`capital_altoria`'s north-gate approach cell —
  the wilderness-side landing of the 北門 gate under the footprint registry — which
  `region_for_coordinates` resolves to `"western_hills_valleys"`)
- **THEN** it returns exactly `"谷地間河流蜿蜒，兩岸散落著手工業者的作坊與磨坊。"` — the literal second
  (index `1`) entry of `WILDERNESS_REGION_REGISTRY["western_hills_valleys"].terrain_flavor_zh`, per
  `(60 * 92821 + 103 * 68917) % 3 == 1`. A reimplementation using different formula constants or
  reworded flavor text — either of which would still satisfy every other scenario in this
  requirement — SHALL fail this scenario, which is the point: it is what pins the formula and the
  registry text together against silent drift, the same concern that ruled out a `hash()`-based
  formula in this capability's own design rationale

#### Scenario: No LLM or network dependency exists in the call path
- **WHEN** `world/maps/wilderness_provider.py` is inspected for imports and calls
- **THEN** it references no module under `world/ai/`, no HTTP client, and no `random` module call
