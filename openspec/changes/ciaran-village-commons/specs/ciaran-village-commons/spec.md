## ADDED Requirements

### Requirement: The village has a communal shelter, a sword instructor and an elder
The village SHALL carry these three locations. The shelter SHALL hold no host and SHALL still
be a complete, enterable, permanently tagged room reachable from and back to its exterior. The
instructor and the elder SHALL each hold one authored host who converses. The instructor's
dwelling SHALL share the training ground's exterior with the blade-smith's.

#### Scenario: Three locations exist, two of them with someone in them
- **WHEN** synchronization completes
- **THEN** all three interiors exist once and are reachable both ways, the instructor's and
  the elder's each hold one dialogue-carrying host, and the shelter holds none

#### Scenario: The training ground carries two dwellings
- **WHEN** the training ground's exterior is inspected
- **THEN** it holds one doorway per dwelling and each leads back to it

### Requirement: The village's shared spaces carry no institution and no counter
None of the three SHALL introduce trade, a commission, a permission, a petition, a council
procedure, an access gate or any persisted state. The shelter SHALL sell nothing, because
sharing food between villagers is not a transaction in this culture. The elder SHALL decide
nothing, because the elder council is a symbolic place rather than a working government. The
instructor SHALL teach through the proficiency system that already exists and grant nothing
directly.

#### Scenario: Nothing in the commons can be bought
- **WHEN** a player attempts to trade at any of the three
- **THEN** no merchant capability is found at any of them

#### Scenario: The elder grants no authority and blocks no path
- **WHEN** the elder's host and room are inspected for quest-offering, permission-granting or
  access-gating capability
- **THEN** none exists, and entering her dwelling consults no lock or prerequisite

#### Scenario: No new command or persisted state arrives with the commons
- **WHEN** the command set and the persisted attribute set are compared before and after
- **THEN** they are unchanged
