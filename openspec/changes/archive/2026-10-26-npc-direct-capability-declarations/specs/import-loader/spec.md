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

#### Scenario: An explicitly imported stat value is used verbatim
- **WHEN** an elf record supplies stats.atk_phys 88
- **THEN** its loaded base is exactly 88 with no derivation or multiplier

#### Scenario: An omitted stat falls back to the race floor
- **WHEN** a record omits guild_merit from stats
- **THEN** the loaded value equals that race's ordinary floor

#### Scenario: The loader never applies a skill multiplier
- **WHEN** a warning-only out-of-band static value loads
- **THEN** that literal value persists without scaling and the validation warning remains

#### Scenario: Literal stats beat any profession tier
- **WHEN** a direct-capability record supplies literal stats
- **THEN** they merge onto the race floor without capability-derived tier defaults

#### Scenario: Empty stats with a tiered profession use the tiered baseline
- **WHEN** a direct-capability NPC supplies empty stats
- **THEN** it uses the ordinary race floor; legacy profession input rejects

#### Scenario: No profession means no behavior change
- **WHEN** a valid record omits capabilities and profession
- **THEN** its literal-stats construction remains unchanged

#### Scenario: A null-tier profession row is a no-op
- **WHEN** an input includes a removed profession field
- **THEN** the closed schema rejects it instead of consulting a default tier

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

#### Scenario: Assembly rides the import transaction
- **WHEN** component attachment fails midway
- **THEN** the complete batch and handler caches roll back

#### Scenario: Explicit entries the blueprint omits keep record order
- **WHEN** a direct component list is accepted
- **THEN** exactly its unique entries retain record order without blueprint expansion

#### Scenario: Identity resolution is fail-closed at two gates
- **WHEN** authored component identity/configuration is incomplete
- **THEN** validation rejects before construction and assembly revalidates the complete plan before writes

#### Scenario: The loader never invents an identity value
- **WHEN** a required service_id, shop_key, branch_key or dialogue_key is absent
- **THEN** validation rejects without inventing or defaulting that identifier

#### Scenario: Assembly reuses the guild economy attach path
- **WHEN** imports and roster hosts attach components
- **THEN** both use the same deterministic validated-plan assembly owner

## REMOVED Requirements

### Requirement: A blueprint schedule template is applied to assembled NPCs only
**Reason**: Profession-owned schedule defaults no longer exist.
**Migration**: Use explicit schedule input through the existing schedule owner; no implicit schedule is installed.
