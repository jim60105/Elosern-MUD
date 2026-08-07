## MODIFIED Requirements

### Requirement: Complete command reference

The documentation SHALL provide a player-facing reference of every in-game keyboard command under
`docs/game/`, covering every project-authored command mounted on the `CharacterCmdSet` in
`commands/default_cmdsets.py`, the `character` command mounted on the `CharacterCreationCmdSet` in
`commands/character_creation.py`, the project-owned XYZGrid cmdset, the localized zh-tw wrappers of
the Evennia default commands (看, 說明, 說, 動作, 拿, 丟, 給, 回家, 耳語, 暱稱, 設定描述, 登出, 在線,
離開角色, 進入世界, 傳訊, 密碼, 選項, 連線, 色彩, 樣式, 降權, 地圖, 前往) as canonical entries with
their retained English aliases, and an enumerated index of the Evennia default commands still
retained untranslated through `super()` on the character and account cmdsets. Pre-login commands of
the `UnloggedinCmdSet` are outside the in-game input surface and are not required.

#### Scenario: Every mounted project command is documented

- **WHEN** a project-authored command is added to the `CharacterCmdSet` creation path
- **THEN** the command reference at `docs/game/command-reference.md` SHALL contain an entry for
  that command's primary key

#### Scenario: Character creation is documented as a single entry

- **WHEN** a player is in character-creation mode
- **THEN** the reference SHALL document `character` as one entry whose syntax covers
  `character preset <key>` and `character create` and whose description explains the interactive
  wizard and the `cancel` escape, and SHALL state that the creation cmdset replaces other game
  commands while the localized `說明` and `登出` (aliases `help` and `quit`) remain available

#### Scenario: Contrib commands are documented

- **WHEN** a player looks up movement commands
- **THEN** the project-owned XYZGrid commands appear as canonical entries: the native
  `@teleport`/`@open` with their keys, aliases, and syntax, and the localized `前往` (alias `goto`)
  and `地圖` (alias `map`) superseding the English-keyed contrib commands `goto`/`map`

#### Scenario: Localized default commands are enumerated

- **WHEN** the reference covers the localized Evennia defaults
- **THEN** it SHALL enumerate the complete key set of the localized wrapper commands (看, 說明, 說,
  動作, 拿, 丟, 給, 回家, 耳語, 暱稱, 設定描述, 登出, 在線, 離開角色, 進入世界, 傳訊, 密碼, 選項,
  連線, 色彩, 樣式, 降權, 地圖, 前往) in an index table with one-line descriptions, each mapping to
  its canonical entry

#### Scenario: Retained Evennia defaults are enumerated

- **WHEN** the reference covers retained Evennia defaults
- **THEN** it SHALL enumerate the key sets of the default character and account cmdsets that remain
  untranslated — the upstream key sets minus the localized set — in index tables with one-line
  descriptions, and SHALL point to the Evennia documentation for full details

#### Scenario: Overview groups commands by category

- **WHEN** a player or contributor opens `docs/game/commands.md`
- **THEN** the overview SHALL group the documented commands into categories such as exploration,
  dialogue, time skip, combat, skills, guild, economy, character creation, and admin

### Requirement: Accurate command details

The reference entry for each project-authored and contrib command SHALL state the command's
primary key, its aliases (including Traditional Chinese aliases and, for localized wrappers, the
retained full English alias set), its argument syntax, its availability context, and a non-empty
Traditional Chinese description. The key and aliases SHALL match the command class definition, the
syntax and context SHALL match the curated command manifest in `tests/test_command_docs.py`, and
admin commands SHALL carry their permission requirement.

#### Scenario: Key and aliases match the command class

- **WHEN** the contract test inspects a project-authored command class mounted in a player cmdset
- **THEN** the class key and aliases SHALL appear in the corresponding reference entry

#### Scenario: Syntax and context match the curated manifest

- **WHEN** the contract test runs
- **THEN** the syntax row of each canonical entry SHALL equal the manifest syntax for that key and
  the context row SHALL equal the manifest context

#### Scenario: Context restrictions are documented

- **WHEN** a command is only available in a specific context (combat session, guild service host,
  shop merchant, character creation, or admin permission)
- **THEN** the reference entry SHALL state that restriction, and for commands whose
  `help_category` is `Combat`, `Guild`, `Economy`, or `Admin` the context row SHALL be consistent
  with it

#### Scenario: Admin commands carry a permission note

- **WHEN** a command class is locked to `Developer` permission (the `art` command family)
- **THEN** the reference entry SHALL mark the command as admin-only and the contract test SHALL
  verify the class locks require `Developer`

#### Scenario: Builder-gated commands carry a permission note

- **WHEN** a command class is locked to `Builder` permission (the XYZGrid `map`, `@teleport`, and
  `@open` commands)
- **THEN** the reference entry SHALL state the builder restriction and the contract test SHALL
  verify the class locks require `Builder`

### Requirement: Drift contract test

The repository SHALL include a deterministic regression test, runnable without a database or
server, that fails when the command reference drifts from the mounted command registry or from
the curated manifest.

#### Scenario: Undocumented command fails the test

- **WHEN** a project-authored command is mounted in a player cmdset without a matching reference
  entry
- **THEN** `tests/test_command_docs.py` SHALL fail, reporting the missing command

#### Scenario: Orphan reference entry fails the test

- **WHEN** a canonical reference entry documents a key that no mounted command exposes
- **THEN** `tests/test_command_docs.py` SHALL fail, reporting the orphan entry

#### Scenario: Default command index stays complete

- **WHEN** the contract test runs
- **THEN** the key set of each enumerated Evennia default index table SHALL equal the corresponding
  upstream default cmdset key set minus the localized set (the retained untranslated defaults), the
  localized index table SHALL equal the mounted localized wrapper key set, and the XYZGrid
  enumeration SHALL equal the key set of the project-owned mounted XYZGrid cmdset

#### Scenario: Sidebar, overview, and agent guide stay consistent

- **WHEN** the contract test runs
- **THEN** it SHALL verify that `docs/_sidebar.md` links both new pages, that the overview
  category tables reference only documented canonical keys, and that `AGENTS.md` contains the
  documentation-update convention
