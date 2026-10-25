# Spec Delta

## Purpose

Give generated dream-collaboration NPCs the same complete scene, qualification, reading and playback behavior as static NPC dialogue while preserving immutable package authority.

## ADDED Requirements

### Requirement: Generated dialogue participates in every shared scene feature
Published generated roles SHALL use complete actor-first scenes with variants, all shared condition families, hidden/locked/open qualification, refusal, predecessors, public-chain rules, manual playback, persistent reading and unread notifications. Generated roles SHALL require no static profile or registry membership.

#### Scenario: Generated role plays and completes a scene offline
- **WHEN** a published generated role is selected after model services are disabled
- **THEN** text and browser deliver the same attributed scene, and formal completion persists through save/reload using the owning player's logical package-role/topic identity

#### Scenario: Shared qualification protects generated content
- **WHEN** a generated topic is hidden or locked or its phase is not currently permitted
- **THEN** its formal body is absent from panels, actions, hints, chain bundles and freeform context, and forged/stale selection has no effect

### Requirement: Generated scene identity survives source and runtime boundaries
Generated topic and scene identities SHALL be collision-free namespaced encodings of immutable package, role, phase and local ID. Their validation SHALL be separate from static identifier syntax. Full identity bytes SHALL survive publication, receipts, actions, playback and reading without truncation, within common aggregate payload budgets.

#### Scenario: Identical local IDs in different packages remain distinct
- **WHEN** two packages use the same role, phase and local topic IDs, including maximum valid Unicode identity components
- **THEN** their canonical full identities differ, retain exact bytes after reload and cannot acknowledge or select each other's content

### Requirement: Generated publication uses existing immutable database ownership
Whole-package scene/schema/reference validation SHALL precede deterministic atomic publication to the existing immutable scene-package database. Generated/private content SHALL never be written to source directories or the global static dialogue snapshot. Duplicate identical publication SHALL be idempotent; conflicts/faults SHALL leave no partial package, views or publication references.

#### Scenario: Publication fault restores all owners
- **WHEN** an injected fault follows package-row creation or view registration
- **THEN** database rows, commission grants, process-local views and dispatch publication references match baseline

#### Scenario: A pre-cutover payload resolves to no source
- **WHEN** an already-published package's dialogue still parses only to the removed response-only shape
- **THEN** the trusted provider returns no source for that role, one boundary event reports it, and no partial or converted delivery occurs

### Requirement: Qualification and existing effects precede formal success delivery
Generated effect topics SHALL recheck shared qualification and current deterministic effect authority before formal success delivery. Only existing declared allowlisted effects SHALL execute. Effect/session persistence SHALL be atomic; refusal, replay, duplicate selection and completion SHALL grant no extra effect, affinity or protected formal receipt.

#### Scenario: Refused commission cannot disclose success
- **WHEN** a generated commission topic's issuer, phase, possession or qualification gate refuses
- **THEN** only safe refusal/rejection is delivered and no protected success body, accepted quest or formal receipt is created

#### Scenario: Session failure rolls back accepted commission
- **WHEN** an authorized existing commission effect succeeds but scene-session publication fails
- **THEN** quest acceptance, session state and caches are restored and retry applies the effect at most once

### Requirement: Generated phase retirement preserves reading without stale delivery
Changed phase/binding or cancelled package SHALL retire obsolete delivery, choice, acknowledgement and notification capabilities. Returning to the same phase SHALL retain its saved reading. Existing committed provenance, permitted knowledge, historical turns and late freeform rejection SHALL remain authoritative.

#### Scenario: Phase return retains completion
- **WHEN** a role moves from phase A to B and later lawfully returns to A
- **THEN** old A receipts remain retired, B receives no A private content, and A topic completion remains saved
