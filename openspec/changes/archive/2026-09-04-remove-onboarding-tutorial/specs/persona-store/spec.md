# Delta: persona-store

## MODIFIED Requirements

### Requirement: The look appearance path renders a living entity's persona block
The in-game 「看」 surface (shared by the text command and the WebClient look action) SHALL append a
living entity's flattened persona block (including the `背景：` section when the record carries a
background) when the player looks at themself, at another player character, or at an NPC, using the
same code path for all three. Looking at the room or at an object SHALL NOT append any persona
block. A record without any of the rendered fields renders nothing, so entities without a persona
(e.g. monsters) are unchanged; the displayed-stats block is
unaffected.

#### Scenario: Looking at yourself shows the persona block
- **WHEN** an active character whose persona record has content uses 「看 自己」
- **THEN** the output contains the persona block (including `背景：` when present) after the
  description and displayed-stats block

#### Scenario: Looking at another player character shows that character's persona block
- **WHEN** a player looks at another present player character whose persona record has content
- **THEN** the output contains the target's persona block (including `背景：` when present) and not
  the looker's own block

#### Scenario: Looking at an NPC shows the NPC's persona block
- **WHEN** a player looks at a present NPC whose `entity.db.persona` record has content
- **THEN** the output contains that NPC's persona block (including `背景：` when present)

#### Scenario: Looking at the room or an object omits any persona block
- **WHEN** the actor looks at the room or at an object
- **THEN** no persona block is appended to those outputs
