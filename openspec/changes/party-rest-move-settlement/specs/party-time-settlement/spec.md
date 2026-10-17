# Spec Delta

## Purpose

Define which commander-initiated world-clock advances settle the present party, so resting and travelling regenerate, expire and settle companions together with the commander.

## ADDED Requirements

### Requirement: Skip advances settle the present party
Every SKIP-source advance started by a rest, sleep, wait, or graphical wait SHALL settle the present party scope of the acting character: the acting character, the commander, and every effective companion located in that room.

#### Scenario: Resting regenerates a co-located companion
- **WHEN** the commander rests one hour with companion 艾拉 at MP 10 of 120 in the same room
- **THEN** 艾拉's MP regenerates by her own one-hour regeneration in the same advance as the commander

#### Scenario: A companion in another room is not settled
- **WHEN** the commander rests one hour while companion 卡恩 waits in another room with an active buff
- **THEN** 卡恩's gauges and buff state are unchanged by that advance

### Requirement: Movement advances settle the travelling party
A movement advance for a player-character traverser SHALL settle the traverser and every effective companion co-located with it in the source room before the step. A possessed traverser SHALL settle only itself.

#### Scenario: Followers regenerate with the step
- **WHEN** the commander steps through an exit with 艾拉 in the source room
- **THEN** the one movement advance settles both the commander and 艾拉

#### Scenario: Possessed movement keeps its single scope
- **WHEN** the player, possessing 艾拉, steps through an exit
- **THEN** the movement advance settles only 艾拉

### Requirement: Other advances keep their scope
Church rites, GM console advances, defeat aftermath and combat settlement SHALL keep their existing entity scopes and SHALL NOT be widened by this capability.

#### Scenario: A church rite settles only its participant
- **WHEN** the commander performs a church rite with companions present
- **THEN** the rite's advance settles only the commander

### Requirement: A failed party advance restores every settled member
When a party-scoped advance fails after any settlement write, the system SHALL restore every settled member's gauges, buffs and practice booking together with the tick.

#### Scenario: Injected failure restores the companion
- **WHEN** a rest advance raises after settling the commander and 艾拉
- **THEN** both members' gauges and buffs equal their pre-advance values and the tick is unchanged
