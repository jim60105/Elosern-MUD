## ADDED Requirements

### Requirement: Staff status reports gallery holdings without sensitive data
Staff status SHALL list gallery holdings/default/error state with the existing scene/portrait filter. Per-image jobs SHALL remain absent from status rows. No completed subject-record section or legacy seed row SHALL remain. Output SHALL exclude prompts, persona, stored identities and absolute paths.

#### Scenario: Gallery state is filtered and private
- **WHEN** staff requests status with scene or portrait filters
- **THEN** only matching gallery holdings/default/errors appear; pending job rows and sensitive data do not

#### Scenario: Staff permission remains enforced
- **WHEN** an ordinary player invokes status
- **THEN** access is denied without queue or gallery operations

### Requirement: Staff retry re-drives recorded gallery failures
Staff retry SHALL re-drive subjects with recorded gallery errors through the existing validated automatic gallery seam, report the count requested and preserve per-subject failure isolation. Existing cards SHALL suppress requests and clear moot errors; other declined requests SHALL retain errors. No classic count or record reset SHALL remain.

#### Scenario: Gallery errors retry without restart
- **WHEN** eligible subjects have recorded gallery errors and no cards, in-flight jobs or satisfying official defaults
- **THEN** each gets one new image request and the command reports the requested count

#### Scenario: Moot errors clear
- **WHEN** an erroring subject has gained a valid card
- **THEN** no request occurs and its error clears

#### Scenario: Other declines preserve errors
- **WHEN** an erroring subject is official-satisfied, already in flight or ineligible
- **THEN** its error stays and no job is added; other eligible subjects continue

### Requirement: Staff requeue forces one validated gallery request
Staff requeue SHALL parse one full typed subject key and request one gallery image, bypassing automatic satisfaction by cards or official defaults while retaining capability preconditions. Invalid or gallery-less subjects SHALL reject without writes. Capped subjects SHALL replace on successful settlement; uncapped subjects SHALL retain existing cards.

#### Scenario: A validated key forces regeneration
- **WHEN** staff runs `@art requeue scene:<archetype>` for a registered synthetic archetype that holds one card
- **THEN** one gallery generation is requested, no fixed-output record is created, and the existing
  card stays until the new card replaces it under the declared maximum

#### Scenario: An invalid key is rejected with no record change
- **WHEN** staff runs `@art requeue` with a malformed or unknown full subject key
- **THEN** a named error is returned and no record is changed

#### Scenario: A character key requeue adds a gallery card
- **WHEN** staff runs `@art requeue portrait:character:<stable-key>` for a subject that already holds cards
- **THEN** one gallery generation is requested, no fixed-output record is created, and the existing cards are untouched until the new card is appended

#### Scenario: A monster key requeue requests a gallery card honouring the cap
- **WHEN** staff runs `@art requeue portrait:monster:<visual-key>` for a visual species that already holds its one card
- **THEN** one gallery generation is requested, no fixed-output record is created, and the settled card replaces the existing one under the declared maximum

#### Scenario: A gallery-bearing key issues one request through the shared seam
- **WHEN** the requeue key's subject kind declares a gallery — character and species-keyed monster alike
- **THEN** the command SHALL instead issue exactly one gallery generation request for that subject
  through the shared request seam, appending a new card on success

#### Scenario: Requeue deliberately bypasses the idempotency guard
- **WHEN** requeue targets a subject that already holds cards
- **THEN** because requeue is the staff force path, it SHALL deliberately bypass the
  automatic-generation idempotency guard, so the subject still gets one new generation

#### Scenario: The append respects the declared card maximum
- **WHEN** the new card would exceed the kind's declared card maximum
- **THEN** the append SHALL respect that maximum exactly as any other append does — for the monster
  kind, replacing its single card

#### Scenario: A kind with no declared maximum keeps its existing cards
- **WHEN** the kind declares no card maximum
- **THEN** the existing cards SHALL be untouched

#### Scenario: Every force request creates a per-image job
- **WHEN** either requeue path runs for a gallery-bearing subject
- **THEN** only a per-image gallery job SHALL be created for that subject

#### Scenario: Retired monster tiers never requeue
- **WHEN** staff supplies any threat-tier key as a monster requeue subject
- **THEN** a named invalid-subject error is returned with no generation, record reset or conversion

### Requirement: Staff health separates live jobs from gallery outcome state
Developer health SHALL perform one forced connectivity probe and report reachability, scheduler policy, live gallery-job pending/in_progress counts, gallery holdings/card/error counts, and output policy in that order. Deleted terminal jobs SHALL NOT be represented as persistent done/failed queue rows. It SHALL remain read-only and leak no credentials, paths or prompts.

#### Scenario: Live counts reflect actual job lifetime
- **WHEN** one job is pending, another claimed and a previous failed job has been removed
- **THEN** health reports one pending and one in_progress job, the recorded gallery error separately, and no terminal queue history

#### Scenario: Probe failure does not hide other sections
- **WHEN** the forced probe fails
- **THEN** the bounded error appears with scheduler, gallery and output sections; no state changes

## REMOVED Requirements

### Requirement: @art status lists and filters records without leaking sensitive data
**Reason**: Replaced by Staff status reports gallery holdings without sensitive data; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: @art retry re-enqueues failed records
**Reason**: Replaced by Staff retry re-drives recorded gallery failures; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: @art requeue accepts one validated full subject key and forces regeneration under the lock
**Reason**: Replaced by Staff requeue forces one validated gallery request; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: @art health reports server reachability, scheduler state, queue counts, and output policy
**Reason**: Replaced by Staff health separates live jobs from gallery outcome state; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.
