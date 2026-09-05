# Delta spec: guild-registration (declarative-service-hosts)

The service-host roster moves from Python fixtures into `guild_economy.yaml`; sync becomes its
interpreter with roster-authoritative convergence.

## ADDED Requirements

### Requirement: Service hosts are created and converged from a declarative YAML roster
`world/rules/rulebook/guild_economy.yaml` SHALL carry a `service_hosts:` roster where each row
declares `name`, `title`, `profession`, `anchor_room` (a room tag), `service_id`, and the authored
component identity kwargs. `world/rules/guild_config.py` SHALL parse and batch-validate the roster
(config load never touches the database): missing fields, a `profession` naming no registry row,
a blueprint component type whose identity kwargs the row fails to supply, or a non-string
`anchor_room` each raise the catalog's named error and cache nothing.
`world/rules/guild_economy.py::sync_service_content` SHALL be an interpreter of the roster: per
row it resolves the room by tag, finds-or-creates the adult host on the `service_id` anchor with
the unchanged never-rename/never-retitle reuse contract, and assembles components through the
shared `world/rules/profession_assembly.py` helper — never through a code-side component literal.
The shipped roster SHALL reproduce the pre-change two hosts exactly (same names, titles, rooms,
`service_id`s `altoria_guild_master` / `altoria_merchant`, and component kwargs), keeping sync
behavior-neutral.

#### Scenario: Shipped roster recreates today's two hosts bit-for-bit
- **WHEN** sync runs against a database whose two service hosts were deleted
- **THEN** the recreated guild master and merchant carry the same key, title, room, race
  baseline, adult identity, and component kwargs as the pre-change sync produced

#### Scenario: Config-time roster validation rejects a nameable offense without DB access
- **WHEN** a roster row declares `profession: blacksmith` (no such registry row) or omits the
  merchant row's `shop_key`
- **THEN** config loading raises the named catalog error and no host sync occurs

#### Scenario: An unresolvable anchor room fails sync closed and names the row
- **WHEN** sync resolves a row whose `anchor_room` tag matches no room
- **THEN** the named warning event carries the row's `service_id`, no host is created or moved,
  and the remaining rows still process exactly as the pre-change missing-interiors path

#### Scenario: Assembly is the shared helper, not a code-side literal
- **WHEN** `world/rules/guild_economy.py` is searched for `ComponentClass` literals or
  `component_specs` tuples
- **THEN** none remain; component attachment flows only through `profession_assembly`

#### Scenario: Idempotent re-sync changes nothing
- **WHEN** the roster-driven sync runs twice in a row
- **THEN** the second run creates no host, renames nothing, attaches no duplicate component, and
  deletes nothing

### Requirement: Roster convergence deletes service hosts absent from the roster
Sync SHALL treat the roster as authoritative, and the roster's authority SHALL NOT depend on
anchor-room resolution: the duplicate-anchor fail-closed probe and the convergence sweep run for
every roster row on every sync. A live NPC whose EVERY service-component `service_id` matches no
roster row is deleted; a host the roster still claims through ANY anchor is never destroyed —
titled mixed residue is ambiguous, emits a named warning, and survives for manual repair. Each
deletion emits one info event with the host and service identifiers.

#### Scenario: A roster-shrunk host is deleted on next sync
- **WHEN** a roster row is removed and sync runs
- **THEN** its host (and only hosts failing roster membership) is deleted, its party bindings
  purged through the existing `NPC.at_object_delete` hook, and an info event names it

#### Scenario: An unrelated NPC sharing a retired key survives
- **WHEN** an NPC without any service component shares a retired legacy key
- **THEN** convergence leaves it untouched, exactly as the pre-change cleanup did
