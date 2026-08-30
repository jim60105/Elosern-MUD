## MODIFIED Requirements

### Requirement: The command reference documents the title commands
`docs/game/command-reference.md` SHALL carry canonical entries for `title` (used
as `title list`, `title equip fixed <display|key>` /
`title equip epithet <display>`, `title accept <1|2|3>`, and `title decline`; no
aliases) with availability in and out of combat and non-empty Traditional Chinese
descriptions stating that 稱號冊 lists fixed titles and 異名, that equipping swaps
one occupied slot for another and there is no unequip, that unknown displays are
rejected, and that `title accept` / `title decline` answer a pending 異名提名投票
(accepting records the 異名 and answers with the numbered choice only — free text
is never used for ballots). The curated manifest in `tests/test_command_docs.py`
SHALL carry the same syntax and context, and `docs/game/commands.md` SHALL carry
a `title` row in its character-growth category table.

#### Scenario: The title entries satisfy the drift contract
- **WHEN** the drift contract test runs after the command is mounted
- **THEN** the `title` canonical entry's key, syntax rows, and context match the command class and the curated manifest

#### Scenario: The overview links the title row
- **WHEN** a player opens `docs/game/commands.md`
- **THEN** the character-growth category table carries a `title` row describing list/equip and the accept/decline ballot answers, and the overview link set gains exactly that documented key
