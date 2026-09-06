# Proposal: quest-deliver-general-give

## Why

The general give verb advances no delivery. Change 6's implementation research falsified the
quest-issuer design's premise that no give verb exists: the localized Evennia general give —
`commands/localized/general.py::CmdGive`, `key = "給"`, mounted in `CharacterCmdSet` — already
transfers `db.inventory` registry keys to a co-located target through `plan_inventory_delta` /
`apply_inventory_plan`. But it does not route through the delivery observer, so handing the parcel
to the bound recipient with `給 治療藥水 = 灰婆婆` moves the item into the recipient's inventory
while the quest does not advance — a silent trap, not a refusal. The item is gone and nothing tells
the player why.

This is not a hypothetical path: the main `quest-delivery` spec's scenario "Handing the parcel to
the bound recipient advances the stage" already demands that a committed transfer from the holder to
the bound recipient advances the stage, and `給` is exactly such a transfer. The current wiring
(only `world/rules/npc_intents.py::_transfer_items` calls the delivery advance) under-satisfies the
spec for the one movement verb every player knows. The quest-issuer design §13 "Follow-up notes
from implementation" records this gap and sketches this change.

## What Changes

- **One delivery-advance seam.** The committed-transfer advance block inside `_transfer_items`
  (compute the delivery replacement, apply the quest-log delta and pin operations, schedule the
  delivery events) is extracted into one public seam,
  `world/rules/npc_intents.py::advance_deliveries_for_transfer(...)`. `_transfer_items` calls it —
  a behavior-preserving refactor whose regression net is the existing
  `world.quests.tests.test_deliver` suite.
- **`CmdGive` advances deliveries.** Both of its transfer branches — the canonical-key branch (the
  key is held without a materialized mirror) and the materialized-object branch — call the seam
  inside their transactions, guarded by `_transfer_items`' full snapshot/restore discipline: both
  parties' inventory, quest log, and traits surfaces, the receiver plan's acquisition pin rooms,
  and the pin rooms the advance touches lazily; a failed advance additionally reconciles the moved
  or materialized objects' in-process caches. A failed advance rolls the whole give back to a
  byte-identical world and reports a safe message; the give's established refusals (unmovable
  items, refused moves) keep their existing outcomes.
- **The honesty split is preserved.** `給` stays a raw transfer: no quest-scoped refusals, no
  combat gate, no bound-recipient check — giving to an unbound recipient legitimately transfers
  without advancing anything, and only the committed-transfer observer decides progress. The
  quest-scoped refusal semantics (`not_colocated`, `no_active_delivery`, `item_not_held`,
  `in_combat`) remain the exclusive contract of `交付` / `explore.deliver` through
  `world/rules/quest_delivery.py`.
- **Documentation.** The `給` entries in `docs/game/commands.md` and `docs/game/command-reference.md`
  state that handing a quest item to its bound recipient advances the delivery, and that
  `交付` remains the quest-scoped verb. The drift contract test stays green.

## Impact

- `world/rules/npc_intents.py`: the extracted `advance_deliveries_for_transfer` seam; `_transfer_items`
  refactored onto it. No behavior change.
- `commands/localized/general.py`: `CmdGive.func` — snapshot discipline around both branches and
  the advance call inside each transaction.
- `commands/tests/test_localized.py`: give-advance integration tests (registry-key branch, object
  branch, unbound recipient, mid-combat give, rollback including acquisition-pin and
  contents-cache state).
- `world/quests/tests/test_deliver.py`: seam-level advance and rollback tests (the seam's own
  contract, shared by both callers).
- `docs/game/commands.md`, `docs/game/command-reference.md`: `給` prose.
- No schema, panel, or client-mirror changes. No shard manifest changes (both test modules are
  already registered).

## Non-Goals

- No general give for money or for unregistry objects beyond today's behavior.
- No combat gate on `給`: the raw transfer has no combat contract today, and a completed delivery
  grants no combat advantage. Mid-fight advancement through `給` is accepted; `交付` remains the
  gated quest surface.
- No change to `_transfer_items` semantics, to the delivery observer, or to `交付` /
  `explore.deliver`.
- No durability or migration concerns: the project has no released users.
