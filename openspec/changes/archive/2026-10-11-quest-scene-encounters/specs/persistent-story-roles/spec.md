# Spec Delta

## Purpose

Preserve exact named story character identities independently of accepted quest stages and generated planning text.

## ADDED Requirements

### Requirement: Published packages separate immutable definitions from runtime bindings

Published packages SHALL retain stable immutable versioned definitions separately from mutable role, encounter and dialogue runtime state. Package-role and encounter identities SHALL have database-enforced uniqueness. Reprocessing a source SHALL return its existing package; conflicting replacement payloads SHALL reject without overwriting materialized persona or history.

#### Scenario: Publication retains the complete definition
- **WHEN** a valid package is published and reloaded
- **THEN** its package/version, owner, available source request/decision, publication status, validated quest/scene payloads, role definitions, typed relationships, provenance-bearing role-owned knowledge, encounters and dialogue definitions are preserved separately from runtime state

#### Scenario: Source replay after reload preserves publication
- **WHEN** an already published source is processed again after committed state is reloaded
- **THEN** the original immutable version and runtime bindings are returned without duplicate records or overwritten history

### Requirement: Reusable roles bind exact actor identities

A package SHALL define each role once and bind its identity to one exact actor with provenance and availability across encounters and stages. Existing-NPC references SHALL pass explicit identity, ownership, compatibility and authority validation. Names and fuzzy similarity SHALL never select actors; reciprocal typed relationships SHALL confer no private knowledge.

#### Scenario: Two scenes share one retained actor
- **WHEN** two encounters and a later stage reference the same role and their committed bindings are reloaded
- **THEN** they reference one actor with unchanged baseline persona and prior memory

#### Scenario: Equal names do not authorize reuse
- **WHEN** an unbound role has the same display name as an unrelated NPC or names an incompatible existing NPC
- **THEN** no name-based reuse occurs and an invalid explicit reference is rejected without granting authority

### Requirement: Named role retention survives quest termination

Quest termination and stage release SHALL preserve retained named actor identity, persona, history, memory, phase and actual living state. Teardown SHALL affect only package-owned disposable state and objects. Cancelled unactivated definitions MAY be discarded without actors. Dead, deleted or departed actors SHALL never be cloned, resurrected or reset.

#### Scenario: Abandonment preserves an unresolved live character
- **WHEN** a quest is abandoned and its stage binding released
- **THEN** the retained actor remains the same interactable identity with its memories and outcome-consistent phase

#### Scenario: Terminal loss remains real
- **WHEN** a bound actor dies or is deleted before scene re-entry
- **THEN** the binding reports that outcome without creating a replacement actor
