## MODIFIED Requirements

### Requirement: A puppet change carries no session-scoped state across characters
A transition performed by an account-scoped action SHALL leave the retiring character's
session-scoped presentation state behind: the previous character's transient creation concept
proposal, and its completed-result cache and in-flight marker SHALL NOT be visible to or reusable
by the new puppet. Per-character persistent state SHALL remain on the character it belongs to and
SHALL be unchanged by the switch.

#### Scenario: The new puppet inherits no suggestion state
- **WHEN** a player switches to another character after a committed action-suggestion era state had existed on the session
- **THEN** no client surface carries a suggestion card, a suggestion fingerprint, or a dismissal barrier from the previous character, because the retired suggestion state is never written and the switch clears every session-scoped slice

#### Scenario: An in-flight generation cannot cross the switch
- **WHEN** a deferred generative reply started for the previous character settles after the switch completes
- **THEN** it publishes no panel state or result into the new character's sequence

#### Scenario: Per-character persistent state stays with its character
- **WHEN** a player switches away from a character holding quest progress and a party binding, and
  later switches back
- **THEN** that character's quest progress and party binding are unchanged

#### Scenario: An in-flight generation for the old character publishes nowhere
- **WHEN** a generation is still in flight for the previous character when the switch lands
- **THEN** it publishes nothing into the new sequence

#### Scenario: Dialogue sessions are persistent per-character state
- **WHEN** a player switches away from a character holding a dialogue session
- **THEN** the dialogue session — like party and companion bindings and quest progress — remains on the character it belongs to, unchanged by the switch
