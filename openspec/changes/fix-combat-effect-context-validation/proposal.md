## Why

`status_disguise` and `dominion_art` appear enabled in the combat menu and pass `preflight()` because both check only that the effect prefix is registered; their handlers require `event_context` fields that combat sessions never supply, so the action rejects only after initiative — consuming the player's turn with the enemy acting for free (audit finding F19).

## What Changes

- Effect handlers declare their required `event_context` keys; preview and `preflight()` validate handler-specific context before initiative.
- The combat menu marks skills whose required context cannot be supplied as unavailable, instead of advertising them enabled.
- Out-of-combat casting keeps working: commands that do supply the context (e.g. disguise context for `status_disguise`) are unaffected.

## Capabilities

### New Capabilities

- `effect-context-validation`: handler-declared `event_context` requirements checked by preview and preflight.

### Modified Capabilities

- `action-resolution-pipeline`: preflight rejects actions whose handler context is missing, before any round cost.
- `webclient-combat-menu`: availability reflects context requirements.

## Impact

- `world/rules/action.py` (handler context declarations + preflight), `world/rules/action_preview.py`, `world/rules/combat_view.py`, `world/rules/combat_session.py` (session context builder), tests.
