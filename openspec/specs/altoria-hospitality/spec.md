# altoria-hospitality Specification

## Purpose
Give the capital a tavern, an inn and a public bathhouse — permanent
hospitality interiors whose hosts teach, by conversation alone, what their
rooms exist for. The rooms land as narrative homes for commands the world
already has (rest, sleep, practice, talk, invite): the inn offers paid lodging
through its existing host, while no drink effect or bathing mechanic is
invented, because the source document leaves those two unproposed.

## Requirements

### Requirement: The capital has a tavern, an inn and a bathhouse
The capital SHALL carry three hospitality locations, a tavern, an inn and a public bathhouse, each a permanent interior. Staffing and authored host identity SHALL follow each current place declaration. The inn and tavern SHALL share one exterior, because an inn lane with both on it is one street.

#### Scenario: All three exist and are enterable
- **WHEN** synchronization completes
- **THEN** each of the three interiors exists once, is reachable both ways and contains exactly its declared dialogue-capable staffing

### Requirement: A hospitality location adds no mechanism it does not have
The capital inn SHALL offer paid lodging through its existing host and authored lobby as defined by `inn-lodging`. The tavern and bathhouse SHALL NOT introduce drink, gambling, or bathing effects, charges, or persisted fields. All three places SHALL follow `city-sleep-policy`; awake rest, practice, conversation, and party invitation retain their existing rules.

#### Scenario: No new command or persisted state arrives with the rooms
- **WHEN** the player requests lodging from each of the three hospitality hosts
- **THEN** only the inn can quote and confirm lodging; the tavern and bathhouse add no command and create no lodging state

#### Scenario: Resting in the inn is resting anywhere
- **WHEN** the player rests awake or practises in a hospitality interior
- **THEN** the same awake settlement and cost apply as elsewhere without a hospitality charge or effect

### Requirement: Each host's dialogue teaches what its location is for
A hospitality host's dialogue SHALL tell, in the host's own in-world voice, what its location is
for, so the location's purpose is discoverable by talking to the person standing in it. The
dialogue SHALL stay in character: it SHALL NOT name a command, a game mechanic, or an interface
element, and SHALL describe the activity the world offers (resting, sleeping, quiet practice,
conversation, finding a travelling companion) rather than how a player performs it.

#### Scenario: Talking to a hospitality host surfaces its affordances
- **WHEN** a player talks to every declared hospitality host
- **THEN** dialogue describes the unchanged purpose of its location: inn resting/sleeping/practice, tavern conversation/companions and bathhouse separated sides

#### Scenario: No hospitality line breaks character
- **WHEN** every current hospitality greeting and keyword response is inspected
- **THEN** none names commands, game mechanics or interface elements
