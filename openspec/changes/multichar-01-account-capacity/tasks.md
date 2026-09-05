# Tasks: multichar-01-account-capacity

## 1. The character-capacity knob

- [ ] 1.1 `server/conf/settings.py`: add
  `MAX_NR_CHARACTERS = _env_int_bounded("ELOSERN_MAX_CHARACTERS", 5, low=1, high=10)` beside the
  other `ELOSERN_*` deployment knobs, with a comment naming the roster/dropdown bound as the
  reason for the upper limit.
- [ ] 1.2 `.env.example`: add the commented `#ELOSERN_MAX_CHARACTERS=5` entry in the
  `ELOSERN_*` block, matching the file's existing comment style.
- [ ] 1.3 `docs/development/settings-and-environment.md`: add the `ELOSERN_MAX_CHARACTERS` row
  (variable / reader / type / default / validation rule), matching the `ELOSERN_VUE_CLIENT` row's
  shape.
- [ ] 1.4 `server/conf/test_settings.py`: confirm the env-scrubbing list is derived rather than
  hand-written; add `ELOSERN_MAX_CHARACTERS` explicitly if it is a literal list.

## 2. Login screens keyed to the session's puppet

- [ ] 2.1 `typeclasses/accounts.py`: change `at_post_login` to resolve the session's own puppet
  after `super().at_post_login(...)` and send `render_pending_character_login` only when that
  puppet is non-`None` and `creation_pending`. Retire `_pending_character`'s account-wide scan
  from the login path (delete it if it has no other reader).
- [ ] 2.2 Keep `render_pending_character_login` as the single coordinator (world introduction then
  creation start screen) and keep its `session=` targeting.

## 3. Localized OOC surface and the account command locks

- [ ] 3.1 `commands/localized/account.py`: delete the `_AUTO_PUPPET_ON_LOGIN and
  _MAX_NR_CHARACTERS == 1` branches from `CmdOOCLook.func` and `CmdOOC.func`, so both fall through
  to `account.at_look(target=self.playable, session=...)`. Delete the now-unused module-level
  `_MAX_NR_CHARACTERS` binding (and `_AUTO_PUPPET_ON_LOGIN` if it loses its last reader).
- [ ] 3.2 `commands/default_cmdsets.py`: in `AccountCmdSet.at_cmdset_creation`, remove the
  upstream `charcreate` / `chardelete` keys and re-add project subclasses carrying
  `locks = "cmd:perm(Developer)"`, using the same remove-then-add mechanism as the localized
  wrappers. Keep their keys, aliases, and behaviour otherwise untouched.
- [ ] 3.3 `docs/game/command-reference.md`: update the `charcreate` / `chardelete` rows to state
  the Developer permission requirement explicitly, and check `docs/game/commands.md`'s admin
  category for a matching mention.

## 4. Tests

- [ ] 4.1 `server/conf/tests/test_env_overrides.py`: default is 5; `=1` and `=10` accepted; `=0`,
  `=11`, and a non-integer each raise the named settings error; the `.env.example` inventory check
  and the settings-guide check both pass with the new key.
- [ ] 4.2 New account-capacity test beside the account typeclass tests (`EvenniaTest`): create
  characters up to the cap on one account, assert each is in `account.characters` and
  `creation_pending`, then assert the cap+1st `create_character` returns `(None, [error])` and
  leaves `account.characters` unchanged.
- [ ] 4.3 Login-screen test: an account owning one activated and one pending character, logging in
  as the activated one, receives neither the world introduction nor the creation start screen; the
  same account logging in as the pending one receives both; an unpuppeted login receives neither.
- [ ] 4.4 `commands/tests/test_localized.py`: `離開角色` and OOC `看` render the playable-character
  list at both `MAX_NR_CHARACTERS=1` and a raised cap, and never print the retired
  「使用 進入世界 回到遊戲」 hint.
- [ ] 4.5 `tests/test_command_docs.py`: extend the Developer-lock assertion to cover `charcreate`
  and `chardelete`, and keep the reference/overview drift checks green.
- [ ] 4.6 Add the `covers_requirement` annotations for the four delta requirements
  (IDs from `uv run --locked python -m tools.spec_traceability list`).

## 5. Verification

- [ ] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  commands server typeclasses world` and `uv run --locked python -m tools.spec_traceability check`.
- [ ] 5.2 `uv run --locked python -m tools.observability_lint check` and
  `uv run --locked python -m compileall -q world typeclasses commands server`.
- [ ] 5.3 Repo-wide grep for `MAX_NR_CHARACTERS` to confirm no other module snapshots it at import
  time.
- [ ] 5.4 Live container check: register a fresh account, complete creation, then confirm a
  Developer account can `charcreate` a second shell and `進入世界` switches between them, while a
  Player-permission account is refused.
