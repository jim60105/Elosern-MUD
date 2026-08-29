## MODIFIED Requirements

### Requirement: display_stat_block renders the displayed combat five through the disguise accessor
`world/rules/displayed_stats.py` SHALL provide
`display_stat_block(entity, looker=None) -> str | None` that renders one
`label：value` row per key in the fixed order `atk_phys`, `agility`,
`defense`, `magic_level`, `hp`, every value read through
`get_display_value()`. The labels SHALL be the canonical Traditional
Chinese trait labels used by the character panel (`生命` for `hp`, `攻擊`
for `atk_phys`, `敏捷` for `agility`, `防禦` for `defense`, `魔法階級` for
`magic_level`). The `hp` row SHALL render the gauge's current value (the
value the accessor returns), not a maximum. The function SHALL return
`None` for a non-living target (an object or a room) and SHALL omit —
never raise on — a missing or malformed trait row. The function SHALL be
read-only: it SHALL NOT write attributes, mutate traits, advance the
clock, or record map knowledge.

When `looker` is the observing entity itself (a self-look), the block
SHALL instead render the character-breakdown-view rows server-side in
Traditional Chinese: one row per panel stat in the fixed panel order,
showing the total-display value and, for named-source contributions, the
layer segments `（來源 ＋8｜來源 ×1.1｜來源 −10%）` produced from the same
single breakdown assembly that feeds the character panel — never a second
computation path. Every non-self observation (`looker` absent or a
different entity) SHALL render the five-row third-party block exactly as
before.

#### Scenario: Third-party rows are unchanged
- **WHEN** `display_stat_block(entity, looker=observer)` is called with an
  observer that is not the entity
- **THEN** the block is byte-identical to the previous five-row output,
  including for a disguised entity

#### Scenario: A self-look shows the breakdown rows
- **WHEN** a player self-looks while wearing 騎士全套板甲
- **THEN** the block prints the eight panel stat rows with their totals
  and the named source segments, matching the character panel's effective
  values from the same read

#### Scenario: A disguised living entity shows disguised values in fixed order
- **WHEN** `display_stat_block(entity)` is called on a living entity with
  `disguised_stats = {"atk_phys": 60}` whose true `atk_phys` base is 88,
  true `agility` 92, true `defense` 90, true `magic_level` 250, and true
  `hp` current value 120 of 10000
- **THEN** the block contains exactly five rows in the order 攻擊, 敏捷,
  防禦, 魔法階級, 生命; the 攻擊 row shows 60; the 敏捷, 防禦, and
  魔法階級 rows show 92, 90, and 250; and the 生命 row shows 120

#### Scenario: A non-living target yields no block
- **WHEN** `display_stat_block(target)` is called on an object or a room
- **THEN** it returns `None` and no rows are rendered

#### Scenario: A missing trait row is omitted, not fatal
- **WHEN** `display_stat_block(entity)` is called on a living entity whose
  `hp` trait is missing or malformed while the other four keys are valid
- **THEN** the block renders the four valid rows and omits the 生命 row
  without raising
