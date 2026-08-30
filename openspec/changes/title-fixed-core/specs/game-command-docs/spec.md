## ADDED Requirements

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
