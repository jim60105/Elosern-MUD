# Design: add-equipment-effect-rulebook

## Context

The parent design is
`docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md`
(P1 of seven). Today `ItemDefinition` (in `world/lore/items.py`) allows
exactly one of `use_mechanics` or `equipment_slot`; 35 registered items
declare an equipment slot, and none carry numbers. The item-effect precedent
(`ItemEffectKey` registry vocabulary + `item_effects.yaml` magnitudes + a
validated loader in `world/rules/items.py`) is the pattern this change
mirrors for equipment. `ITEM_REGISTRY` is module-only data (not DB-mirrored),
so no startup-sync work is involved.

## Goals / Non-Goals

**Goals:**

- A closed equipment effect vocabulary in the registry, one key per equipment
  item, validated to a new rulebook with a five-column per-rarity budget
  table.
- A complete, budget-checked value roster for all 35 existing equipment items
  plus 10 new items (incl. the 光明教會 line), authored once here.
- Fail-loud loader with idempotent reload, mirroring `load_item_effect_rules`.

**Non-Goals:**

- Wiring anything that *reads* the bundle at gameplay time (P2), immunity or
  attached-buff enforcement (P3), sexual-field consumers (P4),
  `equipment_worn` rules (P5), panel/UI (P6/P7).
- Shop trade-rule changes; the region/non-sellable future is untouched.

## Decisions

### D1 — Total bijection with explicit empty entries

Every equipment item must declare exactly one `EquipmentModifierKey`, and
every rulebook entry must name a registered equipment item. Non-combat
equipment that exists today (e.g. `storage_pouch`) gets an explicit
`{}` effects entry rather than an exemption. Rationale: a total bijection is
trivially testable and closes the "silently no stats because nobody
remembered" failure mode; an exemption list would rot. Alternative
considered: optional modifier keys — rejected because budget coverage of the
roster would become unassertable.

### D2 — Full field vocabulary now, consumers later

`adjustments` ships the complete closed vocabulary of the parent design
(`atk_phys`, `defense`, `magic_level`, `agility` flat-or-percent,
`mp_cost`, `sp_cost`, `pleasure_gain`, `heal_gain`) plus `gauge_caps`
(positive integers only — v1 discipline per the parent design §6; the gear
ceiling is synced on toggle with an explicit same-transaction current
clamp), `immune`, `attached_buffs`, and `exposure_bias`, so roster values
are authored by one balance pass and never rewritten per-consumer. Fields with
no consumer before their owning change (P2–P5) are dormant data: nothing
reads them, loader tests cover them, and each owning change turns them on.
Alternative: shard the vocabulary across P2/P3/P4 — rejected because each
change would re-open the balance sheet and the registry↔rulebook diff.

### D3 — Budget table lives in the same YAML, enforced per column

`budgets` is a top-level mapping keyed by `ItemRarity` with columns
`flat` (int fields), `percent` (agility/cost percents), `soft_percent`
(`pleasure_gain`/`heal_gain`), `bias` (`exposure_bias`), `gauge`
(`gauge_caps`). The loader checks every authored value against its column by
the item's registry rarity, so "value matches worth" is mechanical. Values:
flat 4/6/8/10/12, percent 5/8/10/12/15, soft_percent 10/15/20/25/30, bias
0/1/1/2/2, gauge 5/10/15/20/25 (common→legendary). Rarity is never read at
runtime — only at validation time — preserving its presentation-only
contract.

### D4 — Loader placement and reload

`world/rules/equipment_effects.py` mirrors the item-effects loader: frozen
dataclasses, `MAX_EFFECT_AMOUNT`-style hard ceilings, one
`load_equipment_effect_rules(path=None)` with an override path for
deviant-table tests, and a module-level `reload_equipment_effect_rules()`
that is idempotent. It validates: closed vocabularies, percent-string
format, budget columns, `immune`/`attached_buffs` keys existing in
`BUFF_DEFINITIONS`, an entry never attaching a buff it also immunises,
registry↔rulebook bijection, and `modifier_key`/`equipment_slot` pairing on
definitions. Failures raise `EquipmentEffectsRulebookError` at load.

### D5 — The regen buff entry rides here

`attached_buffs` references must resolve, so `apothecary_beads` forces the
new `item_regen_light` buff entry into `buffs.yaml` in this change
(`duration: null`, `unique_per_source`, gentle hp `rate`). Two shipped
contracts then demand matching entries in the same change: the
`status_display.yaml` import-time coverage check (one metadata entry per
buff key) and the rule-id/test correspondence contract in
`world/rules/tests/test_rule_id_test_correspondence.py` (exactly one
`test_buff_<key>` in `BuffIntegrationTests`). Both are added with the buff
key. All of it is data-only on shipped engines — no consumer change — and
P3 is still the change that equips attach the buff.

### D6 — New items are ordinary shop goods

All 10 new items reuse existing price-table keys (`mundane_weapon`, `armor`,
`magic_accessory`, `jewelry`, `magic_weapon`) and are appended to
`altoria_general_store.offered_item_keys` as registry data. No new price
entries, no trade-rule change.

### D7 — Test fixtures opt in via an existing canonical key

Strict `modifier_key` validation would break every test fixture that
constructs an equipment-slot `ItemDefinition` (9+ known files across
`world/lore`, `world/skills`, `world/rules`, `commands`, `web.webclient`
tests). Policy: fixtures pass any valid canonical `EquipmentModifierKey` and
never join `ITEM_REGISTRY`, so the loader's triple bijection over the
production registry is untouched; no test-only enum members are added
(keeping the enum total-bijective with the roster is what makes it auditable).
The tasks list the known fixture files and require a `rg "ItemDefinition\("`
sweep at implementation time.

The loader additionally enforces three fail-loud properties on the production
side (construction stays permissive, so the fixture policy above holds): a
registered item whose modifier *value* is not its own item key is a load-time
error — the enum guarantees the pair invariant, and the loader enforces the
identity the enum alone cannot, so a registered item can never hijack another
item's effects or budget; the rules document may not repeat a key at any
nesting (PyYAML's default last-wins would silently diverge from the reviewed
file); percent grammar is ASCII-only because `int()` accepts non-ASCII digits.

### D8 — Church doctrine scope is a named set, not a runtime tag

A registry-owned faith tag would be a new persistent identity surface with
exactly one consumer today. Scope is instead the named key set
(`sister_vestments`, `radiant_holy_emblem`, `saintess_vestments`,
`pilgrim_medallion` — 朝聖者銅符's summary already binds it to 光明教會) that
the doctrine coverage test iterates; future Church items join by amending
the requirement in their own change. A registry faction tag stays a
forward seam for whatever change first needs faith identity at runtime.

### Commit atomicity

The enum, strict construction validation, the 45 registry bindings, the
canonical YAML, the loader, the buffs/display/test-correspondence entries,
and the fixture migration form one commit (tasks header): any earlier split
leaves either fixture construction or module import red at an intermediate
state.

## Risks / Trade-offs

- [Dormant fields could be wired differently by P2–P5 than balance assumes] →
  The parent design fixes the merge formula; this change's loader tests pin
  value semantics (flat vs percent vs soft vs gauge), so consumer changes
  bind data, not reshape it.
- [A future item needs a stat outside the closed vocabulary] → Adding one
  vocabulary member is one reviewed field in two files plus a budget column
  decision; the alternative (free-form YAML) would silently bypass budgets.
- [Roster numbers are placeholders pending a balance pass] → All values are
  budget-respecting starting points explicitly labelled as such; the parent
  design already defers one "combat-balance pass", and budgets bound the
  damage of any miscalibration.
- [`item_regen_light` in buffs.yaml is readable by existing buff surfaces
  before P3 attaches it] → Nothing grants it until P3; it is inert registry
  data, matching the current 28-key `buffs.yaml` where several keys are only
  reachable through specific spells.

## Balance sheet (authored here, budget-checked)

Budgets: common {f4, p5, s10, b0, g5} · uncommon {f6, p8, s15, b1, g10} ·
rare {f8, p10, s20, b1, g15} · epic {f10, p12, s25, b2, g20} ·
legendary {f12, p15, s30, b2, g25}.
(f = flat, p = percent [agility/cost], s = soft_percent [pleasure/heal],
b = bias, g = gauge.)

Existing items (slot: values):

| key | rarity | effects |
|---|---|---|
| plain_sword | common | atk +2 |
| wooden_club | common | atk +3, agility −2 |
| leather_armor | common | defense +4 |
| iron_dagger | common | atk +1 |
| hunting_throwing_axe | common | atk +2, agility −1 |
| iron_shield | common | defense +4 |
| silver_hairpin | common | pleasure +5% |
| guild_recruit_badge | common | defense +1 |
| knight_blade | uncommon | atk +5, defense +1 |
| ashen_scimitar | uncommon | atk +4, agility +2 |
| gilded_saber | uncommon | atk +5 |
| steel_fang_dagger | uncommon | atk +4, agility +2 |
| great_axe | uncommon | atk +6, agility −8% |
| hunters_longbow | uncommon | atk +4, agility +2 |
| apprentice_focus_staff | uncommon | magic +4, mp_cost −5% |
| chainmail | uncommon | defense +5, agility −5% |
| mage_robe | uncommon | magic +3, mp_cost −8% |
| black_maid_dress | uncommon | bias +1, pleasure +10% |
| wolf_fang_necklace | uncommon | atk +3 |
| prism_charm | uncommon | magic +5 |
| pilgrim_medallion | uncommon | pleasure +10%, heal +5% |
| protective_ring | epic | defense +6, gauge hp +10 |
| crescent_earring | epic | pleasure +15%, sp_cost −8% |
| gliding_cloak | epic | agility +8 |
| magic_sword | epic | atk +8, magic +6 |
| rose_crest_rapier | epic | atk +7, agility +3 |
| dark_elf_kimono | epic | bias +1, pleasure +15%, agility +3 |
| dark_elf_ninja_garb | epic | defense +5, agility +5 |
| purified_pendant (new) | rare | immune poisoned, defense +2 |
| fearless_brooch (new) | rare | immune fear |
| radiant_holy_emblem (new) | rare | heal +20%, pleasure +10%, immune dark_curse |
| knight_platemail (new) | rare | defense +8, agility −10%, atk −2, gauge hp +15 |
| royal_heirloom_pendant | rare | mp_cost −5%, defense +4 |
| royal_signet_ring | rare | atk +3, sp_cost −5% |
| silver_feather_earring | rare | pleasure +15%, bias +1 |
| storage_pouch | rare | (empty) |
| saintess_vestments (new) | epic | bias +2, pleasure +25%, heal +25%, defense −3 |
| sister_vestments (new) | uncommon | bias +1, pleasure +15%, heal +10% |
| enticing_lace_set (new) | uncommon | pleasure +15%, bias +1 |
| apothecary_beads (new) | uncommon | attached item_regen_light |
| archmage_mending_robe (new) | epic | mp_cost −12%, magic +8 |
| passion_silk_choker (new) | epic | pleasure +25%, defense −3 |
| shadow_blade | legendary | atk +12, agility +3 |
| shadow_blade_echo | legendary | atk +10, agility −3 |
| elven_traditional_robe | legendary | bias +2, pleasure +20%, defense +3 |

## Open Questions

None — the parent design fixes vocabulary, budgets, doctrine mapping, and
roster shape; per-item numbers above are the authored starting values.
