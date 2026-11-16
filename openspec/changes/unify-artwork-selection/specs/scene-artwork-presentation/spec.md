## MODIFIED Requirements

### Requirement: Normal scenes use the complete authored source chain
Normal scenes SHALL attempt authored room official art before the common archetype subject chain: explicit official choice, generated gallery default, operator archetype default, required bundled type and distinct declared terminal. Source selection SHALL use authored scene type rather than game mode. Exhaustion SHALL preserve reached failures with a non-image background.

#### Scenario: Room override suppresses lower faults
- **WHEN** a healthy room image precedes a failed archetype job
- **THEN** the room image displays with no unused job failure

#### Scenario: Generated art wins before official defaults
- **WHEN** no room override or explicit official choice resolves and generated plus operator/bundled type art coexist
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

#### Scenario: Scene official choice outranks generated default
- **WHEN** a scene archetype has an explicit valid official choice and a generated default with no room override
- **THEN** its explicit choice wins through the common subject chain; generation state remains independent
