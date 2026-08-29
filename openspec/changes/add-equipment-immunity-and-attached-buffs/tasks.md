# Tasks: add-equipment-immunity-and-attached-buffs

Depends on P1 (rulebook/roster incl. `item_regen_light`) and P2 (gauge-sync
transaction + accessor in place).

## 1. Immunity

- [ ] 1.1 Add `equipment_immune_buff_keys(entity)` to
      `world/rules/equipment_effects.py` (pure, no-create, malformed → empty
      set).
- [ ] 1.2 Stage immunity at `world/rules/action.py`'s
      `_handle_buff_apply`/`_handle_self_buff_apply`: for `polarity ==
      debuff` definitions consult the predicate before building the effect;
      immune → non-mutating pending effect tagged
      `equipment_immune|<entity>|<buff_key>` (the `_resist_pending_effect`
      pattern) with 正體中文 text in the shipped event-text map.
- [ ] 1.3 Add the defense-in-depth no-write gate for immune targets inside
      `_add_buff()` (same predicate; no event expectation at this layer).

## 2. Attached buffs

- [ ] 2.1 In `toggle_equipment()`'s transaction: worn-set-diff lifecycle
      (`removed = worn_before − worn_after` instances removed first, then
      `added = worn_after − worn_before` applied as
      `<definition_key>:<item_key>`, `source_key = item_key`,
      `unique_per_source`, `duration: null`); add the `buffs` dbkey to the
      snapshot set via `surfaces.attribute_snapshot` /
      `restore_attribute_best_effort` alongside P2's gauge snapshot.
- [ ] 2.2 Confirm `item_regen_light` ticks through the existing combat/
      clock engines with no engine changes; confirm no attached instance
      carries gauge-ceiling mods (rulebook guard or assertion).

## 3. Holy water cleanse + prose

- [ ] 3.1 Register `ItemEffectKey.BLESSED_CLEANSE`; switch
      `baptismal_holy_water`'s item-effects entry to the cleanse form;
      extend the item-effects loader (cleanse entries carry no amount, heal
      entries keep requiring one) and the settlement branch to reuse the
      `cleanse:status` removal path.
- [ ] 3.2 Add `ItemUseReason.NO_DEBUFFS` preflight (zero active debuffs →
      reject, consume nothing, no clock advance) wired through every
      existing reason consumer (`service_messages`, command/web responses)
      with 正體中文 text.
- [ ] 3.3 Extend `ItemTouchedJournal` with a `buffs` surface: capture the
      `buffs` dbkey without materializing the handler; restore through the
      attribute handler.
- [ ] 3.4 Implement `equipment_adjustment_text(item_key)` (「｜」-joined,
      vocabulary-declaration order, `±N%`, `<gauge>上限 ±N`, zero fields
      omitted, immunity via registered display names) and surface it in the
      successful toggle message, item inspection/look rows, and accessory
      listing — no command keys/aliases/syntax changes.

## 4. Tests

- [ ] 4.1 Immunity: blocked grant leaves buff storage byte-identical + one
      neutralization event visible to both sides; already-applied poison
      keeps ticking after equipping the pendant; buff-polarity unaffected;
      three casts → three events, storage unchanged; malformed storage
      confers nothing; predicate purity; `_add_buff` backstop refuses direct
      writes.
- [ ] 4.2 Attached buffs (EvenniaTest): equip ticks regen at rulebook rate;
      singleton-slot replacement swaps exactly one instance out and one in;
      unequip removes exactly its instance (other buffs untouched);
      fault-injection after apply/remove restores equipment + gauge mods +
      buff storage AND live handler reads; ten toggles leave exactly one
      instance.
- [ ] 4.3 Holy water: cleanse-all + consume + event; `no_debuffs` rejection
      consumes nothing, logs no event, advances no clock, renders the
      zh prose; injected post-cleanse fault restores potion key, debuffs,
      and live buff reads; loader rejects `amount` on cleanse entries;
      existing item-use suites stay green.
- [ ] 4.4 Formatter unit tests incl. the exact 騎士全套板甲 string
      「攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15」 and the immunity-only
      無懼胸針 case; prose snapshots for toggle/inspect surfaces;
      `tests/test_command_docs.py` green (no command-surface change).
- [ ] 4.5 After spec sync, obtain canonical IDs via
      `uv run --locked python -m tools.spec_traceability list`, annotate
      the covering tests with literal IDs (`covers_requirement` for all
      four delta requirements), and keep
      `uv run --locked python -m tools.spec_traceability check` green.

## 5. Regression and handoff

- [ ] 5.1 Focused suites: `world.rules` (buffs, items, equipment toggle,
      action), `commands.tests`; then the non-browser suite once with
      `--parallel 16 --noinput --keepdb`.
- [ ] 5.2 Record deviations (or none) from the parent design here; run
      `openspec validate add-equipment-immunity-and-attached-buffs --strict`.
