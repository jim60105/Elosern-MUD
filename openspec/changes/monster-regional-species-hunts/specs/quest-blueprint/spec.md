## ADDED Requirements

### Requirement: Published regional species hunts are legally provisionable in their authored region
A published regional species hunt SHALL be provisionable by the region's own authored placement: the hunt's
region SHALL have an ambient placement rule, at least one of the hunt's ordinary countable variants SHALL
be in that rule's eligible variant set (otherwise the acceptance-time guarantee could only ever refuse),
and the hunt's required quantity SHALL NOT exceed the region's authored per-coordinate legal supply —
`min(quantity, capacity)` of that rule. A region with no authored ambient placement SHALL carry no
regional hunt, because such a hunt could never be satisfied and the board is not an inventory of
impossible work. The shipped catalog SHALL carry exactly one regional hunt per species that a
placement-covered region actually places. This is a property of published content, not a promise that
every acceptance succeeds: the acceptance-time guarantee still refuses with its named reason when the
world is not provisioned or the region's authored capacity is momentarily exhausted.

#### Scenario: Every published hunt can be provisioned by its region
- **WHEN** each published regional hunt is compared against its region's authored ambient placement rule
- **THEN** the rule exists, at least one ordinary countable variant is eligible in it, and the hunt's quantity is at or below `min(quantity, capacity)`

#### Scenario: A region without authored placement carries no regional hunt
- **WHEN** the shipped catalog is inspected for a hunt naming a region that has no ambient placement rule
- **THEN** none exists, and the region's species presence is expressed only through its authored site content

#### Scenario: A hunt beyond the region's legal supply is not published
- **WHEN** a hunt's quantity exceeds its region's authored per-coordinate legal supply
- **THEN** the content contract reports it rather than letting the board offer work whose guarantee must refuse

#### Scenario: One hunt per placed species in a covered region
- **WHEN** a placement-covered region's ambient rule names variants of two species
- **THEN** the shipped catalog carries one hunt for each of them, each naming its own species and the countable variants that species owns

### Requirement: Every shipped hunt carries authored rank, rating rationale, background flavor, and a rank-banded reward
Every published hunt SHALL carry an authored guild rank, an authored rating rationale describing the risk
the arrangement, numbers, or terrain create, an authored background flavor describing the issuer's
motivation and local events, and a hand-written reward whose copper lies inside the rank's own reward band
in the guild-economy rulebook. The rank SHALL be authored for the arrangement and SHALL NOT be derived
from a targeted variant's individual danger grade: a run of hunts whose strongest countable or bound
individual is graded above the hunt's rank SHALL remain lawful and unchanged. The prose fields SHALL
describe effects and risks that actually exist in play and SHALL NOT assert an effect of a special ability
that has no mechanics.

#### Scenario: A hunt offers a reward inside its rank band
- **WHEN** each published hunt's registered guild offer is checked against its definition's rank
- **THEN** the reward copper lies inside that rank's reward band and the offer registers at the branch as an ordinary guild commission

#### Scenario: The rank is authored, not inherited from a danger grade
- **WHEN** a published hunt's countable or bound individuals carry a danger grade above the hunt's own rank
- **THEN** the hunt keeps its authored rank for board eligibility, reward band, and rendering

#### Scenario: Shipped prose asserts no unimplemented ability
- **WHEN** the published hunts' rating rationales and background flavors are inspected
- **THEN** they cite composition, numbers, and terrain, and none of them claims a special ability effect that has no executable mechanics

#### Scenario: The prose stays inside the rendered-detail budget
- **WHEN** every published hunt's rationale and flavor are validated at registration
- **THEN** each is bounded Traditional Chinese prose and the pair fits the shared rendered-detail budget
