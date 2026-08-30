## Purpose

Define the player-facing game command reference under `docs/` and the repository contract that keeps it in sync with the mounted command registry.

## Requirements


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

### Requirement: Docsify navigation

The new command pages SHALL be linked from `docs/_sidebar.md` and SHALL be served by the existing
docsify setup without configuration changes.

#### Scenario: Sidebar links the command pages

- **WHEN** the docs site loads
- **THEN** `docs/_sidebar.md` SHALL link to `docs/game/commands.md` and
  `docs/game/command-reference.md`

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

### Requirement: Documentation-update convention

`AGENTS.md` SHALL state that any change adding, removing, renaming, or altering a player command
(key, alias, syntax, or context) MUST update the command reference documentation in the same
change.

#### Scenario: Convention is present in the agent guide

- **WHEN** the contract test runs
- **THEN** it SHALL verify that `AGENTS.md` contains the command-reference update convention

### Requirement: The cast command reference documents the optional scale token
The reference entry for `cast` SHALL document the syntax `cast <skill_key>[@<scale>][=<target_key>]`
where `<scale>` is one of `1/4`, `1/2`, `1`, `2`, `4` (default `1`) and SHALL state that the token
adjusts the spell's MP cost and damage/heal magnitude proportionally, available only to holders of
the matching element's mastery skill (all other uses are rejected). The curated manifest in
`tests/test_command_docs.py` SHALL carry the same syntax, and `docs/game/commands.md` SHALL describe
the capability in its cast row.

#### Scenario: The reference matches the manifest
- **WHEN** the drift contract test inspects the `cast` entry
- **THEN** the reference syntax row equals the manifest syntax
  `cast <skill_key>[@<scale>][=<target_key>]` and the description mentions the proportional
  magnitude adjustment and the mastery requirement

#### Scenario: The overview describes scaled casting
- **WHEN** a player opens `docs/game/commands.md`
- **THEN** the cast row states that a mastery holder may adjust a spell's power and MP cost with the
  `@<scale>` token

### Requirement: The command reference documents the sexual act system
The `cast` and `combat actions` entries in `docs/game/command-reference.md` SHALL document that
性愛 (sexual act) skills are ordinary castable skills reached through the two existing commands, with
no separate syntax or command of their own. The `cast` entry's 說明 field SHALL state that a
character's unlocked 性愛 skills are cast through the same `cast <skill_key>[@<scale>][=<target_key>]`
syntax — a few basic seed acts are available from character creation, the rest once unlocked by play —
and SHALL contain the substrings `性愛` and `解鎖`. The `combat actions` entry's 說明 field SHALL
state that owned skills are grouped by category and that unlocked 性愛 acts form their own category
once their unlock requirement is met, and SHALL contain the substring `性愛`. This requirement adds
documentation content only; it changes neither entry's `語法` nor `情境` field, and the curated
manifest in `tests/test_command_docs.py` (`EXPECTED_COMMANDS["cast"]` and `["combat actions"]`) is
unchanged.

#### Scenario: The cast entry mentions unlocked sexual acts
- **WHEN** the drift contract test inspects the `cast` canonical entry's 說明 field
- **THEN** the field contains the substrings `性愛` and `解鎖`, and states that unlocked sexual-act
  skills use the same cast syntax as any other skill

#### Scenario: The combat actions entry mentions category grouping
- **WHEN** the drift contract test inspects the `combat actions` canonical entry's 說明 field
- **THEN** the field contains the substring `性愛` and states that owned skills are grouped by
  category, with unlocked sexual acts forming their own category

### Requirement: The command reference documents the resist, affinity, and status consequences
`docs/game/command-reference.md` SHALL document, in prose placed under the existing `### cast`
heading (not as a new canonical heading — a new heading with no corresponding mounted command would
be an orphan canonical entry), the parts of the sexual act system a player must understand before
casting one against another character: that unlock is per-act — a few basic acts are available from
character creation while the rest are gained by meeting their unlock conditions in play (SHALL
contain the substring `解鎖`); that a resistible act's target receives one resist roll, in or out of
combat, where a successful resist leaves that target unaffected by the cast's target effects while
the cast still consumes time and the skill's resource cost (if any), and a failed resist executes the
act against the target (SHALL contain the substrings `抵抗` and `戰鬥`); that a forced act (a failed
resist) against a companion NPC costs relationship affinity and can trigger the companion
auto-leaving the party, with the caster notified when it happens — the consequence applies to forced
acts in combat and out of combat alike, both halves shipped and archived
(`sexual-resist-turn-cost`'s `_scan_sexual_coercion` and `sexual-resist-out-of-combat`'s
`_scan_out_of_combat_sexual_coercion`) (SHALL contain the substring `好感度`); that sustained arousal,
an in-progress climax, and high exposure appear as ordinary combat condition labels while active
(SHALL contain the substrings `興奮`, `高潮`, and `露出`, matching the shipped 高度興奮敏捷與準度減損,
高潮進行中鎖定行動, and 高露出防禦減損 labels); and that 神之秘法 (divine arts) acts require a
race-eligible caster and have no counter unlock threshold (SHALL contain the substring `神之秘法`),
without asserting which individual divine-arts acts exist and SHALL NOT name any of them.

#### Scenario: The reference documents the unlock ladder
- **WHEN** the drift contract test inspects the full text of the `### cast` section (its field table
  plus the trailing prose block)
- **THEN** the section contains the substring `解鎖` and states that basic acts are available from
  character creation while the rest unlock in play

#### Scenario: The reference documents the resist and affinity consequence
- **WHEN** the drift contract test inspects the full text of the `### cast` section
- **THEN** the section contains the substrings `抵抗`, `好感度`, and `戰鬥`

#### Scenario: The reference documents the status conditions
- **WHEN** the drift contract test inspects the full text of the `### cast` section
- **THEN** the section contains the substrings `興奮`, `高潮`, and `露出`

#### Scenario: The reference documents the divine-arts race gate
- **WHEN** the drift contract test inspects the full text of the `### cast` section
- **THEN** the section contains the substring `神之秘法`, states that casting acts on that line
  requires a race-eligible caster, and names no individual divine-arts act

#### Scenario: No orphan canonical heading is introduced
- **WHEN** `test_no_orphan_canonical_entries` runs after this content is added
- **THEN** it reports no new failure, because the new prose is not preceded by any new `### <key>`
  heading

### Requirement: The overview page describes the sexual act system's discoverability
`docs/game/commands.md`'s `cast` row (in its 技能施放 category table) SHALL state that sexual-act
skills are included among castable skills, are unlocked through play, and are discoverable through
`combat actions`'s category grouping, and SHALL contain the substring `性愛`. This requirement adds no
new row and no new key, so `test_overview_links_only_documented_keys_and_all_keys`'s exact-match
between overview links and canonical-entry keys is unaffected.

#### Scenario: The overview cast row mentions sexual acts
- **WHEN** the drift contract test inspects `docs/game/commands.md`'s 技能施放 table
- **THEN** the `cast` row's description contains the substring `性愛` and mentions that such skills are
  unlocked through play

#### Scenario: The overview link set is unchanged
- **WHEN** `test_overview_links_only_documented_keys_and_all_keys` runs after this content is added
- **THEN** the set of documented keys linked from the overview page is identical to the set before this
  change

### Requirement: The command reference documents the title commands
`docs/game/command-reference.md` SHALL carry canonical entries for `title` (used
as `title list` and `title equip fixed <display|key>` /
`title equip epithet <display>`; no aliases) with availability in and out of
combat and non-empty Traditional Chinese descriptions stating that 稱號冊 lists
fixed titles and 異名, that equipping swaps one occupied slot for another and
there is no unequip, and that unknown displays are rejected. The curated manifest
in `tests/test_command_docs.py` SHALL carry the same syntax and context, and
`docs/game/commands.md` SHALL carry a `title` row in its character-growth
category table.

#### Scenario: The title entries satisfy the drift contract
- **WHEN** the drift contract test runs after the command is mounted
- **THEN** the `title` canonical entry's key, syntax rows, and context match the command class and the curated manifest

#### Scenario: The overview links the title row
- **WHEN** a player opens `docs/game/commands.md`
- **THEN** the character-growth category table carries a `title` row describing list/equip, and the overview link set gains exactly that documented key


### Requirement: The command reference documents the lineage command
`docs/game/command-reference.md` SHALL carry a canonical entry for `lineage`
(no aliases) with syntax `lineage`, availability context in and out of combat,
and a non-empty Traditional Chinese description stating that the command prints
the character's skill lineages with per-node proficiency, 見頂 saturation marks,
and the prerequisite of each locked node. The curated manifest in
`tests/test_command_docs.py` SHALL carry the same syntax and context, and
`docs/game/commands.md` SHALL carry a `lineage` row in its skill-growth category
table.

#### Scenario: The lineage entry satisfies the drift contract
- **WHEN** the drift contract test runs after the command is mounted
- **THEN** the `lineage` canonical entry's key, absent aliases, syntax row, and context row match the command class and the curated manifest

#### Scenario: The overview links the lineage row
- **WHEN** a player opens `docs/game/commands.md`
- **THEN** the skill-growth category table carries a `lineage` row describing the tree, saturation, and prerequisite display, and the overview link set gains exactly that one documented key
