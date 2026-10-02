## ADDED Requirements

### Requirement: Host synchronization uses authored canonical ages without rewriting reused state
A newly created service host SHALL receive the canonical age pair from its resolved authored profile before publication, within the same creation transaction as its card. Synchronization of a reused host SHALL preserve each present age attribute, the effective edited persona, greeting, persona version, and existing service identity; only an absent age field SHALL be supplied from the corresponding profile value. Invalid age authorship SHALL fail preflight before synchronization writes.

#### Scenario: Fresh host agrees with its authored identity
- **WHEN** synchronization creates a host whose authored profile has age 52 and apparent age 52
- **THEN** the usable host carries 52 for both canonical age attributes, not 18, and its valid profile card is initialized together with them

#### Scenario: Reuse after editing preserves identity and card
- **WHEN** an existing service host with age 61, missing apparent age, an edited card/version, and a profile now authoring 52/52 is synchronized
- **THEN** the same host keeps age 61, receives apparent age 52, and retains its edited card, greeting, version, components and service bindings
