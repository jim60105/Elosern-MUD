## MODIFIED Requirements

### Requirement: Normal scenes use the complete authored source chain
A normal scene SHALL attempt explicit room official art, archetype generated art (the archetype's scene gallery default card), optional operator archetype official art, required bundled type art, then a distinct declared town/forest terminal image. Source selection SHALL use authored scene type rather than game mode. Exhaustion SHALL produce a non-image background with persistent reached failures.

#### Scenario: Room override suppresses lower faults
- **WHEN** a healthy room image precedes a failed archetype job
- **THEN** the room image displays with no unused job failure

#### Scenario: Generated art wins before official defaults
- **WHEN** no room override resolves and generated plus operator/bundled type art coexist
- **THEN** the generated image wins; its generation state is independent of official availability

#### Scenario: Corrupt override stays visible
- **WHEN** a configured operator image fails and bundled art succeeds
- **THEN** bundled art displays with the reached operator fault

#### Scenario: Identical terminal is never retried
- **WHEN** forest_path or city_street bundled art fails and also names itself as terminal
- **THEN** that resource is attempted once and exhaustion uses non-image presentation

#### Scenario: Malformed scene metadata is explicit
- **WHEN** a scene lacks a valid archetype or supported scene definition
- **THEN** town terminal is attempted with a configuration-failure indication

#### Scenario: A scene gallery card is the generated source
- **WHEN** a synthetic archetype holds a scene gallery default card
- **THEN** the generated position presents that card, and an archetype without a card has no generated attempt
