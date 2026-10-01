## Why

An asynchronous NPC exchange is built from the card current at prompt time but settles later; if the author editor saves a new card in between, the old exchange can still speak, write memory, and apply intents in a voice the card no longer has. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §7.2, §11.1 case 8) requires a persona-version completion gate on every consumer of the exchange seam, with a distinct stale-persona terminal. Split out of `npc-persona-dialogue-consumption` so each is one workday; it depends only on the foundation's metadata.

## What Changes

- `run_npc_exchange` captures the NPC's `persona_version` when it builds the prompt and compares at settlement; any inequality yields a new stale-persona terminal (`DialogueExchangeResult.stale_persona`) that suppresses speech, NPC memory append, intent application, session-line recording, and the degraded invite threshold, settles with one localized explanation, and never retries.
- Wired through `at_talked_to`, `explore.talk_freeform`, `explore.party_invite`, and the text `invite` command.
- Read-only `current_persona_version(npc)` helper in `world/rules/npc_persona.py`; `STALE_PERSONA_NOTE` in `world/rules/player_messages.py`; event `npc_dialogue_stale_persona`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-dialogue`: ADDED persona-version completion gate across all exchange consumers.

## Impact

- Code: `typeclasses/npcs.py` (`run_npc_exchange`, `at_talked_to` result handling, `DialogueExchangeResult`), `world/rules/npc_persona.py` (one read-only helper), `world/rules/player_messages.py`, `web/webclient/actions/exploration_actions.py` (talk_freeform and party_invite mapping), `commands/invite.py`.
- Tests: `typeclasses/tests/`, `web/webclient/actions/tests/`, `commands/tests/` (package-owned shard labels).
- Observability catalog row for the new event.

## Batch:

depends-on: npc-persona-card-foundation

Code-conflict notes: `typeclasses/npcs.py` is also edited by `npc-persona-dialogue-consumption` (field set, frame, and the degraded-greeting branch of `at_talked_to`); this change edits `run_npc_exchange`, `DialogueExchangeResult`, and the stale branch at the top of `at_talked_to`'s result handling — adjacent hunks, so apply the two sequentially or rebase mechanically. Sole editor in this batch of `commands/invite.py` and of `web/webclient/actions/exploration_actions.py`; it must keep the private `_present_by_id` helper's name and signature unchanged because `npc-persona-editor-actions` imports it. `world/rules/npc_persona.py` gains one read-only function (mechanical rebase with other additions).
