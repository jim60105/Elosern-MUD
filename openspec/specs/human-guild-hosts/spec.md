# human-guild-hosts Specification

## Purpose
Define author complete persistent hok, cassandra and augustine adventurers with real homes and routines as observable deterministic behavior with explicit rejection and acceptance boundaries.

## Requirements

### Requirement: Altoria qualifications select one persistent adventurer per branch and target
The qualification registry SHALL select one authored persistent adventurer per branch and target rank. Missing, duplicate, wrong-branch or insufficient-rank bindings SHALL fail closed. Profession SHALL remain adventurer with separate exam authority. Person identity and qualification membership SHALL remain data; synchronization SHALL reuse the same person without overwriting live ordinary state.

#### Scenario: Different qualified hosts co-locate
- **WHEN** multiple differently qualified persistent hosts stand at the guild
- **THEN** the requested target selects its registry-bound person without generic component ambiguity

#### Scenario: Missing binding
- **WHEN** a new branch lacks its own senior
- **THEN** no Altoria fallback is selected

#### Scenario: Repeat sync
- **WHEN** an authored host has moved and edited its persona
- **THEN** sync retains dbref/location and mutable state

#### Scenario: Occupied key at persistent creation
- **WHEN** another live entity holds the authored person's key before normal host creation
- **THEN** one host is created with its own primary-key suffix and stable person provenance, and later sync/exams reuse its key/dbref without renaming

### Requirement: Normal hosts own literal bases gear and usable complete human skill lineages
Hosts SHALL use complete authored normal bases and canonical ages, rank-matched military gear and full learned utility/sword prerequisite ownership and proficiency. Subrace modifiers SHALL NOT be reapplied to authored final bases. Person-specific biography, gear membership and lineage choices SHALL remain data. Cards/dialogue SHALL reflect implemented capabilities without unsupported claims or OOC speech.

#### Scenario: Persistent normal configuration
- **WHEN** a host enters and exits an examination
- **THEN** the existing host row and normal bases, owned lineage, gear and identity survive restoration; normal values are compared to the pre-exam snapshot rather than historical numerical pins, and references and real construction/restoration are validated without duplicated base-stat or age tables

#### Scenario: Usable top lineage
- **WHEN** a normal synthetic qualified adventurer requests its top sword skill
- **THEN** required lower ownership/proficiency is present and the resolver accepts execution

#### Scenario: Invalid age or unsupported item
- **WHEN** authored profile ages are boolean/out-of-range or gear is unregistered
- **THEN** preflight rejects before creation, preserving the existing 0..10000 age bound

### Requirement: Hosts live in connected residences and traverse authored recurring guild visits
Each persistent host SHALL have a real connected residence and resolved recurring guild-visit route using ordinary place/movement systems. Person-specific visits, cadence and offsets SHALL remain authored schedule data. Maps SHALL own residence materialization and real Exits SHALL govern travel; schedules SHALL NOT teleport people to satisfy an examination.

#### Scenario: Residence route
- **WHEN** normal departure and return occurrences settle
- **THEN** the host traverses actual connected Exits between residence and guild with no holding-room teleport

#### Scenario: Locked weekly arrival
- **WHEN** an arrival Exit is locked
- **THEN** the host remains absent and cannot host the exam
