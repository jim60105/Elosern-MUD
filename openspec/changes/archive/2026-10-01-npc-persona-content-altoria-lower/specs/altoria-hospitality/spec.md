## MODIFIED Requirements

### Requirement: Each host's dialogue teaches what its location is for
A hospitality host's dialogue SHALL tell, in the host's own in-world voice, what its location is
for, so the location's purpose is discoverable by talking to the person standing in it. The
dialogue SHALL stay in character: it SHALL NOT name a command, a game mechanic, or an interface
element, and SHALL describe the activity the world offers (resting, sleeping, quiet practice,
conversation, finding a travelling companion) rather than how a player performs it.

#### Scenario: Talking to a hospitality host surfaces its affordances
- **WHEN** a player talks to each of the three hosts
- **THEN** the innkeeper's lines speak of resting, sleeping and practising, the tavern keeper's
  speak of conversation and inviting a travelling companion, and the bathhouse keeper's explain
  the separated sides

#### Scenario: No hospitality line breaks character
- **WHEN** the three hosts' greetings and keyword responses are inspected
- **THEN** none contains a backticked command token or a command name
