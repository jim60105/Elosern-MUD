## Purpose

Define the shared object-appearance layer's Traditional Chinese presentation frames, used
identically by the text look command, the `at_look` seam, and the webclient explore-look action.

## Requirements

### Requirement: The shared appearance layer renders Traditional Chinese frames

The object-appearance layer SHALL render its presentation frames in Traditional Chinese for every
entry path: the text look command (localized 「看」), the character's `at_look` hook, and the
webclient `explore.look` action SHALL all produce the same zh-tw appearance. The room frame SHALL
label its exits as 「出口」 (never `Exits:`). No English frame string SHALL appear in the appearance
of a room or object.

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

#### Scenario: Room sections use zh-tw headers

- **WHEN** a player looks at a room whose frame has contents/characters sections
- **THEN** those sections carry zh-tw headers and never `Characters:` or `You see`

#### Scenario: An un-described object renders a zh-tw default description

- **WHEN** a player looks at an object with no description of its own
- **THEN** the default description is zh-tw and never `You see nothing special.`

#### Scenario: The room frame renders scene_flavor in position

- **WHEN** a room carries `room.db.scene_flavor`
- **THEN** the room frame renders it as a paragraph after the room description and before the
  「出口」 line

#### Scenario: Every room typeclass renders the shared zh-tw room frame

- **WHEN** a player looks at a `Room`, `GridRoom`, `AnchorRoom`, `TerrainRoom`, or `InstanceRoom`
- **THEN** each renders the shared zh-tw room frame — including the flavor-bearing `InstanceRoom`,
  which is not a subclass of `Room` (design D4 correction)

#### Scenario: A flavor-less room matches the flavor-bearing rendering minus the paragraph

- **WHEN** the appearance of a room without a flavor is compared to the flavor-bearing rendering
  of the same room
- **THEN** the two are identical except for the absence of the flavor paragraph

#### Scenario: The affinity stage line is one shared-layer line per NPC

- **WHEN** a player looks at an NPC with an affinity record for them
- **THEN** the NPC appearance includes one affinity stage line (for example
  「她看著你的眼神裡帶著信賴。」) rendered by the shared layer from the NPC's affinity record
  for the looking player, identical across all three entry paths

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

### Requirement: Grid room look emits the ordinary appearance without an automatic ASCII map

For grid and anchor rooms without an explicit developer display override, ordinary room look through text commands, the appearance hook and the browser action SHALL preserve the same zh-tw appearance on every client, including Telnet. Neither the returned appearance nor any emitted message SHALL contain an automatic ASCII minimap.

#### Scenario: Text look in a GridRoom contains only the ordinary appearance

- **GIVEN** a player in a plain grid room on a loaded connected map with a description, visible contents and a traversable exit
- **WHEN** the player executes `看` or its `look` alias without a target
- **THEN** the output contains the ordinary room name and description with the contents and localized exit listing
- **AND** none of the command's emitted text messages contains the automatic ASCII minimap or has `type: xymap`

#### Scenario: Text look in an AnchorRoom inherits the same suppression

- **GIVEN** a player in an anchor room on the same kind of loaded map
- **WHEN** the player executes `看` without a target
- **THEN** the ordinary anchor-room appearance is emitted with its localized exits
- **AND** no separate ASCII-map text message is emitted

#### Scenario: Browser explore look preserves the appearance and success response

- **GIVEN** a browser-controlled player in either a plain grid room or an anchor room on a loaded map
- **WHEN** the player submits `explore.look` with `{"room": true}`
- **THEN** the action succeeds with the existing `looked` result and ordinary appearance text matching that room's text-command appearance after envelope normalization
- **AND** no `xymap`-tagged message or ASCII-map block is sent to the narrative stream
- **AND** the existing full presentation refresh remains in effect

#### Scenario: Direct at look does not emit a map side message

- **GIVEN** a player looking at either grid-room type on a loaded map
- **WHEN** the ordinary `at_look` hook returns its appearance
- **THEN** the returned appearance contains the existing room frame
- **AND** the hook emits no ASCII-map side message

#### Scenario: Optional scene flavor and non-grid appearance are preserved

- **GIVEN** otherwise identical grid or anchor rooms with and without a scene-flavor paragraph
- **WHEN** each is looked at through the text command, direct appearance hook and browser action
- **THEN** the flavor-bearing appearance retains description, flavor paragraph and exits in that order, and the flavor-less appearance omits only that paragraph
- **AND** neither emits an ASCII minimap
- **AND** ordinary room, Limbo, terrain and instance appearance behavior remains unchanged
