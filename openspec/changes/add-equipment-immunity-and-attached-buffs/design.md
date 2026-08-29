# Design: add-equipment-immunity-and-attached-buffs

## Context

Parent design §7. Buff grants flow through `world/rules/buffs.py::_add_buff()`,
but the visible event tag (`buff_applied|<entity>|<key>`) and renderer text
are fixed at `PendingEffect` staging time in `world/rules/action.py`
(`_handle_buff_apply` ~line 490, `_handle_self_buff_apply` ~line 532); the
mutator lambda's return value is ignored. `_resist_pending_effect` is the
shipped precedent for staging a logged, non-mutating verdict event.
Evennia's `BuffHandler` (`evennia.contrib.rpg.buffs`) keeps no cache of its
own — every read/write goes through `owner.attributes.get(dbkey)` — so the
project's `surfaces.attribute_snapshot`/`restore_attribute_best_effort`
pair on the `buffs` dbkey keeps live handler reads consistent with restored
storage. `ItemTouchedJournal` (`world/rules/items.py:231`) snapshots
traits/inventory/quest-log/mirror today — not buffs. `toggle_equipment()`
already runs one `transaction.atomic()` with P2's gauge sync and
snapshot/restore. The `cleanse:status` purge and the `unique_per_source` +
`duration: null` precedent (`conferred_growth_rate`) ship today.

## Goals / Non-Goals

**Goals:**

- Equipment immunity enforced at staging time with a visible deterministic
  neutralization event, plus a no-write backstop at the chokepoint.
- Attached buffs owned by the toggle transaction, orphan-free and
  rollback-safe (including the singleton-slot replacement case).
- 受洗聖水 purges debuffs as a registered item effect with journal-level
  buff rollback.
- Players can read what equipment does (adjustment prose).

**Non-Goals:**

- `pleasure_gain`/`exposure_bias` (P4), `equipment_worn` rules (P5), panel
  payload changes (P6/P7), immunity for NPCs/monsters (they never wear
  equipment; an empty worn set is the universal non-immunity).

## Decisions

### D1 — Immunity decided at staging; chokepoint gate is a write backstop

Because the event tag is fixed when `PendingEffect` is built, an
`IMMUNE`-at-`_add_buff` design cannot produce the required event. Instead:
the two buff-staging handlers check the pure predicate
`equipment_immune_buff_keys(target)` — only for definitions whose rulebook
`polarity` is `debuff` — BEFORE building the effect. For an immune target
they stage, exactly like `_resist_pending_effect`, a non-mutating pending
effect tagged `equipment_immune|<entity>|<buff_key>` with 正體中文 renderer
text in the shipped event-text map, so actor and target see the
neutralization and the roll is never silently lied about. `_add_buff()`
keeps an independent no-write gate for the same predicate as a defense-in-
depth backstop for any direct caller; the requirement that grants produce an
event is scoped to the action-resolution workflow (the only shipped debuff
writer). Alternatives — translating an `_add_buff` sentinel at the call
site: rejected, the lambda return is discarded by the effect-commit layer;
gating only in `_add_buff`: rejected, it cannot emit the event.

Immunity semantics (spelled into the spec): the predicate rejects NEW
debuff grants while the item is worn. It does not retroactively cleanse,
pause, or un-tick debuffs that were already applied — equipping 淨化吊墜
mid-poison does not cure the poison.

### D2 — Attached buffs: worn-set-diff lifecycle in the toggle transaction

Within `toggle_equipment()`'s existing transaction, the plan already knows
`worn_before`/`worn_after`. Attachments are recomputed as set diffs —
`added = worn_after − worn_before`, `removed = worn_before − worn_after`
(by item key) — instances removed first, then applied, so replacing item A
with item B in a singleton slot in ONE toggle removes exactly A's instance
and adds exactly B's. Instances are keyed `<definition_key>:<item_key>`
with `source_key = item_key`, `unique_per_source`, `duration: null` (the
`conferred_growth_rate` precedent); two items attaching the same buff
coexist as distinct sources. The `buffs` dbkey joins the snapshot set via
`surfaces.attribute_snapshot(actor, "buffs")` and
`restore_attribute_best_effort` — sound because `BuffHandler` re-reads the
attribute on every access (no private cache), and restore writes through
the attribute handler, refreshing the live in-memory attribute cache.
Attached-buff instances SHALL NOT carry gauge-ceiling stat modifiers:
gauge headroom is owned exclusively by P2's worn-set recompute (a future
equipment cap must go through that path, validated at rulebook load).
Only the toggle path creates attached instances; monsters never wear.

### D3 — `blessed_cleansing`: registered effect + journal-level buff rollback

`ItemEffectKey.BLESSED_CLEANSE` joins the closed vocabulary; the
item-effects rulebook entry for `baptismal_holy_water` switches from its
healing amount to the cleanse form (loader: cleanse entries carry no
amount; heal entries keep requiring one). Preflight requires at least one
active debuff: zero debuffs rejects with a new `ItemUseReason.NO_DEBUFFS`
(mirroring `hp_full`), rendered through the shipped reason renderers
(`service_messages` and the out-of-combat command/web consumers) in
正體中文, consuming nothing and advancing no world clock. The settlement
reuses the shipped `cleanse:status` removal path, and `ItemTouchedJournal`
gains a `buffs` surface: `capture()` snapshots the `buffs` dbkey without
materializing the handler and `restore()` restores it through the attribute
handler — a post-cleanse failure therefore rolls back persistence AND live
handler reads, keeping the existing all-or-nothing contract. Doctrine:
光明 淨化 as the Church's signature consumable.

### D4 — One server-side prose formatter, read surfaces unchanged

`equipment_adjustment_text(item_key)` composes a deterministic 正體中文
summary from the rulebook entry with one exact contract: segments joined by
「｜」 in field-vocabulary declaration order
(攻擊／防禦／敏捷／魔力／施法消耗／治療／生命上限／法力上限／體力上限／免疫),
signed integers, percent fields rendered as `±N%`, gauge fields rendered as
`<gauge>上限 ±N`, zero-valued fields omitted. Surfaces: successful toggle
result message, item inspection/look rows for equipment items, accessory
listing rows. No command keys/aliases/syntax change, so the command-docs
contract is untouched; prose lives in message payloads only.

## Risks / Trade-offs

- [Staging-time check duplicates the gate inside `_add_buff`] → both call
  the same pure predicate; the duplicate is the deliberate backstop, not a
  second formula.
- [Attached regen ticks out of combat through the world clock] → intended
  (slow out-of-combat recovery is the item's fantasy); rate is rulebook
  data, not code.
- [Holy water loses its old heal effect] → unreleased project, zero users;
  doctrine fit replaces it outright (no migration per AGENTS.md).
- [A neutralization event per grant attempt could spam] → each attempt is a
  real action cost; event log already compresses repeats.
- [Journal buff restore after handler `remove()` calls fired side hooks] →
  shipped buffs' `at_remove` hooks only touch the cache being restored;
  fault-injection test pins the contract.

## Open Questions

None.
