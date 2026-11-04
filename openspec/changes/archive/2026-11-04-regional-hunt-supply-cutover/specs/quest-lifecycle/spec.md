# Spec Delta

## REMOVED Requirements

### Requirement: accept_quest creates one deterministic active record
**Reason**: Regional acceptance supply guarantees are deliberately retired; preserved issuance, escort, binding, deadline and atomicity scenarios remain in the replacement contract.

**Migration**: Cut all callers and substantively matching test annotations to the replacement contract using tool-generated canonical IDs; retain no legacy behavior, alias or data migration.

## ADDED Requirements

### Requirement: Quest acceptance persists validated records without ordinary provisioning
Acceptance SHALL validate issuance, lawful hunt sources and exact standing site or escort bindings, then atomically persist deterministic quest metadata and owned binding, membership and knowledge effects without ordinary target provisioning.

#### Scenario: Acceptance returns the committed bound record
- **WHEN** an authorized available multi-role escort is accepted at full general quota
- **THEN** the returned record equals a fresh read, binds every exact published protected actor and commits unique reasons and acceptance sequence together

#### Scenario: Acceptance refuses a partial protected roster
- **WHEN** any required actor is dead, missing, remote, substituted, or owned by another player
- **THEN** the named refusal creates no record, source reason, authority change or partial roster

#### Scenario: Stale capability or resolved group refuses acceptance
- **WHEN** an old offer is submitted after its phase or exclusive outcome has changed
- **THEN** acceptance returns `offer_stale` or `outcome_resolved` without retroactive record creation

#### Scenario: Acceptance faults restore all surfaces
- **WHEN** failures are injected after record, binding, membership and dialogue writes
- **THEN** database reload and live caches match baseline and no acceptance event is committed

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
- **WHEN** a previous unrelated record is completed or failed and the definition remains currently available
- **THEN** existing next-number acceptance retains terminal history; a resolved exclusive alternative instead refuses with outcome_resolved

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
- **THEN** acceptance is refused with the not-yet-populated reason, and a before/after comparison shows the site still unpopulated with no individual created for it

#### Scenario: The returned record carries the binding
- **WHEN** a clear-out acceptance succeeds
- **THEN** the returned record's objective target set equals the site's living individuals that were bound, the same set a fresh read of the quest log returns, and a rollback of an injected failure restores the log to its pre-acceptance value

#### Scenario: The new record carries deterministic acceptance metadata
- **WHEN** accept_quest creates a record
- **THEN** its deterministic `quest_id` uses the definition key and that character's next acceptance number
- **AND** its `accepted_tick` is the current world tick
- **AND** its `deadline_tick` is either `None` or the accepted tick plus the definition's positive hours converted with `CLOCK_YAML`

#### Scenario: Clear-out acceptance reads the site's own population
- **WHEN** the definition's current stage is a bound clear-out over an authored site
- **THEN** acceptance additionally requires that the site currently owns at least the objective's quantity of living individuals
- **AND** that guarantee is a read of the site owner's own state and population — acceptance does not create, populate, move, recover, or delete an individual

#### Scenario: The site's durable state is the sole answer
- **WHEN** clear-out acceptance consults the site
- **THEN** the site's durable lifecycle state is the sole answer — world absent, unknown site, never populated, cleared, or short — and no path early-recovers a site
- **AND** a site the world has not yet populated refuses with its own named reason, distinct from both a cleared site and a shortfall

#### Scenario: A satisfied guarantee binds exactly the site's individuals
- **WHEN** the clear-out guarantee holds
- **THEN** acceptance binds exactly the site's living individuals as the record's stage-zero objective targets through the existing binding writer, inside the same all-or-nothing transaction as the record write, and creates no instance pin: the site is a permanent wilderness location, not a spawned scene

#### Scenario: The refusal vocabulary is closed and named
- **WHEN** clear-out acceptance refuses
- **THEN** the reason is one of `world_unavailable`, `unknown_site`, `site_unpopulated`, `site_cleared`, and `site_short`

#### Scenario: Acceptance is one all-or-nothing transaction
- **WHEN** standing-site validation, binding, and record creation run
- **THEN** they form one all-or-nothing transaction: any validation or owner-write failure rolls back all of them, leaving no active record, no binding, and no partial target arrangement
- **AND** when the condition cannot be legally satisfied, acceptance is refused with a named reason before any persistence

#### Scenario: The returned record is the persisted bound record
- **WHEN** a binding acceptance completes
- **THEN** the record the operation returns is the persisted, bound record rather than the unbound value written a moment earlier

#### Scenario: Acceptance fault, quota and retry behavior
- **WHEN** an escort acceptance writes, joins at full general quota, or is retried
- **THEN** Any later write failure SHALL restore quest, party, component and dialogue caches. Full general quota SHALL permit temporary joining, terminal retry SHALL remain allowed for unrelated definitions under existing rules, and resolved exclusive alternatives SHALL refuse every retry.

#### Scenario: Undersupplied hunt accepts without birth
- **WHEN** a valid source-backed regional hunt is accepted with zero or fewer living targets than its quantity
- **THEN** one normal active record commits with the existing deadline and no population/registration/due/sequence write; completing it may span encounters and waves

