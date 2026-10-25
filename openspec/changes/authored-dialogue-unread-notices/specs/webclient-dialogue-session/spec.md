# Spec Delta

## MODIFIED Requirements

### Requirement: The dialogue session is deterministic-core-only character state
The dialogue session SHALL remain deterministic-core-only persistent state for a native line or complete delivered scene snapshot. Replay SHALL begin at line one without effects. Existing open/refresh/clear authority, current-host/phase validation and history-preserving invalidation SHALL remain; presenters SHALL not write sessions.

#### Scenario: Opening a generated host records its fixed line
- **WHEN** a present generated host is opened with models disabled
- **THEN** its current fixed greeting is recorded in the existing session and displayed with its scripted topics without another choice interface

#### Scenario: Phase change refreshes through the sole writer
- **WHEN** a supported committed phase transition changes a live session's role dialogue
- **THEN** the existing deterministic refresh records the current greeting and update marker, preserves history and publishes a newer surface that rejects old choice capabilities

#### Scenario: Cleanup clears the live session
- **WHEN** the player moves, combat starts, or the session host departs or despawns
- **THEN** the existing cleanup clears the session and no stale host is presented

#### Scenario: Talking through any surface opens the session
- **WHEN** the same scripted exchange is delivered via the WS action and via the `talk` command
- **THEN** both paths leave the character holding a session naming that NPC with the authored
  delivery, and no other session writer is involved

#### Scenario: Moving away clears the session
- **WHEN** a viewer with a live dialogue session completes a successful movement settlement
- **THEN** the session is cleared and the committed presentation returns to mode `exploration`
  with the `dialogue` panel unavailable

#### Scenario: Entering combat clears the session
- **WHEN** the actor engages a hostile while a dialogue session is live
- **THEN** the session is cleared and the committed mode is `combat`

#### Scenario: The host departing ends the session presentation
- **WHEN** the session NPC leaves the room or despawns
- **THEN** the session is cleared on the cleanup seam and the panel is unavailable at the next
  commit, never presenting a stale host

#### Scenario: Offline scripted dialogue drives the whole panel
- **WHEN** every LLM and image profile is disabled and the player opens a conversation with
  `explore.talk_open` and then works only scripted keywords
- **THEN** session open, line refresh, choices, mode, and clears all behave identically with zero
  network requests

#### Scenario: Opening a conversation is a session write
- **WHEN** an actor with no session submits a successful `explore.talk_open` for a present host
- **THEN** the character holds a session naming that host whose line is the host's greeting (or
  the fixed fallback line), a live session naming another host is replaced by it, and no gameplay effect changes; only db.dialogue_session and narrative-owned availability observation are written

#### Scenario: The clear seams are exactly the movement, engage, and NPC cleanup paths
- **WHEN** a clear seam fires
- **THEN** it is one of: a successful `settle_movement` of the character, an `engage` involving the actor, and NPC leave-room, despawn, or leave-party cleanup naming the session NPC

#### Scenario: The talk_open success path writes only the session opening
- **WHEN** conversation open succeeds
- **THEN** it writes the session with the current greeting/fallback and deterministic narrative availability observation, without gameplay effects or a model call

#### Scenario: No other layer touches a session directly
- **WHEN** a presenter, generative layer or client encounters a session
- **THEN** it performs no direct session writes; deterministic phase transitions invoke only the existing sole-writer refresh helper

#### Scenario: A session whose host no longer resolves is treated as not live
- **WHEN** a session's NPC identity no longer resolves to a present, interactable NPC in the character's location
- **THEN** the session SHALL be treated as not live: the panel degrades to the unavailable form, the next clear seam or talk retires it, and the stale dbid SHALL NOT reach the wire

#### Scenario: The scripted table path drives the session fully offline
- **WHEN** every AI profile is disabled
- **THEN** the scripted table path SHALL fully drive open, refresh, line, and choices

#### Scenario: Session publication rollback compensates effects
- **WHEN** a selection effect succeeds but delivery/session persistence fails
- **THEN** no partial effect or session survives in the database or Attribute caches and no protected success body is delivered
