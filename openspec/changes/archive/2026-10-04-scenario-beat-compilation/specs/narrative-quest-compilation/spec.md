## Purpose

Compiles validated quest-seed beats through the existing quest proposal/compiler/materializer without fallback filler, unauthorized acceptance, or partial quest publication.

## ADDED Requirements

### Requirement: Quest-seed beats compile only through existing owners

A validated quest-seed beat SHALL pass its permitted immutable narrative context to ScenarioDirector and produce a QuestBlueprint proposal. Existing deterministic quest compilation, issuance authorization, registration, SceneBuilder and runtime SHALL remain authoritative. Prose SHALL NOT complete objectives, fabricate past actions or accept a quest remotely.

#### Scenario: Valid quest beat compiles
- **WHEN** a validated beat generates a supported context-fitting blueprint
- **THEN** the quest owner compiles/publishes it and the maps/materializer lifecycle remains authoritative

#### Scenario: Letter claims completion
- **WHEN** a beat or letter claims its quest was already completed
- **THEN** objective progress and acceptance remain unchanged

#### Scenario: Stale compilation
- **WHEN** relevant state changes between blueprint generation and publication
- **THEN** revalidation rejects without partial quest/beat publication

### Requirement: Beat-context failure creates no template replacement

On disabled/unreachable/exhausted/misfitting quest-beat generation the beat path SHALL create no quest or replacement filler and retain its thread/source provenance. Existing generic template-pool quest generation SHALL remain playable offline. Accepted repeated beat compilation SHALL be idempotent across restart.

#### Scenario: Offline beat generation
- **WHEN** all profiles are disabled and a quest-seed beat is compiled
- **THEN** no template substitution or partial quest is published

#### Scenario: Generic offline quest remains
- **WHEN** a generic non-beat quest request runs offline
- **THEN** the existing compatible authored template path remains available

#### Scenario: Restart repeats publication
- **WHEN** the same accepted quest-seed source is handled after restart
- **THEN** one linked publication exists with recoverable blueprint/snapshot identity

