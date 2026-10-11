# Spec Delta

## Purpose

Activate independently eligible published scenes before quest acceptance through a deterministic transaction boundary.

## ADDED Requirements

### Requirement: Encounter activation is independent of quest acceptance

Each encounter SHALL declare its own locator, prerequisites, required roles and bounded presentation. Deterministic activation SHALL consume player/package/scene identity, actual room/tick and authoritative observations, materializing only required unbound roles without accepting a quest or revealing future secrets.

#### Scenario: Permanent activation has no implicit world edits
- **WHEN** an eligible encounter activates in an existing permanent room
- **THEN** it creates no duplicate room, overwrites no shared description, fabricates no active quest record and grants no quest progress

#### Scenario: Either encounter activates first
- **WHEN** a synthetic related pair's independent encounters are activated in each visit order before any quest acceptance
- **THEN** each first encounter creates only its required role, the declared relationship remains valid, and the player's accepted quest log stays empty

### Requirement: Activation commits one durable identity or no partial scene

Activation SHALL lock and revalidate encounter/binding identities, locator, prerequisites and actors. Creation, scoped component authorization, strict registration, bindings, phase and owner-API knowledge/events SHALL commit together. Failure SHALL restore caches and registration views, leaving an unactivated invocable scene. Presentation SHALL follow commit; activation identity SHALL be durable independently of callbacks.

#### Scenario: Failures at each write boundary leave no remnants
- **WHEN** failures are injected after actor creation, component configuration, and commission registration
- **THEN** committed reload reveals no orphan actor, partial role binding, activation record, knowledge write, or stale issuer registration and a later invocation uses the same encounter identity

### Requirement: Repeated activation never repairs missing actors

Repeat activation, reconnect, restart, and re-entry SHALL return existing committed state without duplicate actors. Bound actors SHALL remain at their actual locations. Changed prerequisites and missing required, dead, deleted, or departed actors SHALL return named unavailable reasons without teleporting or recreating them; cancellation SHALL prevent activation.

#### Scenario: Repeat entry and reload retain one actor
- **WHEN** an activated scene is revisited after movement and binding reload
- **THEN** no second actor is created and the original actor's actual location, persona, living state, and memory remain unchanged

#### Scenario: Locator or actor availability changes
- **WHEN** authoritative prerequisites fail, the room differs from the locator, or a required actor is removed
- **THEN** activation returns an explicit reason and makes no partial scene

### Requirement: Scene lifecycle boundaries emit owned operation traces

Publication, activation, authorization settlement, phase changes, retention transfers, and failures SHALL emit stable English operation events through the project observability facade with available package, scene, role, player, NPC, room, tick, and source identifiers. Exceptions and credentials SHALL follow existing rules; player prose SHALL remain bounded context or protected transcript data.

#### Scenario: A failed activation is attributable
- **WHEN** actor availability causes an activation failure
- **THEN** its operation trace records the named reason and available business identities without credentials or prose in the event identifier
