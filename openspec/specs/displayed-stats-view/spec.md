## Purpose

Define the displayed-stats block: D2's appearance-rendering consumer — displayed combat values as
a direct player-facing view on `look <target>`.

## Requirements

### Requirement: display_stat_block renders the displayed combat five through the disguise accessor
`world/rules/displayed_stats.py` SHALL provide
`display_stat_block(entity, looker=None) -> str | None` that renders one
`label：value` row per key in the fixed order `atk_phys`, `agility`, `defense`,
`magic_level`, `hp`, every value read through `get_display_value()`. The labels SHALL be the
canonical Traditional Chinese trait labels used by the character panel (`生命` for `hp`, `攻擊` for
`atk_phys`, `敏捷` for `agility`, `防禦` for `defense`, `魔法階級` for `magic_level`). The `hp` row
SHALL render the gauge's current value (the value the accessor returns), not a maximum. The
function SHALL return `None` for a non-living target (an object or a room) and SHALL omit — never
raise on — a missing or malformed trait row. The function SHALL be read-only: it SHALL NOT write
attributes, mutate traits, advance the clock, or record map knowledge.

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
  `disguised_stats = {"atk_phys": 60}` whose true `atk_phys` base is 88, true `agility` 92, true
  `defense` 90, true `magic_level` 250, and true `hp` current value 120 of 10000
- **THEN** the block contains exactly five rows in the order 攻擊, 敏捷, 防禦, 魔法階級, 生命; the
  攻擊 row shows 60; the 敏捷, 防禦, and 魔法階級 rows show 92, 90, and 250; and the 生命 row shows
  120

#### Scenario: A non-living target yields no block
- **WHEN** `display_stat_block(target)` is called on an object or a room
- **THEN** it returns `None` and no rows are rendered

#### Scenario: A missing trait row is omitted, not fatal
- **WHEN** `display_stat_block(entity)` is called on a living entity whose `hp` trait is missing or
  malformed while the other four keys are valid
- **THEN** the block renders the four valid rows and omits the 生命 row without raising

### Requirement: The disguise accessor tolerates a malformed disguise record
`get_display_value()` SHALL treat a `disguised_stats` value that is not a mapping (for example an
integer or a boolean) as "no disguise" and fall back to the true trait value, instead of raising.
The displayed-stats block SHALL therefore render true values for such entities.

#### Scenario: A non-mapping disguise record falls back to true values
- **WHEN** `get_display_value(entity, "atk_phys")` is called on an entity whose
  `entity.db.disguised_stats` is `42` (a non-mapping) and whose true `atk_phys` base is 88
- **THEN** it returns 88 and the displayed-stats block for that entity shows 88 for 攻擊

### Requirement: look <target> appends the displayed-stats block, room look never does
The shared target-appearance path used by the text `look` command (「看 <對象>」) SHALL append
`display_stat_block(target)` after the target's description and before any onboarding guidance when
the target is a living entity. Bare `look` (the room) SHALL append nothing. The onboarding
`at_look` arrival beat SHALL be unaffected: the block SHALL NOT change beat detection or progress.

#### Scenario: Text look at a living target includes the block
- **WHEN** a player uses 「看 <目標>」 on a present NPC, player character, or monster
- **THEN** the output contains the target's description followed by the displayed-stats block

#### Scenario: Text look at the room omits the block
- **WHEN** a player uses 「看」 with no argument
- **THEN** the room appearance is unchanged and contains no displayed-stats block

#### Scenario: The onboarding look beat still completes
- **WHEN** an onboarding actor at the South Gate uses 「看 衛兵」 while the arrival look beat is
  active
- **THEN** the look completes the beat as before and the displayed-stats block is present without
  altering the guidance text or beat progression

### Requirement: explore.look shows the identical displayed-stats block
The WebClient `explore.look` action's target detail SHALL route through the same shared
target-appearance path as the text command, so a `target_id` submission SHALL present the identical
description and displayed-stats block with no browser-side computation of any value. The action
SHALL NOT parse the block or the appearance text to infer state, SHALL NOT mutate traits, SHALL
publish no panel replacement beyond the ordinary narrative result, and SHALL leave the frozen
version-1 `exploration` panel payload untouched.

#### Scenario: WebClient target look carries the same block
- **WHEN** an actor submits `explore.look` with a present living target's `target_id`
- **THEN** the presented target appearance equals the text 「看」 output for the same target,
  including the displayed-stats block, and no value was computed in the browser

#### Scenario: WebClient room look carries no block
- **WHEN** an actor submits `explore.look` with the room marker
- **THEN** the room appearance contains no displayed-stats block, exactly as the text path

#### Scenario: WebClient look publishes no panel replacement
- **WHEN** an actor submits `explore.look` for a target or the room marker
- **THEN** no panel payload (including the `exploration` panel) is replaced and the block appears
  only in the narrative text result

### Requirement: The displayed-stats block never influences resolution
The block SHALL be presentation-only: no combat, action-resolution, targeting, dice, damage, guild,
quest, or shop code path SHALL read the block or change behavior based on its content, and the
`get_display_value` forbidden-caller boundary SHALL remain enforced by the existing regression
scan.

#### Scenario: The forbidden-caller boundary test stays green
- **WHEN** the disguise-boundary regression test scans the deterministic-core module paths for
  `get_display_value` or `disguised_stats`
- **THEN** it passes unchanged, with the displayed-stats block confined to the presentation layer
