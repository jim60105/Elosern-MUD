# Proposal: Revision-bound exit confirmation and surrender settlement

## Why

Unconfirmed forfeit and personal flee allow party consequences without an explicit party-scoped decision.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- Revision-bound exit confirmation and surrender settlement. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `player-combat-session`: amend the requirements owned by this bounded slice.

## Impact

Implemented surfaces: the new `world/rules/combat_session/exit.py` (request/confirm/token/operation dispatch) and `world/rules/combat_session/__init__.py` re-exports; `world/rules/combat_session/{errors,settlement,rounds}.py`; `world/rules/combat_view.py` (the allied flee row leaves the session skill list); `world/rules/player_messages.py` (the new session reasons and the shared zh-TW party-exit prompt copy); `commands/combat.py` and `commands/action.py` (the confirming text route and the in-session `flee` route); `web/webclient/actions/combat_actions.py` (borrowed from change 12: the flee row reaches the boundary without escaping, the forfeit adapter reaches it through the mounted confirmation window); `docs/game/commands.md`, `docs/game/command-reference.md`, `tests/test_command_docs.py`; test modules `world/rules/tests/test_confirmed_surrender.py` (new), `world/rules/tests/test_combat_view.py`, `test_combat_session_recovery.py`, `test_combat_session_flow/test_engage_and_player_rounds.py`, `commands/tests/test_combat_actions.py`, `web/webclient/actions/tests/test_combat_{actions,dispatcher}.py`, and the browser fixtures/tests for the removed flee row (`.github/evennia-shards.json`, `web/browser_support/browser_fixtures_data/*`). Deliberately untouched, unlike this list's earlier draft: `world/rules/combat_session/records.py` (the receipt write reuses the existing `last_combat_receipt` seam, so no record schema changes), `world/rules/defeat_aftermath.py` (no such module exists — the `world/rules/defeat_aftermath/` package is consumed unchanged) and `world/rules/disengage.py` (change 10 owns it; no second operation constant is introduced there).
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**6 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **9 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: party-combat-atomic-rounds

### Code and spec conflicts within the new batch

- `party-combat-actor-commands`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-persistent-drafts`: world/rules/combat_session/records.py; world/rules/combat_session/rounds.py; world/rules/combat_session/settlement.py; shared specs player-combat-session.
- `party-combat-atomic-rounds`: world/rules/combat_session/records.py; world/rules/combat_session/rounds.py; world/rules/combat_session/settlement.py; shared specs player-combat-session.
- `party-combat-opening-routing`: commands/action.py; docs/game/command-reference.md; docs/game/commands.md; world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-taunt-constraints`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-retreat-resolution`: world/rules/combat_session/rounds.py; world/rules/combat_session/settlement.py; world/rules/disengage.py; shared specs player-combat-session.
- `party-combat-text-commands`: commands/action.py; commands/combat.py; docs/game/command-reference.md; docs/game/commands.md; shared specs player-combat-session.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. The complete batch matrix records transitive coordination.
