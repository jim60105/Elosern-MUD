## Purpose

The character-held dialogue session: deterministic-core-only persistent state
naming the host NPC, the latest server-authored line, and an update marker —
the single invisible source of truth the dialogue panel and mode (change 10)
consume, with the only-writers boundary and stale-host rules pinned here.

## Requirements

### Requirement: The dialogue session is deterministic-core-only character state
The dialogue session SHALL be persistent JSON-safe state on the character (`db.dialogue_session`)
naming the host NPC's database identity, the latest server-authored line, and an update marker.
Its ONLY writers SHALL be the deterministic dialogue-session helpers: the `explore.talk_scripted`
and `explore.talk_freeform` adapter success paths, the `talk` text-command path, and the clear
seams — a successful `settle_movement` of the character, an `engage` involving the actor, and
NPC leave-room, despawn, or leave-party cleanup naming the session NPC. No presenter, AI layer,
client payload, or `ui_action` SHALL open, refresh, or clear a session directly. A session whose
NPC identity no longer resolves to a present, interactable NPC in the character's location SHALL
be treated as not live: the session helper reports it as not live, the next clear seam or talk
retires it, and the stale dbid SHALL NOT reach any presentation. With every AI profile disabled,
the scripted table path SHALL fully drive open, refresh, and line.

#### Scenario: Talking through any surface opens the session
- **WHEN** the same scripted exchange is delivered via the WS action and via the `talk` command
- **THEN** both paths leave the character holding a session naming that NPC with the authored
  line, and no other session writer is involved

#### Scenario: Moving away clears the session
- **WHEN** a viewer with a live dialogue session completes a successful movement settlement
- **THEN** the session is cleared and the session helper reports no live session

#### Scenario: Entering combat clears the session
- **WHEN** the actor engages a hostile while a dialogue session is live
- **THEN** the session is cleared

#### Scenario: The host departing ends the session
- **WHEN** the session NPC leaves the room or despawns
- **THEN** the session is cleared on the cleanup seam and never resolves to a stale host

#### Scenario: Offline scripted dialogue drives the whole session
- **WHEN** every LLM and image profile is disabled and the player works only scripted keywords
- **THEN** session open, line refresh, and clears all behave identically with zero network requests
