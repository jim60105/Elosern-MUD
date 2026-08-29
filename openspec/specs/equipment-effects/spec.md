## Purpose

Closed-vocabulary, budget-validated equipment-effect rulebook with a total one-to-one binding between registered equipment items and rulebook entries, kept inert until each field's owning consumer change lands.

## Requirements

### Requirement: Equipment items bind one-to-one to a closed effect identity
Every registered item that declares an `EquipmentSlot` SHALL also declare exactly one `EquipmentModifierKey` from the closed registry vocabulary, and every `EquipmentModifierKey` SHALL be bound by at most one registered item. Items without an equipment slot SHALL NOT declare a modifier key. A one-to-one binding SHALL be total in both directions: every registered equipment key SHALL have exactly one entry in the equipment-effect rulebook, and every rulebook entry SHALL name exactly one registered equipment key. Registry construction or rulebook loading SHALL fail on any unbound key, orphaned entry, or duplicated binding.

#### Scenario: Equipment without an effect binding fails validation
- **WHEN** an equipment-slot item definition carries no registered modifier key, or the rulebook lacks the entry for a registered equipment key
- **THEN** validation fails at registry construction or rulebook load and the game never starts with a partially bound roster

#### Scenario: Non-equipment items reject effect keys
- **WHEN** a usable-item or inspect-only item definition declares an `EquipmentModifierKey`
- **THEN** registry construction fails before the item can be presented

#### Scenario: Duplicate modifier bindings fail the load
- **WHEN** two registered equipment definitions declare the same modifier key, or two equipment definitions otherwise collapse to one rulebook entry
- **THEN** the equipment-effect rulebook load fails on the triple bijection (equipment key ↔ modifier key ↔ entry)

#### Scenario: Utility equipment declares an explicit empty binding
- **WHEN** a registered accessory exists purely for utility (for example `storage_pouch`)
- **THEN** it is bound to a rulebook entry with an explicitly empty effect set rather than exempted from the bijection

### Requirement: The equipment-effect rulebook validates a closed schema at load time
The equipment-effect rulebook SHALL be loaded through one validated loader that is idempotent on reload and accepts a path override for tests. Each entry SHALL contain only the closed vocabulary: `adjustments` restricted to `atk_phys`, `defense`, `magic_level`, `agility` (signed integer or signed percent string), `mp_cost` and `sp_cost` (signed percent strings only), `pleasure_gain` and `heal_gain` (signed percent strings only); plus `gauge_caps` (positive integers over `hp`/`mp`/`sp`), `immune` and `attached_buffs` (lists of buff keys), and `exposure_bias` (signed integer). Malformed entries SHALL fail the load with a named error; the loader SHALL NOT repair, clamp, or silently drop deviating data.

#### Scenario: Out-of-vocabulary field is rejected
- **WHEN** a rulebook entry contains any field or adjustment key outside the closed vocabulary
- **THEN** the load raises the named rulebook error and nothing loads

#### Scenario: Percent-shaped fields reject flat values
- **WHEN** an `mp_cost` adjustment is authored as a flat integer or an `atk_phys` adjustment as a percent string
- **THEN** the load fails, keeping the flat/percent kinds unambiguous for later consumer changes

### Requirement: Per-rarity budgets mechanically bound every authored value
The rulebook SHALL carry a budgets table keyed by the item's registered rarity with separate ceilings for flat values, combat percents (`agility`, `mp_cost`, `sp_cost`), soft percents (`pleasure_gain`, `heal_gain`), `exposure_bias`, and positive-only `gauge_caps` (v1 discipline: every designed cap is positive and negative resource penalties belong to debuff bounds, not to gear). The loader SHALL reject any entry whose value exceeds the ceiling of its rarity's corresponding column (in absolute value). Rarity SHALL be consulted only at load time and SHALL NOT be read by any runtime resolution path.

#### Scenario: Over-budget equipment fails startup
- **WHEN** a common-rarity item's entry grants `+10 defense`
- **THEN** the load fails with the named rulebook error

#### Scenario: Negative trade-offs count against budgets
- **WHEN** a rare-rarity heavy-armor entry grants `agility: "-99%"`
- **THEN** the load fails on the percent-column ceiling

### Requirement: State-effect references resolve against the buff rulebook
Every `immune` and `attached_buffs` entry SHALL name a buff key defined in the buff rulebook, and a single entry SHALL NOT list the same buff key as both attached and immune. Unresolvable or self-contradictory references SHALL fail the load.

#### Scenario: Immunity naming an undefined buff fails the load
- **WHEN** an entry declares immunity to a key absent from the buff rulebook
- **THEN** the load fails with the named rulebook error

### Requirement: Rulebook fields stay inert until their owning change lands
Rulebook fields whose consumers arrive in later changes (combat/stat merge, immunity enforcement, attached-buff application, sexual-system integration, rule conditions, presentation) SHALL NOT be read by gameplay resolution before the change that owns the consumer. A rulebook value with no consumer yet SHALL NOT change any deterministic gameplay outcome.

#### Scenario: Authored values cannot leak before their consumer exists
- **WHEN** two deviant rulebook copies differ only in dormant-only fields (for example `pleasure_gain` or `immune` values) while the consuming changes have not landed
- **THEN** combat, act resolution, and buff application produce byte-for-byte identical results between the two copies, and no production module outside the validated loader imports the equipment-effect rulebook

### Requirement: The new equipment roster is registered and tradeable
The roster SHALL add the ten designed equipment items — 淨化吊墜, 無懼胸針, 騎士全套板甲, 藥師珠串, 大術師補綴長袍, 誘蠱蕾絲內衣, 迷情絲頸環, 修女聖袍, 光輝聖徽, 聖女聖袍 — each with a registry presentation identity, an existing price-table key, an effect binding, and a listing in the existing general store's offered keys.

#### Scenario: New items are purchasable and fully bound
- **WHEN** the general store is inspected after this change
- **THEN** each of the ten new item keys appears in the offered keys with a resolvable price entry and a budget-checked rulebook entry

### Requirement: Church-of-Light equipment obeys its canon doctrine
The named 光明教會 equipment set — `sister_vestments`, `radiant_holy_emblem`, `saintess_vestments`, and `pilgrim_medallion` — is governed by the Church's canon doctrine (坦露與歡愉為正向、光之治療與淨化): every member's rulebook entry SHALL carry non-negative `exposure_bias` and non-negative `pleasure_gain`, SHALL provide at least one of `heal_gain` or an immunity, and SHALL NOT carry chastity-style suppression (negative `pleasure_gain` or negative `exposure_bias`); ordinary combat trade-offs (negative `defense`, `atk_phys`, agility, etc.) remain permitted as the mechanical cost of holiness. A future registry-owned faith-identity tag is out of scope here; membership is this named set, and a new Church item enters by amending this requirement in the change that adds it.

#### Scenario: Doctrine coverage for the named Church set
- **WHEN** the rulebook entries of the four named Church keys are validated
- **THEN** each has non-negative `exposure_bias` and `pleasure_gain`, at least one of `heal_gain` or an immunity, and no suppression value

#### Scenario: Doctrine violation blocks a named Church item
- **WHEN** a deviant rulebook copy gives a named Church item a negative `pleasure_gain`
- **THEN** the doctrine coverage test fails and the change cannot ship
