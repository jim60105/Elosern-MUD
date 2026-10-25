# Spec Delta

## Purpose

Provide server-qualified topic disclosure and committed-state refresh through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## ADDED Requirements

### Requirement: Qualified topic disclosure is server-owned
Hidden topics SHALL be absent. Locked topics SHALL expose only permitted labels, lock state, canonical requirement hints and selectable refusal content. Qualified formal bodies SHALL be omitted until a currently authorized selection. Every selection SHALL recheck current canonical context before effects.

#### Scenario: No protected body in any projection
- **WHEN** a topic is hidden or locked and its formal scene contains a sentinel
- **THEN** no panel, exploration affordance, action descriptor or pure-chain bundle contains the sentinel

#### Scenario: Stale visible choice loses eligibility
- **WHEN** a listed open topic becomes ineligible before selection
- **THEN** the server gives its allowed refusal or rejection with no formal body and no formal effect

### Requirement: Committed state changes refresh eligibility without rewriting playback
Relevant committed state changes SHALL refresh dialogue availability from canonical state. Failed or rolled-back changes SHALL publish no false opening. Ordinary eligibility refresh SHALL preserve a delivered scene variant, while host, phase or control invalidation SHALL retire it.

#### Scenario: Equipped exposure refreshes choices
- **WHEN** a lawful equipment commit crosses a topic exposure boundary during a scene
- **THEN** choices reflect the new availability when shown and the playing scene retains its original wording

#### Scenario: All source families refresh
- **WHEN** item holdings, skills, owner rank/quest/claim/affinity, companion presence or world time commits a condition change
- **THEN** the next committed dialogue projection reflects that source without a second topic selection

