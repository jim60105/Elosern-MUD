# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The dialogue panel is an exact read-only version-2 presentation panel`
- TO: `### Requirement: The dialogue panel is an exact read-only version-3 presentation panel`

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
  the fixed fallback line), a live session naming another host is replaced by it, and no state
  other than `db.dialogue_session` changes

#### Scenario: The clear seams are exactly the movement, engage, and NPC cleanup paths
- **WHEN** a clear seam fires
- **THEN** it is one of: a successful `settle_movement` of the character, an `engage` involving the actor, and NPC leave-room, despawn, or leave-party cleanup naming the session NPC

#### Scenario: The talk_open success path writes only the session opening
- **WHEN** conversation open succeeds
- **THEN** it writes only the session with the shared resolver's current fixed greeting or existing fallback and does not call a model

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

### Requirement: The dialogue panel is an exact read-only version-3 presentation panel
The version-3 dialogue panel SHALL carry bounded host and acting-body identity/portrait descriptors, context-bound delivery, all reachable topic choices, public-chain descriptors, reading revision and optional live unlock batch. Available and unavailable forms SHALL be exact, read-only and JSON-safe. Numeric affinity and unauthorized qualified scene bodies SHALL never ship.

#### Scenario: Generated choices obey existing panel bounds
- **WHEN** a generated current phase exposes more than sixteen permitted topics
- **THEN** the panel renders every permitted topic in declared order up to sixteen with version-3 descriptor fields and rejects schema drift

#### Scenario: Reopening after closure shows current everyday topics
- **WHEN** a supported committed closure transition removes the commission topic and the player reopens the conversation
- **THEN** the same panel shows everyday greeting/topics and no obsolete commission capability

#### Scenario: A live scripted session serializes the host triple and table choices
- **WHEN** a viewer with a live dialogue session against a bonded table host receives a snapshot
- **THEN** `dialogue` is available with the host's identity, display name, and the host's art
  catalog key as `portrait_ref`, the bond stage name, the recorded native line or complete scene delivery, and the host's all at most sixteen
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

#### Scenario: A host with more than sixteen authored keywords is truncated to the all at most sixteen
- **WHEN** the session host's dialogue table carries sixteen authored topics
- **THEN** the panel's `choices` carry exactly the all at most sixteen in table order and the server
  validator accepts the payload

#### Scenario: An unbonded host discloses a null stage
- **WHEN** the session host has no relationship record for the viewer
- **THEN** `bond_stage` is `null` and the rest of the payload is unaffected

#### Scenario: No live session is the unavailable form
- **WHEN** a viewer without a dialogue session receives a snapshot
- **THEN** `dialogue` uses the `dialogue_unavailable` form and no host, line, or choices ship

#### Scenario: Validation rejects payload drift
- **WHEN** a candidate dialogue payload carries a seventeenth choice, an unknown or missing field, a
  numeric `bond_stage`, an over-bound line, a numeric `portrait_ref`, a `portrait_ref` with a
  non-digit character, or a `portrait_ref` longer than 32 characters
- **THEN** the server validator rejects it and the client mirror rejects it identically, while
  the same payload with `portrait_ref` `"42"` or `null` validates on both sides

#### Scenario: The host triple carries its exact fields
- **WHEN** a dialogue payload is validated
- **THEN** `host` SHALL contain exactly `identity` (the present NPC's positive database identity), `display_name` (bounded by the shared display-name bound), and `portrait_ref`

#### Scenario: The bond stage discloses only the stage name
- **WHEN** a dialogue payload renders `bond_stage`
- **THEN** it SHALL be the affinity stage NAME from the rulebook stage table when the host NPC has a relationship with the viewer and `null` otherwise, and the raw affinity number SHALL NOT appear anywhere in the payload

#### Scenario: The line carries the bounded latest reply
- **WHEN** a dialogue payload renders `line`
- **THEN** it SHALL be the current context-bound native line delivery or complete scene with per-line and total scene bounds

#### Scenario: Choices follow the panel-owned sixteen-descriptor table bound
- **WHEN** a dialogue payload renders choices
- **THEN** it emits at most sixteen ordered version-3 topic descriptors from the shared permitted current-definition resolver, retains the existing vocabulary and independent keyword-pool bound, and emits no choices for an empty definition

#### Scenario: The portrait reference is the shared catalog key or null
- **WHEN** a dialogue payload renders `portrait_ref`
- **THEN** it SHALL be the opaque `webclient-art-panel` portrait-catalog key for the host when the host is present in the art view the `art` panel is built from for the same viewer; including an entry that resolves to a placeholder card; and SHALL be `null` only when the host is absent from that view or the art view cannot be built

#### Scenario: Only the server derives the catalog key and the wire form is bounded
- **WHEN** `portrait_ref` is produced and serialized
- **THEN** the server SHALL derive the key with the same single catalog-key mapper the art panel and the combat participants use, so a non-null `portrait_ref` equals a key of the committed catalog in the same snapshot; the client SHALL NOT construct a catalog key from the host identity; and on the wire `portrait_ref` SHALL be `null` or a decimal-digit string of at most 32 characters, the same vocabulary as a combat participant's `portrait_ref`

#### Scenario: The unavailable form carries the stable reason and player message
- **WHEN** the registered unavailable form is used
- **THEN** it SHALL carry reason `dialogue_unavailable` with the player message `對話目前無法顯示` and the shared field set and semantics

#### Scenario: Exact available field set
- **WHEN** a current dialogue snapshot is serialized
- **THEN** its fields are exactly schema_version, available, kind, host, actor, bond_stage, context_id, delivery, choices, pure_chain, reading_revision and unlock_batch; delivery and choices obey the shared version-3 bounds and mirrors reject version 2

#### Scenario: The acting portrait is server-derived
- **WHEN** an acting body differs from the owner during possession
- **THEN** actor names that body and its catalog portrait reference uses the same mapper as art; no owner numeric identity or private affinity value is disclosed

### Requirement: Encounter updates expose only committed visible interaction targets

Activation SHALL refresh existing room occupant/affordance and conversation projections after commit through upstream phase-aware session helpers. Presence, visibility/access and current phase gates SHALL remain authoritative. Arrangement notices SHALL NOT expose unmaterialized roles as occupants. The existing read-only version-3 conversation window SHALL consume actual authorized commission references; client prose SHALL never authorize acceptance.

#### Scenario: Publication and real activation are distinct
- **WHEN** a package is arranged but one future role has not activated
- **THEN** the occupant/conversation projection excludes that role and activation later exposes it only when actually visible/access-eligible

#### Scenario: Real window completes the requested story
- **WHEN** either distinct escort offer is accepted through its actual current conversation window and real movement/possession produces rendezvous
- **THEN** upstream accept_escort_commission and evaluate_escort_event produce the bound record and exclusive result, the alternative becomes invalid, one reward commits and reopening everyday dialogue preserves the same NPC identity and earlier memory

#### Scenario: Rollback sends no false projection
- **WHEN** activation or outcome writes fail and compensate session/cache state
- **THEN** no post-commit new-occupant or success update appears and projections reflect authoritative prior state

#### Scenario: Scripted story works after models are disabled
- **WHEN** profiles are disabled after package publication
- **THEN** real scripted conversation, authorized acceptance, escort, combat/possession and exactly-once settlement remain usable without a model call
