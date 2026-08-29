## ADDED Requirements

### Requirement: Equipment adjustments reach every consumer through one accessor

The equipment-effect capability SHALL provide exactly one pure accessor that
converts the currently worn equipment into a combat adjustment bundle. No
consumer (combat resolution, estimation, preview, cost, resist scoring, or
presentation) SHALL reimplement or bypass that accessor, and no consumer
SHALL compute a parallel equipment formula.

#### Scenario: Single source of truth is enforced structurally

- **WHEN** the codebase is searched for equipment-rulebook reads outside the
  capability's loader, its accessor, and the change-authorized sync/read
  surfaces
- **THEN** no additional gameplay resolution path reads the rulebook
  directly

#### Scenario: Multiple worn items stack additively

- **WHEN** an actor wears a weapon granting `atk_phys +3`, armor granting
  `agility −10%`, and an accessory granting `defense +4`
- **THEN** the accessor returns one bundle containing exactly the additive
  sum of those three items' contributions
