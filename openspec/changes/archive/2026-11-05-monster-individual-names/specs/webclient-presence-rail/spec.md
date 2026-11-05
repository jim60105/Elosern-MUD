## ADDED Requirements

### Requirement: The rail marks a named individual without moving
A rail entry whose identity has an individual name SHALL show an inner gold rule on its medallion, and its name in the gold display treatment between two horizontal gold hairlines that fade at both ends. The entry SHALL keep the size and position of an unnamed entry and SHALL use no selection cue at rest.

#### Scenario: Named and unnamed entries share geometry
- **WHEN** a named and an unnamed entry with equally long names render in one rail
- **THEN** their medallion and name plate positions and sizes are equal, and the name's rendered text is complete

#### Scenario: Unnamed entries are unchanged
- **WHEN** an entry has no identity or a null individual name
- **THEN** it carries no named marker and renders as before

#### Scenario: Focus stays distinct
- **WHEN** a named entry is hovered or holds the rail's focus
- **THEN** it shows the existing lift and focus cues together with the named treatment

### Requirement: The rail readout shows a monster's variant
The readout for a hovered or focused rail entry SHALL show its name with a variant tag derived by the client from `monster_identity`: the variant name for an unnamed individual, and the variant name followed by the species name for a named one. Switching entries SHALL NOT move the readout's lines.

#### Scenario: Unnamed monster
- **WHEN** the player hovers a synthetic unnamed monster
- **THEN** the readout lead shows the species name and a tag holding the variant name

#### Scenario: Named monster
- **WHEN** the player focuses a synthetic named monster
- **THEN** the readout lead shows the individual name in the named treatment and a tag holding the variant name followed by the species name

#### Scenario: Entry without identity
- **WHEN** the player hovers a person or an object
- **THEN** the readout shows no tag and is otherwise unchanged
