# Spec Delta

## MODIFIED Requirements

### Requirement: Loaded trait values are the literal imported stats, merged onto the race floor for omitted keys, never re-derived or multiplied
Loaded traits SHALL equal literal imported stats merged onto the race floor for omitted keys. Capability configuration SHALL apply no skill/profession multipliers or tier defaults. Explicit independently owned tier creation paths SHALL remain unchanged.

#### Scenario: Literal values survive
- **WHEN** an imported record supplies base values including magic_power
- **THEN** all literal bases persist exactly and omitted keys use the race floor

#### Scenario: Empty stats
- **WHEN** an NPC declares capabilities and empty stats
- **THEN** traits use the ordinary race floor without capability-derived tier inference

#### Scenario: Rollback of traits
- **WHEN** a later capability install fails
- **THEN** all constructed traits and objects roll back with the batch

### Requirement: A profession-bearing NPC record assembles blueprint components with explicit precedence
The loader SHALL assemble exactly the validated direct NPC component plan inside the complete import transaction. All required configuration and binding/room references SHALL validate before persistence; assembly failure SHALL restore storage and handler caches.

#### Scenario: Blueprint minus explicit components
- **WHEN** a record declares two direct components
- **THEN** exactly those components and kwargs are installed without expansion or override precedence

#### Scenario: Missing identity kwargs reject the batch instead of guessing
- **WHEN** a merchant entry omits service_id or shop_key
- **THEN** the entire batch rejects naming the field and no entity persists

#### Scenario: No profession means byte-identical construction
- **WHEN** a record declares no components
- **THEN** construction preserves unrelated import semantics

#### Scenario: Each assembled NPC emits one assembly info event
- **WHEN** a direct capability installation commits
- **THEN** one import_capabilities_assembled event names the record and declared types with no profession field; a rollback emits none

## REMOVED Requirements

### Requirement: A blueprint schedule template is applied to assembled NPCs only
**Reason**: Profession-owned schedule defaults no longer exist.
**Migration**: Use explicit schedule input through the existing schedule owner; no implicit schedule is installed.
