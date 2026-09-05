# guild-registration Specification

## Purpose

Define deterministic guild-service capabilities and player registration.

## Requirements

### Requirement: Guild service components are capability adapters, not state writers
The project SHALL define `GuildStaff`, `Merchant`, and `GuildExaminer` Component subclasses attachable
to ComponentHolder NPCs. Components SHALL carry stable service/branch identifiers and persistent
service data only. Their command-facing methods SHALL delegate every registration, quest, trade,
examination, wallet, merit, inventory, and rank mutation to deterministic-core APIs.

#### Scenario: Service NPC exposes its capabilities
- **WHEN** an NPC has `GuildStaff` and `GuildExaminer` attached
- **THEN** local command discovery identifies it as both a guild service and examination service without
  inspecting the NPC's key or typeclass

#### Scenario: Components do not implement business writes
- **WHEN** the component modules are inspected
- **THEN** they contain no direct assignment to player rank, merit, wallet, inventory, quest log, reward
  claims, or active combat state

### Requirement: Registration grants F rank and records one displayed-stat snapshot
`register_adventurer()` SHALL accept only an unregistered PlayerCharacter co-located with a GuildStaff
host. It SHALL read all eight trait keys through `get_display_value()`, persist the branch, current world
tick, and displayed values in `guild_registration`, set `guild_rank` to `F`, and grant +1 affinity
(`guild` source) with the GuildStaff host through the sole-writer affinity API
(`world/rules/affinity.py`) — all in one atomic operation, with the host's affinity record included
in the registration snapshot/restore surfaces so a failed registration restores it.
The branch SHALL be derived exclusively from the validated GuildStaff component; callers SHALL NOT
supply or override it. Registration SHALL NOT derive rank from either displayed or true stats.

#### Scenario: Undisguised character registers at F
- **WHEN** an unregistered character registers with local GuildStaff and has no `disguised_stats`
- **THEN** rank becomes F, every registration snapshot value equals the corresponding true trait
  value, and the GuildStaff host's affinity value rises by 1

#### Scenario: Disguise affects only the registration snapshot
- **WHEN** an elf whose true `atk_phys` is 88 registers while `disguised_stats.atk_phys` is 8
- **THEN** the snapshot records 8, rank is F, the true `atk_phys` remains 88, and the affinity
  gain still applies

#### Scenario: Registration failure is atomic
- **WHEN** persistence is fault-injected after either rank, registration metadata, or the affinity
  record is written
- **THEN** rank, registration metadata, and the affinity record — and their in-process caches —
  equal their pre-registration values

#### Scenario: Staff component is the sole branch authority
- **WHEN** registration occurs at Altoria GuildStaff
- **THEN** the stored branch equals that component's branch and no caller-provided branch input exists

### Requirement: Registration access is local, idempotent, and strict about persisted data
Registration SHALL reject non-player entities, absent or remote staff, and ambiguous multiple local
GuildStaff hosts. Re-registering a valid member SHALL return the original record without replacing its
branch, tick, or snapshot. A partial or malformed existing record SHALL raise `GuildDataError` without
repair or rank mutation.

#### Scenario: Remote staff cannot register a player
- **WHEN** a player invokes registration while the selected GuildStaff host is in another room
- **THEN** registration is rejected and no guild field changes

#### Scenario: Repeated registration preserves historical values
- **WHEN** a registered player changes disguise and invokes registration again
- **THEN** the original tick and displayed-stat snapshot remain unchanged

#### Scenario: Partial membership data fails closed
- **WHEN** `guild_rank` is F but `guild_registration` lacks its displayed-stat snapshot
- **THEN** registration raises `GuildDataError` and writes nothing

### Requirement: Guild service hosts teach their service commands through scripted dialogue
The guild master host SHALL carry a `ScriptedDialogue` component whose `dialogue_key` resolves to
the `guild_staff` table. Talking to the host SHALL present the authored guild-command overview and
known-keyword answers, and SHALL cause no state change. Component attachment SHALL remain idempotent
across repeated startup syncs.

#### Scenario: Guild master answers talk with command guidance
- **WHEN** a player talks to the guild master host
- **THEN** the host teaches the available guild commands through its authored dialogue

#### Scenario: Guild master dialogue causes no state change
- **WHEN** a player talks to the guild master with any keyword
- **THEN** no guild, quest, or player state is written

#### Scenario: Repeated sync attaches the dialogue once
- **WHEN** the guild-economy startup sync runs twice
- **THEN** the guild master host carries exactly one `ScriptedDialogue` component

### Requirement: Guild registration grants the paired starter titles atomically
The registration transaction SHALL additionally grant the F-rank fixed title
(「F級冒險者」) into `db.title_collection`,
auto-equipping the empty fixed slot, inside the same all-or-nothing commit that
grants F rank — no planner, no LLM. The starter epithet (「南門新客」) SHALL NOT
be granted at registration; it is granted by the first guild reward claim
(quest-reward-settlement). Re-registration SHALL leave title state
byte-identical (the fixed-key dedupe rule makes it a no-op), and a
rejected registration SHALL grant no title.

#### Scenario: Registration writes rank and the fixed title in one commit
- **WHEN** a fresh member completes guild registration
- **THEN** F rank, the fixed entry, and the auto-equipped fixed slot are all present at that single commit, with no epithet entry in `title_collection`

#### Scenario: Repeated registration is inert on titles
- **WHEN** an already-registered member registers again
- **THEN** `title_collection` and `title_equipped` are unchanged
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
