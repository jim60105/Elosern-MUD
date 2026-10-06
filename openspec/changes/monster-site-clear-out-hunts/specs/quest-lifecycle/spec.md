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
When the definition's current stage is a bound clear-out over an authored site, acceptance SHALL
additionally require that the site currently owns at least the objective's quantity of living
individuals. That guarantee SHALL be a read of the site owner's own state and population — acceptance
SHALL NOT create, populate, move, recover, or delete an individual, and a site the world has not yet
populated SHALL refuse exactly as a cleared one does. The site's durable lifecycle state SHALL be the
sole answer: a one-shot site already cleared and a cleared recoverable site whose authored in-game
condition has not matured each refuse with their own named reason, and no path SHALL early-recover a
site. When the guarantee holds, acceptance SHALL bind exactly the site's living individuals as the
record's stage-zero objective targets through the existing binding writer, inside the same all-or-nothing
transaction as the record write, and SHALL create no instance pin: the site is a permanent wilderness
location, not a spawned scene.
Guarantee, binding, and record creation SHALL form one all-or-nothing transaction: any validation or
manager failure SHALL roll back all of them, leaving no active record, no binding, and no partial target
arrangement. When the condition cannot be legally satisfied, acceptance SHALL be refused with a named
reason before any persistence.

#### Scenario: First acceptance succeeds
- **WHEN** a character accepts a known definition under a registered issuance with no previous record
  for it
- **THEN** one stage-zero `IN_PROGRESS` record is stored with quest ID `<definition-key>:1` and the
  supplied issuer key

#### Scenario: Duplicate active acceptance is rejected
- **WHEN** the character accepts a definition for which an `IN_PROGRESS` record already exists
- **THEN** `QuestAlreadyActive` is raised and the quest log is unchanged

#### Scenario: Acceptance under an unregistered issuance is rejected
- **WHEN** the character accepts a known definition naming an issuer key with no registered issuance
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

#### Scenario: A standing site clear-out binds the site's own individuals
- **WHEN** a clear-out is accepted while the site owns at least the required living individuals
- **THEN** the new record's objective target set is exactly those individuals, the record carries no instance pin, and the site's own individuals are unchanged in number

#### Scenario: A cleared one-shot site refuses permanently
- **WHEN** a clear-out over a cleared one-shot site is accepted
- **THEN** acceptance is refused with the site-cleared reason, and the quest log, the site's durable state, and every individual it owns equal their pre-acceptance values

#### Scenario: A due recoverable site is bound only after it has recovered
- **WHEN** a clear-out over a cleared recoverable site is accepted before its authored in-game condition matures
- **THEN** acceptance is refused with its named reason, no individual is created, and the site's cleared state is unchanged

#### Scenario: Acceptance never populates a site
- **WHEN** a clear-out is accepted against a site the world has not yet populated
- **THEN** acceptance is refused, and a before/after comparison shows the site still unpopulated with no individual created for it
