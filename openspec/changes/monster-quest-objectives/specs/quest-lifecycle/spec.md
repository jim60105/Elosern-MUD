## MODIFIED Requirements

### Requirement: accept_quest creates one deterministic active record
`accept_quest(actor, definition_key, issuer_key)` SHALL reject an unknown definition, reject when the
actor already has an active record for that definition, and reject when
`resolve_issuance(definition_key, issuer_key)` returns no issuance — a record SHALL never be created
pointing at a commission that does not exist. Otherwise it SHALL create an `IN_PROGRESS` stage-zero
record carrying the supplied `issuer_key`, whose deterministic `quest_id` uses the definition key and
that character's next acceptance number, whose `accepted_tick` is the current world tick, and whose
`deadline_tick` is either `None` or the accepted tick plus the definition's positive hours converted
with `CLOCK_YAML`.
When the definition's current stage is a regional species hunt, acceptance SHALL additionally require
that enough reachable, living, ordinary-eligible target individuals exist within the objective's
declared region to satisfy the quantity. The deterministic core SHALL obtain that guarantee through the
existing ambient/site managers — never by creating, moving, or deleting individuals directly — and those
managers SHALL honor habitat, authored placement capacity, ownership markers, and current site state:
provisioning SHALL NOT rebuild existing eligible individuals and SHALL NOT early-recover a cleared site.
Provisioning and record creation SHALL form one all-or-nothing transaction: any validation or manager
failure SHALL roll back both, leaving no active record and no partial target arrangement. When the
condition cannot be legally satisfied, acceptance SHALL be refused with a named reason before any
persistence.

#### Scenario: First acceptance succeeds
- **WHEN** a character accepts a known definition under a registered issuance with no previous record
  for it
- **THEN** one stage-zero `IN_PROGRESS` record is stored with quest ID `<definition-key>:1` and the
  supplied issuer key

#### Scenario: Duplicate active acceptance is rejected
- **WHEN** the character accepts a definition for which an `IN_PROGRESS` record already exists
- **THEN** `QuestAlreadyActive` is raised and the quest log is unchanged

#### Scenario: Acceptance under an unregistered issuance is rejected
- **WHEN** a character accepts a known definition naming an issuer key with no registered issuance
- **THEN** acceptance raises a named error and the quest log is unchanged

#### Scenario: Terminal quest may be retried deterministically
- **WHEN** the previous record for a definition is `COMPLETED` or `FAILED` and the character accepts it
  again
- **THEN** a new active record is stored with the next acceptance number and the terminal history is
  retained

#### Scenario: Explicit deadline is converted to ticks
- **WHEN** a definition with `deadline_hours=72` is accepted at tick T
- **THEN** its deadline is `T + 72 * CLOCK_YAML["seconds_per_hour"]`

#### Scenario: No-deadline definition remains without a deadline
- **WHEN** a definition with `deadline_hours=None` is accepted
- **THEN** the record's `deadline_tick` is `None`

#### Scenario: The same definition can be held twice under different issuers
- **WHEN** a character completes a definition issued by a guild branch and later accepts the same
  definition from a private commissioner
- **THEN** the new record carries the private issuer key while the terminal record retains the guild
  issuer key

#### Scenario: Species-hunt acceptance guarantees ordinary-eligible targets
- **WHEN** a species hunt is accepted and the region already holds enough reachable living ordinary-eligible individuals
- **THEN** acceptance succeeds without the manager creating anything

#### Scenario: Provisioning fills a shortfall through its owner only
- **WHEN** a species hunt needs more ordinary-eligible targets than currently live in the region and placement capacity permits more
- **THEN** the ambient/site owner provisions the difference within its capacity and ownership rules, and the hunt accepts in the same transaction

#### Scenario: An illegal hunt is refused with no partial state
- **WHEN** provisioning cannot legally satisfy the quantity — capacity full, ownership blocked, or the only source a cleared site whose recovery condition is not due
- **THEN** acceptance is refused with a named reason, and a database before/after comparison shows neither a quest record nor any created or moved individual

## ADDED Requirements

### Requirement: Bound-stage bindings survive every substitution attempt
For a bound-target stage, the record's `objective_target_ids` SHALL be the complete set of individuals
whose defeat counts. Individuals of the same species at other locations, ordinary ambient respawns, and
fresh individuals from a recovered site SHALL never satisfy those bindings, regardless of matching
species or variant identity. A recovered site's newcomers can only ever be referenced by bindings made
after their creation; site recovery state and quest republish decisions SHALL remain mutually
consistent.

#### Scenario: A recovered site's newcomers do not clear an old hunt
- **WHEN** a bound clearing quest is active, its bound individuals were defeated, and its site later recovers fresh individuals
- **THEN** the old record's progress does not advance from the newcomers, and any newly issued quest binds the newcomers as its own fresh targets

#### Scenario: Ambient respawns never substitute
- **WHEN** an ambient individual of the same species and variant dies while a bound stage is active
- **THEN** the bound stage's progress is unchanged
