# Spec Delta

## MODIFIED Requirements

### Requirement: The party panel is an exact read-only version-2 presentation panel
The party panel SHALL present one ordered row per exact NPC in the canonical roster, including dual membership. Existing version-2 identity/display/portrait/HP/bond-stage vocabulary, possession owner resolution, unavailable forms and read-only behavior SHALL remain; server/client validators SHALL extend the version-2 shape together. Each row SHALL add `membership` with boolean `general` and ordered `temporary_commissions`; the panel SHALL add `general_quota` with integer `used` and `limit`.

#### Scenario: Full general party plus escorts is complete
- **WHEN** four general members and two temporary-only members are presented
- **THEN** six ordered rows appear, general usage is four of four, every temporary actor is reachable through existing controls and no quota-based truncation occurs

#### Scenario: Dual member is one truthful row
- **WHEN** a general member carries two escort reasons
- **THEN** one row marks general true and identifies both commissions without duplicate identity or raw affinity

#### Scenario: Stale and dangling bindings do not leak
- **WHEN** membership references a deleted actor or invalid temporary source, or a possessed actor has no valid owner
- **THEN** stale rows/reasons are filtered through canonical readers and invalid-owner presentation uses the shared unavailable form

#### Scenario: Shape validators and clients change together
- **WHEN** server, protocol mirror and Vue validators receive the extended panel or malformed metadata/quota
- **THEN** all accept the same valid shape and reject malformed shapes while retaining existing portrait/HP/display bounds

#### Scenario: A two-companion party serializes exactly the six-key bounded rows
- **WHEN** two general members are presented through the extended version-2 panel
- **THEN** each preserves the existing six NPC fields and adds validated membership metadata, while the panel separately reports general quota usage

#### Scenario: The raw affinity number never appears
- **WHEN** any party payload is serialized
- **THEN** the raw affinity number appears nowhere in the payload

#### Scenario: Possession keeps listing the owner's party
- **WHEN** the player possesses one of her two companions and the next full snapshot arrives
- **THEN** `party.slots` still carries both companions — the possessed NPC among them — with the owner-keyed bond stages, and a client can join the front figure to the banner by identity

#### Scenario: A possessed stranger's party is unavailable, not empty
- **WHEN** the session actor is an NPC whose `party_member` back-reference names no live player and a snapshot presents the party panel
- **THEN** the panel takes the shared unavailable form rather than an available empty row list

#### Scenario: An empty party is an available empty list
- **WHEN** a puppeted explorer with no companions receives a full snapshot
- **THEN** `party` is available with `slots` exactly `[]` and no unavailable reason

#### Scenario: Stale membership bindings never reach the wire
- **WHEN** a player's stored party list contains a database identity whose NPC no longer exists
- **THEN** the party panel's slots omit that identity without error and validation accepts the
  payload

#### Scenario: Validation rejects row-shape drift
- **WHEN** a panel contains missing/unknown keys, malformed membership or quota, numeric bond stage, invalid HP, display or portrait reference
- **THEN** server and client mirrors reject identically; a fifth valid temporary row is accepted

#### Scenario: Creation-pending puppets see the unavailable form
- **WHEN** a creation-pending puppet receives a snapshot
- **THEN** `party` uses the shared unavailable form with its standard reason

#### Scenario: Identity is the database identity shared with combat rows
- **WHEN** a slot row is serialized
- **THEN** `identity` is the companion's positive integer database identity — the same field a
  combat participant row carries, so a client can join the two panels

#### Scenario: Display names honor the shared bound
- **WHEN** the companion's canonical NPC display name exceeds the shared display-name bound
- **THEN** `display_name` is the canonical name truncated to that bound

#### Scenario: portrait_ref is the art panel's opaque reference format
- **WHEN** a companion's gallery record has a default card
- **THEN** `portrait_ref` is the opaque string key of the companion NPC's default gallery portrait
  — an ASCII decimal string of 1–32 characters that resolves through the art panel's
  `portrait_catalog`, emitted by the same reference format the art panel presenter uses

#### Scenario: A missing portrait is null, not fabricated
- **WHEN** the companion has no gallery record or no default card
- **THEN** `portrait_ref` is `null` and the client renders its truthful initial-letter placeholder

#### Scenario: HP fields come from the true traits
- **WHEN** a slot row is serialized
- **THEN** `hp_current` and `hp_maximum` are non-negative integers from the companion's true traits

#### Scenario: bond_stage carries only the stage name
- **WHEN** a slot row is serialized
- **THEN** `bond_stage` is the canonical stage NAME string from the affinity rulebook's stage table

#### Scenario: The presenter is read-only and leak-free
- **WHEN** the party presenter runs
- **THEN** it does not mutate party membership, traits, affinity, combat, quest, or world state,
  and emits no live object or filesystem reference

#### Scenario: Portrait resolution never writes or invents
- **WHEN** the presenter resolves `portrait_ref`
- **THEN** it reads each companion's gallery record (`world.art.gallery.record_for` with
  `create=False`) and its default card, never creating a record, queueing generation, or inventing
  a URL

#### Scenario: A possessed NPC presents the bound owner's party
- **WHEN** the session actor is a possessed NPC
- **THEN** the presenter resolves the party's bound OWNER — the player named by the NPC-side
  `party_member` back-reference — and serializes that player's live companions with their
  owner-keyed bond stages, so the panel keeps listing the whole party, including the possessed
  companion, instead of the NPC's own (empty) party binding

#### Scenario: A dangling owner back-reference raises unavailable
- **WHEN** the `party_member` back-reference resolves to no live player
- **THEN** the presenter raises the registry-unavailable error and the panel takes the shared
  unavailable form

#### Scenario: Quota, row count and commission reference bounds
- **WHEN** a dual member or an over-quota party is presented
- **THEN** General usage SHALL use valid general identity, total roster rows SHALL not be limited to four, and temporary commission references SHALL contain exact quest identity and protected-role reference with player-permitted labels, never private planning data. Existing portrait formatting/bounds and no-raw-affinity rules SHALL remain.

### Requirement: Party presentation stays current across membership and combat changes
Existing exploration/combat party push seams SHALL include temporary joins, per-source releases and general identity changes after commit. Existing combat HP/portrait refresh behavior SHALL remain. Related mission state/reason, phase and offer capabilities SHALL refresh after committed changes; stale choices SHALL refuse. Text clients SHALL retain equivalent interaction and explicit reasons. No new escort-control UI SHALL be added.

#### Scenario: Membership and invalidation refresh committed controls
- **WHEN** an escort ends or an alternative invalidates while the party/quest/dialogue surfaces are open
- **THEN** the next committed view shows remaining membership and explicit mission reason, refreshes capability versions, and rejects old acceptance/dismissal choices

#### Scenario: Rolled-back transitions do not refresh false state
- **WHEN** a release or arbitration rolls back after a write
- **THEN** connected clients receive no success view or stale-capability replacement based on that rolled-back state

#### Scenario: Dismissing a companion re-pushes the party panel
- **WHEN** a companion leaves the party through the leave seam while the puppet is connected
- **THEN** the coordinator pushes an update whose `party.slots` no longer carries that identity

#### Scenario: Combat settlement refreshes companion HP
- **WHEN** combat settlement changes a participating companion's HP and the presentation
  refreshes
- **THEN** the next committed `party` payload carries the companion's new HP integers

#### Scenario: The three panel allowlists agree
- **WHEN** the panel contract test enumerates the server registry names, the UMD allowlist, and
  the Vue store allowlist
- **THEN** every registered panel name appears in all three lists and the contract fails on any
  drift

#### Scenario: Committed slots never show stale companion state
- **WHEN** updates are pushed per the seams and settlement re-pushes
- **THEN** committed `party.slots` never displays a dismissed companion, a stale HP integer, or a
  stale `portrait_ref` after the next settlement commit

#### Scenario: Client mirrors name the panel in lockstep
- **WHEN** the client-side panel allowlists (the UMD protocol mirror and the Vue store mirror)
  are compared with the server registry
- **THEN** they name `party` in lockstep so a committed party payload validates identically on all
  three

### Requirement: The party drawer offers possession controls per companion
Existing party drawer controls SHALL render server-owned possess/release enablement and reasons for every effective row, including temporary actors beyond the general quota. Dispatch SHALL remain through the shared action path. Existing layout/input behavior SHALL remain; no dedicated escort-control screen SHALL be introduced. Source-aware dismissal SHALL route to existing quest abandonment choices when an effective escort reason would be removed.

#### Scenario: Beyond-quota temporary actor remains controllable
- **WHEN** a temporary-only sixth row passes possession gates
- **THEN** its existing possess control dispatches for its exact identity and the normal release control remains available

#### Scenario: A possessable companion row offers the action
- **WHEN** the drawer renders a co-located bound companion whose possess entry is enabled
- **THEN** the row carries the 附身 control and dispatching it submits `explore.possess` with the
  companion's id

#### Scenario: A gated companion row shows the gate honestly
- **WHEN** the companion's possess entry is disabled with a gate reason
- **THEN** the row renders the control disabled carrying the emitted reason, never hidden

#### Scenario: The panel payload schema is untouched
- **WHEN** party possession controls render for general and temporary rows after the coordinated unreleased payload extension
- **THEN** controls use the existing vocabulary while server and client validators agree on membership metadata and general quota fields

#### Scenario: Possession state rides the vocabulary and banner only
- **WHEN** possession control state is displayed on the extended party panel
- **THEN** control permission still comes from the existing shared vocabulary/banner and rows add no duplicated possession state or combat token
