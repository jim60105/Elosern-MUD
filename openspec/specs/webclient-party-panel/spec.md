## Purpose

The version-1 `party` presentation panel: the server-owned companion read
model (shape, NPC wire vocabulary reuse, stage-name-only bond disclosure,
staleness filtering, push timing around the party write seams, and read-only
presenter isolation) that the companion quickbar and party drawer consume.

## Requirements

### Requirement: The party panel is an exact read-only version-2 presentation panel
The presentation registry SHALL register a `party` panel at schema version 2. Its available form
SHALL contain exactly `schema_version`, `available`, and `slots`, where `slots` is an ordered
array of zero to four companion rows, and the registered common unavailable form SHALL keep the
shared field set, reason, and semantics. Each slot row SHALL contain exactly `identity`,
`display_name`, `portrait_ref`, `hp_current`, `hp_maximum`, and `bond_stage`: `identity` SHALL be
the companion's positive integer database identity — the same field a combat participant row
carries, so a client can join the two panels; `display_name` SHALL be the canonical NPC display
name truncated to the shared display-name bound; `portrait_ref` SHALL be the opaque string key of
the companion NPC's default gallery portrait — an ASCII decimal string of 1–32 characters
that resolves through the art panel's
`portrait_catalog`, emitted by the same reference format the art panel presenter uses — or `null`
when the companion has no gallery record or no default card, in which case the client renders its
truthful initial-letter placeholder; `hp_current` and `hp_maximum` SHALL
be non-negative integers from the companion's true traits; and `bond_stage` SHALL be the
canonical stage NAME string from the affinity rulebook's stage table. The raw affinity number
SHALL NOT appear anywhere in the payload. The presenter SHALL be read-only: it SHALL NOT mutate
party membership, traits, affinity, combat, quest, or world state, and SHALL emit no live object
or filesystem reference. The presenter SHALL resolve `portrait_ref` by reading each companion's
gallery record (`world.art.gallery.record_for` with `create=False`) and its default card, never
by creating a record, queueing generation, or inventing a URL.

While the session actor is a possessed NPC, the presenter SHALL resolve the party's bound OWNER —
the player named by the NPC-side `party_member` back-reference — and serialize that player's live
companions with their owner-keyed bond stages, so the panel keeps listing the whole party,
including the possessed companion, instead of the NPC's own (empty) party binding. When the
back-reference resolves to no live player, the presenter SHALL raise the registry-unavailable
error and the panel SHALL take the shared unavailable form.

#### Scenario: A two-companion party serializes exactly the six-key bounded rows
- **WHEN** a puppeted explorer with two live companions — one with a gallery portrait, one without — receives a full snapshot
- **THEN** `party.slots` carries two rows in party-list order with the exact field set, their
  true HP integers, each companion's canonical bond stage name, the first companion's
  `portrait_ref` as a non-null `portrait_catalog` key and the second's as `null`, and no raw
  affinity value appears in the payload

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
- **WHEN** a candidate party payload carries a fifth row, an unknown or missing row key, a
  numeric `bond_stage`, a negative HP value, an over-bound display name, or a non-string
  non-null `portrait_ref`, an empty/non-decimal ref, or a ref longer than 32 characters
- **THEN** the server validator rejects it and the client mirror rejects it identically

#### Scenario: Creation-pending puppets see the unavailable form
- **WHEN** a creation-pending puppet receives a snapshot
- **THEN** `party` uses the shared unavailable form with its standard reason

### Requirement: Party presentation stays current across membership and combat changes
The coordinator SHALL include the `party` panel in the presentation updates it pushes after the
party write seams (`join_party`, `leave_party`, membership purge) and wherever it already
re-pushes companion-adjacent state on combat settlement, so committed `party.slots` never
displays a dismissed companion, a stale HP integer, or a stale `portrait_ref` after the next
settlement commit. The panel
SHALL be pushed for exploration and combat puppets alike. The client-side panel allowlists (the
UMD protocol mirror and the Vue store mirror) SHALL name `party` in lockstep with the server
registry so a committed party payload validates identically on all three.

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

### Requirement: Party tokens are joined, not duplicated
The `party` panel SHALL NOT carry a combat token field: the session's `aN` numbering SHALL stay
owned solely by the combat view, and any surface needing both SHALL join `party.slots` to the
combat panel's participant rows by `identity`.

#### Scenario: Join by identity recovers the session token
- **WHEN** a companion participates in the player's combat session and a client joins
  `party.slots` to `combat.participants` on `identity`
- **THEN** every party row that is fighting resolves to exactly one `aN` token from the combat
  panel, and the party payload itself named no token

### Requirement: The party drawer offers possession controls per companion
The Vue PartyDrawer SHALL render, on each companion row, the `explore.possess` affordance from
the shared exploration vocabulary (enabled state and disabled reason exactly as emitted), and
SHALL present the single `explore.possess_release` control while the vocabulary carries one; the
controls SHALL dispatch through the same `ui_action` path as every other affordance. The `party`
panel payload itself SHALL NOT gain any possession field: possession state reaches the client
through the vocabulary and the possession banner only, and the schema-version-2 six-key row
contract is unchanged.

#### Scenario: A possessable companion row offers the action
- **WHEN** the drawer renders a co-located bound companion whose possess entry is enabled
- **THEN** the row carries the 附身 control and dispatching it submits `explore.possess` with the
  companion's id

#### Scenario: A gated companion row shows the gate honestly
- **WHEN** the companion's possess entry is disabled with a gate reason
- **THEN** the row renders the control disabled carrying the emitted reason, never hidden

#### Scenario: The panel payload schema is untouched
- **WHEN** the party panel payload is validated while the player possesses a companion
- **THEN** the payload is byte-identical in shape to the schema-version-2 contract and carries no
  possession field
