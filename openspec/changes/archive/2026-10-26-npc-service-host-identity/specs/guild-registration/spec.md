# Spec Delta

## MODIFIED Requirements

### Requirement: Roster convergence deletes service hosts absent from the roster
Only explicitly source-owned hosts whose complete host declaration is removed SHALL be retired through the existing host lifecycle. Capability removal or component service IDs SHALL NOT authorize deleting a host; unrelated NPCs SHALL survive.

#### Scenario: A roster-shrunk host is deleted on next sync
- **WHEN** an explicitly source-tagged host loses its whole declaration
- **THEN** only that host is deleted through existing party/dialogue lifecycle cleanup with commit-bound logging

#### Scenario: An unrelated NPC sharing a retired key survives
- **WHEN** an unmanaged NPC shares a name or component service ID
- **THEN** it remains untouched

#### Scenario: A host claimed through any anchor is never destroyed
- **WHEN** a currently declared canonical host loses its first or final capability
- **THEN** the host survives with exactly its remaining managed set

#### Scenario: Titled mixed residue survives for manual repair
- **WHEN** an unmanaged host carries arbitrary old title/component attributes
- **THEN** none grants roster deletion authority and it survives without reading the title

### Requirement: Service hosts are created and converged from a declarative YAML roster
The service-host roster SHALL be derived from the place registry rather than hand-authored: each
place yields one row declaring `name`, `title`, `profession`, a canonical host_key equal to profile_key and the initial spawn room tag,
`service_id`, and the authored component identity kwargs.
`world/rules/guild_economy.py::sync_service_content` SHALL interpret the roster and assemble
components through the shared `world/rules/profession_assembly.py` helper, never a code-side
component literal.

#### Scenario: Shipped roster recreates today's two hosts bit-for-bit
- **WHEN** all declared service hosts are deleted and sync runs
- **THEN** each recreated host matches its live authored identity, provenance, canonical ages, anchor and blueprint component arguments

#### Scenario: Config-time roster validation rejects a nameable offense without DB access
- **WHEN** a place declares `profession: blacksmith` (no such registry row) or omits the
  merchant place's `shop_key`
- **THEN** config loading raises the named catalog error and no host sync occurs

#### Scenario: An unresolvable anchor room fails sync closed and names the row
- **WHEN** sync resolves a row whose room tag matches no room
- **THEN** the complete operation fails before persistence and names the unresolved row

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

#### Scenario: The derived roster reproduces the pre-change hosts
- **WHEN** the place-derived roster is compared with current hosted place records
- **THEN** one matching row exists per declared service identity, with no historical count, personal-name or two-host approval table

#### Scenario: Config-time batch validation covers every named offense
- **WHEN** a derived roster row has missing fields, a `profession` naming no registry row, a
  blueprint component type whose identity kwargs the place fails to supply, or a non-string room tag
- **THEN** `world/rules/guild_config.py` batch-validation raises the catalog's named error and
  caches nothing, and config load never touches the database

#### Scenario: Sync resolves rows and reuses hosts under the unchanged contract
- **WHEN** `sync_service_content` processes one roster row
- **THEN** it resolves the spawn room uniquely and finds-or-creates the host by canonical npc_profile_key provenance, preserving reused location, identity and runtime state
