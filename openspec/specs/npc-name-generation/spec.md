# npc-name-generation Specification

## Purpose

Define the deterministic rules-layer name rollers over the frozen name corpus —
`world/rules/namegen.py` — where every random decision flows through a
caller-injected `Random` so consumers own their replay strategy: the sex→pool
mapping and Chinese display-name composition, race resolution through
`NAME_PACK_BY_RACE` with a bound-packs-only random fallback, and the error
semantics (verbatim `KeyError`, empty-pool full-given fallback) that keep the
generator never dying.

## Requirements

### Requirement: roll_name maps sex to the given pool of a pack and composes the Chinese display name
`world/rules/namegen.py` SHALL expose `roll_name(pack_key: str, sex: str | None, rng: Random) -> str`
that looks up `NAME_PACK_REGISTRY[pack_key]` and selects the given pool by `sex`: `"female"` →
pool `"f"`, `"male"` → pool `"m"`, `"other"` → pool `"u"`, and an empty string, `None`, or any
value outside `SEX_VALUES` → a pool chosen randomly from `"m"`, `"f"`, `"u"` via `rng` (design D2:
unrecognised values are treated exactly like unspecified ones; this layer validates nothing).
It SHALL return
`compose_display_name(given, surname)` — the `given.zh・surname.zh` composition owned by
`world/lore/names.py` — picking both parts from the selected pack via `rng`, and SHALL NOT define
its own separator constant or concatenate parts itself. The original-language `NamePart.text`
SHALL never appear in the returned name.

#### Scenario: female and male select the f and m pools
- **WHEN** `roll_name("fantasy-human", "female", rng)` and `roll_name("fantasy-human", "male", rng)`
  are called with a fixed-seed `Random`
- **THEN** each returned name's given component equals the `zh` of some part in the pack's `"f"`
  (respectively `"m"`) pool, and the full result matches the `given.zh・surname.zh` form with the
  U+30FB separator

#### Scenario: other prefers the u pool and empty, None, or unrecognised values pick a pool at random
- **WHEN** `roll_name` is called with `sex` `"other"`, and separately with `""`, `None`, and a
  value outside `SEX_VALUES` such as `"unspecified"`
- **THEN** the `"other"` call always draws its given part from the pack's `"u"` pool, and the
  other calls draw from one of the three pools according to `rng` — the random pool selection
  offers the pool candidates `("m", "f", "u")` to `rng` exactly once per call, reproducibly for
  the same seed

#### Scenario: Composed output is Chinese renderings only
- **WHEN** `roll_name` returns a name for any pack and any sex value
- **THEN** the result consists solely of `zh` fields joined by `NAME_SEPARATOR` and contains no
  part's `text` value as a substring

### Requirement: roll_name_for_race resolves via NAME_PACK_BY_RACE with a bound-packs-only random fallback
`world/rules/namegen.py` SHALL expose `roll_name_for_race(race_key: str | None, sex: str | None,
rng: Random) -> str` that resolves the pack through `NAME_PACK_BY_RACE` when `race_key` names a
bound race, delegating to the same rolling logic as `roll_name`. When `race_key` is `None` or has
no mapping, it SHALL choose uniformly at random via `rng` among the packs that appear as values of
`NAME_PACK_BY_RACE` (the race-bound packs), so `fantasy-dwarf` and `fantasy-halfling` — registered
with `race_key=None` — never participate in the random fallback.

#### Scenario: Bound races roll from their mapped pack
- **WHEN** `roll_name_for_race` is called with `"human"`, `"elf"`, or `"beastfolk"`
- **THEN** the given and surname components of the result come from the pools of the pack mapped
  to that race in `NAME_PACK_BY_RACE` (`fantasy-human`, `fantasy-elf`, `fantasy-orc` respectively)

#### Scenario: Unbound or missing race falls back to a random bound pack
- **WHEN** `roll_name_for_race` is called with `None`, an unknown race key such as `"dragonborn"`,
  or any key absent from `NAME_PACK_BY_RACE`
- **THEN** the result comes from one of the race-bound packs, chosen reproducibly via `rng`, and
  across the full seed space never comes from `fantasy-dwarf` or `fantasy-halfling`. The fallback
  SHALL offer `rng` exactly the sorted distinct values of `NAME_PACK_BY_RACE` as the choice
  candidates, so every bound pack is selectable and the choice index is decoupled from the
  mapping's literal insertion order.

### Requirement: Unknown pack keys raise KeyError and empty filtered pools fall back to the full given pool
`roll_name` SHALL propagate `KeyError` unchanged when `pack_key` is not a key of
`NAME_PACK_REGISTRY` — callers pass program constants and the generator MUST NOT swallow or
substitute. When the sex-selected pool is empty, the roller SHALL fall back to the concatenation of
that pack's three given pools (`"m"` ＋ `"f"` ＋ `"u"`) so the generator never dies; the surname
pool is not sex-filtered and needs no fallback. The empty-pool semantics SHALL be testable against
synthetic `NamePack` values without mutating the frozen registry.

#### Scenario: Unknown pack key raises KeyError
- **WHEN** `roll_name("fantasy-dragonkin", "female", rng)` is called
- **THEN** a `KeyError` naming the unknown pack key propagates to the caller and no name is returned

#### Scenario: Empty filtered pool falls back to the pack's full given pool
- **WHEN** the rolling core is given a synthetic pack whose `"u"` pool is empty and `sex` is
  `"other"`
- **THEN** the given part is drawn from the union of the pack's remaining non-empty given pools
  and the call returns a composed name instead of raising

### Requirement: Rolling is a pure function of the injected rng for replayability
`world/rules/namegen.py` SHALL be a pure-logic module with no database access, no Evennia imports,
and no module-level or global RNG: every random decision (pool selection for unspecified sex, pack
selection for the race fallback, given and surname draws) MUST be made through the caller-injected
`rng: Random` argument. Two identical calls with `Random` instances seeded identically SHALL return
the same name, which is how the consuming changes obtain their replay guarantees — the character
creation dice injects an unseeded module-level `Random()` (names enter the payload like typed
input), while the NPC flow injects `Random(zlib.crc32(f"{definition.key}:{stage}:{role}".encode()))`
so blueprint rebuilds yield the same NPC name. Neither strategy lives in this module.

#### Scenario: Fixed seed replays identical names
- **WHEN** `roll_name` and `roll_name_for_race` are each called twice through freshly constructed
  `Random(42)` instances
- **THEN** every corresponding pair of calls returns the identical composed name

#### Scenario: The module holds no RNG state of its own
- **WHEN** `world.rules.namegen` is inspected
- **THEN** it constructs no `Random` instance at import or call time, never calls module-level
  `random.choice`-style functions, and its only randomness source is the `rng` parameter
