# Spec Delta

## REMOVED Requirements

### Requirement: Authored crocodile behavior uses the existing first-owned strategy
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Authored monster kits use shared policy selection and fallback. Retarget substantive tests in this change.

### Requirement: 穗鳴雀 contact kit uses existing first-owned policy and fallback
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Authored monster kits use shared policy selection and fallback. Retarget substantive tests in this change.

### Requirement: 潮燈蟹 contact kit uses existing first-owned policy and fallback
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Authored monster kits use shared policy selection and fallback. Retarget substantive tests in this change.

## ADDED Requirements

### Requirement: Authored monster kits use shared policy selection and fallback
A monster SHALL use its validated authored behavior binding or existing tier default. First-owned selection SHALL prefer the first eligible affordable damage skill in owned order and fall back to an available ordinary attack when either resource or eligibility fails. Declared flee thresholds SHALL retain inclusive priority. Existing target/displacement/knockout gates and initiative-time revalidation SHALL remain authoritative.

#### Scenario: Selection and exhaustion
- **WHEN** a synthetic first-owned kit executes with full resources then separately exhausted MP and SP
- **THEN** the preferred action executes first and each exhaustion selects available ordinary attack without utility planning

#### Scenario: Threshold and late changes
- **WHEN** a monster reaches its declared flee edge or targets/eligibility change before resolution
- **THEN** ordinary flee takes inclusive priority and final resolver gates reject invalid late state without creature-specific logic
