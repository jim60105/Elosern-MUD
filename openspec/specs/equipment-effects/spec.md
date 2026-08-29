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

### Requirement: Attached buffs never carry gauge-ceiling modifiers
An `attached_buffs` entry SHALL NOT reference a buff whose modifiers include a `bounds` target over `hp`/`mp`/`sp`: gauge ceiling headroom is owned exclusively by the equipment-cap recompute, and an attached instance must never carry a gauge-ceiling modifier. Damage/regeneration `rate` modifiers remain permitted (the shipped `item_regen_light` regen is the canonical attached-buff precedent).

#### Scenario: A gauge-bounds attached buff fails the load
- **WHEN** an attached-buff reference resolves to a buff definition whose `bounds` modify `hp` (or any other gauge target)
- **THEN** the equipment-effect rulebook load fails with the named rulebook error

#### Scenario: A regen-rate attached buff is accepted
- **WHEN** `apothecary_beads` attaches `item_regen_light` (HP `rate`, no gauge bounds)
- **THEN** the rulebook loads and the attachment stays live

### Requirement: Equipment immunity predicate is pure and fail-closed
The equipment-effect capability SHALL expose one predicate returning the union of `immune` keys over the entity's currently worn equipment. It SHALL read stored state without materializing handlers, SHALL write nothing, and malformed equipment storage SHALL yield no immunities at all (fail-closed: broken storage never grants protection).

#### Scenario: Worn pendant grants poison immunity
- **WHEN** an actor wearing 淨化吊墜 is queried for immune buff keys
- **THEN** the result contains `poisoned` and nothing was written

#### Scenario: Malformed storage grants nothing
- **WHEN** the predicate runs against malformed equipment storage
- **THEN** it returns an empty set

### Requirement: Equipment adjustments render as deterministic prose
The capability SHALL provide one server-side formatter converting a registered item's rulebook entry into one deterministic 正體中文 summary: segments joined by 「｜」 in field-vocabulary declaration order, signed integers, percent fields as `±N%`, gauge fields as `<gauge>上限 ±N`, immunity keys rendered by their registered display names, and zero-valued fields omitted. Every number SHALL come from the rulebook; the formatter SHALL NOT recompute effective values.

#### Scenario: Heavy armor describes its trade-off verbatim
- **WHEN** the formatter renders 騎士全套板甲's entry (atk −2, defense +8, agility −10%, hp cap +15)
- **THEN** the output is exactly 「攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15」

#### Scenario: Immunity-only item
- **WHEN** the formatter renders 無懼胸針's entry (immune `fear` only)
- **THEN** the output contains only the immunity segment with the registered display name and no numeric segments

### Requirement: Rulebook fields stay inert until their owning change lands
Rulebook fields whose consumers arrive in later changes (combat/stat merge, immunity enforcement, attached-buff application, sexual-system integration, rule conditions, presentation) SHALL NOT be read by gameplay resolution before the change that owns the consumer. A rulebook value with no consumer yet SHALL NOT change any deterministic gameplay outcome.

#### Scenario: Authored values cannot leak before their consumer exists
- **WHEN** two deviant rulebook copies differ only in dormant-only fields (for example `pleasure_gain` values) while the consuming changes have not landed
- **THEN** combat, act resolution, and buff application produce byte-for-byte identical results between the two copies, and no production module outside the validated loader and the change-authorized consumers imports the equipment-effect rulebook

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

### Requirement: Equipment adjustments reach every consumer through one accessor

The equipment-effect capability SHALL provide exactly one pure accessor that
converts the currently worn equipment into a combat adjustment bundle. No
consumer (combat resolution, estimation, preview, cost, resist scoring, or
presentation) SHALL reimplement or bypass that accessor, and no consumer
SHALL compute a parallel equipment formula.

#### Scenario: Single source of truth is enforced structurally

- **WHEN** the codebase is searched for equipment-rulebook reads outside the
  capability's loader, its accessor, and the change-authorized sync/read
  surfaces
- **THEN** no additional gameplay resolution path reads the rulebook
  directly

#### Scenario: Multiple worn items stack additively

- **WHEN** an actor wears a weapon granting `atk_phys +3`, armor granting
  `agility −10%`, and an accessory granting `defense +4`
- **THEN** the accessor returns one bundle containing exactly the additive
  sum of those three items' contributions

### Requirement: Effective exposure is a pure clamped read-time overlay

The equipment-effect capability SHALL expose one accessor returning the
entity's effective exposure: the stored `EXPOSURE_LEVELS` ordinal shifted by
the summed `exposure_bias` of worn equipment, clamped to the vocabulary
bounds. It SHALL read the stored level through one neutral shared reader
(that imports no rules modules), SHALL write nothing, SHALL materialize no
handlers, and malformed equipment storage SHALL contribute zero bias. The
capability SHALL also expose one pure summed `pleasure_gain` accessor over
worn equipment with the same purity contract and a malformed-yields-zero
rule.

#### Scenario: Vestments lift a nun's exposure two bands

- **WHEN** an actor with stored exposure 中等 wears 聖女聖袍 (bias +2)
- **THEN** effective exposure is 極高 and the stored trait is untouched

#### Scenario: Bias clamps at both vocabulary ends

- **WHEN** effective exposure is computed for stored 極高 with bias +2, and
  for stored 極低 with a negative-sum hypothetical
- **THEN** the results clamp to 極高 and 極低 respectively without error

#### Scenario: Malformed storage contributes no bias

- **WHEN** the accessor runs against malformed equipment storage
- **THEN** it returns exactly the stored exposure level
