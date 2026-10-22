# Spec Delta

## ADDED Requirements

### Requirement: Immediate source suppression uses automatic award results
An otherwise eligible immediate nomination trigger SHALL be suppressed when its source has automatic built-in-title grant results for the nominated player. The check SHALL NOT classify event types, display names or unrelated owned titles, or duplicate results with a producer Boolean. Future award producers SHALL use the same contract without nomination-service changes.

#### Scenario: Synthetic award extension
- **WHEN** a synthetic future event grants a new built-in title through the common contract and sends an otherwise eligible immediate notification
- **THEN** the player is suppressed with no nomination-service event-type change, while the deed remains eligible at later wake/logout

#### Scenario: Recipient attribution
- **WHEN** only another participant receives a new title, or the player merely owns an unrelated title
- **THEN** the occurrence is not suppressed by this rule

#### Scenario: Already-owned and several grants
- **WHEN** a new occurrence grants no new title because it is already owned, and separately one occurrence grants several titles
- **THEN** the first is not suppressed by this rule and the second suppresses once

### Requirement: Awakening admission observes committed player transitions
Awakening SHALL mean a committed voluntary or forced sleep-to-awake player transition, independent of command, transport or midnight. Notification SHALL occur after outer commit and the same transition SHALL cause at most one attempt. Teammates, NPCs and live-combat wakes SHALL NOT nominate the player; no deferred combat-wake trigger SHALL be added.

#### Scenario: Voluntary and forced wakes
- **WHEN** either kind of player sleep commits a transition to awake
- **THEN** one notification follows outer commit even without midnight or UI notification

#### Scenario: Negative wake cases
- **WHEN** a teammate or NPC wakes, the player remains asleep, midnight passes alone, or the transition rolls back
- **THEN** no player nomination occurs

#### Scenario: Replay after completion
- **WHEN** a wake notification is replayed after its first generation has completed
- **THEN** no second attempt is admitted

#### Scenario: Live combat prevents nomination
- **WHEN** the player wakes but is still in live combat
- **THEN** no nomination occurs and leaving combat does not dispatch a deferred wake

### Requirement: Nomination has one in-flight request per player identity
Within a server process at most one nomination SHALL be in flight per durable player identity. Overlapping triggers SHALL neither create a new call nor replace request data. Every completion/failure path SHALL release the slot. The rules writer SHALL recheck suppression on arrival; restart SHALL retain ballots without resuming abandoned generation.

#### Scenario: Wake then logout overlap
- **WHEN** logout arrives while wake generation is pending
- **THEN** only one call runs with the original frozen tick and source set

#### Scenario: All paths release the slot
- **WHEN** generation succeeds, query fails, feed is empty, profile is disabled, output is void, transport fails, cancellation occurs or ballot persistence fails
- **THEN** the slot is released and an otherwise eligible later trigger can run

#### Scenario: Late result preserves state
- **WHEN** a ballot or decline cooldown appears while generation is pending
- **THEN** the result cannot overwrite the ballot or bypass suppression

#### Scenario: Restart does not resume generation
- **WHEN** a process restarts with a stored ballot and an abandoned call
- **THEN** the ballot persists while the abandoned generation is not resumed

### Requirement: Empty and failed nomination leave deterministic gameplay intact
Empty authorized renderable material and disabled profiles SHALL cause no model call. Read, transport and invalid-output failures SHALL create no ballot or decline cooldown and SHALL NOT undo committed gameplay. Identity/preferences alone SHALL NOT justify generation. Malformed persisted title state SHALL retain existing fail-closed behavior.

#### Scenario: No evidence means no attempt
- **WHEN** all deeds are absent, inaccessible, unsupported, malformed or oversized
- **THEN** no call, ballot or cooldown is created

#### Scenario: Offline failure after settlement
- **WHEN** gameplay commits and the model is unavailable or returns invalid output
- **THEN** gameplay and deterministic title grants remain committed without substitute deeds or names

#### Scenario: Consent remains preserved
- **WHEN** a valid candidate ballot is reloaded across sessions and then accepted or declined
- **THEN** only acceptance grants the chosen epithet, ballots do not expire, acceptance starts no cooldown and decline retains its existing two-day-boundary cooldown

### Requirement: Nomination diagnostics preserve privacy
Nomination workflow diagnostics SHALL identify player, trigger, frozen tick and source counts through the existing observability boundary. Exceptions SHALL retain exception context. Operational logs SHALL omit full private deed prose; transcript payloads SHALL follow existing retention and credential exclusions.

#### Scenario: Bounded operational context
- **WHEN** a source query or generation raises after gameplay commits
- **THEN** a bounded workflow diagnostic carries exception context and no full private deed prose


## MODIFIED Requirements

### Requirement: Epithet nomination fires only at rest points and is throttled
Epithet nomination SHALL admit only player logout, committed awakening and qualifying quest completion after settlement commits, never during live combat. Pending ballots SHALL suppress new nomination without replacement. Midnight alone and passed examinations SHALL NOT trigger nomination. A source occurrence newly awarding a built-in title to the nominated player SHALL suppress its own immediate trigger through authoritative award results.

#### Scenario: A pending ballot suppresses every trigger
- **WHEN** any rest-point trigger fires for an entity with a pending ballot
- **THEN** no LLM call is made and the ballot is unchanged

#### Scenario: Scheduling lives in the service, persisting in the rules writer
- **WHEN** the nomination trigger's placement is checked against the transport contract
- **THEN** the contract's ban on `world/rules` and `commands` importing `world/ai` holds — scheduling lives in the composition-root service and persisting in the rules writer

#### Scenario: Decline cools down two day boundaries
- **WHEN** a ballot is declined and day boundaries pass
- **THEN** nominations resume only after the second boundary

#### Scenario: Offline LLM mints nothing
- **WHEN** a trigger fires while the options profile is degraded or absent
- **THEN** the round is void, no ballot is stored, and gameplay is unaffected

#### Scenario: Only decline starts a cooldown
- **WHEN** a ballot is declined, and separately when one is accepted
- **THEN** the decline suppresses renomination for `NOMINATION_COOLDOWN_DAYS` (title-registry constant, initial value 2) world-clock day boundaries — decline is the only cooldown source, because ballots never expire — and the accepted ballot starts no cooldown

#### Scenario: An unavailable LLM never fires the stage
- **WHEN** the LLM is offline, degraded, or past its bounded timeout
- **THEN** the stage does not fire and fixed titles are unaffected
