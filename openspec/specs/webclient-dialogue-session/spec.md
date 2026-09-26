## Purpose

The character-held dialogue session: deterministic-core-only persistent state
naming the host NPC, the latest server-authored line, and an update marker —
the single invisible source of truth the dialogue panel and mode (change 10)
consume, with the only-writers boundary and stale-host rules pinned here.

## Requirements

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
### Requirement: The dialogue panel is an exact read-only version-2 presentation panel
The presentation registry SHALL register a `dialogue` panel at schema version 2. Its available
form SHALL contain exactly `schema_version`, `available`, `kind`, `host`, `bond_stage`, `line`,
and `choices`: `host` SHALL contain exactly `identity` (the present NPC's positive database
identity), `display_name` (bounded by the shared display-name bound), and `portrait_ref`;
`bond_stage` SHALL be the affinity stage NAME from the rulebook stage table when the host NPC has
a relationship with the viewer and `null` otherwise, and the raw affinity number SHALL NOT appear
anywhere in the payload; `line` SHALL be the session's latest server-authored reply line bounded
by the shared narrative-line bound; and `choices` SHALL be an ordered list of at most four
`{keyword_id, label}` descriptors — the panel-owned presentation bound, independent of the
interact target descriptor's own sixteen-keyword keyword-pool bound — derived from the host's
dialogue table in table order (the same prefix the interact affordance truncation takes), the
same vocabulary owner the interact target descriptor uses, empty when the host's table is empty.

`portrait_ref` SHALL be the opaque `webclient-art-panel` portrait-catalog key for the host when the
host is present in the art view the `art` panel is built from for the same viewer — including an
entry that resolves to a placeholder card — and SHALL be `null` only when the host is absent from
that view or the art view cannot be built. The server SHALL derive the key with the same single
catalog-key mapper the art panel and the combat participants use, so a non-null `portrait_ref`
equals a key of the committed catalog in the same snapshot; the client SHALL NOT construct a
catalog key from the host identity. On the wire `portrait_ref` SHALL be `null` or a decimal-digit
string of at most 32 characters, the same vocabulary as a combat participant's `portrait_ref`.

The registered
unavailable form SHALL carry reason `dialogue_unavailable` with the player message
`對話目前無法顯示` and the shared field set and semantics. The panel SHALL be available exactly
when the viewer's live dialogue session resolves; the presenter SHALL be read-only — it SHALL NOT
open, refresh, clear, or mutate any session, affinity, memory, art, or world state — and SHALL
emit no live object or filesystem reference.

#### Scenario: A live scripted session serializes the host triple and table choices
- **WHEN** a viewer with a live dialogue session against a bonded table host receives a snapshot
- **THEN** `dialogue` is available with the host's identity, display name, and the host's art
  catalog key as `portrait_ref`, the bond stage name, the recorded line, and the host's first four
  keyword descriptors in table order, with no affinity numeral present

#### Scenario: The host's portrait reference matches the art catalog
- **WHEN** a viewer with a live session against a scripted host receives one snapshot carrying
  both the `art` and the `dialogue` panel, once while the host's portrait is generated and once
  while it is still pending
- **THEN** in both snapshots `dialogue.host.portrait_ref` is a key of `art.portrait_catalog`, and
  that entry carries the image URL in the first snapshot and the placeholder card in the second

#### Scenario: A host outside the art view carries a null reference
- **WHEN** the session host is a generative NPC with no dialogue component and no named portrait
  policy, or the art view cannot be built for the viewer
- **THEN** `portrait_ref` is `null`, the rest of the payload is unaffected, and the panel stays
  available

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
- **WHEN** a candidate dialogue payload carries a fifth choice, an unknown or missing field, a
  numeric `bond_stage`, an over-bound line, a numeric `portrait_ref`, a `portrait_ref` with a
  non-digit character, or a `portrait_ref` longer than 32 characters
- **THEN** the server validator rejects it and the client mirror rejects it identically, while
  the same payload with `portrait_ref` `"42"` or `null` validates on both sides

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
