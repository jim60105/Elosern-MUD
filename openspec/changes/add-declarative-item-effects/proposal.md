# Proposal: add-declarative-item-effects

## Why

A usable item today declares one member of a four-member closed enumeration
(`ItemEffectKey`: `self_heal`, `greater_heal`, `mana_restore`, `blessed_cleansing`), and
`world/rules/items.py` hard-codes the rest — a key-to-gauge map, a dedicated branch for cleansing, a
per-gauge rejection table, and a per-gauge Chinese noun for the event text. Three consequences block
`docs/lore/items.md`:

1. **Every new effect is a schema change.** 解毒, 回復體力值, 持續回春, and 催情 are all flagged in
   the lore document as blocked behind "a dedicated enumeration extension and design review", and the
   whole 性玩具 category is blocked on the same list.
2. **One item can express exactly one effect.** 靈露 is specified as an extreme aphrodisiac whose
   wound-closing is a downstream consequence — two effects on one drink, unrepresentable today.
3. **Magnitudes are keyed by effect, not by item**, so two items can never share an effect shape with
   different strengths without minting a third enumeration member.

The approved design is `docs/superpowers/specs/2026-09-14-item-effect-model-design.md`. This change
implements §3 and §5 of it for **self-scoped effects only**; the `add-item-effect-targeting`
follow-up widens the scope vocabulary to other entities.

## What Changes

- **BREAKING**: delete `ItemEffectKey` from `world/lore/items.py`. `ItemUseMechanics` keeps only
  `consumable` and `combat_allowed`; the registry declares the *shape* of the mechanic and owns no
  magnitude, exactly as it already does for equipment.
- Re-key `world/rules/rulebook/item_effects.yaml` by **item key**, each entry carrying an ordered
  list of 1..N effects. Each effect carries exactly one verb: `stat` + signed `amount`,
  `apply_status`, or `remove_status`.
- Add `world/rules/item_effects.py`: the closed vocabularies (`ItemStat` = hp/mp/sp/pleasure;
  `ItemTargetScope`), the three frozen effect dataclasses, and a validating loader enforcing
  two-way alignment with the registry — an orphan entry and a missing entry both fail startup,
  mirroring `equipment_effects.py`.
- Rewrite `world/rules/items.py` preflight and settlement around an ordered step list: one
  `ItemEffectStep` per effect, each carrying the magnitude actually applicable to current state.
  Rejection happens only when **no** step is effective; the reason code is the shared one when every
  ineffective step agrees, and `no_effect` otherwise — so today's `hp_full`, `mp_full`, and
  `no_debuffs` behavior survives unchanged for single-effect items.
- Bind each effect verb to the shared entry point `extract-shared-effect-appliers` published:
  `_write_gauge` for hp/mp/sp, `apply_pleasure_gain` for pleasure, `apply_buff` for `apply_status`,
  `remove_by_selector` for `remove_status`.
- **BREAKING**: the `item_used` EventLog entry drops `effect_key`; one entry is emitted per
  **effective** step, carrying either `{stat, amount}` or `{status_keys, count}`.
- `ItemUseReason` gains `SP_FULL`, `PLEASURE_FULL`, `NO_EFFECT`, `STATUS_BLOCKED` (an
  `apply_status` whose target is equipment-immune to it) and `NOTHING_TO_REMOVE` (a `remove_status`
  selector matching nothing, for every selector except `negative`, which keeps the shipped
  `no_debuffs` reason), each with a Traditional Chinese message. Completing the per-family reason
  vocabulary now keeps the "each ineffective effect names its own reason" rule true for the status
  verbs as well as the stat verb, rather than leaving them to fall through to the generic code.
- Migrate the four shipped items at identical magnitudes: `hp +40`, `hp +120`, `mp +40`, and
  `remove_status: negative`. **No balance changes.**
- **Scope limit**: this change accepts only `scope: self`. The scope vocabulary is defined and
  validated, and the loader rejects any other value with a message naming the follow-up change — a
  forward-declared seam in the sense `AGENTS.md` sanctions.

## Capabilities

### New Capabilities

- `item-effect-rulebook`: the declarative item-effect vocabulary and its validated rulebook — the
  three effect verbs, the stat and scope vocabularies, the status selectors, the amount bounds, and
  the two-way registry alignment the loader enforces at startup. This mirrors `equipment-effects`,
  which already owns the equivalent contract for worn items, and keeps the effect *vocabulary*
  separate from `item-use-resolution`, which owns *settlement*.

### Modified Capabilities

- `item-use-resolution`: the mechanics-declaration requirement loses the effect key and binds by item
  key instead; preflight becomes per-step effectiveness with the at-least-one rule and the shared
  reason-code fallback; settlement applies an ordered step list atomically; the EventLog requirement
  becomes one entry per effective step with the new payload shapes; the blessed-cleansing requirement
  is restated as a `remove_status: negative` effect on 受洗聖水 rather than a named effect key.

## Impact

- **Code**: `world/lore/items.py` (`ItemEffectKey` deleted, `ItemUseMechanics` slimmed, four
  definitions updated), new `world/rules/item_effects.py`, `world/rules/items.py` (preflight, plan,
  settlement, event log — the bulk of the change), `world/rules/rulebook/item_effects.yaml` (re-keyed),
  `world/rules/service_messages.py` (three new reasons).
- **Consumers that do not change**: `world/rules/service_view.py`, `commands/items.py`,
  `web/webclient/actions/service_actions.py`, and `world/rules/combat_session.py` keep their current
  signatures, because every shipped item stays self-scoped. They change in
  `add-item-effect-targeting`.
- **Tests**: `world/rules/tests/test_item_effects_rulebook.py` (rewritten for the new loader),
  `test_item_use.py`, `test_holy_water_cleanse.py`, `test_item_combat_turn.py`,
  `world/lore/tests/test_items.py`, `commands/tests/test_items.py`,
  `web/webclient/actions/tests/test_inventory_actions.py`, `world/tests/synthetic_data.py`, and
  `world/rules/tests/test_equipment_combat_wiring.py` — the last one is **not** an import-path fix: it
  builds `ItemUseMechanics(effect_key=...)` at `:188`, derives `_HEAL_AMOUNT` from
  `ITEM_EFFECT_RULES[ItemEffectKey.SELF_HEAL].amount` at `:191`, and asserts on `preflight.plan.amount`
  and `preflight.plan.gauge_restored` at `:693-694`, all of which the rewrite removes.
- **Docs**: `docs/lore/items.md` 第六層 and the pending-effect notes in 藥劑 and 性玩具;
  `docs/development/adding-items.md` §1 table, §2 question 4, and §5.
- **Depends on**: `extract-shared-effect-appliers` (the four entry points). Does **not** depend on
  `refactor-target-resolution-srp`.
- **Data**: none. No migration (unreleased project, zero users).
