# social-identity Specification

## Purpose
Provide typed social identity source without parsing persona prose through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## Requirements

### Requirement: Social qualification has identical meaning across sources
Static and generated scenes SHALL read the same explicit acting-body identities. Generated persona or scene prose SHALL confer no social membership or write authority, and a generated role SHALL require no static NPC profile.

#### Scenario: Generated prose cannot invent noble membership
- **WHEN** a generated actor is described as noble but has no typed noble identity
- **THEN** noble qualification fails with the same result as an equivalent static actor

### Requirement: Social identity is explicit typed state
Dialogue social identity SHALL read registered explicit identity tags on the acting body. Persona text, racial ancestry, displayed titles and missing storage SHALL never imply membership or an ordered social hierarchy.

#### Scenario: Unknown is not commoner
- **WHEN** an actor has no social identity storage but persona calls it a noble
- **THEN** its structured identity remains empty and a noble requirement fails

#### Scenario: Typed import survives reload
- **WHEN** a validated import explicitly supplies clergy and official
- **THEN** those tags persist and can be read after reload without mutating handlers

### Requirement: Identity writes follow deterministic construction
Only deterministic construction or an owning deterministic domain operation SHALL establish registered social identities. Invalid imports and failed multi-attribute construction SHALL leave no partial identity or character state.

#### Scenario: Invalid key rejects import
- **WHEN** an import supplies an unknown social identity key
- **THEN** the batch rejects before any objects or identity records are committed

#### Scenario: Construction rollback restores identities
- **WHEN** construction or guild registration fails after assigning a tag
- **THEN** durable and cached identity state match baseline
