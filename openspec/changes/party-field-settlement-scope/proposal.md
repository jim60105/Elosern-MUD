# Proposal: Party-wide field cast and item use settlement

## Why

Design §4.6 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md` names out-of-combat field casting and item use as the third commander-initiated advance that must settle the commander plus every effective party member present. Today `world/rules/cast_settlement.py` and `world/rules/items/settlement.py` advance with `(request.actor,)` / `(actor,)` only.

## What Changes

- The out-of-combat cast settlement and the out-of-combat item-use settlement pass the acting character's present party scope (`party-member-authority`) to `WorldClock.advance`, and snapshot/restore every member in that scope on failure.
- The time cost is unchanged (the skill's `time_cost_seconds`, the six-second item use).
- Combat item use and combat casts are untouched (combat settlement owns their time).
- This slice changes scope only. Which member may act is owned by `companion-field-cast-rule` and `companion-field-item-use`; when they land, the scope still anchors on the acting member's room and includes the commander.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `party-time-settlement`: adds the field cast and item use requirement.
- `cast-settlement-atomicity`: the nested advance and its snapshot cover the present party.
- `item-use-resolution`: the six-second advance settles the present party.
- `world-clock`: the documented CmdCast and item-use call-site scopes.

## Impact

- `world/rules/cast_settlement.py` (`_snapshot_settlement_state`, the advance call, restore), `world/rules/items/settlement.py` (`build_advance_snapshot_registry`, `_restore_advance_registry`, the advance call).
- Tests: extend `world/rules/tests/test_party_time_settlement.py`; adjust existing cast/item settlement tests that pinned the single-entity tuple.
- Observability: existing `clock_advance` context gains `scope`; lint runs.

## Effort

**5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **3 of 30**.

- depends-on: party-rest-move-settlement

### Code and spec conflicts within the new batch

- `party-rest-move-settlement`: shared specs `world-clock`, `party-time-settlement` (S; this change re-modifies the same world-clock requirement after it).
- `companion-field-cast-rule`: shared file `world/rules/cast_settlement.py`; shared spec `cast-settlement-atomicity` not modified there (F; this change first).
- `companion-field-item-use`: shared file `world/rules/items/settlement.py`; shared spec `item-use-resolution` (F; this change first).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change.
