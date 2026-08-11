## Why

Two WebClient lifecycle defects from audit run-1: (F14) `ooc`/unpuppet neither retires the presentation/dispatch sequence nor tells the client, a no-puppet `ui_action` is silently dropped leaving the client mutation lock permanently held, and repuppeting the same character reuses the old epoch and request cache; (F15) a terminal combat outcome flips the published mode to exploration but the update replaces only status/context_actions/art, leaving exploration/character/services/local_map panels stale (dead monster still attackable, pre-combat HP).

## What Changes

- The presentation/dispatch sequence is retired on the real puppet lifecycle: unpuppet clears the client view (and locks mutations) and repuppet — even of the same character — starts a fresh epoch/sequence.
- A no-puppet `ui_action` returns a bounded protocol rejection so the client can release its in-flight lock.
- Terminal combat outcomes publish a full snapshot (or an equivalent mode-change refresh) so no panel keeps combat-stale state.

## Capabilities

### Modified Capabilities

- `webclient-oob-protocol`: unpuppet/repuppet sequence handling and no-puppet action responses.
- `webclient-action-dispatch`: no-puppet actions receive a bounded rejection instead of silence.
- `webclient-combat-menu`: terminal outcomes refresh all mode-relevant panels.

## Impact

- `commands/localized/account.py` (OOC/IC hooks), `server/conf/inputfuncs.py::ui_action`, `web/webclient/presentation/ingress.py`, `web/webclient/presentation/coordinator.py`, `web/webclient/actions/dispatcher.py`, `world/rules/combat_result.py`, client `protocol.js`/`elosern_actions.js`, browser tests.
