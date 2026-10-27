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

#### Scenario: Mainland control polygon
- **WHEN** an irregular mainland is loaded from explicitly labelled kilometre vertices
- **THEN** geometry uses its declared closed boundary and independently tested polygon/cell-centre rules; source conversion preserves existing vertices through temporary comparison

#### Scenario: Nine geographic anchors
- **WHEN** discovered locations are loaded and resolved by stable identity
- **THEN** every declared geographic cell remains available without room spawning or knowledge revelation; roster size is authored data rather than a fixed-count assertion

#### Scenario: Six reserved harbor sites
- **WHEN** reserved geographic sites are loaded from the continent document
- **THEN** each uses its declared cell and role without creating a named location, settlement, quest or population; the source owns membership rather than a specification-owned count

