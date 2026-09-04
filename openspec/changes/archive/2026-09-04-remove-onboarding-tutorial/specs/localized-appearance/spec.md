# Delta: localized-appearance

## MODIFIED Requirements

### Requirement: The shared appearance layer renders Traditional Chinese frames

The object-appearance layer SHALL render its presentation frames in Traditional Chinese for every
entry path: the text look command (localized 「看」), the character's `at_look` hook, and the
webclient `explore.look` action SHALL all produce the same zh-tw appearance. The room frame SHALL
label its exits as 「出口」 (never `Exits:`), its contents/characters sections with zh-tw headers
(never `Characters:` or `You see`), and the default description of an un-described object SHALL be
zh-tw (never `You see nothing special.`). The room frame SHALL additionally render
`room.db.scene_flavor` as a paragraph after the room description and before the 「出口」 line when
the attribute is present. Every room typeclass (`Room`, `GridRoom`, `AnchorRoom`, `TerrainRoom`,
`InstanceRoom`) SHALL render the shared zh-tw room frame — including the flavor-bearing
`InstanceRoom`, which is not a subclass of `Room` (design D4 correction); no English frame string
SHALL appear in the appearance of a room. A room without a flavor SHALL render no flavor paragraph:
its appearance SHALL be identical to the flavor-bearing rendering of the same room except for the
absence of that paragraph. No English frame string SHALL appear in the appearance
of a room or object. The appearance of an NPC SHALL additionally include one affinity stage line
(for example 「她看著你的眼神裡帶著信賴。」) rendered by the shared layer from the NPC's affinity
record for the looking player, identical across all three entry paths; the numeric affinity value,
cap, and threshold SHALL never appear, and entities without an affinity record SHALL render no
stage line.

#### Scenario: The text look command shows a zh-tw frame

- **WHEN** a player uses the localized 看 command in a room with an exit
- **THEN** the output shows the room's zh-tw name and description, a 「出口」 line listing the exit
  names, and no `Exits:` or other English frame string

#### Scenario: The webclient look action shows the same zh-tw frame

- **WHEN** a webclient player triggers the explore-look action in the same room
- **THEN** the appearance equals the text 看 output — zh-tw name, description, and 「出口」 line —
  with no English frame string

#### Scenario: The at_look seam stays intact

- **WHEN** a player looks through the character's `at_look` hook
- **THEN** the look still flows through the hook and the presented appearance is the zh-tw frame

#### Scenario: NPC appearance includes the affinity stage line on every path

- **WHEN** a player looks at an NPC holding an affinity record at the 信賴 stage through the text
  look command, the `at_look` hook, and the webclient explore-look action
- **THEN** all three outputs contain the same stage flavor line for 信賴 and no numeric value, cap,
  or threshold appears in any of them

#### Scenario: Recordless entities render no affinity line

- **WHEN** a player looks at a monster or an NPC with no affinity record
- **THEN** the appearance contains no affinity line on any entry path

#### Scenario: A flavor-bearing room renders the flavor paragraph on every path

- **WHEN** a player looks at a room carrying `room.db.scene_flavor` through the text 看 command, the
  `at_look` hook, and the webclient `explore.look` action
- **THEN** all three outputs show the room description, then the flavor paragraph, then the
  「出口」 line, with no English frame string

#### Scenario: A flavor-less room renders no flavor paragraph

- **WHEN** a player looks at a room with no `room.db.scene_flavor`
- **THEN** the appearance is byte-identical to the same room with the flavor attribute absent —
  no flavor paragraph appears, the zh-tw room frame is unchanged, and the flavor feature adds
  nothing to a flavor-less room

### Requirement: Target appearance includes the displayed-stats block on every entry path
The shared target-appearance layer SHALL append the displayed-stats block (`display_stat_block`)
for living targets identically across all three entry paths: the text look command (「看 <目標>」),
the character's `at_look` hook, and the webclient `explore.look` action. The block SHALL appear
after the target's zh-tw description and SHALL NOT appear in room appearance. Entities that are not
living SHALL render no block. The affinity stage-line behavior SHALL
be unchanged.

#### Scenario: All three entry paths show the same block
- **WHEN** a player looks at the same living NPC through the text 「看」 command, the `at_look`
  hook, and the webclient `explore.look` action
- **THEN** all three outputs contain the same displayed-stats block after the description, with the
  same values in the same fixed order

#### Scenario: Non-living targets never show the block
- **WHEN** a player looks at a present object or a room through any of the three entry paths
- **THEN** no displayed-stats block appears
