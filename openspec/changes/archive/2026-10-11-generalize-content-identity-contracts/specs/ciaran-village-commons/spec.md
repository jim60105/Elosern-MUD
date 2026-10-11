# Spec Delta

## MODIFIED Requirements

### Requirement: The village has a communal shelter, a sword instructor and an elder
The village SHALL carry a communal shelter, a sword instructor's dwelling and an elder's dwelling as complete, enterable tagged locations reachable both ways. Staffing and host identity SHALL follow current place declarations. The instructor's dwelling SHALL share the training ground's exterior with the blade-smith's. Staffing changes SHALL NOT introduce the excluded institutions, counters or guild work.

#### Scenario: Three locations exist, two of them with someone in them
- **WHEN** synchronization completes
- **THEN** all three interiors exist once and remain reachable both ways; every declared dialogue host exists and declared hostless records create none

#### Scenario: The training ground carries two dwellings
- **WHEN** the training ground's exterior is inspected
- **THEN** it holds one doorway per dwelling and each leads back to it
