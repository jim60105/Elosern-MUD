# Proposal: add-equipment-effect-rulebook

## Why

Registered equipment is currently cosmetic: `ItemDefinition` carries an
`equipment_slot` but no stat-bearing field, so equipping 騎士制式長劍 over
普通劍 changes nothing in combat. The equipment-effects design
(`docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md`) adds
real equipment impact in seven daily changes; this is P1, the foundation: the
closed identity vocabulary in the lore registry, the validated
`equipment_effects.yaml` rulebook with rarity budgets, and the complete,
budget-checked item roster — including the 光明教會 (Church of Light) line —
so every later change wires consumers against settled data.

## What Changes

- `world/lore/items.py` gains a closed `EquipmentModifierKey` StrEnum
  (mirroring the `ItemEffectKey` pattern) and an optional `modifier_key` field
  on `ItemDefinition`. Every equipment-slot item must declare exactly one
  registered modifier key; usable and inspect-only items must not; registry
  construction fails on any mismatch. This modifies the item-mechanics
  exclusivity contract of `item-use-resolution`.
- New rulebook `world/rules/rulebook/equipment_effects.yaml` plus a validated
  loader in `world/rules/equipment_effects.py` (mirroring
  `load_item_effect_rules`): a five-column per-rarity budget table
  (`flat`/`percent`/`soft_percent`/`bias`/`gauge`) and one entry per equipment
  key with a closed field vocabulary — `adjustments` (`atk_phys`, `defense`,
  `magic_level`, `agility`, `mp_cost`, `sp_cost`, `pleasure_gain`,
  `heal_gain`), `gauge_caps`, `immune`, `attached_buffs`, `exposure_bias`.
  Any out-of-vocabulary field, budget violation, dangling `buffs.yaml`
  reference, or registry↔rulebook bijection violation fails startup loudly.
- The full field vocabulary lands here so item values are authored once;
  consumers wire up in P2–P5. Fields with no consumer yet are dormant data
  (never read at runtime until their owning change lands) and are covered by
  loader validation only.
- Rulebook entries are authored for all existing registered equipment
  (≈30 keys) following slot archetypes, and 10 new equipment items are
  registered (incl. 修女聖袍／光輝聖徽／聖女聖袍 of the 光明教會 line, each
  item's magnitude matching its canonical doctrine). Non-combat accessories
  that exist today (e.g. 儲物袋) get explicit empty-effect entries to keep the
  bijection total.
- New items receive price-table keys and are listed in the existing shops as
  ordinary tradeable goods (data registration; no trade-rule change).

No player command surface changes. No backward compatibility or migration
work (unreleased, zero users).

## Capabilities

### New Capabilities

- `equipment-effects`: equipment effect identity (closed registry vocabulary
  bound one-to-one to rulebook entries), the validated rulebook contract
  (closed field vocabulary, five-column rarity budget enforcement, buffs.yaml
  reference resolution), and the guarantees that later changes rely on
  (dormant-field discipline, fail-loud startup validation, tradeable
  registration of the roster).

### Modified Capabilities

- `item-use-resolution`: MODIFIES "Item mechanics are immutable and
  independent from presentation" — the equipment-slot form additionally
  requires exactly one registered `EquipmentModifierKey`, the field is
  rejected on non-equipment items, and presentation may not carry or select
  it.

## Impact

- `world/lore/items.py`: `EquipmentModifierKey` vocabulary, `modifier_key`
  field + construction validation, ~10 new `ItemDefinition` registrations.
- `world/rules/rulebook/equipment_effects.yaml` (new) and
  `world/rules/equipment_effects.py` (new validated loader, idempotent reload
  following the item-effects loader precedent).
- `world/lore/shops.py` and the economy price table: new-item listings
  (registry data only).
- Tests: loader validation suite (budgets per column, closed vocabularies,
  triple bijection incl. duplicate modifier bindings, buffs.yaml references,
  self-attached/immune guard), registry construction validation, roster
  coverage + named-set Church doctrine test, `test_buff_item_regen_light`
  for the buff-key/test correspondence contract, inertness guards (loader
  import allowlist + identical outcomes across dormant-value deviant copies),
  and migration of every test fixture that constructs an equipment
  `ItemDefinition`. `covers_requirement` annotations land with the first
  change whose tests exercise the synced main-spec requirements.
- Not affected: combat settlement, buff application, sexual system, panel
  payloads (P2–P7), shop trade rules, world-clock, command docs.
