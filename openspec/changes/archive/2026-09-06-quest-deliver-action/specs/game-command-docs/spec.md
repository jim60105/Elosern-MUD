# Delta spec: game-command-docs (quest-deliver-action)

## ADDED Requirements

### Requirement: The command reference documents the delivery command

`docs/game/command-reference.md` SHALL carry a canonical entry for the delivery command with its
exact key, its declared aliases, its syntax naming the recipient and the item, its availability
context (usable in exploration, refused during an active combat session), and a non-empty
Traditional Chinese description stating that the command hands a quest item to the recipient the
quest bound it to, that only the bound recipient satisfies a delivery, and that a refused delivery
changes nothing. The curated manifest in `tests/test_command_docs.py` SHALL carry the same key,
aliases, syntax, and context, and `docs/game/commands.md` SHALL carry a delivery row in the
appropriate category table.

#### Scenario: The delivery entry satisfies the drift contract
- **WHEN** the drift contract test runs after the command is mounted
- **THEN** the delivery canonical entry's key, aliases, syntax row, and context row match the command
  class and the curated manifest

#### Scenario: The overview links the delivery row
- **WHEN** a player opens `docs/game/commands.md`
- **THEN** the category table carries a delivery row describing the hand-over and the bound-recipient
  rule, and the overview link set gains exactly that one documented key
