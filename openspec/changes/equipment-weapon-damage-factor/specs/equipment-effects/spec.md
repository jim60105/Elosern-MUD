# Spec Delta

## MODIFIED Requirements

### Requirement: The equipment-effect rulebook validates a closed schema at load time
The equipment-effect rulebook SHALL be loaded through one validated loader that is idempotent on reload and accepts a path override for tests. Each entry SHALL contain only the closed vocabulary enumerated below. Malformed entries SHALL fail the load with a named error; the loader SHALL NOT repair, clamp, or silently drop deviating data.

#### Scenario: Out-of-vocabulary field is rejected
- **WHEN** a rulebook entry contains any field or adjustment key outside the closed vocabulary
- **THEN** the load raises the named rulebook error and nothing loads

#### Scenario: The closed entry vocabulary
- **WHEN** a rulebook entry is validated
- **THEN** it may contain only `adjustments` restricted to `atk_phys`, `defense`, `magic_power`, `agility`, `mp_cost`, `sp_cost`, `pleasure_gain`, and `heal_gain`; plus `gauge_caps`, `immune`, `attached_buffs`, `exposure_bias`, and optional weapon-only `weapon_damage_multiplier`

#### Scenario: Percent-shaped fields reject flat values
- **WHEN** an `mp_cost` adjustment is authored as a flat integer or an `atk_phys` adjustment as a percent string
- **THEN** the load fails, keeping the flat/percent kinds unambiguous for later consumer changes

#### Scenario: Adjustment fields accept only signed integers or signed percent strings
- **WHEN** an `atk_phys`, `defense`, `magic_power`, or `agility` adjustment carries any other value shape
- **THEN** the load fails with the named rulebook error

#### Scenario: Percent-only fields accept signed percent strings only
- **WHEN** an `mp_cost`, `sp_cost`, `pleasure_gain`, or `heal_gain` adjustment carries any value shape other than a signed percent string
- **THEN** the load fails with the named rulebook error

#### Scenario: Gauge caps are positive integers over the gauge vocabulary
- **WHEN** `gauge_caps` names a gauge outside `hp`/`mp`/`sp` or carries a value that is not a positive integer
- **THEN** the load fails with the named rulebook error

#### Scenario: Buff lists and exposure bias are typed
- **WHEN** `immune` or `attached_buffs` is not a list of buff keys, or `exposure_bias` is not a signed integer
- **THEN** the load fails with the named rulebook error

### Requirement: Per-rarity budgets mechanically bound every authored value
The rulebook SHALL carry a budgets table keyed by the item's registered rarity with separate ceilings for flat values, combat percents (`agility`, `mp_cost`, `sp_cost`), soft percents (`pleasure_gain`, `heal_gain`), `exposure_bias`, and positive-only `gauge_caps`, and a finite `weapon_multiplier` ceiling of at least 1.0. The loader SHALL reject any entry whose value exceeds the ceiling of its rarity's corresponding column (in absolute value for signed adjustments; directly for weapon multipliers).

#### Scenario: Over-budget equipment fails startup
- **WHEN** a common-rarity item's entry grants `+10 defense`
- **THEN** the load fails with the named rulebook error

#### Scenario: Negative trade-offs count against budgets
- **WHEN** a rare-rarity heavy-armor entry grants `agility: "-99%"`
- **THEN** the load fails on the percent-column ceiling

#### Scenario: Gauge-cap ceilings follow the v1 positive-only discipline
- **WHEN** the `gauge_caps` budget column is authored
- **THEN** every designed cap is positive, because negative resource penalties belong to debuff bounds, not to gear

#### Scenario: Rarity is consulted only at load time
- **WHEN** any runtime resolution path runs
- **THEN** it never reads rarity; only the loader consults the budgets table

### Requirement: Equipment adjustments render as deterministic prose
The capability SHALL provide one server-side formatter converting a registered item's rulebook entry into one deterministic 正體中文 summary: segments joined by 「｜」 in field-vocabulary declaration order, signed integers, percent fields as `±N%`, gauge fields as `<gauge>上限 ±N`, immunity keys rendered by their registered display names, the authored weapon multiplier rendered as a multiplier segment in declaration order, and zero-valued adjustments or neutral 1.0 multipliers omitted. Every number SHALL come from the rulebook; the formatter SHALL NOT recompute effective values.

#### Scenario: Heavy armor describes its trade-off verbatim
- **WHEN** the formatter renders a synthetic armor entry (atk −2, defense +8, agility −10%, hp cap +15)
- **THEN** the output is exactly 「攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15」

#### Scenario: Immunity-only item
- **WHEN** the formatter renders 無懼胸針's entry (immune `fear` only)
- **THEN** the output contains only the immunity segment with the registered display name and no numeric segments

## ADDED Requirements

### Requirement: Weapon multiplier uses exactly one equipped weapon declaration
The weapon damage factor SHALL be a validated finite numeric declaration at least 1.0 and within its rarity ceiling. Runtime SHALL use the main-hand weapon, falling back to off-hand only when main-hand is empty, otherwise 1.0. Two factors SHALL NOT combine. Rarity SHALL be load-time validation only.

#### Scenario: Main and off hand precedence
- **WHEN** main hand has factor 1.5 and off hand factor 2.0
- **THEN** factor is 1.5; emptying main hand makes it 2.0; an occupied nonweapon main hand makes it 1.0

#### Scenario: Malformed declarations and no gear
- **WHEN** a factor is bool, nonfinite, below one, on nonweapon gear or over budget, or the actor has empty hands
- **THEN** invalid declarations reject load; empty hands and gear with no declared bonus use 1.0

#### Scenario: Existing gear semantics
- **WHEN** a dual-wielder has existing off-hand flats and passives
- **THEN** those adjustments retain their existing behavior and the selected factor is applied once


