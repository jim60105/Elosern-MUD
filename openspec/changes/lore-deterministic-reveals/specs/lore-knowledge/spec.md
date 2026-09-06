# Delta spec: lore-knowledge (lore-deterministic-reveals)

## ADDED Requirements

### Requirement: The codex is discoverable with every generative service offline

At least one reveal source SHALL be reachable through purely deterministic play, so a player who
never speaks to a generative NPC still accumulates codex entries and the codex is never a guaranteed
empty surface. Every deterministic source SHALL write exclusively through `record_lore_reveal`, so
the append-only semantics, the repeat-is-a-no-op rule, and the sole-writer rule are unchanged.

#### Scenario: A codex fills with every generative profile failing
- **WHEN** every `LLM_PROFILES` entry is configured to fail and a character is created, travels to a
  registered anchor, and defeats a monster of a registered tier
- **THEN** the codex holds the corresponding origin, anchor, and monster entries and no generative
  service was consulted

#### Scenario: Deterministic sources do not bypass the sole writer
- **WHEN** the deterministic reveal sources are inspected
- **THEN** each writes through `record_lore_reveal` and none assigns `db.lore_discovered` directly

### Requirement: Arrival reveals the anchor and region a room resolves to

Entering a room that resolves to a registered anchor SHALL reveal that `anchor` entry, and entering a
room that resolves to a registered wilderness region SHALL reveal that `region` entry. A room
resolving to neither SHALL reveal nothing. The reveal SHALL occur on arrival, not on quest
acceptance and not on merely knowing a destination exists, so the codex records where the character
has actually been.

#### Scenario: Arriving at an anchor records it
- **WHEN** a character enters a room resolving to a registered anchor for the first time
- **THEN** that anchor entry is present in the character's codex

#### Scenario: Arriving in a region records it
- **WHEN** a character enters a wilderness room resolving to a registered region
- **THEN** that region entry is present in the character's codex

#### Scenario: An unremarkable room reveals nothing
- **WHEN** a character enters a room resolving to no registered anchor and no registered region
- **THEN** the codex is unchanged

#### Scenario: Re-entering reveals nothing new
- **WHEN** a character re-enters a room whose anchor is already discovered
- **THEN** the codex is unchanged and no error is raised

### Requirement: Defeating a monster reveals its tier

A committed defeat of a monster carrying a registered monster tier SHALL reveal that `monster` entry
for the character credited with the defeat. A defeat carrying no tier, or a tier absent from the
registry, SHALL reveal nothing. A simulated defeat SHALL reveal nothing, matching the existing rule
that a simulated battle grants no DEFEAT progress.

#### Scenario: A first kill of a tier records it
- **WHEN** a character commits a defeat of a monster of a registered tier
- **THEN** that monster-tier entry is present in the character's codex

#### Scenario: A simulated defeat records nothing
- **WHEN** a defeat is marked simulated, as in a guild examination
- **THEN** the codex is unchanged

#### Scenario: An untiered defeat records nothing
- **WHEN** a committed defeat carries no monster tier or a tier absent from the registry
- **THEN** the codex is unchanged

### Requirement: Origin reveals seed the codex at creation and registration

Completing character creation SHALL reveal the character's chosen `race` entry and its `nation`
entry, and completing guild registration SHALL reveal the registrant's `guild` rank entry. A chosen
value that resolves to no registry entry — a subrace rather than a race, for instance — SHALL reveal
nothing rather than rejecting the creation or the registration.

#### Scenario: A new character starts with its origin entries
- **WHEN** character creation completes for a character with a registered race and nation
- **THEN** those two entries are present in the character's codex

#### Scenario: Registering reveals the starting rank
- **WHEN** a character completes guild registration
- **THEN** that guild rank entry is present in the character's codex

#### Scenario: An unresolvable origin value reveals nothing and blocks nothing
- **WHEN** a chosen value resolves to no entry in its category's registry
- **THEN** the codex is unchanged and the creation or registration still completes

### Requirement: A reveal never blocks or fails the play that triggered it

A deterministic reveal SHALL be best-effort with respect to the operation that triggered it: a
rejection from the writer, a corrupt codex record, or any other reveal failure SHALL NOT fail or roll
back the arrival, the combat settlement, the character creation, or the guild registration. The
failure SHALL be reported through the observability facade with its exception rather than swallowed
silently. A reveal SHALL emit no player-facing message by default, so it never interrupts movement or
combat.

#### Scenario: A corrupt codex record does not break movement
- **WHEN** a character with a malformed `lore_discovered` record enters a registered anchor
- **THEN** the movement completes normally, the codex record is neither reset nor rewritten, and the
  failure is logged through the facade with its exception

#### Scenario: A reveal failure does not roll back combat settlement
- **WHEN** a reveal raises during the settlement of a committed defeat
- **THEN** the combat settlement commits unchanged and the failure is logged

#### Scenario: A reveal is silent
- **WHEN** any deterministic reveal succeeds
- **THEN** no message is sent to the character
