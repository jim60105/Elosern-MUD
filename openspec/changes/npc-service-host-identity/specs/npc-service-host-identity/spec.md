# Spec Delta

## Purpose

Define stable canonical ownership and convergent source synchronization of NPC service capabilities while preserving subsystem-owned live game state.

## ADDED Requirements

### Requirement: Canonical source identity selects one host independently of capabilities
A source-managed host SHALL be selected by its unique canonical authored profile provenance, independently of component type/order, display name, location and component service identifiers. Duplicate or conflicting person ownership SHALL reject the complete operation.

#### Scenario: Reordering retains the person
- **WHEN** capabilities are reordered, extended, emptied or service identifiers change
- **THEN** the same canonical host dbref is reused without creating a second person

#### Scenario: Duplicate provenance rejects atomically
- **WHEN** two live hosts claim one canonical authored host identity
- **THEN** synchronization rejects before any creation, deletion or configuration write

#### Scenario: Moved host remains moved
- **WHEN** an existing managed host stands outside its original spawn room
- **THEN** sync preserves its location and the place-bound service remains paused

### Requirement: Managed reconciliation preserves unrelated and subsystem-owned state
Synchronization SHALL converge the declared managed capability set and authored configuration only. It SHALL preserve unrelated components and subsystem-owned state, remain idempotent, and roll back the complete batch including in-process caches on failure.

#### Scenario: Removed capability leaves unrelated state
- **WHEN** a declared merchant is removed while unrelated components and game state exist
- **THEN** only the obsolete managed slot is removed; inventory, relationships, location and unrelated components survive

#### Scenario: Live commerce survives configuration updates
- **WHEN** shop configuration or binding changes after stock/restock progress exists
- **THEN** authored fields converge while live stock/restock progress is unchanged

#### Scenario: Rollback restores every host
- **WHEN** a later row or component removal fails after earlier writes
- **THEN** database rows, attributes and handler caches equal the pre-batch state
