## MODIFIED Requirements

### Requirement: A round and its settlement form one atomic persistence unit

`submit_player_action` SHALL persist the round's action effects (HP/resources/knockouts/quest effects), the updated session metadata (round count, fled/knockout sets), and any terminal settlement (exam outcome, clock advance, session clearing) as a single durable transaction with snapshot/restore of all touched entities, so a process termination can never leave half-round durable state. Upkeep-settled effects (damaging-tick HP, defeat entries, and quest effects staged by the upkeep settlement) SHALL commit inside the same unit: `submit_player_action` SHALL forward the session's `simulated` and companion `nonlethal_keys` policy to `run_round` and overwhelm compression, and an upkeep settlement failure SHALL roll back the whole round.

#### Scenario: Termination mid-round leaves no half-committed round

- **WHEN** a process terminates after some combatant effects committed but before the session record update
- **THEN** after restart either the full round (effects plus `rounds_elapsed`) is durable or none of it is

#### Scenario: Terminal settlement failure rolls back the round

- **WHEN** a terminal settlement step raises after round effects were applied
- **THEN** the round effects, session metadata, exam outcome, clock tick, and session clearing all roll back together

#### Scenario: An upkeep-settled kill commits with its round

- **WHEN** a round's upkeep settlement stages a defeat entry and quest effects for an attributed lethal tick and the round then settles terminally
- **THEN** the tick HP, defeat entry, quest log, session metadata, and terminal settlement commit or roll back as one unit

#### Scenario: Upkeep settlement failure rolls back the round

- **WHEN** the upkeep settlement raises while staging defeat or quest effects after round actions applied
- **THEN** the round actions, tick HP, session metadata, and in-process entity surfaces all roll back together
