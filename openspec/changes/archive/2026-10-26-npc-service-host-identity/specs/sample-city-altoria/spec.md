# Spec Delta

## MODIFIED Requirements

### Requirement: Altoria service content synchronizes idempotently without resetting live state
Startup SHALL create service hosts by stable canonical host provenance from every current hosted place declaration, using its authored identity and resolved capability plan. Repeated sync SHALL update authored descriptions/component definitions without duplicating hosts, relocating reused hosts or resetting initialized merchant stock, restock progress or mutable identity. Interiors, doorways and exam metadata SHALL retain their existing synchronization contract.

#### Scenario: Fresh startup creates a playable service path
- **WHEN** startup runs on an empty database after grid sync
- **THEN** one interior per current place row and its two doorway exits exist, with exactly the declared service hosts/components and exam metadata before commands are accepted

#### Scenario: Repeated startup creates no duplicates
- **WHEN** guild-economy sync runs twice
- **THEN** object, exit, component-host, and component counts remain unchanged

#### Scenario: Live merchant stock survives content resync
- **WHEN** a player buys an item and startup sync runs again
- **THEN** the decremented stock remains rather than returning to initial stock

#### Scenario: A new specialist shop trades through the ordinary command path
- **WHEN** a player stands in a specialist shop's interior during its opening hours and invokes
  the stock listing and a purchase
- **THEN** the listing names that shop's own interior and every good its assortment carries,
  and the purchase moves goods, wallet and stock through the same deterministic trade APIs
  every other shop uses

#### Scenario: Interiors, doorways, and exam metadata are created exactly once
<!-- The shipped text fixed the surface at ONE merchant NPC, TWO interiors and FOUR doorway
     exits while the place registry already drove two, three and six. altoria-adornments-and-
     remedies adds two more merchant places, so the quantities are restated as registry-driven
     — the idempotence, no-reset and single-creation guarantees elsewhere are unchanged. -->
- **WHEN** guild-economy startup runs against the place registry
- **THEN** it SHALL create one permanent interior and its two directed doorway exits for each
  place-registry row, and exam spawn metadata, exactly once
