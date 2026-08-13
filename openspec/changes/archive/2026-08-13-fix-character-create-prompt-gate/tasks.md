## 1. Gate-aware prompt routing

- [x] 1.1 Extend `CmdCreationRequired` in `commands/character_creation.py`: add the `CMD_NOINPUT` alias and, in `func()`, first resolve `caller.ndb._getinput` (with the stock account-level fallback); when a prompt is open, feed `self.raw_string.rstrip()` into its stored callback exactly like Evennia's `CmdGetInput.func` (including the `_getinput` teardown and `InputCmdSet` removal when the callback returns falsy, state preservation when it returns truthy, and cleanup plus trace logging on exception); when no prompt is open, keep the exact current creation-required message
- [x] 1.2 Verify the wizard still rejects `age=17`, keeps all-or-nothing activation, and leaves the gate `Replace`/priority-200 contract untouched (no changes to `CharacterCreationCmdSet`)

## 2. Regression tests

- [x] 2.1 Add a merged-cmdset contract test in `commands/tests/test_character_creation.py`: merge `InputCmdSet` + `CharacterCreationCmdSet` in cmdhandler order and assert the surviving `__nomatch_command` is an instance of `CmdCreationRequired` (and that `CmdGetInput` is absent) and that `cmdset.get(CMD_NOINPUT)` resolves to it
- [x] 2.2 Add direct handler tests: with a stub `ndb._getinput` + mock callback, `CmdCreationRequired.func()` forwards the raw reply; a falsy callback return cleans up (`_getinput` deleted, `input_cmdset` removed) while a truthy return preserves both; without `_getinput` it emits the creation-required message and changes nothing; a throwing callback still cleans up
- [x] 2.3 Add an account-fallback direct test: prompt state on `caller.account.ndb._getinput` is routed with the account as callback receiver and torn down on the account
- [x] 2.4 Add a shared queued-`deferLater` test helper (capture callbacks, run `execute_cmd` first, then drain the queue) with a module docstring explaining the cleanup-before-resume reactor ordering; use it for all real-handler end-to-end tests
- [x] 2.5 Real-handler end-to-end cancel test: `execute_cmd("character create")` shows the name prompt and mounts `_getinput`; `execute_cmd("cancel")` + drain returns `已取消角色建立`, the shell stays pending, and `_getinput`/`input_cmdset` are gone
- [x] 2.6 Real-handler end-to-end success test: drive `character create` to completion (name, ages, race, subrace, allocations, `yes`) with drain after each reply and assert activation succeeds
- [x] 2.7 Real-handler end-to-end failure test: reply with a non-integer age, then assert the input-error message, pending state, and `_getinput`/`input_cmdset` teardown
- [x] 2.8 Real-handler sync-concept continuation test: `character concept` with an already-fired proposal reaches the name prompt through the real handler and `cancel` exits cleanly
- [x] 2.9 Add a gate empty-input test: an empty line with no open prompt emits the creation-required message
- [x] 2.10 Confirm existing wizard/concept tests (including the async `_ConceptPromptCmdSet` flow) still pass

## 3. Verification

- [x] 3.1 Run `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands` and confirm green
- [x] 3.2 Run `uv run --locked python -m compileall -q world typeclasses commands server` and `git diff --check` clean
- [x] 3.3 Run `uv run --locked python -m tools.spec_traceability check`; annotate with literal `covers_requirement` IDs for BOTH the modified `player-character-creation` gate requirement and the ADDED `character-creation-ux` requirement (the real-handler success/cancel tests are the substantive coverage for the new UX requirement)
