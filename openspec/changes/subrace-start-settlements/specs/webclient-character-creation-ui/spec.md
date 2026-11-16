# Spec Delta

## MODIFIED Requirements

### Requirement: Activation is all-or-nothing and hands off to exploration
Successful `creation.activate` SHALL remain all-or-nothing for character state: either the pending gate is removed with the full deterministic initialization committed, or the character stays pending with no partial trait, identity, or progression state. After a committed activation the adapter SHALL publish a full `exploration` snapshot so the browser atomically replaces the creation dock.

#### Scenario: Successful activation moves the shell to exploration
- **WHEN** `creation.activate` commits
- **THEN** the full snapshot mode is `exploration`, the creation dock unloads, the character stands in the start room resolved for its subrace, and `creation_pending` is false

#### Scenario: A failed activation transaction leaves the character pending
- **WHEN** a write failure is injected into the activation transaction
- **THEN** the whole activation rolls back, the character remains pending with its prior draft and its original location and `home`, and no partial trait, identity, or progression state is persisted

#### Scenario: The activated character stays home in 虛境
- **WHEN** an activation commits
- **THEN** the character no longer stays in 虛境: its `home` is the start room it was placed
  in, never 虛境

#### Scenario: No affected-panel set can strand the shell in creation mode
- **WHEN** a creation adapter publishes after a successful activation
- **THEN** it publishes no affected-panel set that leaves the shell in creation mode
