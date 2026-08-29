# Equipment Combat & State Effects — Design

**Date:** 2026-08-29
**Status:** Approved
**Scope:** Make worn equipment materially affect combat stats, resource gauge
ceilings, status-effect susceptibility, and the sexual system; add the
Church of Light (光明教會) equipment line; upgrade the character panel to a
multi-source stat breakdown.

---

## 1. Context and Problem

Equipment today is cosmetic: `ItemDefinition` carries an `equipment_slot` but
no stat-bearing field, and nothing in `world/rules/combat.py` or the
combat-modifier pipeline reads equipped items. A player who equips 騎士制式長劍
over 普通劍 fights identically.

This design gives every registered equipment item (≈30 keys) a deterministic
stat profile with trade-offs, lets equipment interact with buffs (immunity,
attached beneficial buffs) and with the sexual system (pleasure gain,
effective 露出 exposure), and makes all of it visible as a labelled,
per-source breakdown on the character panel.

Lore source of truth for religious items: `tmp/story_settings/world_info.md`.
The 光明教會 doctrine is sex-positive — 以坦露為聖 (exposure is holy) and
pleasure as divine blessing — which inverts the common fantasy chastity-cleric
trope. All religious item mechanics below obey the canon, not the trope.

## 2. Goals

- Worn equipment changes combat: `atk_phys`, `defense`, `agility` (flat or
  percent), `magic_level`, `mp_cost`/`sp_cost` (percent), gauge ceilings
  (`hp/mp/sp` maximum).
- Negative contributions are first-class: heavy plate buys `defense` with
  `agility`/`atk_phys`.
- Magnitudes are tied to the item's registered `ItemRarity` through a
  machine-enforced budget table.
- Equipment can grant immunity to specific debuffs (they never apply) and can
  attach a permanent beneficial buff while worn.
- Equipment integrates with the sexual system: `pleasure_gain` (percent of
  act pleasure gain) and `exposure_bias` (read-time exposure ordinal shift);
  sexual states already feed combat, so the feedback direction (arousal/exposure
  changing how equipped gear performs) opens through one new rule condition.
- The character panel shows every stat as an explicit multi-source breakdown:
  base / skill / condition / equipment, with the effective number computed by
  the same formula combat uses.

## 3. Non-Goals and Forward Seams

Recorded deliberately so future changes can land without redesign; nothing
here is faked in this change (AGENTS.md forward-seam rule):

- **Monster loot drops.** Not implemented. Equipment effects bind to item
  keys, not acquisition paths, so a future drop table can grant equipment keys
  with zero changes to this design.
- **Shop region gating / non-sellable goods.** Out of scope by explicit
  decision: shops keep selling everything registered. `price_table_key` and
  `sellable` already exist on `ItemDefinition`, giving a future change a
  natural per-item hinge. New items get ordinary shop price entries.
- **聖所 contraception (避孕之術).** The Church's light-magic contraception is
  narrative; there is no pregnancy system. Forward seam only.
- **Equipment affecting `sensitivity`, `shame`, `virgin`, or lifetime
  counters.** These carry one-way / state-machine semantics with defined
  mutators; equipment reacts to them numerically but never rewrites them.
- **Critical-hit or other new dice channels.** Dice influence stays inside the
  existing `accuracy`-via-agility path; no new roll vocabulary.
- **No new player commands.** Existing equip/unequip, look, inventory, and
  panel surfaces are extended in prose/payload only, keeping
  `tests/test_command_docs.py` green.

## 4. Architectural Invariants Respected

- Single-writer boundary: every contribution in this design is a **pure read**
  derived from already-persisted state (`entity.db.equipment`, buff cache,
  skill storage). The only new write paths are the ones that already own their
  subsystem: `toggle_equipment()` (equipment mapping + attached-buff cache in
  the same transaction) and item-use settlement for holy water (existing
  all-or-nothing action workflow).
- Registry holds identity, rulebook holds magnitudes (the established
  `ItemEffectKey` / `item_effects.yaml` split).
- Stored traits stay literal: equipment never bakes into `traits` storage,
  exactly like skill multipliers (`skills.effective_value()` precedent).
- `disguised_stats` stays display-only; combat keeps using true values.
- Fail-closed reads: malformed equipment storage (already detected by
  `_normalized_equipment()`) yields **no** equipment contributions in
  combat/settlement (combat continues on base stats) while still rejecting
  every new mutation, matching existing preflight behaviour.

## 5. Data Model

### 5.1 Registry (identity) — `world/lore/items.py`

`ItemDefinition` gains one field:

```python
modifier_key: EquipmentModifierKey | None = None
```

`EquipmentModifierKey` is a closed `StrEnum` following the `ItemEffectKey`
pattern: every equipment item declares exactly one canonical key; the
validated loader rejects a registered key with no rulebook entry and a
rulebook entry with no registered key. `__post_init__` enforces that a
modifier key may only appear on an item with an `equipment_slot` (mutually
exclusive with `use_mechanics`, same discipline as today).

### 5.2 Rulebook (magnitudes) — new `world/rules/rulebook/equipment_effects.yaml`

```yaml
budgets:                     # max absolute magnitude per rarity, by kind
  common:     { flat: 4,  percent: 5,  soft_percent: 10, bias: 0, gauge: 5 }
  uncommon:   { flat: 6,  percent: 8,  soft_percent: 15, bias: 1, gauge: 10 }
  rare:       { flat: 8,  percent: 10, soft_percent: 20, bias: 1, gauge: 15 }
  epic:       { flat: 10, percent: 12, soft_percent: 25, bias: 2, gauge: 20 }
  legendary:  { flat: 12, percent: 15, soft_percent: 30, bias: 2, gauge: 25 }

effects:
  platemail_knightly:
    adjustments: { defense: 8, agility: "-10%", atk_phys: -2 }
    gauge_caps: { hp: 15 }
  sister_vestments:
    adjustments: { pleasure_gain: "+15%", heal_gain: "+10%" }
    exposure_bias: 1
  pendant_purification:
    immune: [poisoned]
    adjustments: { defense: 2 }
```

Field vocabularies are closed and validated by a loader in
`world/rules/equipment_effects.py` (mirroring `load_item_effect_rules`):

- `adjustments`: `atk_phys`, `defense`, `magic_level` (signed flat ints);
  `agility` (flat int or signed percent string); `mp_cost`, `sp_cost`
  (signed percent only); `pleasure_gain`, `heal_gain` (signed percent only).
- `gauge_caps`: positive integers over `hp`/`mp`/`sp` (negative caps are
  rejected — see §6 gauge sync); the effective gauge maximum clamps to ≥ 1.
- `immune`: buff keys that must exist in `buffs.yaml`.
- `attached_buffs`: buff keys that must exist in `buffs.yaml`; an entry may
  not attach a buff key it also claims immunity for (loader guard).
- `exposure_bias`: signed ordinal steps into the existing 露出 vocabulary.
- Budget enforcement by column: flat ints vs `percent` (combat-relevant
  percents: agility/costs) vs `soft_percent` (`pleasure_gain`, `heal_gain`)
  vs `bias` vs `gauge` (`gauge_caps` are resource points, budgeted apart from
  combat ratings). Any field exceeding its rarity budget fails startup loudly.

Rarity remains a registry presentation classification for everything except
this budget check; the budget table is what makes "value matches worth"
mechanical instead of conventional.

## 6. Combat and Stat Integration (read-time)

New pure function `equipment_adjustments(entity) -> dict` reads
`normalized_equipment()` (the sole fail-closed read point), resolves each worn
key's rulebook entry, and folds them with the existing `_merge_adjustments`
(additive for flats and percents). Malformed storage returns an empty bundle.

Merge point: `evaluate_combat_modifiers()` and
`evaluate_combat_modifiers_no_create()` append the equipment bundle after
rule-table matching. Every existing consumer — `_to_hit`,
`_adjusted_attack`/`_adjusted_defense`, the overwhelm estimator, action
preview, MP/SP cost via `apply_cost_modifier`, `sexual_resist` score
building, and heal magnitude via `combat._heal_magnitude()` (which consumes
the `heal_gain` percent) — therefore reads one identical effective bundle.
No second formula exists.

Evaluation order (documented invariant, used identically by combat and the
breakdown panel):

```
effective = round( ( stored_base × skill_multiplier ) × (1 + percent_sum/100) )
            + flat_sum
```

- `skill_multiplier`: existing `StatMultiplyEffect` layer (身體強化 ×N),
  unchanged.
- `percent_sum` / `flat_sum`: merged bundle fields (equipment and rule-table
  contributions merged numerically; the breakdown panel re-splits them per
  source — see §10).
- New clamp: adjusted `agility ≥ 0` (prevents a heavy-gear negative percent
  from inverting the to-hit formula).

Gauge ceilings: the summed `gauge_caps` contributions are authored as
positive integers only (negative caps are rejected by the loader, because
Evennia's `GaugeTrait` re-clamps `current` whenever its ceiling drops, and a
silent retroactive clamp would violate the no-retroactive-rewrite rule).
`toggle_equipment()` — already the sole equipment writer — recomputes each
gauge trait's non-literal `mod` from scratch as Σ(equipment caps) inside the
same transaction (base stays the literal value; `mod` is Evennia's sanctioned
non-literal adjuster, and `max` is `(base+mod)`). All maximum readers and
heal clamps then agree for free. This amends the earlier read-time phrasing:
gauge caps are a deterministic derived write owned by the single writer,
recomputed — never accumulated — so no drift state exists.

## 7. Status-Effect Interactions

### 7.1 Immunity (`immune`)

`equipment_immune_buff_keys(entity)` (pure, no-create) returns the union of
immune keys across worn items. The buff-grant chokepoint (`world/rules/buffs.py`
`_add_buff()` and its callers in the action workflow) consults it before
writing: an immune debuff writes nothing, and the combat/action event stream
emits a deterministic resistance beat in 正體中文 (e.g. 「毒霧在你胸前消散——
你對此免疫」) visible to both sides, so rolls are never silently lied about.
Immunity is evaluated at grant time; equipping/unequipping takes effect
immediately with no persisted state.

### 7.2 Attached buffs (`attached_buffs`)

`toggle_equipment()` — the sole equipment mutator — applies or removes an
item's attached buffs inside the same `transaction.atomic()` as the equipment
mapping write (both attributes snapshotted and restored on failure). Attached
buffs use the shipped `unique_per_source` stacking with
`source_key` anchored to the item key and `duration: null` (precedent:
`conferred_growth_rate`). Tick effects (e.g. light regen) run through the
existing `tick_buffs` engine unchanged. Known accepted cost: externally
corrupted equipment storage can leave an attached buff behind; fail-closed
mutation already blocks any new equip/unequip, and no repair daemon is added.

## 8. Sexual-System Integration (all read-time)

Two new closed fields in the equipment rulebook:

- `pleasure_gain` (±%) folded as one final multiplier into
  `compute_pleasure_gain()` — the sole pleasure-gain funnel for in-combat and
  out-of-combat acts alike.
- `exposure_bias` (signed ordinal): **effective exposure** is computed at
  read time as `clamp(stored_ordinal + bias, floor, vocabulary_top)`; the
  stored trait is never rewritten (same semantics as buff bounds). The
  combat-modifier condition contexts (`_build_context` and
  `build_no_create_condition_context`) switch their `exposure` read to the
  effective value, so the existing 「露出 ≥ 高 → defense −15」 rule fires for
  revealing outfits with no new rule, and status presentation shows the
  effective level.

Free bidirectionality (no new code): the sexual-act resist contest
(`sexual_resist.resist_verdict`) already scores participants through
`evaluate_combat_modifiers_no_create`, so equipment agility/attack bonuses
flow into resist rolls the moment §6 lands; high-arousal penalties scale
equipment percent bonuses in the same merged bundle.

## 9. `equipment_worn` Rule Condition

`world/rules/combat_modifiers.yaml` gains one condition vocabulary,
`equipment_worn: <item_key>` — an equipment fact read from
`normalized_equipment()` and injected into the condition context the same way
the shipped `dual_wielding` fact is. It AND-composes with existing conditions:

```yaml
- id: sister_vestment_grace
  when: {equipment_worn: sister_vestments, field: arousal, gte: 中等}
  then: {defense: 4}
```

(Arousal thresholds use the shipped `AROUSAL_LEVELS` vocabulary:
平靜／微興奮／中等／高度／極限.)

Rulebook validation requires the key to exist in `ITEM_REGISTRY` as a
slot-bearing item. Every displayable rule (grace rules included) gets an
entry in `status_display.yaml` (label + severity), keeping the display
coverage test green.

## 10. Equipment Content

### 10.1 Existing items

All ≈30 registered equipment items receive rulebook entries following slot
archetypes (values inside their rarity budgets):

- Weapons: positive `atk_phys` scaling with rarity; two-handed weapons pay
  `agility %`; bows carry a small `agility` component.
- Armor: `defense` main stat; light/mage robes take `mp_cost %` /
  `magic_level`; heavy armor pays `agility %` and/or `atk_phys`.
- Off-hand: shields take small `defense`; off-hand blades small `atk_phys`
  (stacking with the existing dual-wield skill rule).
- Accessories: niche utility (`mp_cost %`, `magic_level`, small `defense`,
  immunity at rare+).

Religious and revealing existing garments are aligned to canon:

- 朝聖者銅符 (accessory, uncommon): `pleasure_gain +10%`, `heal_gain +5%`.
- 黑色女僕裝 (armor, uncommon): `exposure_bias +1`, `pleasure_gain +10%`.
- 精靈傳統服飾 / 黑暗精靈傳統服飾 / 黑暗精靈戰鬥服飾: sexual fields assigned per
  each branch's lore positioning (values finalized in the implementation table
  under the budget check).
- 受洗聖水 (consumable): its item-effect rulebook entry becomes a cleanse
  effect (new `ItemEffectKey.BLESSED_CLEANSE`) routed through the existing
  buff-cleanse handler — light 淨化 as doctrine intends.

### 10.2 New items (fill gaps only)

| Item | Slot / rarity | Effects |
|---|---|---|
| 淨化吊墜 | accessory / rare | immune `poisoned`; `defense +2` |
| 無懼胸針 | accessory / rare | immune `fear` |
| 騎士全套板甲 | armor / rare | `defense +8`, `agility −10%`, `atk_phys −2`, gauge cap `hp +15` |
| 藥師珠串 | accessory / uncommon | attached regen buff (new `buffs.yaml` entry, `unique_per_source`, `duration: null`) |
| 大術師補綴長袍 | armor / epic | `mp_cost −12%`, `magic_level +8` |
| 誘蠱蕾絲內衣 | armor / uncommon | `pleasure_gain +15%`, `exposure_bias +1` |
| 迷情絲頸環 | accessory / epic | `pleasure_gain +25%`, `defense −3` |
| 修女聖袍 | armor / uncommon | `exposure_bias +1`, `pleasure_gain +15%`, `heal_gain +10%` |
| 光輝聖徽 | accessory / rare | `heal_gain +20%`, immune `dark_curse`, `pleasure_gain +10%` |
| 聖女聖袍 | armor / epic | `exposure_bias +2`, `pleasure_gain +25%`, `heal_gain +25%`, `defense −3` |

### 10.3 光明教會 (Church of Light) design constraints

Canon mapping (from `world_info.md`): 以坦露為聖 → Church gear is a *positive*
`exposure_bias` source, and the existing exposure defense penalty is the
mechanical cost of holiness; 性之歡愉為至高恩賜 → Church gear grants
`pleasure_gain +`; 光＝治療與淨化 → `heal_gain` and dark-curse immunity;
女神回應敬拜 → `equipment_worn` × arousal grace rules.

Chastity/repression gear is therefore **anti-doctrine** and must not carry
Church identity; two earlier draft items (a knight-order chastity belt and a
"devout" pleasure-suppressing sash) were removed on exactly this ground.
阿爾托利亞's 聖騎士團 is a secular honour order — its gear stays martial and
carries no Church tagging. Acquisition is through existing shops and quest
rewards only (§3).

## 11. Multi-Source Breakdown Panel

The character panel payload bumps to v5. Each stat row becomes:

```
{ key, label, base, effective,
  layers: [ {source: skill|equipment|condition, name, kind: mult|flat|pct,
             amount}, ... ] }
```

- `base`: stored literal value (never baked).
- `skill` layers: one row per owned/conferred skill holding a matching
  `StatMultiplyEffect` (name = skill registry label), kind `mult`.
- `condition` layers: one row per matched combat-modifier rule/buff affecting
  the stat (names = existing `STATUS_DISPLAY` labels — the same strings the
  condition chips show), kinds `flat`/`pct`.
- `equipment` layers: one row per worn contributing item (name =
  `display_name_zh`), kinds `flat`/`pct`; equipment caps on gauges render as
  a `flat` layer on the gauge maximum.
- `effective`: produced by the single §6 formula, shared with combat — the
  panel and settlement cannot disagree.

Gauge rows decompose their maximum with the same layer structure.
The compact status surface keeps showing effective totals only (breakdown is
the character panel's job). The text client's status/inventory views print
the same layer rows. Equipment rows in inventory/panels carry a server-formatted
adjustment summary (e.g. 「防禦 +8｜敏捷 −10%｜免疫中毒」) generated from the
rulebook + registry in 正體中文.

Vue work: `CharacterStatusDrawer` stat rows render `effective（breakdown）`;
`EquipmentDoll`/inventory rows render the adjustment text; the intimate view
shows effective exposure. Storybook stories, Vitest components, panel payload
validators, and `showcase-coverage` move to v5 together.

## 12. Error Handling Summary

| Condition | Behaviour |
|---|---|
| Rulebook budget violation / unknown key / bad reference | Startup load fails loudly |
| Registered equipment without rulebook entry | Startup load fails loudly |
| Malformed equipment storage | Combat & previews run on base stats (empty equipment bundle); all mutations keep failing preflight as today |
| Immunity hit | No buff written; deterministic resistance event |
| Toggle transaction failure | Equipment mapping and buff cache both restored (existing snapshot pattern) |
| Percent string malformed at a consumer | Existing fail-loud `ValueError` paths unchanged |

## 13. Testing Strategy

Deterministic throughout; no live LLM/SD, fixed seeds or patched RNG.

- Loader unit tests (`unittest.TestCase`): budgets (flat/percent/
  soft_percent/bias columns), closed vocabularies, immune/attached references
  against `buffs.yaml`, registry/rulebook bijection, `equipment_worn` key
  validation against `ITEM_REGISTRY`.
- Bundle unit tests: multi-item stacking, malformed-storage empty bundle,
  agility clamp, `((base×mult)×(1+pct))＋flat` order, gauge cap clamp ≥ 1.
- Integration: to-hit / damage / heal with worn gear (fixed RNG), heal clamp
  to effective max, `compute_pleasure_gain` multiplier, exposure bias
  triggering the 露出 rule, resist verdict picking up equipment-adjusted
  scores, `equipment_worn` match/no-match, immunity blocking `_add_buff` with
  its event, attached buff apply/remove through `toggle_equipment` including
  rollback, holy-water cleanse via the existing handler.
- Evennia tests: end-to-end equip toggle, `status_query` breakdown model,
  character panel v5 validator, item adjustment prose, text status output.
- JS: Vitest for breakdown rows and equipment adjustment rows, Storybook
  stories, payload validator tests, `npm run showcase-coverage`.
- Traceability: new main capability `equipment-effects`; every requirement
  annotated with `covers_requirement`, `tools.spec_traceability check` green.

## 14. OpenSpec Decomposition

Seven sequential changes, each scoped to roughly one working day:

| # | Change | Dependency |
|---|---|---|
| P1 | `add-equipment-effect-rulebook` — registry `EquipmentModifierKey` + `modifier_key` field; new `equipment_effects.yaml` with the five-column budget table + validated loader (registry↔rulebook bijection, immune/attached reference checks); rulebook entries for all existing equipment and all ten new items (incl. Church line) with registry + shop listings | none |
| P2 | `wire-equipment-combat-modifiers` — `equipment_adjustments()` merged into both `evaluate_combat_modifiers` variants; agility ≥ 0 clamp; gauge-cap read/consume points incl. heal clamp; `heal_gain` into `_heal_magnitude()`; overwhelm/preview consistency tests | P1 |
| P3 | `add-equipment-immunity-and-attached-buffs` — immunity check at the buff-grant chokepoint with deterministic resistance prose; attached buffs applied/removed inside `toggle_equipment`'s transaction; 藥師珠串 regen buff; 受洗聖水 cleanse item effect; equipment adjustment prose on toggle/inspect surfaces | P1 (parallel-safe with P2) |
| P4 | `add-equipment-sexual-effects` — `pleasure_gain` folded into `compute_pleasure_gain()`; effective 露出 (bias) in condition contexts and intimate presentation; regression test that resist scores pick up equipment-adjusted stats | P2 |
| P5 | `add-equipment-worn-grace-rules` — `equipment_worn` condition vocabulary, context injection, loader validation; 聖袍/聖徽 grace rules; `status_display.yaml` coverage | P2 (after P4 recommended) |
| P6 | `expose-stat-breakdown-read-model` — character panel payload v5 with `layers` (skill/condition/equipment), read model, text-client breakdown rows, payload validators | P2, P4, P5 |
| P7 | `render-equipment-breakdown-webclient` — Vue breakdown rows and equipment adjustment display, Storybook/Vitest/coverage | P6 |

Execution order: P1 → P2 → P3 → P4 → P5 → P6 → P7 (P3 may run in parallel
with P2; sequential execution is the safe default). Each change lands its own
delta specs against `openspec/specs/`; the new capability `equipment-effects`
is introduced by P1 and amended by its successors.
