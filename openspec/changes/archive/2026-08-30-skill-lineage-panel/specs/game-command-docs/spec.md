## ADDED Requirements

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
