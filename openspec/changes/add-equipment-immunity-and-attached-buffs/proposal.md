# Proposal: add-equipment-immunity-and-attached-buffs

## Why

The roster authored by P1 carries `immune` and `attached_buffs` values that
nothing enforces yet: a 淨化吊墜 currently does nothing against 中毒, and
藥師珠串 attaches nothing. This is P3 of the equipment-effects design
(`docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md`
§7): making worn equipment interact with the status-effect system —
debuff immunity at the single buff-grant chokepoint, attached beneficial
buffs owned by the equipment toggle — plus the doctrine fit for 受洗聖水
(light 淨化 as an item effect) and the player-facing adjustment prose that
lets players actually see what they wear.

## What Changes

- Immunity is decided at effect STAGING in `world/rules/action.py`'s two
  buff handlers (the event tag is fixed there, not in `_add_buff`): an
  immune debuff target gets a non-mutating `equipment_immune|…` neutralized
  event with 正體中文 prose visible to actor and target — the roll is never
  silently lied about. `_add_buff()` keeps an independent no-write gate as a
  defense-in-depth backstop. Immunity rejects only new grants while worn;
  it never retro-cleanses existing debuffs.
- `toggle_equipment()` recomputes `attached_buffs` from the worn-set diff
  inside the same `transaction.atomic()` (remove `before−after` instances,
  then apply `after−before`; singleton-slot replacement swaps in one
  toggle). Instances are `unique_per_source`, keyed by definition+item,
  `duration: null` (the `conferred_growth_rate` precedent); the `buffs`
  dbkey joins the snapshot/restore set (`BuffHandler` re-reads the
  attribute per access, so assignment-restore keeps live reads correct).
  `item_regen_light` (P1 data) becomes live through the existing tick
  engine. Attached instances must not carry gauge-ceiling mods.
- New registered item effect key `blessed_cleansing`: using 受洗聖水 removes
  every active debuff-polarity buff from the actor through the existing
  cleanse path and consumes the potion; `ItemTouchedJournal` gains buff
  snapshot/restore; zero debuffs rejects with a new `ItemUseReason`
  `no_debuffs` (mirrors `hp_full`) wired through the reason renderers.
- Deterministic equipment adjustment prose: the toggle result message, the
  inventory/equipment listing, and item inspection render each worn/holdable
  equipment item's authored values as 正體中文 (e.g. 「防禦 +8｜敏捷 −10%｜
  免疫中毒」), generated server-side from the rulebook + registry. No command
  key/alias/syntax changes, so the command docs keep their contract and stay
  green.

No backward compatibility or migration work.

## Capabilities

### New Capabilities

(None — this change extends `equipment-effects` and three existing
capabilities.)

### Modified Capabilities

- `equipment-effects`: ADDS the immunity predicate contract (pure, no-create,
  malformed storage yields no immunities) and the adjustment-prose
  requirement.
- `buff-handler-integration`: ADDS the immunity gate at the single buff-grant
  chokepoint — immune debuffs are not written, a neutralization event is
  emitted, and non-debuff buffs are unaffected.
- `equipment-inventory`: ADDS attached-buff lifecycle ownership by the
  toggle — same-transaction apply/remove with snapshot/restore, source-keyed
  stacking, and no orphans after repeated toggling.
- `item-use-resolution`: ADDS the `blessed_cleansing` item effect (registered
  effect key, debuff-polarity cleanse on the actor, atomic consumption).

## Impact

- `world/rules/equipment_effects.py`: `equipment_immune_buff_keys()`,
  adjustment-prose formatter.
- `world/rules/action.py`: staging-time immunity check + non-mutating
  neutralization pending effect + event renderer text in the shipped map.
- `world/rules/buffs.py`: no-write backstop gate inside `_add_buff()`.
- `world/rules/equipment.py`: attached-buff worn-set-diff lifecycle in
  `toggle_equipment` (extends P2's sync transaction; `buffs` dbkey joins
  the snapshot set).
- `world/lore/items.py` + `world/rules/items.py` + `item_effects.yaml`:
  `BLESSED_CLEANSE` effect key, its settlement branch reusing the cleanse
  removal path, `ItemTouchedJournal.buffs` surface, and the `no_debuffs`
  `ItemUseReason` with its renderers/consumers (`service_messages`,
  out-of-combat command/web responses).
- `world/rules/player_messages.py` / event renderers: neutralization and
  adjustment prose (Traditional Chinese); `docs/game/commands.md` untouched
  (no command-surface change) with `tests/test_command_docs.py` kept green.
- Tests: immunity blocks grant + event, non-debuff unaffected, attached-buff
  apply/remove/rollback/no-accumulation, regen tick through existing engine,
  holy-water cleanse consumption, formatter unit tests, prose snapshots on
  toggle/inspect.
- Not affected: combat bundle math (P2), sexual fields (P4), condition rules
  (P5), payloads (P6/P7).
