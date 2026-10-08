## Purpose

Read-only compact character status derived from canonical resources, active conditions, disguise state, and persistent combat-session metadata.

## Requirements

### Requirement: Compact status reports canonical true resources
The available version-3 status panel SHALL contain exactly `schema_version: 3`, `available: true`, `actor`, `resources`, `conditions`, `disguise_active`, and `combat`. `resources` SHALL contain exactly `hp`, `mp`, and `sp`, each with non-negative JavaScript-safe integer `current` and positive safe integer `maximum`, with current not exceeding maximum. Resource values SHALL come directly from canonical traits and SHALL never call `get_display_value` or substitute `disguised_stats`.

#### Scenario: Active disguise does not alter resources
- **WHEN** an actor has true HP 80/100, MP 40/60, SP 30/50 and display-only disguised values for any traits
- **THEN** the status payload reports 80/100, 40/60, and 30/50 and marks `disguise_active` true

#### Scenario: Missing gauge fails closed
- **WHEN** the active puppet lacks a valid required HP, MP, or SP gauge
- **THEN** the status panel is unavailable at schema version 3 and does not report zero for the missing resource

#### Scenario: Status version cutover is exact
- **WHEN** equivalent available and unavailable status payloads are checked at versions 2 and 3
- **THEN** the registered version-3 forms are accepted and version-2 forms are rejected without replacing committed presentation

#### Scenario: Actor envelope fields are bounded
- **WHEN** an available version-3 status payload is validated
- **THEN** `actor` contains display `name` of 1..256 Unicode code points, opaque correlation `identity` of 1..64 ASCII characters, and nullable `location`, with the existing optional composed `full_title` contract unchanged
- **AND** a present location contains exactly a 1..256-code-point display `label` and 1..64-character opaque `identity`

#### Scenario: Condition and remaining envelope bounds
- **WHEN** an available version-3 status payload is validated
- **THEN** `conditions` contains at most 32 entries
- **AND** `disguise_active` is boolean and `combat` is null or the exact combat object

#### Scenario: Missing or malformed traits fail closed
- **WHEN** required canonical traits are missing or malformed
- **THEN** the common status-unavailable payload is produced rather than fabricated zero values

#### Scenario: Both status forms share registered version 3
- **WHEN** available and unavailable status forms are checked
- **THEN** both use the same registered version 3
- **AND** envelope protocol version and unrelated panel versions remain unchanged and status version 2 is not accepted as a compatibility form

### Requirement: Status conditions use deterministic matched modifiers
The deterministic combat-modifier module SHALL expose a read-only query of each currently matched rule ID and its exact adjustment bundle without changing existing merged evaluation. The status presenter SHALL combine that query with active rulebook buff instances and immutable display metadata.

#### Scenario: Matching buff reports duration and exact adjustment
- **WHEN** a synthetic actor has an active independent poisoned buff with 120 game seconds remaining and its deterministic adjustment rule matches
- **THEN** status contains the stable poisoned condition with its Traditional Chinese label, harmful severity, 120-second duration, non-equipment provenance, and the exact agility adjustment supplied by the matched deterministic rule

#### Scenario: Sexual threshold appears only while matched
- **WHEN** the actor's canonical arousal state crosses the configured combat-modifier threshold
- **THEN** status contains the matched rule ID and exact agility/accuracy adjustments, and the entry disappears after canonical state no longer matches

#### Scenario: Condition presentation metadata covers current rules
- **WHEN** current buff definitions and combat-modifier rule IDs are compared with the status display registry
- **THEN** every condition that can enter the status payload has one stable Traditional Chinese label and severity

#### Scenario: Provenance does not change actual mechanics
- **WHEN** a synthetic equipment overlay activates an adverse combat modifier and its status provenance is classified
- **THEN** its severity, exact adjustments, and combat/breakdown outcome equal those obtained from the actual effective state, and comparison-only rules are absent from status

#### Scenario: Invalid provenance is rejected
- **WHEN** a v3 condition omits provenance, uses an unknown kind, includes an extra field, repeats an item key, exceeds eight sources, or pairs equipment kind with an empty source list
- **THEN** it fails validation and cannot replace the accepted status panel

#### Scenario: Condition entry required fields are bounded
- **WHEN** a condition entry is validated
- **THEN** it contains stable `code` of 1..64 lowercase dotted or underscored identifier characters, Traditional Chinese `label` of 1..128 code points, `severity` from `beneficial`, `informational`, `warning`, `harmful`, or `critical`, and required `provenance`

#### Scenario: Condition optional fields are bounded
- **WHEN** a condition entry is validated
- **THEN** only optional non-negative safe-integer `remaining_seconds` and optional `modifiers` with at most 16 stable keys and exact JSON scalar rule values are permitted

#### Scenario: Absent duration is omitted
- **WHEN** a condition has no duration
- **THEN** the duration is omitted without a fabricated value

#### Scenario: Sexual entries follow canonical predicates
- **WHEN** status conditions are assembled
- **THEN** sexual-state entries are included only while their effective canonical combat predicates match

#### Scenario: Provenance classification is presentation-only
- **WHEN** a condition's provenance is classified
- **THEN** global display severity, actual adjustment values, active buff stacking or duration, and condition membership are unchanged

#### Scenario: Same-definition instances are never merged
- **WHEN** independent and attached active instances share the same logical definition
- **THEN** both remain represented without merging away either instance

#### Scenario: Provenance object shape is exact
- **WHEN** a condition's `provenance` is validated
- **THEN** it contains exactly `kind` and `equipment_sources`
- **AND** `kind` is one of `equipment`, `non_equipment`, `mixed`, or `unknown`
- **AND** `equipment_sources` is a duplicate-free array of at most eight entries sorted by item key, each entry containing exactly a stable `item_key` of 1..64 identifier characters and an item-registry-backed Traditional Chinese `label` of 1..128 code points

#### Scenario: Provenance kind constrains source count
- **WHEN** a provenance object is validated
- **THEN** `equipment` and `mixed` kinds require at least one equipment source and `non_equipment` and `unknown` kinds require none

#### Scenario: Boundary rejects malformed provenance
- **WHEN** provenance is missing, malformed, carries an unknown field, exceeds a bound, or is inconsistent
- **THEN** the read-model/presenter boundary and browser protocol validation reject it rather than fabricate a source or adopt a legacy shape

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
The deterministic rules layer SHALL provide a frozen no-create status read model that interprets existing persistent trait, optional buff, sexual baseline/materialized state, creation, and combat-session records without constructing a lazy handler that can materialize defaults. The presenter SHALL serialize only that read model.

#### Scenario: Status construction preserves canonical state
- **WHEN** a status payload is built for an actor with gauges, active buffs, sexual state, disguise data, and combat state
- **THEN** a before/after comparison of every canonical value is equal

#### Scenario: Malformed combat record does not escape presenter isolation
- **WHEN** the actor's persistent combat-session record is malformed
- **THEN** status becomes unavailable with a correlation ID logged and narrative plus other registered presentation remains usable

#### Scenario: Unmaterialized sexual baseline remains unmaterialized
- **WHEN** a valid actor has baseline sexual data but no materialized sexual trait handler and status is built
- **THEN** matching presentation state is interpreted in memory and no sexual trait Attribute is created

#### Scenario: Status building never mutates state
- **WHEN** status is built
- **THEN** it creates or repairs no traits, materializes no uninitialized sexual baseline, ticks no gauges or buffs, changes no sexual state, rewrites no combat record, activates no disguise, and invokes no state-mutating deterministic API

#### Scenario: Presenter failure is isolated
- **WHEN** the status presenter fails
- **THEN** the failure is isolated under the OOB protocol's unavailable-panel behavior

### Requirement: The no-create status read model resolves the derived arousal level from stored pleasure, not a raw arousal key
`world/rules/status_query.py::_sexual_condition_context()` SHALL resolve its `"arousal"` context
entry from the persisted `pleasure` counter's stored value (via the same band lookup
`SexualState.arousal` uses at read time), for any entity whose `sexual_traits` handler has been
materialized, rather than from a raw `"arousal"` key — which SHALL NOT exist in that storage once an
entity's `SexualState` has been built.

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

#### Scenario: The resolution materializes nothing
- **WHEN** the arousal context resolution runs for any entity
- **THEN** it does not read `entity.sexual`, construct a `TraitHandler`, or otherwise materialize any persistent state, matching "Status presentation has no mutation side effects"'s existing no-create discipline

#### Scenario: Unmaterialized entities keep the pre-amendment read path
- **WHEN** an entity's `sexual_traits` handler has never been materialized
- **THEN** this path still reads `"arousal"` as a level string from the entity's frozen import-time baseline Attribute, exactly as before this capability's amendment — preserving "Unmaterialized sexual baseline remains unmaterialized" without modification

#### Scenario: Pleasure-driven tracking keeps the threshold scenario true
- **WHEN** `pleasure` (not a directly-stored `arousal` level) is the canonical quantity
- **THEN** "Sexual threshold appears only while matched"'s existing, unmodified scenario — the sexual condition entry appears and disappears as the actor's *canonical* arousal state crosses and re-crosses the configured threshold — continues to hold true
- **AND** without this resolution, a materialized entity's status entry would freeze at its import-time baseline and stop tracking canonical state entirely, silently violating that scenario

### Requirement: Equipment condition provenance preserves independent sources
Condition provenance SHALL be computed read-only from the same canonical snapshot used for the condition's actual values. An active attached buff SHALL have equipment provenance only when its instance identity, cached logical definition and cached source item agree with the currently worn item's declared attachment.

#### Scenario: Worn attached adverse buff identifies its item
- **WHEN** a synthetic worn accessory declares an adverse attached buff and an active instance has the exact declared identity, logical definition and cached source item
- **THEN** its status row has equipment provenance naming that accessory's registry key and label, while its severity and remaining duration remain unchanged

#### Scenario: Independent instance of the same definition survives
- **WHEN** the actor also has an independent active instance of that attached buff's definition
- **THEN** both buff rows remain represented with their own durations and provenance, the independent instance retains attention, and any definition-based matched rule still matches independently in the equipment-free comparison

#### Scenario: A source string alone does not prove equipment ownership
- **WHEN** an independent buff has a source string equal to a worn item's key but lacks the item's declared attachment identity
- **THEN** it is not classified equipment-only and cannot lose its adverse-condition attention

#### Scenario: Inconsistent attachment retains conservative attention
- **WHEN** an otherwise readable active attached-looking instance is orphaned after its item is absent or has inconsistent cached source metadata
- **THEN** its provenance is unknown with no invented equipment source and its adverse severity retains attention

#### Scenario: Declared orphan differs from an item-looking independent instance
- **WHEN** synthetic equipment declares one attached buff, that item's canonical attachment identity remains active while the item is not worn, and a second ordinary instance has a colon-shaped identity for an undeclared item/buff pair
- **THEN** the declared orphan has unknown provenance, the ordinary instance has non-equipment provenance, and neither loses adverse-condition attention or invents an equipment source

#### Scenario: Equipment induces an exposure threshold crossing
- **WHEN** a synthetic actor stores exposure 中等, synthetic worn equipment adds +1 bias, and an adverse rule requires exposure at least 高
- **THEN** actual status contains that rule with equipment provenance naming the bias contributor, while stored exposure stays 中等 and the same rule does not independently match without equipment

#### Scenario: Mixed exposure retains the independent warning
- **WHEN** a synthetic actor stores exposure 高 and equipment raises its effective exposure to 極高 while an adverse rule requires exposure at least 高
- **THEN** that rule has mixed provenance naming the equipment contributor and retains independent attention

#### Scenario: Saturated baseline already needs attention
- **WHEN** a synthetic actor stores exposure 極高, equipment adds +1 bias, and an adverse rule requires exposure at least 高
- **THEN** effective exposure remains 極高, the unchanged input yields non-equipment provenance with no equipment source, and the warning retains attention both with and without equipment

#### Scenario: Unrelated equipment cannot suppress a state warning
- **WHEN** an actor wears exposure-bias equipment while an adverse condition depends solely on stored pleasure or an independent active buff
- **THEN** the unrelated equipment is absent from that condition's provenance and the adverse condition retains independent attention

#### Scenario: Equipment prerequisite has no independent match
- **WHEN** a synthetic adverse rule requires both a stored-state threshold and a named worn item, and only the state threshold remains in the equipment-free comparison
- **THEN** the actual rule remains represented with equipment provenance and no claim that the stored prerequisite independently activates that rule

#### Scenario: Repeated reads preserve canonical storage
- **WHEN** provenance is built twice for synthetic materialized and unmaterialized actors with equipment and buffs
- **THEN** all canonical Attributes, world time, equipment and buff values remain unchanged and no lazy handler or new storage record is created

#### Scenario: Possession uses the status owner's equipment
- **WHEN** the controlled host and status resource owner wear different synthetic equipment under possession
- **THEN** condition source labels and independent-match comparison use the status resource owner's equipment and state, while the existing controlled actor identity remains unchanged

#### Scenario: Independent instances keep non-equipment provenance
- **WHEN** an ordinary independent buff instance's definition matches an attached instance or its source string resembles an item key
- **THEN** it retains non-equipment provenance

#### Scenario: Unprovable attachments are unknown, never equipment-only
- **WHEN** an orphaned or inconsistent attachment's origin cannot be proven
- **THEN** it has unknown provenance and is not treated as equipment-only

#### Scenario: Bad canonical inputs stay fail-closed
- **WHEN** required canonical status inputs are missing or malformed
- **THEN** status remains unavailable rather than repaired

#### Scenario: Declared attachment identity is recognized without wearing
- **WHEN** an exact canonical attachment identity's registered equipment item declares the identified buff, independently of current worn membership
- **THEN** the absent-item attachment is recognized by that identity

#### Scenario: A declared identity with absent or inconsistent equipment is unknown
- **WHEN** a declared attachment identity's equipment is absent or its cached ownership is inconsistent
- **THEN** its provenance is unknown

#### Scenario: Key shape alone never identifies an attachment
- **WHEN** only an instance-key shape or source string — including an undeclared item/buff pair — suggests an attachment
- **THEN** it does not identify an attachment and an otherwise ordinary readable instance remains non-equipment

#### Scenario: Equipment-induced matches are equipment-dependent
- **WHEN** an actually matched derived condition does not match without the current read-time equipment contributions and those contributions have verified sources
- **THEN** the condition is equipment-dependent

#### Scenario: Independent matches keep independence
- **WHEN** a condition matches independently without the current read-time equipment contributions
- **THEN** it retains independent provenance and attention

#### Scenario: Shared contribution is mixed; no effect is non-equipment
- **WHEN** equipment also contributes to a matching input
- **THEN** the condition is mixed
- **AND** when equipment does not change any input consumed by the condition, it is non-equipment

#### Scenario: Equipment-free comparison scope is exact
- **WHEN** the equipment-free comparison runs
- **THEN** it preserves stored state, skills, grants, and independent buffs, removes only proven worn attachments and read-time equipment facts/overlays, and uses the same deterministic condition semantics as actual combat

#### Scenario: Buff predicates identify definitions
- **WHEN** buff predicates evaluate conditions
- **THEN** they identify logical definitions rather than confusing source-specific instance identities with definitions

#### Scenario: Unproven attribution never suppresses attention
- **WHEN** a condition's attribution cannot be proven
- **THEN** it uses unknown provenance without suppressing attention

#### Scenario: Gameplay-caused state stays canonical
- **WHEN** canonical state changes were previously caused by gameplay
- **THEN** they remain canonical in the equipment-free comparison and historical causal reconstruction is not required

#### Scenario: Provenance building and comparison are side-effect-free
- **WHEN** these provenance values are built or compared
- **THEN** no handler is materialized, no Attribute is written or repaired, time does not advance, buffs do not tick, equipment is not altered, and combat evaluation does not change

#### Scenario: Possession follows the status owner
- **WHEN** provenance is computed under possession
- **THEN** it follows the same canonical subject that owns the status resources and conditions, without borrowing sources from the controlled host
