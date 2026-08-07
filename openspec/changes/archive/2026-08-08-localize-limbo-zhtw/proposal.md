# Localize the starting Limbo room, the shared appearance layer, and the player-facing default command surface to Traditional Chinese

## Why

A fresh Elosern database still shows Evennia's stock English artifact: the starting room is keyed
and rendered as the English `Limbo`, its description is the upstream "Welcome to your new Evennia
game…" boilerplate, and everything a new player reads or types there falls through to Evennia's
English defaults — the `look` appearance frame (`Exits:`, `You see…`), `help` output, `say`/`get`/
`drop` echoes, movement commands, and even the webclient's explore-look path. Player-facing prose
must be Traditional Chinese everywhere a player stands — starting with the room every character is
born in — and the room name and every command the player sees or types must be zh-tw too. The
project has no released users, so the English surface can be replaced outright without migrations
or backward-compatibility layers.

## What Changes

- **The starting room is localized and story-fitting.** Its object key changes from `"Limbo"` to a
  zh-tw name (draft: 「虛境」), its description is replaced with zh-tw prose about Elosern's
  threshold between worlds, and an idempotent startup sync (`sync_limbo()`) converges existing
  developer databases by renaming the old key in place and re-authoring the description on every
  server start, mirroring the existing interiors-sync convention. When both the zh-tw room and a
  legacy `"Limbo"` room coexist, the canonical room wins and the legacy room is warned about, never
  silently selected.
- **The shared appearance layer renders zh-tw frames.** The project typeclasses override Evennia's
  appearance hooks (`get_display_exits` 「出口」, contents/characters sections, default description)
  so the text `看` command, the stock `at_look` seam, and the webclient `explore.look` action all
  render the identical zh-tw appearance — no English scaffolding remains on either path.
- **The Limbo bridge exit pair is fully zh-tw and stays that way.** The exit toward the city keeps
  key 「南門」 and the return exit keeps 「離開王都」; their English aliases (`south gate`, `altoria`,
  `leave`, `limbo`) are replaced with zh-tw aliases (e.g. 「王都」, 「城門」, 「回虛境」), and the grid
  bootstrap reconciles key/aliases **in place** on pre-existing exits at every start, not only at
  creation. **BREAKING** for any code that searches the room by key `"Limbo"` or traverses the
  bridge by English alias: the lookup moves to a shared `LIMBO_KEY` constant and all test fixtures
  are renamed.
- **Every default command a normal player can invoke as gameplay surface is localized.** (The
  permission-inspection and account-management tools `access`/`perm`/`charcreate`/`chardelete` and
  all Builder/Developer-gated commands stay English — see the out-of-scope boundary below.)
  Wrapper subclasses of the Evennia defaults get zh-tw primary keys, retain the class's **full**
  alias set (e.g. `look` keeps `l`, `ls`), carry zh-tw help text, and emit zh-tw output:
  - Character set: `look`→看, `help`→說明, `say`→說, `pose`→動作, `get`→拿, `drop`→丟, `give`→給,
    `home`→回家, `whisper`→耳語, `nick`→暱稱, `setdesc`→設定描述.
  - Account set: `quit`→登出, `who`→在線, `ooc`→離開角色, `ic`→進入世界, `page`→傳訊,
    `password`→密碼, `option`→選項, `sessions`→連線, `color`→色彩, `style`→樣式, `quell`→降權.
  - XYZGrid: `map`→地圖, `goto`→前往 — mounted through a project-owned XYZGrid cmdset that keeps
    the native `@teleport`/`@open` and swaps `goto`/`map` for the wrappers, with the auto-walk
    semantics preserved for both 「前往」 and the `goto` alias (`path` stays path-only).
  The stock English commands are removed from the merged player cmdsets so no English-keyed or
  English-output variant remains reachable in normal play. Wrappers branch on the actual typed
  command string (`cmdstring`), not on their key, so behavioral aliases (`doing`, `path`, `grab`,
  `emote`…) keep their upstream semantics.
- **Player-facing prose that names commands is updated**: the onboarding guard's `look` prompt in
  `world/onboarding/scenes.py` and the 新手引導 help entry use the zh-tw keys.
- **Command documentation contract follows the surface.** `docs/game/commands.md`,
  `docs/game/command-reference.md`, the curated manifest, and `tests/test_command_docs.py` are
  reworked: localized wrappers become documented canonical entries (zh-tw key, full alias list),
  the Evennia-default index tables enumerate the retained defaults minus the localized set, and the
  XYZGrid enumeration reflects the project's mounted cmdset (`@teleport`/`@open` plus the
  wrappers).

## Capabilities

### New Capabilities

- `limbo-room`: the starting room's localized zh-tw identity (key, aliases, story description), the
  idempotent `sync_limbo()` startup convergence (including legacy-key rename and dual-room
  precedence), and the zh-tw bridge exit aliases reconciled in place.
- `localized-appearance`: the shared object-appearance layer renders Traditional Chinese frames
  (room title/description, 「出口」, contents sections) identically for the text `看` command, the
  `at_look` seam, and the webclient `explore.look` action.

### Modified Capabilities

- `grid-room-sync`: the Limbo-bridging lookup changes from key `"Limbo"` to the `LIMBO_KEY`
  constant, the bridge exit aliases are zh-tw and are reconciled in place on pre-existing exits;
  scenarios rewritten accordingly.
- `game-command-docs`: the reference index tables and drift-contract scenarios change — the
  "Evennia default" tables enumerate the retained defaults minus the localized set, the localized
  wrappers are documented as canonical project commands with their full alias sets, and the XYZGrid
  enumeration covers the project's mounted set.
- `onboarding-guide`: the arrival-scene prose and spec scenarios that name the `look` command
  change to the zh-tw key （看）.

## Impact

- `world/maps/bootstrap.py`: new `sync_limbo()`, `LIMBO_KEY` constant, zh-tw bridge aliases plus
  in-place alias reconciliation in the bridge sync; `server/conf/at_server_startstop.py` calls the
  new sync before `sync_grid()`.
- `typeclasses/objects.py` (`ObjectParent`): zh-tw appearance hooks shared by text and webclient
  look paths.
- New `commands/` module hosting the localized default-command wrappers and a project-owned XYZGrid
  cmdset; `commands/default_cmdsets.py` removes the stock defaults and mounts the wrappers;
  `commands/character_creation.py` swaps the creation-mode `help`/`quit` for the localized wrappers.
- `world/onboarding/scenes.py`, `world/help_entries.py`: prose updates naming zh-tw commands.
- Docs and contract: `docs/game/commands.md`, `docs/game/command-reference.md`,
  `tests/test_command_docs.py` (manifest + index-table + XYZGrid enumeration),
  `openspec/specs/` deltas for `grid-room-sync`, `game-command-docs`, `onboarding-guide`, and the
  new `limbo-room` + `localized-appearance` capabilities (each with `covers_requirement`
  traceability).
- Mechanical fixture rename: every test that creates or searches the starting room by
  `key="Limbo"` moves to the `LIMBO_KEY` constant (map/bootstrap-adjacent tests) or the zh-tw key.
- **BREAKING**: object key `"Limbo"` no longer exists anywhere; English aliases on the bridge exits
  are removed. No migration layer is added (no released users).
- Out of scope (permission-gated admin/builder/system surface, retained English and documented):
  all `@`-prefixed builder commands, `access`, `perm`, `sethelp`, `emit`, `force`, `wall`, `ban`,
  `boot`, `unban`, `unlink`, `batchcode`, `batchcommands`, `charcreate`/`chardelete` (the project's
  creation flow is `character`), channel commands (`@channel`, `rss2chan`, `irc2chan`,
  `discord2chan`, `grapevine2chan`, `ircstatus`), `@about`, `@time`, `@server`, `@service`,
  `@scripts`, `@tickers`, `@tasks`, `@examine`, `@py`, `@objects`, `@accounts`. The connection
  screen and `UnloggedinCmdSet` are already localized by another capability; webclient UI labels are
  owned by webclient changes.
