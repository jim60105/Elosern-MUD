# Spec Delta

## MODIFIED Requirements

### Requirement: The command reference documents the lineage command
`docs/game/command-reference.md` SHALL carry a canonical entry for `lineage`
(alias `系譜`) with syntax `lineage [<成員>]`, availability context in and out of combat,
and a non-empty Traditional Chinese description stating that the command prints
the named party member's (default: the commander's) skill graphs with per-node
proficiency, prerequisite edges with their minimum levels, 見頂 saturation marks,
可解鎖 marks, and the prerequisite of each locked node.

#### Scenario: The lineage entry satisfies the drift contract
- **WHEN** the drift contract test runs after the command is mounted
- **THEN** the `lineage` canonical entry's key, its `系譜` alias, syntax row, and context row match the command class and the curated manifest

#### Scenario: The overview links the lineage row
- **WHEN** a player opens `docs/game/commands.md`
- **THEN** the skill-growth category table carries a `lineage` row describing the tree, saturation, and prerequisite display, and the overview link set gains exactly that one documented key

#### Scenario: The manifest and overview carry the lineage entry

- **WHEN** the lineage documentation is authored
- **THEN** the curated manifest in `tests/test_command_docs.py` SHALL carry the same syntax and
  context
- **AND** `docs/game/commands.md` SHALL carry a `lineage` row in its skill-growth category table
