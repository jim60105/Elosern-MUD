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
narrative-line bound; and `choices` SHALL be an ordered list of at most sixteen
`{keyword_id, label}` descriptors derived from the host's dialogue table — the same vocabulary
owner the interact target descriptor uses — empty when the host's table is empty. The registered
unavailable form SHALL carry reason `dialogue_unavailable` with the player message
`對話目前無法顯示` and the shared field set and semantics. The panel SHALL be available exactly
when the viewer's live dialogue session resolves; the presenter SHALL be read-only — it SHALL NOT
open, refresh, clear, or mutate any session, affinity, memory, or world state — and SHALL emit no
live object or filesystem reference.

#### Scenario: A live scripted session serializes the host triple and table choices
- **WHEN** a viewer with a live dialogue session against a bonded table host receives a snapshot
- **THEN** `dialogue` is available with the host's identity/display name and null portrait, the
  bond stage name, the recorded line, and the host's keyword descriptors in table order, with no
  affinity numeral present

#### Scenario: An unbonded host discloses a null stage
- **WHEN** the session host has no relationship record for the viewer
- **THEN** `bond_stage` is `null` and the rest of the payload is unaffected

#### Scenario: No live session is the unavailable form
- **WHEN** a viewer without a dialogue session receives a snapshot
- **THEN** `dialogue` uses the `dialogue_unavailable` form and no host, line, or choices ship

#### Scenario: Validation rejects payload drift
- **WHEN** a candidate dialogue payload carries a seventeenth choice, an unknown or missing
  field, a numeric `bond_stage`, or an over-bound line
- **THEN** the server validator rejects it and the client mirror rejects it identically

### Requirement: Dialogue mode resolves after combat and before exploration
The coordinator SHALL resolve the committed presentation mode in the order creation-pending →
`creation`, active combat → `combat`, live dialogue session → `dialogue`, else `exploration`.
While mode is `dialogue`, the `exploration` and `character` panels SHALL keep shipping their
ordinary exploration-mode payloads unchanged. Every session open, refresh, and clear SHALL mark
the viewer's presentation dirty so the mode and `dialogue` panel commit atomically with the
underlying state change, and a refresh SHALL keep the recorded line and choices current without
re-opening ceremony. The client-side protocol mirrors (UMD and Vue store) SHALL accept mode
`dialogue` and name the `dialogue` panel in lockstep with the server registry under the
panel/mode agreement contract.

#### Scenario: A reply commits dialogue mode atomically
- **WHEN** a scripted reply is recorded for a connected viewer
- **THEN** one committed presentation carries mode `dialogue`, the available `dialogue` panel, and
  the unchanged exploration panel together

#### Scenario: Combat outranks a live session
- **WHEN** combat becomes active while a session object still exists before its cleanup seam runs
- **THEN** the committed mode is `combat`, never `dialogue`

#### Scenario: A refresh updates the line in place
- **WHEN** the player exchanges another scripted keyword with the same host
- **THEN** the committed `dialogue.line` equals the newest authored reply and the mode stays
  `dialogue` without an intermediate unavailable commit
