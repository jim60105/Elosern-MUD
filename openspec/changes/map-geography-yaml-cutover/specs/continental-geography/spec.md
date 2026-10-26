# Spec Delta

## MODIFIED Requirements

### Requirement: The known continent has frozen geographic declarations
Geographic consumers SHALL read immutable continent and location values from the shared map source while non-map demographic declarations retain their existing authority.

#### Scenario: Mainland and reserved sites
- **WHEN** a synthetic irregular mainland with reserved geographic sites is loaded
- **THEN** geometry uses its declared kilometre frame and sites create no settlement, population or knowledge

#### Scenario: Location without a local map
- **WHEN** a known location has no settlement document
- **THEN** its geographic identity remains available without fabricating local content

