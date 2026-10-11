# Spec Delta

## MODIFIED Requirements

### Requirement: Defeat of an exact protected entity fails its active quests atomically
The failure planner SHALL match exact protected IDs and actual committed death, never display keys or objective-target sets. The canonical failure reason SHALL be protected_actor_dead for protected records; the old protected_entity_defeated reason SHALL be replaced without an alias. Hostile/environmental death SHALL fail each active affected escort and release its reasons/pins atomically with originating damage, compensating control and caches. Ordinary knockout SHALL not count as death.

#### Scenario: Protected NPC death fails an escort quest
- **WHEN** a lawful hostile or environmental source commits exact protected NPC death
- **THEN** damage, protected_actor_dead failure, exact pin/source release and required handback commit together, with no payout or successful reunion

#### Scenario: Same display key does not create a false failure
- **WHEN** another NPC shares the protected NPC's display key but has a different dbref and is defeated
- **THEN** the quest remains active

#### Scenario: Objective target death cannot trigger protected failure
- **WHEN** a DEFEAT stage's `objective_target_ids` target is killed and that ID is absent from
  `protected_entity_ids`
- **THEN** it may advance DEFEAT progress but cannot fail the quest

#### Scenario: Commit fault rolls back death and quest failure together
- **WHEN** a pin/source/quest/group write or handback fails during a protected-death commit
- **THEN** HP, record, pins, membership, possession/session and cached surfaces return to pre-action baseline

#### Scenario: Knockout is not protected death
- **WHEN** existing ordinary companion policy produces knockout and later recovery for a protected temporary actor
- **THEN** no protected death reason is recorded and current engagement/recovery behavior remains
