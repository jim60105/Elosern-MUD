## Why

Async freeform dialogue validates co-location and schedule state only before the LLM call; on completion the reply's intent (give/take item, adjust relation, reveal lore) applies with no recheck, so an intent can land after the player or NPC left the room or the NPC became busy (audit finding F22). Party-invite and exam intents already re-verify; the remaining intent kinds do not.

## What Changes

- After an async exchange completes, the system revalidates that the player and NPC are still co-located and that the NPC is still interactable (`interaction_reason(..., "talk")`) before applying any intent.
- On a stale completion, the speech is still shown but the intent is discarded with a clear message; per-intent domain checks (e.g. party rechecks) remain.
- Applies to both the Web adapter and the NPC typeclass seam so all transports share the behavior.

## Capabilities

### Modified Capabilities

- `npc-dialogue`: completion-time context revalidation for async intents.
- `webclient-exploration-menu`: freeform-talk completion rechecks presence before intent application.

## Impact

- `typeclasses/npcs.py::at_talked_to`, `world/rules/npc_intents.py` (shared completion gate), `web/webclient/actions/exploration_actions.py`, tests.
