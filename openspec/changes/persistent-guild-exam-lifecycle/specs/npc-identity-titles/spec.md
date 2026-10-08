## MODIFIED Requirements

### Requirement: Shop and guild registries author host and examiner identities validated at load
`ShopDefinition` and `GuildBranch` SHALL each carry required `host_name` and `host_title` fields,
and branch-qualified persistent adventurer records SHALL carry required authored name and title fields, all declared
without defaults so a missing column is a module-import `TypeError`. The lore modules owning
these registries SHALL validate every row's authored names and titles through the shared name and
title validators at module load time (invalid values raise named `ValueError`s), and SHALL check
that authored NPC names do not repeat across the shop, guild-branch, and persistent-person identity registries (deduplicated by authored person key before qualification references are checked).
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
- **WHEN** `world.lore.settlements.shops` and `world.lore.guild` are imported
- **THEN** every shipped row passes name, title, and cross-registry uniqueness validation

GuildRank SHALL no longer own examiner name/title/profile fields. Qualification validation SHALL use persistent adventurer authored identity and existing shared name/title validators; unrelated ShopDefinition/GuildBranch host identity checks SHALL remain unchanged.

#### Scenario: Rank metadata has no opponent factory identity
- **WHEN** ranks and qualification records load
- **THEN** ranks contain progression/reward/title metadata and person identity validates on qualification sources

#### Scenario: The lore modules check cross-registry name uniqueness at load

- **WHEN** the lore modules owning the registries load
- **THEN** they check that authored NPC names do not repeat across the shop, guild-branch, and
  guild-rank registries

#### Scenario: The row validators are pure and explicitly callable

- **WHEN** the row validators' shape is inspected
- **THEN** they are pure functions callable with explicit rows, so violations are testable
  without mutating the shipped registries

### Requirement: Exam examiners carry their authored identity
Persistent qualified adventurer assembly SHALL establish authored name/title once through existing identity validators and collision-safe roster discipline. Exams SHALL reuse that identity and stable dbref without rank-derived spawn identities or card/title replacement.

#### Scenario: A spawned examiner carries the authored title
- **WHEN** a qualified host starts two exams
- **THEN** authored name/title/dbref remain the same and no opponent spawns

### Requirement: Host and examiner creation emit boundary info events
Service-host and persistent adventurer creation SHALL each emit one facade info event only on actual creation, never idempotent reuse, with char/service and profile/branch identifiers. Examination starts SHALL emit lifecycle boundary events with exam/host/target identifiers, without entity-creation events or player-facing prose.

#### Scenario: Host creation logs once
- **WHEN** a persistent adventurer is created then reused by sync and exams
- **THEN** one entity-creation event emits and subsequent exam-start events identify the same dbref

#### Scenario: Opponent spawn logs
- **WHEN** persistent adventurer assembly creates the qualified person
- **THEN** its creation event identifies char/profile/branch once, while examination reuse emits no opponent-spawn creation event

