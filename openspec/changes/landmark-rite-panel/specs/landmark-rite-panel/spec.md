# Spec Delta

## Purpose

Defines the `rite` presentation panel: the committed, server-owned data from which the browser presents a landmark rite, and the identical validation of that data on both sides of the wire.

## ADDED Requirements

### Requirement: The rite panel is available exactly on a rite landmark
The `rite` panel SHALL be available when the record owner's current canonical node is a rite landmark's node, whether or not the district is lit and whether the node is a wilderness cell or a settlement room, and SHALL otherwise be the registered unavailable form.

#### Scenario: On and off the landmark
- **WHEN** the panel is rendered on a synthetic landmark node and then on a neighbouring node
- **THEN** the first is available and names that district and guardian, and the second is unavailable

#### Scenario: Lit state
- **WHEN** the panel is rendered on a landmark whose district is unlit and then lit
- **THEN** the district's lit flag is false and then true, and the panel is available both times

### Requirement: The rite panel lists options, performers and experienced options
An available `rite` panel SHALL list the archetype's options in authored order with whether each admits a companion, the eligible performers with the controlled character first, and the option keys the record owner has completed at this district.

#### Scenario: Options and performers
- **WHEN** the panel is rendered for a party with one present companion on a landmark whose archetype has one solo-only option and one option with a watch scene
- **THEN** the options carry the companion flag false and true in authored order, and the performers are the controlled character with a null member identifier, marked as the record owner, followed by the companion, not so marked

#### Scenario: Possessed companion
- **WHEN** the controlled character is a companion the player possesses
- **THEN** the first performer is not marked as the record owner

#### Scenario: Ineligible companion
- **WHEN** a companion is asleep or absent
- **THEN** it is not among the performers

#### Scenario: Experienced options
- **WHEN** one option was completed and the panel is rendered again
- **THEN** that option's key, and only that key, is listed as experienced

#### Scenario: Unreadable record
- **WHEN** the record owner's record violates its envelope
- **THEN** the panel is still available, lists nothing as experienced, and one warning is logged

### Requirement: The rite panel carries the last delivery only on its node
After a rite commits through the browser action, the `rite` panel SHALL carry that rite's delivery while the record owner's current canonical node is the node the rite committed on, and SHALL carry no delivery on any other node.

#### Scenario: Same node
- **WHEN** a rite commits and the panel is rendered again on the same node
- **THEN** the panel carries the delivery the action returned

#### Scenario: Another node
- **WHEN** the owner moves to another rite landmark, or leaves the landmark
- **THEN** the panel there carries no delivery from the earlier node

#### Scenario: Return to the committed node
- **WHEN** the owner leaves and returns to the node the rite committed on
- **THEN** the panel carries that delivery again

### Requirement: The rite panel is validated identically by server and browser
The server and the browser SHALL accept exactly the same bounded `rite` panel shape and SHALL reject a malformed or oversize panel whole, never trimming it into validity.

#### Scenario: Mutation table
- **WHEN** a valid synthetic panel and one mutation per bound (an extra key, too many options, a duplicate option key, a malformed performer list, an experienced key that is not an option, a malformed delivery line, an oversize panel) cross both validators
- **THEN** both accept the valid panel and both reject every mutation

#### Scenario: Version parity
- **WHEN** the panel schema parity contract runs
- **THEN** the server's `rite` schema version equals the browser allowlist's
