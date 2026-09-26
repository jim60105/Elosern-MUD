## MODIFIED Requirements

### Requirement: The dialogue session is deterministic-core-only character state
The dialogue session SHALL be persistent JSON-safe state on the character (`db.dialogue_session`)
naming the host NPC's database identity, the latest server-authored line, and an update marker.
Its ONLY writers SHALL be the deterministic dialogue-session helpers: the `explore.talk_open`,
`explore.talk_scripted`, and `explore.talk_freeform` adapter success paths, the `talk` text-command
path, the `explore.dialogue_leave` adapter success path, and the clear seams — a successful
`settle_movement` of the character, an `engage` involving the actor, and
NPC leave-room, despawn, or leave-party cleanup naming the session NPC. The `explore.talk_open`
success path SHALL open the session with the host's authored greeting or, for a host without one,
the fixed server-authored fallback line, and SHALL write nothing else. No presenter, AI layer,
client payload, or `ui_action` other than these adapters SHALL open,
refresh, or clear a session directly. A session whose
NPC identity no longer resolves to a present, interactable NPC in the character's location SHALL
be treated as not live: the panel degrades to the unavailable form and the next clear seam or
talk retires it, and the stale dbid SHALL NOT reach the wire. With every AI profile disabled,
the scripted table path SHALL fully drive open, refresh, line, and choices.

#### Scenario: Talking through any surface opens the session
- **WHEN** the same scripted exchange is delivered via the WS action and via the `talk` command
- **THEN** both paths leave the character holding a session naming that NPC with the authored
  line, and no other session writer is involved

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
  the fixed fallback line), a live session naming another host is replaced by it, and no state
  other than `db.dialogue_session` changes
