# Delta spec: npc-identity-titles (declarative-service-hosts)

Roster-authoritative convergence replaces the batch's one-time legacy-key cleanup as the
deletion mechanism; the anchor-reuse and never-rename contract survives verbatim.

## MODIFIED Requirements

### Requirement: Guild service hosts reuse by service anchor and never rename
`sync_guild_economy` SHALL locate a service host by the `service_id` recorded on its service
component — never by display `key`. A missing host SHALL be created once under the roster row's
authored `name` as its `key` with the authored `title` persisted as its NPC title. An existing
host located by its service anchor SHALL never be renamed and SHALL never have its title written
at sync time — a host that predates authored identities is reused as-is, never backfilled.
Roster-authoritative convergence replaces the batch's one-time legacy-key cleanup as the
deletion mechanism: deletion anchors on roster membership of the component `service_id`, never
the entity key. A titleless candidate whose service anchors all match no roster row is
unambiguous stale development state and SHALL be deleted so the roster pass recreates it under
the full authored identity when its row returns; an NPC carrying no service component SHALL
survive untouched, and a titled candidate that still holds at least one roster-matching anchor
SHALL be kept with a named warning for manual repair. Locating an anchor claimed by more than
one live host SHALL fail closed with a named integrity error before any mutation.

#### Scenario: First sync creates the authored host
- **WHEN** `sync_guild_economy` runs with no existing host for a service component
- **THEN** exactly one NPC is created whose `key` is the roster row's authored `name`, whose
  `npc_title` is the row's authored `title`, and which carries the service component

#### Scenario: Re-sync neither duplicates nor renames
- **WHEN** `sync_guild_economy` runs again after the host exists, including with a changed
  roster `name`
- **THEN** the same NPC is reused, no second host exists, and its `key` is unchanged

#### Scenario: A host predating authored identities is reused, not backfilled
- **WHEN** a pre-existing host located by its service anchor carries no authored title and its
  `service_id` is on the roster
- **THEN** the sync reuses it as-is: no title is written, nothing is renamed, and no second
  authored host is created

#### Scenario: An unrelated NPC with no service component survives convergence
- **WHEN** convergence runs while an NPC shares a retired host key but carries no service
  component
- **THEN** the NPC is not deleted

#### Scenario: Duplicate service anchors fail closed
- **WHEN** two live NPCs carry service components with the same `service_id` and sync runs
- **THEN** a named integrity error is raised and no host is created, renamed, or deleted
