## 1. Client confirm-view gating

- [ ] 1.1 In `creation_dock.js::_submitCustom`, move the `_pendingActivate`/`_view='confirm'` switch into the `creation.custom` success callback; on rejection/error stay on the form and render the rejection code
- [ ] 1.2 Update the browser creation test to assert the confirmation view is not shown after a rejected save

## 2. Server-side activation binding

- [ ] 2.1 Make `save_custom_draft`/the custom adapter return the fingerprint of the stored draft in the success result
- [ ] 2.2 Make the activate adapter carry the confirmed fingerprint and reject with a stable code when it does not match the stored draft before activating
- [ ] 2.3 Add a test: stale confirmation (fingerprint mismatch) is refused and no character is activated

## 3. Shared portrait finalization

- [ ] 3.1 Extract `finalize_player_portrait(character)` into `world/rules/character_creation.py` (named policy + `transaction.on_commit(schedule_portrait_ensure)`)
- [ ] 3.2 Call it from the Web `_creation_activate_adapter` after successful activation
- [ ] 3.3 Call it inside the activation transaction in the shared activation path and replace the Telnet-only block in `commands/character_creation.py`
- [ ] 3.4 Add tests: Web activation sets policy and queues exactly one ensure; activation-failure fault injection leaves no policy and no job

## 4. Verification

- [ ] 4.1 Run `web/webclient/actions/tests`, `web/tests/browser/test_browser_creation.py`, and `world/rules` creation tests
- [ ] 4.2 Update `docs/game/commands.md` only if player-visible command behavior changed (expected: none)
