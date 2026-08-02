## MODIFIED Requirements

### Requirement: The South Gate guard offers scripted guidance
The game SHALL create exactly one guard NPC at the South Gate carrying an `OnboardingGuide`
component, idempotently at startup. The guard SHALL be an adult (`age >= 18` and `apparent_age >= 18`,
persisted on the NPC). After the arrival beat, the guard SHALL prompt the player to first move
north to 南大道 and then east to the adventurers' guild exterior (冒險者公會外), naming the guild as
the next destination. The `talk` command SHALL answer known
keywords with authored responses and give a no-understanding line for unknown input.

#### Scenario: Guard creation is idempotent
- **WHEN** the startup sync runs twice
- **THEN** exactly one guard NPC exists at the South Gate

#### Scenario: The guard is an adult
- **WHEN** the guard NPC is inspected after sync
- **THEN** its actual and apparent ages are both at least 18

#### Scenario: The guard guides toward the guild
- **WHEN** the arrival beat completes
- **THEN** the guard prompts the player to move north to 南大道 and then east,
  naming the adventurers' guild as the destination

#### Scenario: The guard's route matches the city map
- **WHEN** the guidance prose is checked against the capital_altoria grid
- **THEN** it describes the two-step path 南門 → 南大道 → 冒險者公會外 and never
  directs the player north through 中央廣場

#### Scenario: talk answers known keywords
- **WHEN** the player talks to the guard with a known keyword (e.g. 公會, 冒險, 危險)
- **THEN** the guard responds with the authored response for that keyword

### Requirement: talk behaves predictably for any NPC
The `talk` command SHALL accept the syntax `talk <npc>` and `talk <npc> <keyword>`. `talk <npc>`
SHALL present the target's current topic: the active guide prompt for the onboarding guard, or the
authored greeting for any other NPC carrying a scripted dialogue component. A missing or ambiguous
target, a non-NPC target, an NPC without a dialogue component, and an unknown keyword each SHALL
produce a distinct line and cause no
state change; a `talk` on an NPC without a dialogue component SHALL yield the no-response line.

#### Scenario: talk to an NPC without a dialogue component
- **WHEN** the player talks to an NPC that lacks a dialogue component
- **THEN** the player receives the no-response line and no state changes

#### Scenario: talk target resolution errors
- **WHEN** the player talks to a missing or ambiguous target, or to a non-NPC object
- **THEN** the player receives the corresponding resolution error and no state changes

#### Scenario: talk with an unknown keyword
- **WHEN** the player talks to a dialogue-capable NPC with an unrecognized keyword
- **THEN** the NPC gives the no-understanding line and no state changes

### Requirement: A help entry explains onboarding afterwards
The game SHALL provide a 新手引導 help entry readable after onboarding completes or is skipped, so a
player can revisit the guidance. The entry SHALL describe the route to the adventurers' guild
correctly: first north to 南大道, then east to 冒險者公會外.

#### Scenario: Help exposes the onboarding entry
- **WHEN** a player reads help for 新手引導
- **THEN** the entry explains the arrival, the guard, and the first-day path

#### Scenario: The help entry states the correct route to the guild
- **WHEN** a player reads the 新手引導 help entry
- **THEN** the entry directs the player north to 南大道 and then east to the
  adventurers' guild
