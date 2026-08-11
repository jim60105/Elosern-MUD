## 1. Client confirm-view gating

- [x] 1.1 In `creation_dock.js::_submitCustom`, move the `_pendingActivate`/`_view='confirm'` switch into the `creation.custom` success callback; on rejection/error stay on the form and render the rejection code
- [x] 1.2 Update the browser creation test to assert the confirmation view is not shown after a rejected save
- [x] 1.3 Gate the preset-card confirmation the same way (result-gated via request id; rejection rendered on the preset list) and add a browser test for a rejected preset save

## 2. Server-side activation binding

- [x] 2.1 Make `save_custom_draft`/the custom adapter return the fingerprint of the stored draft in the success result
- [x] 2.2 Make the activate adapter carry the confirmed fingerprint and reject with a stable code when it does not match the stored draft before activating
- [x] 2.3 Add a test: stale confirmation (fingerprint mismatch) is refused and no character is activated
- [x] 2.4 Invalidate the recorded confirmation on any rejected save (custom, preset, concept); add tests: activation after a rejected save is refused and no character is activated

## 3. Shared portrait finalization

- [x] 3.1 Extract `finalize_player_portrait(character)` into `world/rules/character_creation.py` (named policy + `transaction.on_commit(schedule_portrait_ensure)`)
- [x] 3.2 Call it from the Web `_creation_activate_adapter` after successful activation
- [x] 3.3 Call it inside the activation transaction in the shared activation path and replace the Telnet-only block in `commands/character_creation.py`
- [x] 3.4 Add tests: Web activation sets policy and queues exactly one ensure; activation-failure fault injection leaves no policy and no job

## 4. Verification

- [x] 4.1 Run `web/webclient/actions/tests`, `web/tests/browser/test_browser_creation.py`, and `world/rules` creation tests
- [x] 4.2 Update `docs/game/commands.md` only if player-visible command behavior changed (expected: none)
