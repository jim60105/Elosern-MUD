# Spec Delta

## MODIFIED Requirements

### Requirement: Normal hosts own literal bases gear and usable complete human skill lineages
Hosts SHALL use their complete authored normal bases and canonical ages, actual rank-matched military gear and full learned utility/sword prerequisite ownership and proficiency. Hok SHALL retain coastal literal inputs without reapplying subrace modifiers and his nearshore/escort/hunt identity. Cassandra and Augustine SHALL retain their authored normal configurations. Cards/dialogue SHALL reflect implemented capabilities without fire-sword/far-ocean claims or OOC speech.

#### Scenario: Persistent normal configuration
- **WHEN** a host enters and exits an examination
- **THEN** the existing host row and normal bases, owned lineage, gear and identity survive restoration; normal values are compared to the pre-exam snapshot rather than historical numerical pins, and references and real construction/restoration are validated without duplicated base-stat or age tables

#### Scenario: Usable top lineage
- **WHEN** a normal synthetic qualified adventurer requests its top sword skill
- **THEN** required lower ownership/proficiency is present and the resolver accepts execution

#### Scenario: Invalid age or unsupported item
- **WHEN** authored profile ages are boolean/out-of-range or gear is unregistered
- **THEN** preflight rejects before creation, preserving the existing 0..10000 age bound
