## Purpose

Read-only compact character status derived from canonical resources, active conditions, disguise state, and persistent combat-session metadata.

## Requirements


### Requirement: Compact status reports canonical true resources
The available version-1 status panel SHALL contain exactly `schema_version: 1`, `available: true`, `actor`, `resources`, `conditions`, `disguise_active`, and `combat`. `actor` SHALL contain exactly display `name` of 1..256 Unicode code points, opaque correlation `identity` of 1..64 ASCII characters, and nullable `location`; a present location SHALL contain exactly a 1..256-code-point display `label` and 1..64-character opaque `identity`. `resources` SHALL contain exactly `hp`, `mp`, and `sp`, each with non-negative JavaScript-safe integer `current` and positive safe integer `maximum`, with current not exceeding maximum. `conditions` SHALL contain at most 32 entries. `disguise_active` SHALL be boolean, and `combat` SHALL be null or the exact combat object. Resource values SHALL come directly from canonical traits and SHALL never call `get_display_value` or substitute `disguised_stats`. Missing or malformed required traits SHALL produce the common status-unavailable payload rather than fabricated zero values.

#### Scenario: Active disguise does not alter resources
- **WHEN** an actor has true HP 80/100, MP 40/60, SP 30/50 and display-only disguised values for any traits
- **THEN** the status payload reports 80/100, 40/60, and 30/50 and marks `disguise_active` true

#### Scenario: Missing gauge fails closed
- **WHEN** the active puppet lacks a valid required HP, MP, or SP gauge
- **THEN** the status panel is unavailable and does not report zero for the missing resource

### Requirement: Status conditions use deterministic matched modifiers
The deterministic combat-modifier module SHALL expose a read-only query of each currently matched rule ID and its exact adjustment bundle without changing existing merged evaluation. The status presenter SHALL combine that query with active rulebook buff instances and immutable display metadata. Each condition entry SHALL contain exactly stable `code` of 1..64 lowercase dotted or underscored identifier characters, Traditional Chinese `label` of 1..128 code points, `severity` from `beneficial`, `informational`, `warning`, `harmful`, or `critical`, nullable non-negative safe-integer `remaining_seconds`, and `modifiers` with at most 16 stable keys and exact JSON scalar rule values. It SHALL include sexual-state entries only while their canonical combat predicates match.

#### Scenario: Matching buff reports duration and exact adjustment
- **WHEN** an actor has an active poisoned buff with 120 game seconds remaining
- **THEN** status contains the stable poisoned condition with its Traditional Chinese label, harmful severity, 120-second duration, and the exact agility adjustment supplied by the matched deterministic rule

#### Scenario: Sexual threshold appears only while matched
- **WHEN** the actor's canonical arousal state crosses the configured combat-modifier threshold
- **THEN** status contains the matched rule ID and exact agility/accuracy adjustments, and the entry disappears after canonical state no longer matches

#### Scenario: Condition presentation metadata covers current rules
- **WHEN** current buff definitions and combat-modifier rule IDs are compared with the status display registry
- **THEN** every condition that can enter the status payload has one stable Traditional Chinese label and severity

### Requirement: Snapshot mode is derived from canonical puppet state
The coordinator SHALL derive mode as `creation` when the active puppet is creation-pending, otherwise `combat` when it has a valid persistent combat session, and otherwise `exploration`. Status `combat` SHALL be null outside combat and otherwise contain exactly session `mode` from `hostile` or `guild_exam` and non-negative safe-integer `round`. The browser SHALL NOT derive mode from narrative text or local actions.

#### Scenario: Pending creation takes creation mode
- **WHEN** the active puppet has `creation_pending` true
- **THEN** the full snapshot mode is `creation` even though ordinary exploration panels are unavailable

#### Scenario: Active combat reports persisted round
- **WHEN** the active puppet has a valid combat session with three elapsed rounds
- **THEN** the snapshot mode is `combat` and status reports the session mode and round 3

#### Scenario: Ordinary puppet receives exploration mode
- **WHEN** the active puppet is not creation-pending and has no active combat session
- **THEN** the full snapshot mode is `exploration` without combat-round metadata

### Requirement: Server time and location are read-only presentation data
Under the `world-clock` capability's startup and no-create read contract, each full snapshot SHALL obtain calendar data only through the read-only accessor, and status SHALL obtain location display context from the active puppet. Building or rendering either value SHALL NOT create a clock, advance time, move the puppet, settle scheduled stages, or expose a local filesystem path.

#### Scenario: Status read leaves world state unchanged
- **WHEN** the coordinator builds two consecutive full snapshots without an intervening player action
- **THEN** both show the same canonical world time and location and the world tick and puppet location remain unchanged

#### Scenario: Missing clock degrades without persistence
- **WHEN** the clock singleton is unexpectedly absent and a puppeted WebClient requests synchronization
- **THEN** the server emits safe protocol code `presentation_unavailable`, leaves text play available, and creates no Script or other persistent record

### Requirement: Status presentation has no mutation side effects
The deterministic rules layer SHALL provide a frozen no-create status read model that interprets existing persistent trait, optional buff, sexual baseline/materialized state, creation, and combat-session records without constructing a lazy handler that can materialize defaults. The presenter SHALL serialize only that read model. Building status SHALL NOT create or repair traits, materialize an uninitialized sexual baseline, tick gauges or buffs, change sexual state, rewrite a combat record, activate a disguise, or invoke any state-mutating deterministic API. Presenter failure SHALL be isolated under the OOB protocol's unavailable-panel behavior.

#### Scenario: Status construction preserves canonical state
- **WHEN** a status payload is built for an actor with gauges, active buffs, sexual state, disguise data, and combat state
- **THEN** a before/after comparison of every canonical value is equal

#### Scenario: Malformed combat record does not escape presenter isolation
- **WHEN** the actor's persistent combat-session record is malformed
- **THEN** status becomes unavailable with a correlation ID logged and narrative plus other registered presentation remains usable

#### Scenario: Unmaterialized sexual baseline remains unmaterialized
- **WHEN** a valid actor has baseline sexual data but no materialized sexual trait handler and status is built
- **THEN** matching presentation state is interpreted in memory and no sexual trait Attribute is created

### Requirement: The no-create status read model resolves the derived arousal level from stored pleasure, not a raw arousal key
`world/rules/status_query.py::_sexual_condition_context()` SHALL resolve its `"arousal"` context
entry from the persisted `pleasure` counter's stored value (via the same band lookup
`SexualState.arousal` uses at read time), for any entity whose `sexual_traits` handler has been
materialized, rather than from a raw `"arousal"` key — which SHALL NOT exist in that storage once an
entity's `SexualState` has been built. For an entity whose handler has never been materialized, this
path SHALL still read `"arousal"` as a level string from the entity's frozen import-time baseline
Attribute, exactly as before this capability's amendment — preserving "Unmaterialized sexual baseline
remains unmaterialized" without modification. This resolution SHALL NOT read `entity.sexual`,
construct a `TraitHandler`, or otherwise materialize any persistent state, matching "Status
presentation has no mutation side effects"'s existing no-create discipline.

This requirement exists so that "Sexual threshold appears only while matched"'s existing, unmodified
scenario — the sexual condition entry appears and disappears as the actor's *canonical* arousal state
crosses and re-crosses the configured threshold — continues to hold true once `pleasure` (not a
directly-stored `arousal` level) is the canonical quantity: without this resolution, a materialized
entity's status entry would freeze at its import-time baseline and stop tracking canonical state
entirely, silently violating that scenario.

#### Scenario: The status panel reflects live pleasure on a materialized entity
- **WHEN** an entity's `SexualState` has been materialized and its `pleasure` has since been raised at
  runtime past the `高度` band's floor, and a status payload is built for that entity without first
  reading `entity.sexual` directly
- **THEN** the status payload's `conditions` include the `high_arousal_agility_accuracy_penalty`
  entry with its Traditional Chinese label and exact `agility`/`accuracy` adjustments

#### Scenario: The status panel's sexual entry disappears again as canonical state changes
- **WHEN** a status payload is built for a materialized entity whose `pleasure` is within the `高度`
  band (condition present), `pleasure` is then reduced below that band's floor by any canonical path,
  and a second status payload is built
- **THEN** the second payload's `conditions` no longer include the sexual-threshold entry — matching
  the shipped "Sexual threshold appears only while matched" scenario's existing "disappears after
  canonical state no longer matches" behaviour, now driven by `pleasure` rather than a directly-stored
  `arousal` level

#### Scenario: An unmaterialized entity's status still resolves from its import baseline, and remains unmaterialized
- **WHEN** a valid actor has import-time baseline sexual data but no materialized `sexual_traits`
  handler, and a status payload is built
- **THEN** the resolved arousal-driven presentation state matches the baseline's `arousal` level
  string, and no `sexual_traits` Attribute is created as a result of building status
