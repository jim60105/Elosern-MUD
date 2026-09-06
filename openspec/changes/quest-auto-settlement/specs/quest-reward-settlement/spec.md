# Delta spec: quest-reward-settlement (quest-auto-settlement)

## MODIFIED Requirements

### Requirement: Completed guild quests may be claimed exactly once per quest ID
`turn_in_quest(actor, staff, quest_id)` SHALL require a parsed `COMPLETED` quest record, the matching
local issuer branch and registered offer, and a quest ID absent from the actor's JSON-safe
`guild_reward_claims` list. Success SHALL append that exact ID. A different acceptance number for the
same definition SHALL remain independently claimable after completion.

The `guild_reward_claims` list SHALL be the single exactly-once ledger for BOTH settlement modes:
automatic settlement SHALL append to the same list under the same rule, and neither mode SHALL pay a
quest ID already present in it. The counter path SHALL therefore refuse to pay a quest already
settled automatically, and automatic settlement SHALL skip a quest already claimed at a counter,
without either treating the other's claim as an error condition to be repaired.

#### Scenario: First completed acceptance is paid once
- **WHEN** a completed `<definition>:1` record is turned in at its issuer
- **THEN** `<definition>:1` is appended once to reward claims and the configured reward is applied

#### Scenario: Duplicate turn-in pays nothing
- **WHEN** the same completed quest ID is turned in again
- **THEN** an already-claimed error is returned and wallet, inventory, merit, claims, and quest log remain
  unchanged

#### Scenario: Later acceptance has independent claim identity
- **WHEN** `<definition>:2` is completed after `<definition>:1` was claimed
- **THEN** the second ID can be claimed once without removing the first claim record

#### Scenario: An automatically settled quest cannot also be claimed at a counter
- **WHEN** a quest settled automatically on completion is presented to `turn_in_quest`
- **THEN** an already-claimed error is returned and wallet, inventory, merit, claims, and quest log
  remain unchanged

#### Scenario: The two settlement modes share one ledger
- **WHEN** one quest is settled automatically and another is claimed at a counter
- **THEN** both quest IDs appear exactly once in the same `guild_reward_claims` list
