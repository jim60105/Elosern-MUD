# story-encounter-activation Specification

## Purpose
Activates published story encounters at authoritative exploration positions through the upstream deterministic scene and escort boundaries.

## Requirements

### Requirement: All production encounter triggers use one eligibility boundary

Post-publication, settled room entry, wilderness-coordinate travel, reconnect, startup of connected owners and declared prerequisite changes SHALL use one deterministic eligibility/activation boundary. It SHALL consume the saved package/owner, lawful actual exploring actor, current authoritative position/tick and owner-resolved prerequisites through upstream activate_scene_encounter. Pending lookup SHALL be indexed by owner/locator or affected prerequisite.

#### Scenario: Publication at current eligible location
- **WHEN** a connected owner remains at the confirmed south-gate locator while its package commits
- **THEN** the eligible daughter encounter activates without exit/re-entry, one exact NPC has current greeting/topics and an authorized private offer, and no guild membership is required

#### Scenario: All exploration and recovery boundaries
- **WHEN** room entry, wilderness coordinate change, reconnect, startup after lost fan-out or a declared prerequisite change reaches an eligible saved encounter
- **THEN** the shared boundary activates it once from actual location and owner without arbitrary model subscriptions or scanning unrelated scenes

#### Scenario: Publication while disconnected
- **WHEN** a package commits offline and reconnect occurs at an eligible position
- **THEN** status synchronizes and the encounter activates from the current controlled actor's authoritative position

### Requirement: Activation precedes final settled escort observations

Traversal SHALL settle actual movement and followers, activate relevant encounters transactionally and then call upstream evaluate_escort_event on the resulting position/source. Only final settled evaluation SHALL consume transition eligibility. Standalone activation SHALL use its owning transaction/source. Unrelated NPC roaming SHALL NOT activate every future player encounter; NPC rendezvous movement SHALL keep the upstream evaluator path.

#### Scenario: Traversal materializes the meeting actor
- **WHEN** a followed or lawfully possessed protected actor reaches a locator that activates its meeting role
- **THEN** the real role exists before final escort/outcome evaluation, and repeated observation cannot advance a second stage or duplicate resolution/reward

### Requirement: Independent encounters retain actual actor identity

Eligibility SHALL remain independent of commission acceptance or the other encounter where declared. Activation SHALL use upstream lookup_story_role and activate_scene_encounter identities, never respawn or teleport bound actors to an origin. Wrong locator, cancelled encounter and unavailable actor SHALL remain named non-success outcomes.

#### Scenario: Both encounter orders and possessed exploration
- **WHEN** mother-first and daughter-first exploration run separately with normal and lawful possessed actors
- **THEN** each independently eligible encounter works before acceptance, ownership remains the original player and reload/re-entry preserves exact actor state, dialogue phase and memory

#### Scenario: Actor already moved or unavailable
- **WHEN** eligibility is reevaluated after a bound actor moved, died or was removed
- **THEN** its actual binding/location is retained or its unavailability reported with no clone, resurrection or return-to-origin teleport
