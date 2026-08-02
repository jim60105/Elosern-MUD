## MODIFIED Requirements

### Requirement: Player-facing guild commands resolve one local service host
The character cmdset SHALL provide commands for guild registration, offer listing, acceptance,
quest-log listing, detail viewing, abandonment, and turn-in. Every guild service command
(registration, board listing, acceptance, abandonment, turn-in) SHALL search only the caller's room
and SHALL reject absent or ambiguous matching hosts with Traditional Chinese output. Read-only
personal quest-log commands (`guild log` and `guild show`) SHALL operate on the caller's own
persisted quest log and SHALL NOT require a local `GuildStaff` host.

#### Scenario: Guild workflow is reachable from commands
- **WHEN** a player enters the Altoria guild hall and invokes the documented guild commands
- **THEN** the same deterministic registration, board, lifecycle, and turn-in APIs used by tests are called

#### Scenario: Guild command cannot address a remote dbref
- **WHEN** a player supplies the dbref of GuildStaff in another room
- **THEN** the command rejects rather than performing a remote operation

#### Scenario: Read-only quest-log commands work without a service host
- **WHEN** a player runs `guild log` or `guild show` in a room with no `GuildStaff` host
- **THEN** the command renders the caller's own quest log or quest detail instead of reporting an
  absent service host

## ADDED Requirements

### Requirement: Board listing and quest log surface objective guidance
`guild list` SHALL render each eligible offer with a one-line Traditional
Chinese summary of the offered definition's first objective, in addition to the
existing key, display name, and reward. `guild log` SHALL render a hint that
`guild show <quest_id>` reveals full objective detail. Both SHALL be read-only
presentation over existing registries and records, and SHALL NOT change board
eligibility or quest state.

#### Scenario: Board rows show a first-objective one-liner
- **WHEN** an F member lists a board containing the `introductory_hunt` offer
- **THEN** the row shows the offered definition's first objective summary (for
  example a DEFEAT goal) alongside the name and reward

#### Scenario: Quest log hints at the detail command
- **WHEN** a player with at least one quest record runs `guild log`
- **THEN** the output points the player to `guild show` for full objective
  detail

#### Scenario: Objective summaries never affect eligibility
- **WHEN** a board is listed with objective summaries enabled
- **THEN** rank-eligible filtering and ordering are byte-for-byte identical to
  the behavior without summaries
