## ADDED Requirements

### Requirement: The Vue app binds the preserved strict DOM-independent logic to a reactive store
The Vue application SHALL use a single reactive store (Pinia) as the sole writer of client view state.
The store SHALL consume the preserved DOM-independent logic — the protocol reducer, the keyboard router,
the narrative markup pipeline, the local-map model, and the choice-point and option-card logic — through
ES-module wrappers rather than reimplementing it. The store SHALL publish committed state atomically so
that no subscriber observes partially applied panel state, and it SHALL hold only data derived from the
OOB panel allowlist (art, status, context_actions, local_map, services, creation, exploration,
character) and the transport text stream; it SHALL NOT invent data. Components emit only user-intent
dispatches, and the store is driven in tests by raw reducer inputs; binding the live transport and the
components to this store are established by later changes.

#### Scenario: Renderers observe only committed state
- **WHEN** a valid snapshot or update is accepted by the preserved protocol reducer through the store
- **THEN** the store publishes one commit of completely replaced panel state and no subscriber observes partially applied state

#### Scenario: Stale epochs and revisions are rejected
- **WHEN** an old-epoch snapshot or a stale active-epoch revision is presented to the store
- **THEN** the store discards it and preserves the last committed state

#### Scenario: The store holds only backed data
- **WHEN** the store receives panel data
- **THEN** it holds only data sourced from the OOB allowlist or the transport text stream and holds no invented data
