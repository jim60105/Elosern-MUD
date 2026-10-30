# Spec Delta

## Purpose

Select the wilderness presentation, remap HUD slots, refresh the live area map and show committed party medallions without waiting for sight rules. This capability defines observable browser travel behavior and its data boundaries.

## ADDED Requirements

### Requirement: Wilderness presentation follows committed room identity
The browser SHALL select travel presentation from committed wilderness room identity during exploration, remap existing HUD anchors and restore ordinary dialogue, combat and settlement layouts without adding a server mode.

#### Scenario: Committed entry and exit
- **WHEN** a synthetic gate move commits wilderness and then settlement identities, or dialogue/combat opens there
- **THEN** the matching presentation changes only on commits, travel actor anchors stay empty and ordinary layouts return

#### Scenario: Motion and absent identity
- **WHEN** motion is off or the room descriptor is unavailable
- **THEN** selection has no delayed transition at off and an unavailable identity never fabricates travel mode

### Requirement: Travel area refresh follows committed state
The active travel stage SHALL request current area data through the existing on-demand map transport, retain stale committed imagery dimmed and disable movement until a correlated complete current map is adopted.

#### Scenario: Result and body order
- **WHEN** a refresh result and complete map arrive in either order, with intervening partial, stale or foreign-epoch responses
- **THEN** only the current matching pair enables the stage and no partial response replaces the last map

#### Scenario: Refresh causes
- **WHEN** entry, committed movement, time change and look occur while aim/render/failed moves also change
- **THEN** only committed refresh causes schedule coalesced requests through the single dispatch gate

### Requirement: Medallions identify committed physiological subjects
Travel medallions SHALL join each present member to its own committed portrait and fatigue facts, expose reserve and sleep with text or shape cues and identify the controlled body without deriving fatigue rules.

#### Scenario: Possession and missing facts
- **WHEN** synthetic owner and controlled companion have different reserves/postures and one portrait or fatigue row is absent
- **THEN** each identity retains its own supplied values, sleep cue and truthful missing state without duplicate controlled members

