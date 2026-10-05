## MODIFIED Requirements

### Requirement: Automatic generation is idempotent against the subject's gallery
An automatic path SHALL request a generation only when the subject's gallery holds no card AND no
gallery job for that subject is in flight AND — for an entity whose official content reference is
eligible and already satisfied by a valid catalog entry in the startup official snapshot (see the
`official-art-resolution` capability) — no official default resolves for it. A subject that already
holds any card — generated, seed-synced, or player-kept — SHALL be left alone. This SHALL hold across
restarts, so repeated startup recovery and repeated startup synchronization never stack duplicate
cards, and across quests, so a `stable_key` shared by several scenes yields exactly one
auto-generated card. The guard SHALL be the
same one for every gallery-bearing kind, so a monster tier is protected by exactly the rule a character
subject is — which is also what keeps a capped kind from replacing its one card on every restart. A
suppressed automatic request SHALL leave no record and enqueue nothing; the entity presents the
official default through the presentation chain, and updating the official directory later does not
retroactively enqueue the suppressed subject.

#### Scenario: Repeated recovery appends nothing
- **WHEN** startup recovery runs on consecutive restarts for a subject that already holds one card
- **THEN** no additional generation is requested and the gallery still holds one card

#### Scenario: Repeated startup synchronization never replaces a monster card
- **WHEN** startup synchronization runs on consecutive restarts for a monster tier that already holds its one card
- **THEN** no generation is requested, the existing card is not replaced, and its stored file is untouched

#### Scenario: A seed-synced subject is not auto-generated
- **WHEN** an automatic path runs for a subject whose only card came from seed synchronization
- **THEN** no generation is requested

#### Scenario: An in-flight job suppresses a second request
- **WHEN** an automatic path runs for a subject whose gallery job is already pending or in progress
- **THEN** no second job is enqueued

#### Scenario: Satisfying official artwork suppresses the initial automatic generation
- **WHEN** a preset-born character activates with an empty gallery while its preset content reference resolves a valid official default
- **THEN** no gallery generation is enqueued, the character still carries its named portrait policy, and it presents the official default

#### Scenario: An ineligible or unsatisfied reference does not suppress
- **WHEN** an automatic path runs for an entity with no content reference, or one the snapshot does not hold
- **THEN** the existing automatic request proceeds exactly as today

#### Scenario: Manual generation remains available after suppression
- **WHEN** an entity whose automatic generation was official-suppressed is later requested through the manual gallery generation seam
- **THEN** the request is served through the existing seam and settles a runtime card that then outranks the official default
