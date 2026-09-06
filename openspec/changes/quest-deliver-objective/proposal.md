# Proposal: quest-deliver-objective

## Why

The headline world-commission shape is a delivery: a shopkeeper hands the player a parcel to carry
to a named recipient. The existing objective vocabulary cannot express it. `ACQUIRE` advances only
on positive inventory deltas — it counts what you gain, and "removal never reverses progress" is an
explicit rule. `REACH` completes on arriving somewhere, which degrades "hand it to that person" into
"walk to that room" and leaves the parcel in the player's bag.

`DELIVER` is the missing mechanic: progress from a committed transfer of a specific item to a
specific recipient.

## What Changes

- New `ObjectiveKind.DELIVER` carrying `item_key`, `quantity`, and a recipient resolved through the
  existing `objective_target_ids` runtime binding (the same binding mechanism `DEFEAT` already uses
  for bound targets).
- Definition validation: a `DELIVER` objective SHALL require a registered `item_key`, a positive
  `quantity`, and `requires_bound_targets`; it SHALL forbid a destination and a monster tier.
- `describe_objective` renders the delivery line in Traditional Chinese using the item registry's
  display name and the bound recipient.
- New observer `world/quests/deliver.py`, structurally parallel to `acquire.py`: given a committed
  item transfer, compute the quest-log replacement for every active `DELIVER` stage whose item and
  bound recipient match. It computes; it does not write.
- The existing `_transfer_items` primitive (used by the dialogue `take_item` intent) calls the
  observer for the **giver** side inside its existing transaction, so a player handing a parcel to a
  bound recipient advances the objective atomically with the transfer.
- Stage advance and completion reuse `fulfill_record_for` unchanged, so a `DELIVER` final stage
  completes exactly like every other kind.

## Capabilities

### New Capabilities

- `quest-delivery`: the `DELIVER` objective — its definition contract, validation rules, rendered
  prose, recipient binding, the committed-transfer progress rule, and the guarantee that only a
  transfer to the bound recipient counts.

### Modified Capabilities

- `quest-progress-tracking`: the automatic-progress surface gains a fourth mechanic; committed item
  transfers join committed action events, room arrival, and inventory additions as progress sources.

## Impact

- `world/quests/definitions.py`: the objective kind and its validation branch.
- `world/quests/describe.py`: the delivery objective line.
- New `world/quests/deliver.py` observer.
- `world/rules/npc_intents.py`: `_transfer_items` calls the observer for the giver side.
- No player-facing action yet — `quest-deliver-action` supplies the deterministic player verb. Until
  it lands, `DELIVER` advances only through the dialogue-driven transfer, which is stated as a
  deliberate intermediate state rather than a shipped feature.
