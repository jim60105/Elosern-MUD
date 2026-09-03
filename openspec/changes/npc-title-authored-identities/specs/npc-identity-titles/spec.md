# npc-identity-titles delta — authored supply (blueprint + registries)

## ADDED Requirements

### Requirement: Blueprint scene occupants spawn under the authored name with the authored title
The SceneBuilder SHALL spawn every stage occupant whose `key` is the entry's authored
`display_name` (validated through the shared name rule) and SHALL persist the entry's authored
`title` (validated through the shared title rule) as the NPC title. The existing
`db.display_name` write SHALL be preserved so the portrait-subject reader keeps reading the same
value. If any occupant lacks a characterization, its `display_name`, or its `title` at spawn time,
the SceneBuilder SHALL raise `SceneBuilderSpawnError` and roll back the whole materialization
before creating any room or entity — a missing authored identity fails closed exactly like the
existing adult-invariant revalidation does.

#### Scenario: A materialized occupant answers to its authored name
- **WHEN** a compiled stage with `npc_req: [{"role": "bandit", "tier": "bandit", "display_name": "黑鬍", "title": "林間盜匪頭目", ...}]` materializes
- **THEN** the spawned NPC's `key` is `黑鬍`, its `npc_title` is `林間盜匪頭目`, and the full
  identity composer renders 「黑鬍　林間盜匪頭目」 on full-identity surfaces

#### Scenario: A missing title rolls back the materialization
- **WHEN** a forge-constructed spawn requirement reaches the SceneBuilder with `title` absent or
  invalid
- **THEN** `SceneBuilderSpawnError` is raised and no room, entity, or exit from that
  materialization persists

#### Scenario: The portrait subject name keeps its source
- **WHEN** an occupant spawns under its authored name
- **THEN** `db.display_name` still carries the same authored value for the art-subject consumer

### Requirement: The blueprint author face enforces occupant name uniqueness
Within one stage, two `npc_req` entries SHALL NOT declare the same `display_name`. Across stages
of one blueprint, the same `display_name` SHALL be allowed only when the entries denote the same
authored character — identical `title` and identical remaining characterization — mirroring the
existing shared-`stable_key` agreement rule and sharing its identity-tuple comparison.

#### Scenario: Same-stage duplicate names are rejected
- **WHEN** one stage declares two `npc_req` entries whose `display_name` values are identical
- **THEN** the blueprint is rejected before compilation with a named diagnostic

#### Scenario: The same character may reappear across stages
- **WHEN** two stages declare the same `display_name` with identical title and characterization
- **THEN** the blueprint validates

#### Scenario: Same name with different characterization is rejected
- **WHEN** two stages declare the same `display_name` with different titles or ages
- **THEN** the blueprint is rejected before compilation

### Requirement: Shop and guild registries author host and examiner identities validated at load
`ShopDefinition` and `GuildBranch` SHALL each carry required `host_name` and `host_title` fields,
and `GuildRank` SHALL carry required `examiner_name` and `examiner_title` fields, all declared
without defaults so a missing column is a module-import `TypeError`. The lore modules owning
these registries SHALL validate every row's authored names and titles through the shared name and
title validators at module load time (invalid values raise named `ValueError`s), and SHALL check
that authored NPC names do not repeat across the shop, guild-branch, and guild-rank registries.
The row validators SHALL be pure functions callable with explicit rows so violations are testable
without mutating the shipped registries.

#### Scenario: A row with an invalid authored title fails module load
- **WHEN** the pure row validator is called with a registry row whose authored title violates the
  shared title rule (empty, overlong, whitespace/control/`|` characters)
- **THEN** it raises a named `ValueError` naming the offending registry key and field

#### Scenario: A duplicated authored name across registries fails load
- **WHEN** the cross-registry uniqueness check is called with rows where a shop host and an
  examiner share one authored name
- **THEN** it raises a named `ValueError`

#### Scenario: The shipped registries load clean
- **WHEN** `world.lore.shops` and `world.lore.guild` are imported
- **THEN** every shipped row passes name, title, and cross-registry uniqueness validation

### Requirement: Guild service hosts reuse by service anchor and never rename
`sync_guild_economy` SHALL locate a service host by the `service_id` recorded on its service
component — never by display `key`. A missing host SHALL be created once under the registry's
authored `host_name` as its `key` with the authored `host_title` persisted as its NPC title. An
existing host SHALL never be renamed, even if the registry name later changes; its title SHALL be
backfilled only while its stored title is empty, preserving the creation-time immutability of a
title that was already assigned.

#### Scenario: First sync creates the authored host
- **WHEN** `sync_guild_economy` runs with no existing host for a service component
- **THEN** exactly one NPC is created whose `key` is the registry `host_name`, whose `npc_title`
  is the registry `host_title`, and which carries the service component

#### Scenario: Re-sync neither duplicates nor renames
- **WHEN** `sync_guild_economy` runs again after the host exists, including with a changed
  registry `host_name`
- **THEN** the same NPC is reused, no second host exists, and its `key` is unchanged

#### Scenario: A titleless host is backfilled once
- **WHEN** a pre-existing host whose title is empty is found by its service anchor
- **THEN** the registry title is written exactly once and a non-empty stored title is never
  overwritten

### Requirement: Exam examiners carry their authored identity
The examination opponent spawn SHALL use the rank's authored `examiner_name` and SHALL persist the
authored `examiner_title` as the NPC title, replacing the anonymous `guild-examiner-<rank>` key
form; the key-collision behaviour is governed by the `guild-rank-exams` requirement restated by
this change.

#### Scenario: A spawned examiner carries the authored title
- **WHEN** `start_guild_exam` spawns the opponent for a rank
- **THEN** the opponent's `npc_title` equals that rank's `examiner_title` and its key begins with
  the rank's `examiner_name`

### Requirement: Host and examiner creation emit boundary info events
The service-host creation path and the examination-opponent spawn SHALL each emit one observability
facade info event when an entity is actually created (never on idempotent reuse), with business
identifiers in the context — `char` and `shop`/`service` for the host, `char` and `rank` for the
opponent — and no player-facing prose.

#### Scenario: Host creation logs once
- **WHEN** a service host is created and a later sync reuses it
- **THEN** the creation event fires exactly once with `char` and service identifiers in context

#### Scenario: Opponent spawn logs
- **WHEN** an examination opponent is spawned
- **THEN** the spawn event fires with `char` and `rank` context keys

### Requirement: The existing scene-builder and generated-quest contracts are unchanged where not amended
Except for the authored-identity behaviour stated in this delta, the scene-builder spawn contracts
(anti-hallucination characterization ownership, the post-commit portrait-eligibility seam, and the
`db.display_name` write) and the generated-quest durable-store contract SHALL remain as previously
specified; this change adds the authored identity on top and SHALL NOT otherwise alter their
observable behaviour.

#### Scenario: The pre-existing scene contracts still hold
- **WHEN** the scene-builder and durable-store suites run after this change
- **THEN** every pre-existing requirement scenario of those capabilities still passes
