# Proposal: 給 and 取回 member transfer commands

## Why

Design §4.1 and §4.8 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the text client must expose member transfer with `給 <物品> = <成員>` routed through the transfer rule and a new `取回 <物品> = <成員>` that returns an item to the commander. Today `給` (`commands/localized/general.py::CmdGive`) only pushes items from the caller to any character, and nothing pulls one back.

## What Changes

- `給 [數量] <物品> = <目標>`: when the target token resolves (via `resolve_member_token`) to the commander or an effective party member, route to `transfer_item(giver=caller, receiver=member)`; any other target keeps the existing give path (including quest delivery advancement).
- New `取回 [數量] <物品> = <成員>` (alias `retrieve`) in `commands/items.py`: `transfer_item(giver=member, receiver=commander)`.
- Both commands render the rule's fixed messages; both player command documents gain the syntax and context (out of combat only, free).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `party-item-transfer`: adds the text parity requirement.
- `equipment-inventory`: the localized `給` requirement distinguishes member targets from other targets.

## Impact

- `commands/localized/general.py` (CmdGive routing), `commands/items.py` (new CmdRetrieve), the character cmdset in `commands/default_cmdsets.py`.
- `docs/game/commands.md`, `docs/game/command-reference.md`; `tests/test_command_docs.py` stays green.
- Tests: `commands/tests/test_party_transfer_commands.py` (sharded).

## Effort

**4.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **5 of 30**.

- depends-on: party-item-transfer

### Code and spec conflicts within the new batch

- `party-member-equipment`, `companion-field-item-use`: shared file `commands/items.py`; shared player docs (F; ordered).
- `companion-field-cast-rule`, `party-practice-booking`, `shop-party-recipient-seller`, `member-info-text-commands`, `lineage-panel-v2-graphs`: shared files `docs/game/commands.md`, `docs/game/command-reference.md`, `commands/default_cmdsets.py` (F; ordered, append-only rows).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change.
