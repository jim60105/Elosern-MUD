# Spec Delta

## ADDED Requirements

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
