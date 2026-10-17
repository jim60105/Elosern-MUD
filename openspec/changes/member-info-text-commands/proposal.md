# Proposal: 狀態 and 技能 member text views

## Why

Design §4.8 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md` requires `狀態 <成員>` and `技能 <成員>` so the text client sees any member's data (text-client parity for the 狀態 and 技能 tabs). Today only `看` on oneself prints the breakdown, and no command lists a companion's skills or growth.

## What Changes

- New read-only commands `狀態 [<成員>]` (alias `status`) and `技能 [<成員>]` (alias `skills`) in `commands/party_views.py`, resolving the member with `resolve_member_token` (membership only; an absent member can still be viewed), defaulting to the commander, rendering from the same read models the `character` v9 panel uses.
- Both player command documents gain the commands. `系譜 <成員>` is owned by `lineage-panel-v2-graphs`.

## Capabilities

### New Capabilities

- `party-member-text-views`: the text member status and skill views.

### Modified Capabilities

None.

## Impact

- New `commands/party_views.py`, `commands/default_cmdsets.py`; reuses `world/rules/status_query`, `world/rules/status_text.py`, the character skill-row read helpers.
- Docs: both player command documents.
- Tests: `commands/tests/test_party_views.py` (sharded).

## Effort

**4.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **17 of 31**.

- depends-on: character-skill-growth-fields

### Code and spec conflicts within the new batch

- Text-command changes share both command docs and `commands/default_cmdsets.py` (F; ordered, append-only).
- `lineage-panel-v2-graphs`: adds `系譜 <成員>` next to these commands in the docs (F; this change first).

### Active change coordination

No active OpenSpec change.
