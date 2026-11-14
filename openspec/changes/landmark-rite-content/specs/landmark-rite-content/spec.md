# Spec Delta

## ADDED Requirements

### Requirement: The shipped rite document is adopted against the published districts
Adopting the shipped rite document SHALL validate it against the district keys of the published district world and install the resulting snapshot. A rejected or unreadable document SHALL raise, SHALL install nothing and SHALL leave any previously installed snapshot current.

#### Scenario: Valid document
- **WHEN** a valid synthetic document is adopted against a synthetic set of district keys
- **THEN** the returned snapshot is the current snapshot

#### Scenario: Invalid document
- **WHEN** a document that leaves one district unassigned is adopted while another snapshot is current
- **THEN** the rejection is raised and the other snapshot is still current

#### Scenario: Missing document
- **WHEN** adoption is pointed at a path that does not exist
- **THEN** it raises and no snapshot is installed

#### Scenario: Shipped document
- **WHEN** the shipped rite document is loaded against the district keys of the shipped district document
- **THEN** it loads and assigns exactly those districts
