## MODIFIED Requirements

### Requirement: Service hosts are created and converged from a declarative YAML roster
The service-host roster SHALL be derived from the place registry rather than hand-authored: each
place yields one row declaring `name`, `title`, `profession`, the interior room tag it anchors to,
`service_id`, and the authored component identity kwargs. `world/rules/guild_config.py` SHALL
batch-validate the derived roster (config load never touches the database): missing fields, a
`profession` naming no registry row, a blueprint component type whose identity kwargs the place
fails to supply, or a non-string room tag each raise the catalog's named error and cache nothing.
`world/rules/guild_economy.py::sync_service_content` SHALL be an interpreter of the roster: per
row it resolves the room by tag, finds-or-creates the host NPC on the `service_id` anchor with
the unchanged never-rename/never-retitle reuse contract, and assembles components through the
shared `world/rules/profession_assembly.py` helper — never through a code-side component literal.
The derived roster SHALL reproduce the pre-change two hosts exactly (same names, titles, rooms,
`service_id`s `altoria_guild_master` / `altoria_merchant`, and component kwargs), keeping sync
behavior-neutral.

#### Scenario: Shipped roster recreates today's two hosts bit-for-bit
- **WHEN** sync runs against a database whose two service hosts were deleted
- **THEN** the recreated guild master and merchant carry the same key, title, room, race
  baseline, canonical ages, and component kwargs as the pre-change sync produced

#### Scenario: Config-time roster validation rejects a nameable offense without DB access
- **WHEN** a place declares `profession: blacksmith` (no such registry row) or omits the
  merchant place's `shop_key`
- **THEN** config loading raises the named catalog error and no host sync occurs

#### Scenario: An unresolvable anchor room fails sync closed and names the row
- **WHEN** sync resolves a row whose room tag matches no room
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

#### Scenario: A host is declared exactly once
- **WHEN** the rulebook is searched for a hand-authored `service_hosts:` roster
- **THEN** none remains, and every host's name, title and profession appear only on its place
