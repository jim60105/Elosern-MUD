# Delta: webclient-dialogue-session

## MODIFIED Requirements

### Requirement: The dialogue session is deterministic-core-only character state
The dialogue session SHALL be persistent JSON-safe state on the character (`db.dialogue_session`)
naming the host NPC's database identity, the latest server-authored line, and an update marker.
Its ONLY writers SHALL be the deterministic dialogue-session helpers: the `explore.talk_scripted`
and `explore.talk_freeform` adapter success paths, the `talk` text-command path, the
`explore.dialogue_leave` adapter success path, and the clear
seams — a successful `settle_movement` of the character, an `engage` involving the actor, and
NPC leave-room, despawn, or leave-party cleanup naming the session NPC. No presenter, AI layer,
client payload, or `ui_action` other than the `explore.dialogue_leave` adapter SHALL open,
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
- **WHEN** every LLM and image profile is disabled and the player works only scripted keywords
- **THEN** session open, line refresh, choices, mode, and clears all behave identically with zero
  network requests

### Requirement: The dialogue panel is an exact read-only version-1 presentation panel
The presentation registry SHALL register a `dialogue` panel at schema version 1. Its available
form SHALL contain exactly `schema_version`, `available`, `kind`, `host`, `bond_stage`, `line`,
and `choices`: `host` SHALL contain exactly `identity` (the present NPC's positive database
identity), `display_name` (bounded by the shared display-name bound), and `portrait_ref`
(`null` in this schema version, the same vocabulary as party rows); `bond_stage` SHALL be the
affinity stage NAME from the rulebook stage table when the host NPC has a relationship with the
viewer and `null` otherwise, and the raw affinity number SHALL NOT appear anywhere in the
payload; `line` SHALL be the session's latest server-authored reply line bounded by the shared
narrative-line bound; and `choices` SHALL be an ordered list of at most four
`{keyword_id, label}` descriptors — the panel-owned presentation bound, independent of the
interact target descriptor's own sixteen-keyword keyword-pool bound — derived from the host's
dialogue table in table order (the same prefix the interact affordance truncation takes), the
same vocabulary owner the interact target descriptor uses, empty when the host's table is empty.
The registered
unavailable form SHALL carry reason `dialogue_unavailable` with the player message
`對話目前無法顯示` and the shared field set and semantics. The panel SHALL be available exactly
when the viewer's live dialogue session resolves; the presenter SHALL be read-only — it SHALL NOT
open, refresh, clear, or mutate any session, affinity, memory, or world state — and SHALL emit no
live object or filesystem reference.

#### Scenario: A live scripted session serializes the host triple and table choices
- **WHEN** a viewer with a live dialogue session against a bonded table host receives a snapshot
- **THEN** `dialogue` is available with the host's identity/display name and null portrait, the
  bond stage name, the recorded line, and the host's first four keyword descriptors in table
  order, with no affinity numeral present

#### Scenario: A host with more than four authored keywords is truncated to the first four
- **WHEN** the session host's dialogue table carries five or more authored keywords
- **THEN** the panel's `choices` carry exactly the first four in table order and the server
  validator accepts the payload

#### Scenario: An unbonded host discloses a null stage
- **WHEN** the session host has no relationship record for the viewer
- **THEN** `bond_stage` is `null` and the rest of the payload is unaffected

#### Scenario: No live session is the unavailable form
- **WHEN** a viewer without a dialogue session receives a snapshot
- **THEN** `dialogue` uses the `dialogue_unavailable` form and no host, line, or choices ship

#### Scenario: Validation rejects payload drift
- **WHEN** a candidate dialogue payload carries a fifth choice, an unknown or missing
  field, a numeric `bond_stage`, or an over-bound line
- **THEN** the server validator rejects it and the client mirror rejects it identically

## ADDED Requirements

### Requirement: explore.dialogue_leave ends the live session through the sole writer
The production action registry SHALL register `explore.dialogue_leave` with a payload accepting
exactly `npc_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated
session and re-read the actor's LIVE session through
`world.rules.dialogue.live_dialogue_session`; with no live session, or a live session naming an
NPC other than `npc_id`, the adapter SHALL reject with stable code `dialogue_inactive` before
writing anything. On its success path the adapter SHALL clear the session through the sole-writer
`clear_dialogue_session` helper, mark the viewer's presentation dirty through the same push seam
the other clear seams use, and return a deterministic success result; it SHALL NOT change
affinity, memory, party membership, or any other world state. The clear SHALL commit through the
normal presentation path, so the next committed presentation carries mode `exploration` and the
unavailable `dialogue` panel atomically.

#### Scenario: Leaving ends the session and restores exploration mode
- **WHEN** a viewer with a live session against NPC 41 submits `explore.dialogue_leave` with
  `npc_id` 41
- **THEN** the session is cleared through the sole writer, the action succeeds once, and the next
  committed presentation carries mode `exploration` with the `dialogue` panel unavailable

#### Scenario: A stale or mismatched leave rejects without any write
- **WHEN** the viewer holds no live session, or a live session naming a different NPC, and
  submits `explore.dialogue_leave`
- **THEN** the adapter rejects with stable code `dialogue_inactive`, no session state is written,
  and the committed mode is unchanged

#### Scenario: Leaving writes nothing but the session
- **WHEN** a successful `explore.dialogue_leave` settles
- **THEN** affinity, memories, party bindings, and room state are byte-identical to before the
  action, and only `db.dialogue_session` changed
