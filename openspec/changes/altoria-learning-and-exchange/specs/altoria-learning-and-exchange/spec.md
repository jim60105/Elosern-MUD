## ADDED Requirements

### Requirement: The capital has an academy, a merchant hall and covered market stalls
The capital SHALL carry these three locations as permanent interiors. The academy and the
merchant hall SHALL each hold one authored host who converses; the market stalls SHALL hold
none, and SHALL still be a complete, enterable, permanently tagged room reachable from and
back to its exterior. The stalls are host-less by design, not by omission: the source document
states that a market street's trade hangs on individual stallholders rather than on a fixed
functional NPC.

#### Scenario: Three locations exist, two of them staffed
- **WHEN** synchronization completes
- **THEN** all three interiors exist once and are reachable both ways, the academy and the
  merchant hall each hold one dialogue-carrying host, and the stalls hold no service host

### Requirement: The academy is where magical knowledge is asked about
The academy host's dialogue SHALL answer on the world's magic-rank and element vocabulary, so
that the academy functions as the capital's designated place to learn about magic by asking
rather than by reading documentation outside the game.

#### Scenario: The academy host answers on ranks and elements
- **WHEN** a player talks to the academy host about magic ranks and about elements
- **THEN** authored responses are returned for both

### Requirement: Neither location implements the system it is the future home of
The academy SHALL NOT introduce an apprenticeship, tutoring or skill-purchase path: skill
acquisition runs through proficiency accumulation in the lineage tree, and mentorship is
narrative framing. The merchant hall SHALL NOT introduce escort commissions, a caravan
board, or any work-offering surface: escort work requires a quest type that does not exist.
Landing either room SHALL NOT be treated as licence to land the system it anticipates.

#### Scenario: No skill may be acquired by talking to the academy
- **WHEN** the academy host and its room are inspected for skill-granting capability
- **THEN** none exists, and no new command grants or teaches a skill

#### Scenario: No commission surface arrives with the merchant hall
- **WHEN** the merchant hall and its host are inspected for quest-offering capability
- **THEN** the host carries no quest-issuer component and no new work-listing command exists
