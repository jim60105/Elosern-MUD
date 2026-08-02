## ADDED Requirements

### Requirement: New players arrive at the capital's South Gate
After a pending character successfully activates, the game SHALL move that character to the South
Gate of 聖潔王都 (`capital_altoria`, `(2,0)`) and present a welcome message confirming entry into the
world. The move SHALL use the deterministic movement path and SHALL not be conditional on the guide
NPC existing.

#### Scenario: Activation places the character at the South Gate
- **WHEN** a pending character completes activation
- **THEN** the character's location is the South Gate room and a welcome message is presented

#### Scenario: Arrival does not depend on the guide NPC
- **WHEN** the South Gate guard does not exist (sync not run or failed)
- **THEN** activation still teleports the character and the welcome message still appears

### Requirement: The arrival scene plays as the first guided beat
When an onboarding character first arrives at the South Gate, the game SHALL play the authored
arrival scene: prose describing the city and the guard's opening line prompting `look`. The beat
SHALL complete when the player successfully looks while at the South Gate (detected through the
character's look hook); a look anywhere else, or a look that fails, SHALL NOT advance the beat. Until
completion the scene SHALL replay on each arrival (including reconnect while still at the gate); after
completion it SHALL never replay.

#### Scenario: First arrival plays the arrival scene
- **WHEN** a newly activated character first arrives at the South Gate
- **THEN** the arrival prose and the guard's `look` prompt are presented

#### Scenario: look completes the arrival beat
- **WHEN** the player successfully looks while at the South Gate during the arrival scene
- **THEN** the beat advances to the guard-guidance beat and the scene does not replay on later
  arrivals

#### Scenario: A look elsewhere does not advance the beat
- **WHEN** an onboarding character looks while not at the South Gate (or a look fails)
- **THEN** the arrival beat does not advance

#### Scenario: Reconnect before look replays the scene
- **WHEN** the player disconnects before completing the arrival scene and later logs in again while
  still at the South Gate
- **THEN** the arrival scene is presented again

### Requirement: The South Gate guard offers scripted guidance
The game SHALL create exactly one guard NPC at the South Gate carrying an `OnboardingGuide`
component, idempotently at startup. The guard SHALL be an adult (`age >= 18` and `apparent_age >= 18`,
persisted on the NPC). After the arrival beat, the guard SHALL prompt the player to move north to the
plaza and name the adventurers' guild as the next destination. The `talk` command SHALL answer known
keywords with authored responses and give a no-understanding line for unknown input.

#### Scenario: Guard creation is idempotent
- **WHEN** the startup sync runs twice
- **THEN** exactly one guard NPC exists at the South Gate

#### Scenario: The guard is an adult
- **WHEN** the guard NPC is inspected after sync
- **THEN** its actual and apparent ages are both at least 18

#### Scenario: The guard guides toward the guild
- **WHEN** the arrival beat completes
- **THEN** the guard prompts the player to move north to the plaza and mentions the adventurers'
  guild

#### Scenario: talk answers known keywords
- **WHEN** the player talks to the guard with a known keyword (e.g. 公會, 冒險, 危險)
- **THEN** the guard responds with the authored response for that keyword

### Requirement: talk behaves predictably for any NPC
The `talk` command SHALL accept the syntax `talk <npc>` and `talk <npc> <keyword>`. `talk <npc>`
SHALL present the target's current topic. A missing or ambiguous target, a non-NPC target, an NPC
without a dialogue component, and an unknown keyword each SHALL produce a distinct line and cause no
state change; a `talk` on an NPC without a dialogue component SHALL yield the no-response line.

#### Scenario: talk to an NPC without a dialogue component
- **WHEN** the player talks to an NPC that lacks a dialogue component
- **THEN** the player receives the no-response line and no state changes

#### Scenario: talk target resolution errors
- **WHEN** the player talks to a missing or ambiguous target, or to a non-NPC object
- **THEN** the player receives the corresponding resolution error and no state changes

#### Scenario: talk with an unknown keyword
- **WHEN** the player talks to the guard with an unrecognized keyword
- **THEN** the guard gives the no-understanding line and no state changes

### Requirement: Guidance hands off at the guild exterior
When an onboarding player reaches the guild exterior (冒險者公會外), the guard's guidance SHALL end as
completed: the guard no longer prompts and no arrival or guide beat fires again for that character.

#### Scenario: Reaching the guild exterior ends guidance
- **WHEN** an onboarding player moves into the guild exterior room
- **THEN** guidance ends as completed and no further arrival or guide prompts appear

### Requirement: Onboarding state is written only by the deterministic service
The character SHALL persist `onboarded`, `onboarding_beat`, `guide_progress`, and
`first_arrival_seen`; every write to these attributes SHALL route through `world.rules.onboarding.py`.
`guide_progress` SHALL follow the defined schema (`state` in active/completed/skipped and a record of
seen keywords). The service SHALL set `onboarded` to true when the character successfully turns in the
討伐低階魔物 quest, inside the same transaction as the turn-in settlement so the two never diverge.
Entering a room outside the guided corridor (南門, 南大道, 中央廣場, 冒險者公會外) SHALL mark the guide
as skipped without setting `onboarded`, so the tutorial stays reachable afterwards.

#### Scenario: First hunt turn-in completes onboarding
- **WHEN** an onboarding character successfully turns in the 討伐低階魔物 quest
- **THEN** `onboarded` is set to true and no further onboarding guidance appears

#### Scenario: A turn-in settlement failure leaves onboarding incomplete
- **WHEN** a failure is injected into the onboarding write inside the turn-in transaction
- **THEN** the whole settlement rolls back and `onboarded` stays false, with no partially applied
  reward or claim

#### Scenario: Deviating from the guided corridor marks the guide skipped
- **WHEN** an onboarding player enters a room outside the guided corridor without finishing the guide
- **THEN** the guide is recorded as skipped, `onboarded` stays false, and the guard no longer prompts

### Requirement: A help entry explains onboarding afterwards
The game SHALL provide a 新手引導 help entry readable after onboarding completes or is skipped, so a
player can revisit the guidance.

#### Scenario: Help exposes the onboarding entry
- **WHEN** a player reads help for 新手引導
- **THEN** the entry explains the arrival, the guard, and the first-day path
