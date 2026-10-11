# Spec Delta

## MODIFIED Requirements

### Requirement: Guild registration grants the paired starter titles atomically
The registration transaction SHALL additionally grant the F-rank fixed title
(「F級冒險者」) into `db.title_collection`,
auto-equipping the empty fixed slot, inside the same all-or-nothing commit that
grants F rank — no planner, no LLM. The registry-authored starter epithet SHALL NOT
be granted at registration; it is granted by the first guild reward claim
(quest-reward-settlement).

#### Scenario: Registration writes rank and the fixed title in one commit
- **WHEN** a fresh member completes guild registration
- **THEN** F rank, the fixed entry, and the auto-equipped fixed slot are all present at that single commit, with no epithet entry in `title_collection`

#### Scenario: Repeated registration is inert on titles
- **WHEN** an already-registered member registers again
- **THEN** `title_collection` and `title_equipped` are unchanged

#### Scenario: Fixed-key dedupe makes re-registration a no-op
- **WHEN** re-registration runs against the already-granted fixed title
- **THEN** the fixed-key dedupe rule makes the grant a no-op, leaving title state byte-identical

#### Scenario: A rejected registration grants no title
- **WHEN** registration is rejected
- **THEN** no title is granted

### Requirement: Service hosts are created and converged from a declarative YAML roster
The service-host roster SHALL be derived from the place registry rather than hand-authored: each
place yields one row declaring `name`, `title`, `profession`, the interior room tag it anchors to,
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
- **THEN** it resolves the room by tag and finds-or-creates the host NPC on the `service_id`
  anchor under the unchanged never-rename/never-retitle reuse contract
