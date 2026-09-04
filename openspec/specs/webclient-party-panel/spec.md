## Purpose

The version-1 `party` presentation panel: the server-owned companion read
model (shape, NPC wire vocabulary reuse, stage-name-only bond disclosure,
staleness filtering, push timing around the party write seams, and read-only
presenter isolation) that the companion quickbar and party drawer consume.

## Requirements

### Requirement: The party panel is an exact read-only version-1 presentation panel
The presentation registry SHALL register a `party` panel at schema version 1. Its available form
SHALL contain exactly `schema_version`, `available`, and `slots`, where `slots` is an ordered
array of zero to four companion rows, and the registered common unavailable form SHALL keep the
shared field set, reason, and semantics. Each slot row SHALL contain exactly `identity`,
`display_name`, `portrait_ref`, `hp_current`, `hp_maximum`, and `bond_stage`: `identity` SHALL be
the companion's positive integer database identity — the same field a combat participant row
carries, so a client can join the two panels; `display_name` SHALL be the canonical NPC display
name truncated to the shared display-name bound; `portrait_ref` SHALL be `null` in this schema
version, matching the exploration vocabulary's portrait seam; `hp_current` and `hp_maximum` SHALL
be non-negative integers from the companion's true traits; and `bond_stage` SHALL be the
canonical stage NAME string from the affinity rulebook's stage table. The raw affinity number
SHALL NOT appear anywhere in the payload. The presenter SHALL be read-only: it SHALL NOT mutate
party membership, traits, affinity, combat, quest, or world state, and SHALL emit no live object
or filesystem reference.

#### Scenario: A two-companion party serializes exactly the six-key bounded rows
- **WHEN** a puppeted explorer with two live companions receives a full snapshot
- **THEN** `party.slots` carries two rows in party-list order with the exact field set, their
  true HP integers, and each companion's canonical bond stage name, and no raw affinity value
  appears in the payload

#### Scenario: An empty party is an available empty list
- **WHEN** a puppeted explorer with no companions receives a full snapshot
- **THEN** `party` is available with `slots` exactly `[]` and no unavailable reason

#### Scenario: Stale membership bindings never reach the wire
- **WHEN** a player's stored party list contains a database identity whose NPC no longer exists
- **THEN** the party panel's slots omit that identity without error and validation accepts the
  payload

#### Scenario: Validation rejects row-shape drift
- **WHEN** a candidate party payload carries a fifth row, an unknown or missing row key, a
  numeric `bond_stage`, a negative HP value, or an over-bound display name
- **THEN** the server validator rejects it and the client mirror rejects it identically

#### Scenario: Creation-pending puppets see the unavailable form
- **WHEN** a creation-pending puppet receives a snapshot
- **THEN** `party` uses the shared unavailable form with its standard reason

### Requirement: Party presentation stays current across membership and combat changes
The coordinator SHALL include the `party` panel in the presentation updates it pushes after the
party write seams (`join_party`, `leave_party`, membership purge) and wherever it already
re-pushes companion-adjacent state on combat settlement, so committed `party.slots` never
displays a dismissed companion or a stale HP integer after the next settlement commit. The panel
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
