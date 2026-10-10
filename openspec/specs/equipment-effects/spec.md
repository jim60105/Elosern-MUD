## Purpose

Closed-vocabulary, budget-validated equipment-effect rulebook with a total one-to-one binding between registered equipment items and rulebook entries, kept inert until each field's owning consumer change lands.

## Requirements

### Requirement: Equipment items bind one-to-one to a closed effect identity
Every registered item that declares an `EquipmentSlot` SHALL also declare exactly one `EquipmentModifierKey` from the closed registry vocabulary, and every `EquipmentModifierKey` SHALL be bound by at most one registered item. A one-to-one binding SHALL be total in both directions: every registered equipment key SHALL have exactly one entry in the equipment-effect rulebook, and every rulebook entry SHALL name exactly one registered equipment key.

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

#### Scenario: Slotless items reject modifier keys
- **WHEN** an item without an equipment slot declares a modifier key
- **THEN** registry construction fails on the declaration

#### Scenario: Unbound keys, orphaned entries, and duplicate bindings fail the load
- **WHEN** registry construction or rulebook loading encounters an unbound key, an orphaned entry, or a duplicated binding
- **THEN** the construction or load fails

### Requirement: The equipment-effect rulebook validates a closed schema at load time
The equipment-effect rulebook SHALL be loaded through one validated loader that is idempotent on reload and accepts a path override for tests. Each entry SHALL contain only the closed vocabulary enumerated below. Malformed entries SHALL fail the load with a named error; the loader SHALL NOT repair, clamp, or silently drop deviating data.

#### Scenario: Out-of-vocabulary field is rejected
- **WHEN** a rulebook entry contains any field or adjustment key outside the closed vocabulary
- **THEN** the load raises the named rulebook error and nothing loads

#### Scenario: The closed entry vocabulary
- **WHEN** a rulebook entry is validated
- **THEN** it may contain only `adjustments` restricted to `atk_phys`, `defense`, `magic_power`, `agility`, `mp_cost`, `sp_cost`, `pleasure_gain`, and `heal_gain`; plus `gauge_caps`, `immune`, `attached_buffs`, and `exposure_bias`

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
The rulebook SHALL carry a budgets table keyed by the item's registered rarity with separate ceilings for flat values, combat percents (`agility`, `mp_cost`, `sp_cost`), soft percents (`pleasure_gain`, `heal_gain`), `exposure_bias`, and positive-only `gauge_caps`. The loader SHALL reject any entry whose value exceeds the ceiling of its rarity's corresponding column (in absolute value).

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
- **WHEN** the formatter renders a synthetic armor entry (atk −2, defense +8, agility −10%, hp cap +15)
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
The roster SHALL add the ten designed equipment items — 淨化吊墜, 無懼胸針, 騎士全套板甲,
藥師珠串, 大術師補綴長袍, 誘蠱蕾絲內衣, 迷情絲頸環, 修女聖袍, 光輝聖徽, 聖女聖袍 — each
with a registry presentation identity, an existing price-table key, an effect binding, and a
listing in the offered keys of at least one Altoria shop.

#### Scenario: New items are purchasable and fully bound
- **WHEN** the capital's shops are inspected after this change
- **THEN** each of the ten new item keys appears in at least one capital shop's offered keys
  with a resolvable price entry and a budget-checked rulebook entry

#### Scenario: The tradeable guarantee is per-roster, not per-shelf
- **WHEN** altoria-adornments-and-remedies moves the roster's five accessory pieces to 聖潔王都首飾坊 (the armor pieces already sat with 聖潔王都裁縫坊), superseding the original wording "a listing in the existing general store's offered keys"
- **THEN** the shipped behavioral test asserts offered-by-some-capital-shop and the roster stays tradeable across shelves

### Requirement: Church-of-Light equipment obeys its canon doctrine
The named 光明教會 equipment set is governed by the Church's canon doctrine (坦露與歡愉為正向、光之治療與淨化) and is split into two sub-sets by liturgical function. The **vestment-and-emblem** sub-set — `sister_vestments`, `radiant_holy_emblem`, `saintess_vestments`, and `pilgrim_medallion` — SHALL carry non-negative `exposure_bias` and non-negative `pleasure_gain`, and SHALL provide at least one of `heal_gain` or an immunity.

#### Scenario: Doctrine coverage for the named Church set
- **WHEN** the rulebook entries of the four named vestment-and-emblem keys are validated
- **THEN** each has non-negative `exposure_bias` and `pleasure_gain`, at least one of `heal_gain` or an immunity, and no suppression value

#### Scenario: Doctrine coverage for the sanctuary-device sub-set
- **WHEN** the rulebook entries of the named 聖所 device keys are validated
- **THEN** each has non-negative `exposure_bias`, positive `pleasure_gain`, and no suppression value, and none is failed for lacking `heal_gain` or an immunity

#### Scenario: Doctrine violation blocks a named Church item
- **WHEN** a deviant rulebook copy gives a named Church item a negative `pleasure_gain`
- **THEN** the doctrine coverage test fails and the change cannot ship

#### Scenario: A sanctuary device may not borrow the healing exemption
- **WHEN** a deviant rulebook copy moves a vestment key into the sanctuary-device sub-set to drop its healing obligation
- **THEN** the coverage test still fails, because sub-set membership is the named list in this requirement and not a property the rulebook can assert

#### Scenario: Sanctuary-device sub-set carries pleasure-only doctrine
- **WHEN** the 聖所 devices the codex catalogues — currently `nymph_buds_clamp`, `warm_honey_orb`, and `hyperesthesia_charm` — are validated
- **THEN** each carries non-negative `exposure_bias` and positive `pleasure_gain`, and none is required to provide `heal_gain` or an immunity
- **AND** the doctrine rationale holds: a garment or sigil of the faith channels the Light's healing and cleansing, while a device serves the rite of pleasure itself rather than dispensing the Light

#### Scenario: No sub-set member carries chastity-style suppression
- **WHEN** any member of either sub-set is validated
- **THEN** it carries no chastity-style suppression, meaning neither negative `pleasure_gain` nor negative `exposure_bias`
- **AND** ordinary combat trade-offs (negative `defense`, `atk_phys`, agility, etc.) remain permitted as the mechanical cost of holiness

#### Scenario: Sub-set membership is amended by name, not by tag
- **WHEN** a new Church item is added
- **THEN** it enters by amending this requirement in the change that adds it, naming the sub-set it joins; membership is these named sets
- **AND** a future registry-owned faith-identity tag remains out of scope

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
bounds.

#### Scenario: Vestments lift a nun's exposure two bands

- **WHEN** an actor with stored exposure 中等 wears a synthetic equipment declaration with bias +2
- **THEN** effective exposure is 極高 and the stored trait is untouched

#### Scenario: Bias clamps at both vocabulary ends

- **WHEN** effective exposure is computed for stored 極高 with bias +2, and
  for stored 極低 with a negative-sum hypothetical
- **THEN** the results clamp to 極高 and 極低 respectively without error

#### Scenario: Malformed storage contributes no bias

- **WHEN** the accessor runs against malformed equipment storage
- **THEN** it returns exactly the stored exposure level

#### Scenario: The exposure accessor keeps the purity contract

- **WHEN** the effective-exposure accessor reads the stored level
- **THEN** it reads through one neutral shared reader that imports no rules modules, writes nothing, and materializes no handlers

#### Scenario: A summed pleasure_gain accessor shares the contract

- **WHEN** the capability exposes its summed `pleasure_gain` accessor over worn equipment
- **THEN** it follows the same purity contract and a malformed-yields-zero rule

### Requirement: Registration and tradeability are independent
An equipment item SHALL be complete when it declares a slot, binds one-to-one to a budget-checked rulebook entry, and names a resolvable price band. A shop listing SHALL NOT be part of that completeness.

#### Scenario: An unstocked binding loads clean
- **WHEN** the equipment-effect rulebook is loaded with a bound, budget-checked equipment item that no shop offers
- **THEN** the load succeeds with no unbound key and no orphaned entry, and no validator reports a missing offer

#### Scenario: An unstocked piece equips and applies
- **WHEN** an unstocked equipment item is granted into inventory and equipped
- **THEN** it occupies its declared slot and its adjustments reach the shared accessor with the authored values

#### Scenario: Tradeability is a stated roster property
- **WHEN** a roster added by this capability is inspected
- **THEN** its requirement states whether its members are stocked, and the shipped offers match that statement

#### Scenario: Unstocked items are a valid shipped state
- **WHEN** a bound, budget-checked equipment item that no shop offers ships
- **THEN** the rulebook loads and no loader or validator reports it as unbound, orphaned, or missing an offer
- **AND** it equips and applies its adjustments exactly as a stocked item of the same shape would

#### Scenario: Stocking statements follow lore provenance
- **WHEN** a roster added by this capability ships
- **THEN** its statement of whether its members are stocked follows the roster's lore provenance rather than a default
- **AND** the regional equipment roster (7 weapons, 3 armors, 2 accessories) ships unstocked until its regional storefronts land
