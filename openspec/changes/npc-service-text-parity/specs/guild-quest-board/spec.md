# Spec Delta

## MODIFIED Requirements

### Requirement: Player-facing guild commands resolve one local service host
The character cmdset SHALL provide commands for guild registration, offer listing, acceptance,
quest-log listing, detail viewing, abandonment, and turn-in. Provider-dependent guild commands SHALL search only the caller's visible current room. An explicit terminal @#dbid SHALL resolve only that eligible selected host, even among several providers; absence retains implicit ambiguous-host refusal. Ordinary abandonment retains its selected-staff gate, while private escort abandonment remains host-free. Rejections SHALL use Traditional Chinese output. Read-only personal quest-log commands (`guild log` and `guild show`)
SHALL operate on the caller's own persisted quest log and SHALL NOT require a local `GuildStaff` host.

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

#### Scenario: Completed quests are reportable through guild-staff dialogue
- **WHEN** a registered player with a `COMPLETED`, unclaimed quest whose offer is registered at the
  staff's branch talks to the local guild staff with `回報 <quest_id>`
- **THEN** the deterministic settlement commits exactly once, the reward matches the offer, and the
  listing afterwards no longer includes the quest

#### Scenario: Multiple completed quests list in deterministic order
- **WHEN** a player with several completed, unclaimed quests talks to the guild staff with `回報`
- **THEN** the staff lists exactly those quests ordered by accepted tick then quest id, and turning
  one in never affects the reportability of the others

#### Scenario: Dialogue turn-in never bypasses the settlement contract
- **WHEN** a player talks to the guild staff with `回報` naming an unknown, in-progress, failed,
  already-claimed, or offer-less quest id
- **THEN** the dialogue answers with the standard turn-in rejection and no reward state changes

#### Scenario: 回報 outside a guild hall yields no turn-in
- **WHEN** a player talks to an NPC that is not the local `GuildStaff` host with the keyword `回報`
- **THEN** the host answers with the no-understanding line and no state changes

#### Scenario: 回報 on a host reusing the guild_staff table without the staff component stays a plain keyword
- **WHEN** a player talks to a dialogue host carrying the `guild_staff` table but no `GuildStaff`
  component, with `回報 <quest_id>`
- **THEN** the host answers with the no-understanding line, no turn-in is attempted, and no reward
  state changes

#### Scenario: 回報 with ambiguous guild staff is rejected
- **WHEN** a player talks to a guild staff NPC with `回報` while more than one `GuildStaff` host
  occupies the room
- **THEN** both the listing and any turn-in attempt answer with the standard ambiguous-host
  rejection line and no quest, wallet, inventory, merit, or claim state changes

#### Scenario: 回報 with nothing reportable answers so
- **WHEN** a player talks to the local guild staff with `回報` and no quest record is `COMPLETED` with a registered offer at the staff's branch and an absent quest id in the caller's reward claims
- **THEN** the staff answers that nothing is reportable

#### Scenario: Dialogue turn-in routes through the same turn_in_quest API
- **WHEN** a player talks to the local guild staff with `回報 <quest_id>`
- **THEN** exactly that quest turns in through the same deterministic `turn_in_quest` API used by `guild turnin`, with identical atomic settlement and rejection semantics, never accepting a remote host or bypassing `turn_in_quest`

#### Scenario: Explicit provider survives same-class bystanders
- **WHEN** a player supplies the terminal target suffix for a visible eligible provider while another same-class provider is present
- **THEN** only the selected provider is used; if it departs before execution the command rejects without substituting the bystander
