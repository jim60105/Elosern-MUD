# Proposal: Companion field casting rule and text suffix

## Why

Design §4.4 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: out-of-combat field casting takes an actor. Costs go to the actor, SELF binds to the actor, practice XP accrues to the actor through the existing path, and the time cost equals the commander's. Today `world/rules/field_cast.py::cast_in_field(actor, ...)` is only ever called with the puppet.

## What Changes

- New rules entry `cast_as_member(acting, member_id, skill_key, *, targets, opening_target, scale)` in `world/rules/field_cast.py`: member boundary (acting purpose), then `cast_in_field(member, ...)`. A companion's cast at a co-located monster opens combat through the existing field-initiation path under the commander's session, seeding the companion's opening draft entry (user decision of 2026-10-18).
- Target candidates for an ordinary field cast stay room-relative; SELF binds to the caster (existing resolver behaviour once the caster is the request actor).
- Text: `cast ... 由 <成員>` outside combat casts as the member; inside an active session it saves that member's skill command through the existing `combat command` actor path.
- Both player command documents describe the suffix.

## Capabilities

### New Capabilities

- `companion-field-actions`: explicit-caster field casting (this change) and explicit-user item use (`companion-field-item-use`).

### Modified Capabilities

- `field-combat-initiation`: a companion initiator opens the commander's encounter and seeds its own opening entry.
- `game-command-docs`: the `cast` reference syntax documents the `由 <成員>` suffix.

## Impact

- `world/rules/field_cast.py`, `commands/action.py` (`CmdCast` suffix parse and session routing), `world/rules/combat_initiation.py` (companion initiator under the commander's session).
- Docs: `docs/game/commands.md`, `docs/game/command-reference.md`.
- Tests: `world/rules/tests/test_companion_field_cast.py`, `commands/tests/test_cast_member_suffix.py` (sharded).

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **8 of 32**.

- depends-on: party-field-settlement-scope
- depends-on: party-member-equipment

### Code and spec conflicts within the new batch

- `party-field-settlement-scope`: shared file `world/rules/cast_settlement.py` only as a caller (D; scope must land first).
- `companion-field-cast-actions`: shared file `world/rules/field_cast.py` (preview helpers), shared spec `companion-field-actions` (F; this change first).
- `companion-field-item-use`: shared spec `companion-field-actions` (S).
- `party-unlock-notices`: shared file `commands/action.py` notification rendering (F; this change first).
- Command docs and `commands/default_cmdsets.py`-adjacent text rows: shared with every text-command change (F; ordered after `party-member-equipment`, which is why it is a declared prerequisite).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change. The v7 combat command contract is consumed unchanged.
