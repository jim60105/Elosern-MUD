## MODIFIED Requirements

### Requirement: Currency is an integer count of 銅 with no floats in the money path
`world/lore/economy.py` SHALL define `COPPER_PER_SILVER = 100` and `COPPER_PER_GOLD = 10000` as
integer constants, a `to_copper(gold: int = 0, silver: int = 0, copper: int = 0) -> int` helper
that returns an `int`, a frozen `PriceEntry` dataclass with integer `min_copper` and
`max_copper: int | None` fields, and a module-level `PRICE_TABLE: dict[str, PriceEntry]` covering
every purchasing-power reference in `world_info.md` (inn stay, meal, potion, plain sword, magic
weapon, commoner annual income, adventurer annual income) plus every band the lore item codex
assigns to a catalogued item, including the regional-delicacy band that separates named local
foods from an ordinary meal and the intimacy-device band shared by the codex's wearable and
usable 性玩具 entries.

#### Scenario: Conversion constants match the documented rate
- **WHEN** `to_copper(gold=1)`, `to_copper(silver=1)`, and `to_copper(copper=1)` are each called
- **THEN** they return `10000`, `100`, and `1` respectively, matching "1 金 = 100 銀 = 10000 銅"

#### Scenario: No float ever appears in a currency value
- **WHEN** `to_copper`'s return value and every `PriceEntry.min_copper` / `max_copper` (where not
  `None`) are inspected
- **THEN** every one of them is an `int`

#### Scenario: Price table entries never have max below min
- **WHEN** every `PriceEntry` with a non-`None` `max_copper` is inspected
- **THEN** `max_copper >= min_copper`

#### Scenario: Every band a catalogued item names exists
- **WHEN** every registered item's price-table key is resolved against `PRICE_TABLE`
- **THEN** each one resolves to a `PriceEntry`, with no catalogued item naming an absent band

#### Scenario: One band spans both intimacy-device shapes
- **WHEN** the codex's wearable and usable 性玩具 reference prices are checked against the intimacy-device band
- **THEN** every one of them lies inside that single band, so the category's two mechanical shapes never need separate bands
