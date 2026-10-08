## Purpose

Define author complete persistent hok, cassandra and augustine adventurers with real homes and routines as observable deterministic behavior with explicit rejection and acceptance boundaries.

## ADDED Requirements

### Requirement: Altoria qualifications select one persistent adventurer per branch and target
The qualification registry SHALL map guild_branch_altoria E/D/C/B to Hok B, A to Cassandra A and S to Augustine S, using authored and persistent identities. Profession SHALL be adventurer with separate exam authority. Missing, duplicate or wrong-branch bindings SHALL fail closed. Synchronization SHALL reuse the same person without overwriting live ordinary state.

#### Scenario: Different qualified hosts co-locate
- **WHEN** three differently qualified hosts stand at the guild
- **THEN** target A selects Cassandra without generic component ambiguity

#### Scenario: Missing binding
- **WHEN** a new branch lacks its own senior
- **THEN** no Altoria fallback is selected

#### Scenario: Repeat sync
- **WHEN** an authored host has moved and edited its persona
- **THEN** sync retains dbref/location and mutable state

### Requirement: Normal hosts own literal bases gear and usable complete human skill lineages
Hosts SHALL use approved section 3/4.3 normal bases and canonical ages, actual rank-matched military gear and full learned utility/sword prerequisite ownership and proficiency. Hok SHALL retain coastal literal inputs without reapplying subrace modifiers, normal physical reference 25/20/29, age 45 and nearshore/escort/hunt identity. Cassandra SHALL retain 40/40 and Augustine 68/52. Cards/dialogue SHALL match implemented capabilities with no fire-sword/far-ocean claims or OOC speech.

#### Scenario: Usable top lineage
- **WHEN** a normal synthetic qualified adventurer requests its top sword skill
- **THEN** required lower ownership/proficiency is present and resolver accepts it

#### Scenario: Invalid age or unsupported item
- **WHEN** authored profile ages are boolean/out-of-range or gear is unregistered
- **THEN** preflight rejects before creation

### Requirement: Hosts live in connected residences and traverse authored recurring guild visits
Each host SHALL have a real connected residence and resolved routine route using ordinary place/movement systems. Hok SHALL have morning/evening daily guild visits; Cassandra and Augustine SHALL each have one fixed interval per seven-day cycle. Exact offsets SHALL live in NPC schedule data. Maps SHALL own residence materialization and real Exits SHALL govern travel.

#### Scenario: Residence route
- **WHEN** normal departure and return occurrences settle
- **THEN** the host traverses actual connected Exits between residence and guild with no holding-room teleport

#### Scenario: Locked weekly arrival
- **WHEN** an arrival Exit is locked
- **THEN** the host remains absent and cannot host the exam

