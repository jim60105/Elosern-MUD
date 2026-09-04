# Delta: webclient-character-creation-ui

## MODIFIED Requirements

### Requirement: Activation is all-or-nothing and hands off to exploration
Successful `creation.activate` SHALL remain all-or-nothing for character state: either the pending gate is removed with the full deterministic initialization committed, or the character stays pending with no partial trait, identity, or progression state. After a committed activation the character SHALL remain in 虛境 (its unchanged default home — activation performs no relocation and no arrival behavior), and the adapter SHALL publish a full `exploration` snapshot so the browser atomically replaces the creation dock. The creation adapters SHALL NOT publish an affected-panel set that leaves the shell in creation mode after a successful activation.

#### Scenario: Successful activation moves the shell to exploration
- **WHEN** `creation.activate` commits
- **THEN** the full snapshot mode is `exploration`, the creation dock unloads, the character stands in 虛境 with no relocation performed, and `creation_pending` is false

#### Scenario: A failed activation transaction leaves the character pending
- **WHEN** a write failure is injected into the activation transaction
- **THEN** the whole activation rolls back, the character remains pending with its prior draft, and no partial trait, identity, or progression state is persisted
