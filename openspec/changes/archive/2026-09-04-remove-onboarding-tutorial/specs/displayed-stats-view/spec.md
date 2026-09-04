# Delta: displayed-stats-view

## MODIFIED Requirements

### Requirement: look <target> appends the displayed-stats block, room look never does
The shared target-appearance path used by the text `look` command (「看 <對象>」) SHALL append
`display_stat_block(target)` after the target's description when
the target is a living entity. Bare `look` (the room) SHALL append nothing.

#### Scenario: Text look at a living target includes the block
- **WHEN** a player uses 「看 <目標>」 on a present NPC, player character, or monster
- **THEN** the output contains the target's description followed by the displayed-stats block

#### Scenario: Text look at the room omits the block
- **WHEN** a player uses 「看」 with no argument
- **THEN** the room appearance is unchanged and contains no displayed-stats block
