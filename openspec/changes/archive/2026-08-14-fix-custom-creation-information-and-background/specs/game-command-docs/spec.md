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
  wizard (including that a subrace must be chosen for every race, the allocation budget and
  summing rule shown before the allocation step, and the optional background field) and the
  `cancel` escape, and SHALL state that the creation cmdset replaces other game commands while the
  localized `說明` and `登出` (aliases `help` and `quit`) remain available

#### Scenario: The background command is documented

- **WHEN** a player looks up the background command
- **THEN** the reference SHALL document `設定背景` (alias `背景`) as a canonical entry whose syntax
  covers setting and clearing the character's own background text and whose context is the active
  character, matching the command class definition, and SHALL NOT list it among the localized
  Evennia-default wrappers

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
