## MODIFIED Requirements

### Requirement: roll_name maps sex to the given pool of a pack and composes the Chinese display name
`world/rules/namegen.py` SHALL expose `roll_name(pack_key: str, sex: str | None, rng: Random) -> str`
that looks up `NAME_PACK_REGISTRY[pack_key]` and selects the given pool by `sex`: `"female"` →
pool `"f"`, `"male"` → pool `"m"`, `"other"` → pool `"u"`, and an empty string, `None`, or any
value outside `SEX_VALUES` → a pool chosen randomly from `"m"`, `"f"`, `"u"` via `rng` (design D2:
unrecognised values are treated exactly like unspecified ones; this layer validates nothing).
It SHALL return
`compose_display_name(given, surname)` — the `given.zh‧surname.zh` composition owned by
`world/lore/names.py` — picking both parts from the selected pack via `rng`, and SHALL NOT define
its own separator constant or concatenate parts itself. The original-language `NamePart.text`
SHALL never appear in the returned name.

#### Scenario: female and male select the f and m pools
- **WHEN** `roll_name("fantasy-human", "female", rng)` and `roll_name("fantasy-human", "male", rng)`
  are called with a fixed-seed `Random`
- **THEN** each returned name's given component equals the `zh` of some part in the pack's `"f"`
  (respectively `"m"`) pool, and the full result matches the `given.zh‧surname.zh` form with the
  U+2027 separator

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
