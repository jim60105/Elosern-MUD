## Why

The project ships Evennia's default `MAX_NR_CHARACTERS = 1`, never overridden in
`server/conf/settings.py`. Every layer of the multi-character feature — the account roster read
model, the switch/create actions, the TopBar switcher — is untestable until an account can
actually hold a second character.

Raising the cap is not a one-line settings edit. Three behaviours in the tree are correct today
*only* because the cap is 1, and each of them silently becomes wrong the moment it is raised:

1. `Account.at_post_login` sends the world introduction and the creation start screen when
   **any** character in the account is `creation_pending`, not when the session's own puppet is.
   An account holding one activated character plus one abandoned pending shell would then see the
   introduction on every login while walking around as its finished character.
2. `CmdOOCLook` / `CmdOOC` carry `_MAX_NR_CHARACTERS == 1` branches that become dead code paths
   whose surrounding zh-TW prose ("使用 |w進入世界|n 回到遊戲") no longer describes what happens.
3. Evennia's stock `charcreate` / `chardelete` are mounted in the project `AccountCmdSet` at
   `cmd:pperm(Player)`. `charcreate` is inert today only because the slot check always fails;
   raising the cap turns it into a live, unlocalized English creation entry that bypasses the
   creation wizard's confirmation, while `docs/game/command-reference.md` already documents both
   as 管理員 commands. `chardelete` is already live and already contradicts that documentation.

This change raises the capacity and repairs all three, so that changes 02–04 can build on an
account that genuinely supports several characters.

## What Changes

- Add `MAX_NR_CHARACTERS = _env_int_bounded("ELOSERN_MAX_CHARACTERS", 5, low=1, high=10)` to
  `server/conf/settings.py`, with the matching `.env.example` entry and
  `docs/development/settings-and-environment.md` row (both are contract-tested by
  `settings-environment-overrides`).
- Re-key the login world introduction and creation start screen to the **session's own puppet**
  instead of "any pending character in the account", so a multi-character account never re-reads
  the introduction because of an abandoned shell.
- Retire the `_MAX_NR_CHARACTERS == 1` special cases in `CmdOOCLook` / `CmdOOC`; both fall
  through to the account's playable-character list, which is now meaningful.
- **BREAKING (internal only, no released users):** restrict `charcreate` and `chardelete` to
  `cmd:perm(Developer)`, matching what `docs/game/command-reference.md` already claims. This keeps
  the WebClient wizard (and its client-side confirmation, added in change 03) the single player
  creation path, and closes a live "delete your only character" surface.
- Prove the raised capacity end to end: an account can hold up to the cap and the cap+1st
  `create_character` returns Evennia's slot error without creating an object.

## Capabilities

### New Capabilities

None. This change raises capacity and repairs existing behaviour; no new surface appears.

### Modified Capabilities

- `settings-environment-overrides`: the typed-knob table and the `.env.example` /
  settings-and-environment inventory gain `ELOSERN_MAX_CHARACTERS`.
- `connection-screen`: the world-introduction requirement is re-scoped from "the account's
  character" to "the character the session puppets at login", so an account owning several
  characters shows the introduction only while the puppeted one is pending.
- `player-character-creation`: an account SHALL be able to own more than one player character up
  to the configured cap, each with its own independent pending/activated lifecycle.
- `game-command-docs`: `charcreate` / `chardelete` become Developer-locked and the reference rows
  state that.

## Impact

- `server/conf/settings.py`, `.env.example`, `docs/development/settings-and-environment.md`.
- `typeclasses/accounts.py` (`_pending_character`, `at_post_login`,
  `render_pending_character_login`).
- `commands/localized/account.py` (`CmdOOCLook`, `CmdOOC`, `_MAX_NR_CHARACTERS`),
  `commands/default_cmdsets.py` (`AccountCmdSet` lock override).
- `docs/game/command-reference.md`, `tests/test_command_docs.py`.
- Tests: `server/conf/tests/test_env_overrides.py`, `commands/tests/test_localized.py`,
  and a new account-capacity test beside the account typeclass tests.
- Downstream: changes 02 (`multichar-02-roster-read-model`), 03
  (`multichar-03-switch-create-actions`), and 04 (`multichar-04-topbar-switcher-ui`) all depend on
  this landing first.
