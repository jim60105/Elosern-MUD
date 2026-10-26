# guild-registration Specification

## Purpose

Define deterministic guild-service capabilities and player registration.

## Requirements

### Requirement: Guild service components are capability adapters, not state writers
The project SHALL define `GuildStaff`, `Merchant`, and `GuildExamReception` Component subclasses attachable
to ComponentHolder NPCs. Components SHALL carry stable service/branch identifiers and persistent
service data only. Their command-facing methods SHALL delegate every registration, quest, trade,
examination, wallet, merit, inventory, and rank mutation to deterministic-core APIs.

#### Scenario: Service NPC exposes its capabilities
- **WHEN** an NPC has `GuildStaff` and `GuildExamReception` attached
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
(`world/rules/affinity.py`) — all in one atomic operation.

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

#### Scenario: Callers cannot supply or override the branch
- **WHEN** a caller attempts to pass or override the registration branch
- **THEN** the branch is derived exclusively from the validated GuildStaff component

#### Scenario: Rank is never derived from stats
- **WHEN** registration sets the rank
- **THEN** it never derives rank from either displayed or true stats; rank is always F

#### Scenario: The host affinity record rides the snapshot surfaces
- **WHEN** registration begins
- **THEN** the host's affinity record is included in the registration snapshot/restore surfaces so
  a failed registration restores it

### Requirement: Registration access is local, idempotent, and strict about persisted data
Registration SHALL reject non-player entities, absent or remote staff, and ambiguous multiple
local GuildStaff hosts. Local-host acceptance SHALL flow through
`world/rules/service_gate.py::service_available` for the resolved staff component.
Re-registering a valid member SHALL return the original record without replacing its branch, tick,
or snapshot. A partial or malformed existing record SHALL raise `GuildDataError` without repair or
rank mutation.

#### Scenario: Remote staff cannot register a player
- **WHEN** a player invokes registration while the selected GuildStaff host is in another room
- **THEN** registration is rejected and no guild field changes

#### Scenario: An off-anchor traveling clerk refuses registration
- **WHEN** the guild clerk host stands beside the player in a room other than its anchor and the
  player invokes registration
- **THEN** the gate's fixed message is returned and no guild field changes

#### Scenario: Repeated registration preserves historical values
- **WHEN** a registered player changes disguise and invokes registration again
- **THEN** the original tick and displayed-stat snapshot remain unchanged

#### Scenario: Partial membership data fails closed
- **WHEN** `guild_rank` is F but `guild_registration` lacks its displayed-stat snapshot
- **THEN** registration raises `GuildDataError` and writes nothing

#### Scenario: Gate verdicts map to fixed refusals
- **WHEN** the service gate returns a verdict for the resolved staff component
- **THEN** `remote` keeps the existing remote-staff rejection, and an `off_anchor` or
  `malformed_binding` verdict refuses registration with the gate's fixed registry message and no
  guild field written

### Requirement: Guild service hosts teach their service commands through scripted dialogue
The guild master host SHALL carry a `ScriptedDialogue` component whose `dialogue_key` resolves to
the `guild_staff` table. Talking to the host SHALL present the authored, in-character account of
what the guild counter offers and the known-keyword answers, and SHALL cause no state change. The
host teaches the service in the world's own terms and SHALL NOT name a command; the requirement's
title is kept for traceability. Component attachment SHALL remain idempotent
across repeated startup syncs.

#### Scenario: Guild master answers talk with command guidance
- **WHEN** a player talks to the guild master host
- **THEN** the host explains, in character, how registering, taking commissions and reporting back
  work at the counter, and names no command

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
The service roster SHALL derive from each hosted place's canonical identity, spawn room and direct capability declarations. Complete catalog and unique anchor validation SHALL precede atomic assembly. Reused hosts SHALL preserve location and subsystem state under canonical provenance ownership.

#### Scenario: Shipped roster recreates today's two hosts bit-for-bit
- **WHEN** the current declared roster is rebuilt
- **THEN** each host matches its current authored name/profile/age and explicit components without historical roster-count assumptions

#### Scenario: Config-time roster validation rejects a nameable offense without DB access
- **WHEN** a direct component is unknown or missing configuration
- **THEN** catalog loading rejects the complete candidate with named errors

#### Scenario: An unresolvable anchor room fails sync closed and names the row
- **WHEN** an anchor has zero/multiple/non-Room matches
- **THEN** the complete operation rolls back, including prepared interiors

#### Scenario: Assembly is the shared helper, not a code-side literal
- **WHEN** imports and service hosts assemble declarations
- **THEN** both use the same validated capability plan, with no second attach loop

#### Scenario: Idempotent re-sync changes nothing
- **WHEN** the same source synchronizes twice
- **THEN** no host duplicates, runtime state resets or extra capability slots occur

#### Scenario: A host is declared exactly once
- **WHEN** host source definitions are enumerated
- **THEN** each appears only on its canonical place, without a separate hand-authored roster

#### Scenario: The derived roster reproduces the pre-change hosts
- **WHEN** shipped definitions are converted
- **THEN** each preserves its component functionality without profession fields

#### Scenario: Config-time batch validation covers every named offense
- **WHEN** required fields, duplicate types, refs or bindings are malformed
- **THEN** nothing is cached or persisted from the rejected candidate

#### Scenario: Sync resolves rows and reuses hosts under the unchanged contract
- **WHEN** a declaration is synchronized
- **THEN** host_key uses unique canonical profile provenance and reused identity/location/state remain unchanged

#### Scenario: Host authoring has no title
- **WHEN** a current place/roster identity is declared
- **THEN** it has a validated name and profile and no title/host_title field

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
