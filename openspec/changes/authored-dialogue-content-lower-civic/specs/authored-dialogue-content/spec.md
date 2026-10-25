# Spec Delta

## Purpose

Provide complete authored rewrite for altoria_bathhouse, altoria_guardhouse through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## ADDED Requirements

### Requirement: lower-civic dialogue is fully authored and source-backed
The owned lower-civic hosts SHALL replace every fixed authored topic and opening with source-reviewed in-character Traditional Chinese scenes. Formal scenes SHALL start with a complete acting-body utterance, preserve attribution and avoid unintended player commitments. Writers and reviewers SHALL consult the mandatory world source before authoring.

#### Scenario: Every owned topic is replaced
- **WHEN** the complete owned registry set `altoria_bathhouse`, `altoria_guardhouse` is reviewed
- **THEN** each of its original four topics has a newly written multi-line fallback and every declared variant/refusal is authored without old response wrappers

#### Scenario: Lore prerequisite blocks invented content
- **WHEN** the mandatory world source is missing or a line contradicts elves standing, rarity or distinctive religion
- **THEN** writing/review cannot pass until source-backed prose is available, without invented substitute lore

### Requirement: lower-civic scenes preserve services and offline play
The lower-civic rewrite SHALL preserve existing service availability and deterministic effects. It SHALL run through the shared manual player and attributed text interface offline; replay and reading acknowledgements SHALL not repeat effects.

#### Scenario: Real host on both interfaces
- **WHEN** an owned host is constructed with all model/image services disabled and a formal topic is selected then replayed
- **THEN** browser and text use the same stable authored scene, text completion persists reading and replay applies no second effect

#### Scenario: Host office stays authoritative
- **WHEN** a conversation mentions goods, rank, worship or local services
- **THEN** the statements match that host canonical office/assortment and prose itself grants no new service, item or quest effect

