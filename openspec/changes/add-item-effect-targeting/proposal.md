# Proposal: add-item-effect-targeting

## Why

`add-declarative-item-effects` shipped the declarative effect model but deliberately accepts only one
target scope: the acting entity. Its loader rejects every other scope with a message naming this
change. Three lore-specified items have no representation until that restriction lifts:
女神之吻聖霧 (a spray reaching everyone nearby), 情欲香爐 (a censer whose smoke fills a space), and
every future thrown or offensive consumable — the `{stat: hp, amount: -N, scope: single}` shape the
model already knows how to describe but cannot yet resolve.

`refactor-target-resolution-srp` removed the last obstacle on the other side: `resolve_targets` now
takes a `TargetRequirement` rather than a `SkillDef`, so an item scope can map to a requirement and
reuse the shipped presence/alive/range/faction pipeline instead of growing a second one.

## What Changes

- Lift the loader's self-only restriction. All five scopes — the acting entity, one other entity, own
  side, opposing side, everyone — become valid, each mapping to a fixed `TargetRequirement`.
- Add an optional single explicit target to the item-use request. The player supplies **at most one**
  target for a whole use: self scopes resolve to the actor, group scopes expand through the action
  context, and a single scope consumes the supplied target. Unlike a skill, an item's reach is a
  property of the item and is fixed in the rulebook — the player never chooses a group shorthand.
- Thread an `ActionContext` through item preflight: the battlefield context in an active session, a
  room context out of combat. Enablement descriptors, the text command, the UI adapter, and the
  combat-session facade all supply it.
- **BREAKING**: `ItemTouchedJournal` becomes multi-entity. Inventory, quest, and contained-mirror
  surfaces stay actor-only (only the actor consumes), while trait, buff, and sexual-state surfaces —
  **and the in-process cache drop that pops the memoized `entity.sexual` handler** — are captured and
  restored per touched target. The combat resolver's outer rollback contract folds the multi-entity
  journal in.
- The EventLog's target list becomes the deduplicated set of entities actually touched, rather than
  always the actor; each `item_used` entry names its own target.
- `ItemUseReason` gains `NO_TARGET` (a single scope with no target supplied) and `TARGET_INVALID` (the
  shared resolver rejected the supplied target, carrying the resolver's own reason as detail).
- **BREAKING**: `使用 <item_key>` becomes `使用 <item_key> [target]`, and the `inventory.use` UI
  payload gains an optional bounded `target_key`. The payload's existing prohibition on client-chosen
  effects, slots, and quantities is unchanged — a target names *whom*, never *what*.
- Combat round occupancy is unchanged: a multi-target item still consumes exactly one
  initiative-ordered round.

## Capabilities

### New Capabilities

None. Every change extends a capability `add-declarative-item-effects` or an earlier change created.

### Modified Capabilities

- `item-effect-rulebook`: the self-only scope restriction is replaced by the full scope vocabulary and
  its mapping to targeting requirements, including that an item's reach is fixed by the rulebook and
  never chosen by the player.
- `item-use-resolution`: preflight gains the action context and the optional explicit target, and
  resolves each effect's targets through the shared resolver; settlement's atomicity and rollback
  requirements extend to every touched entity; the EventLog requirement names a per-entry target; the
  combat-round requirement states explicitly that target count does not affect round count.
- `inventory-item-actions`: the `inventory.use` payload accepts an optional target key alongside the
  item key, and the text command syntax gains its optional target argument. The prohibition on
  client-chosen effect, slot, quantity, HP, combat, and presentation fields is unchanged.

## Impact

- **Code**: `world/rules/item_effects.py` (scope acceptance and requirement mapping),
  `world/rules/clock.py`'s `_refresh_advance_entity_caches` (called per touched entity rather than
  for the actor alone — the call sites change, not the function),
  `world/rules/items.py` (request shape, context parameter, per-effect target resolution, multi-entity
  journal, event targets), `world/rules/service_view.py:770` (builds a room context),
  `world/rules/combat_session.py:1235` and `:1248` (target and battlefield context),
  `world/rules/combat.py:659` (rollback contract), `commands/items.py` (target argument),
  `web/webclient/actions/service_actions.py:503` (payload target), `world/rules/service_messages.py`
  (two new reasons).
- **Tests**: `world/rules/tests/test_item_use.py`, `test_item_combat_turn.py`,
  `test_item_effects_rulebook.py`, `commands/tests/test_items.py`,
  `web/webclient/actions/tests/test_inventory_actions.py`, plus new multi-target and multi-entity
  rollback suites.
- **Docs**: `docs/game/commands.md` and `docs/game/command-reference.md` (the command syntax change is
  required by `inventory-item-actions` to land in the same change), `docs/lore/items.md` 第六層 scope
  table, `docs/development/adding-items.md` §2.
- **Depends on**: `refactor-target-resolution-srp` (the requirement-based resolver) and
  `add-declarative-item-effects` (the effect model). Both must be implemented before this change.
- **Data**: none. No migration (unreleased project, zero users). No shipped item changes scope; the
  five scopes become available for content that has not been written yet.
- **Archive ordering**: this change's `item-effect-rulebook` delta modifies a spec that
  `add-declarative-item-effects` creates, so that change must be archived first. `openspec validate`
  reports this as an expected informational notice until then.
