# Spec Delta

## MODIFIED Requirements

### Requirement: Admitted action completion publishes canonical state before unlocking
After an admitted nonduplicate action settles, one serialized publication SHALL compare validated canonical candidates, use a fresh complete snapshot for required alignment/recovery, or consume no revision for unchanged content/metadata. Every presentation frame SHALL precede its matching result. Existing result-only and sequence-retiring exceptions SHALL remain; mutations unlock only after the result and its committed revision.

#### Scenario: Successful completion refreshes before result
- **WHEN** a proof adapter commits successfully and declares an affected panel
- **THEN** the server emits one delta only when validated content or metadata changed, then its success result with the published revision, and only then admits a later mutation

#### Scenario: Client waits for declared presentation revision
- **WHEN** an action result naming revision 12 arrives while the accepted client store remains at revision 11
- **THEN** the browser records the result but keeps mutation controls locked until it accepts revision 12 or a later recovery snapshot

#### Scenario: Concurrent sync does not cause a stale next action
- **WHEN** sync and action completion publications occur close together and the player immediately chooses a later action after unlock
- **THEN** the later action uses the newest accepted revision and is not stale solely because result and refresh arrived out of order

#### Scenario: A sequence-retiring action delivers its result before its effect
- **WHEN** an admitted action whose committed effect is a puppet change completes
- **THEN** its exact `ui_action_result` is sent and the in-flight marker released at the still-live epoch, and only afterwards does the puppet change retire the sequence

#### Scenario: A sequence-retiring adapter that transitions inline is a defect
- **WHEN** an adapter performs a puppet change before returning
- **THEN** the completion guard finds the sequence retired and sends no result, leaving the request unanswered — which is why such an effect is required to be scheduled after the result instead

#### Scenario: A scheduled effect's failure is reported outside the retired sequence
- **WHEN** a scheduled puppet change fails after its success result was sent
- **THEN** the player is informed through the ordinary message channel, an operational error event is emitted, and recovery presentation is published for whatever puppet the session still holds, rather than the failure being silently swallowed

#### Scenario: A silently refused effect is not reported as done
- **WHEN** the scheduled effect calls an API that refuses by returning without raising
- **THEN** the verification step detects that the effect did not take hold and the recovery path runs, rather than the transition proceeding as though it had succeeded

#### Scenario: Presentation precedes result and unlock
- **WHEN** the coordinator publishes an admitted action's completion
- **THEN** the server SHALL send every frame of a changed or alignment presentation before an exact ui_action_result naming the published revision; an unchanged completion sends only its result at the current revision
- **AND** it SHALL release the server in-flight marker only after both sends

#### Scenario: Browser lock releases only at the named revision
- **WHEN** the server has sent a completion presentation and result
- **THEN** the browser SHALL release its mutation lock only after receiving the result and accepting presentation state at or above `presentation_revision`

#### Scenario: Duplicate replay and busy rejection leave lock state intact
- **WHEN** a cached duplicate request is replayed, or a busy pre-admission rejection is returned
- **THEN** the duplicate MAY replay its prior result without a new presentation
- **AND** the busy rejection SHALL NOT alter the admitted request's lock

#### Scenario: Sequence-retiring result reports the completed decision
- **WHEN** an action whose committed effect is a puppet change decides its authorization synchronously
- **THEN** its result SHALL report the outcome of the authorization decision, which SHALL be complete before the result is sent
- **AND** the scheduled effect SHALL re-validate that decision against committed state
- **AND** the effect SHALL be scheduled to run only after its result has been sent and both the server in-flight marker and the browser mutation lock have been released

#### Scenario: Sequence-retiring actions emit no completion presentation
- **WHEN** a sequence-retiring action completes
- **THEN** it SHALL declare no affected panels and SHALL emit no completion presentation, so no state derived from the retiring puppet is published at the retiring epoch

#### Scenario: Scheduled effect failures carry matching severity
- **WHEN** a scheduled sequence-retiring effect fails at any stage
- **THEN** it SHALL report the failure to the player through the ordinary message channel at a severity matching how far the failure got
- **AND** it SHALL publish recovery presentation whenever a puppet remains to render it for

### Requirement: A non-success action result surfaces its message exactly once

When the client recognizes a matching non-success ui_action_result with the same request ID and epoch as its in-flight dispatch, and creation overlay is not the presenting surface, it SHALL show the server-authored message exactly once as one bounded narrative error line. Presentation/result ordering SHALL retain synchronization safety.

#### Scenario: A rejected move explains itself in the feed
- **WHEN** a dispatched action receives a matching rejected result carrying a server-authored message while exploration mode is presented
- **THEN** exactly one narrative line shows that message verbatim, the player keeps keyboard focus without any modal, and no result echo line accompanies it beyond the pre-existing dispatch command echo

#### Scenario: A stale admission speaks through the recovery
- **WHEN** the client dispatches against a superseded base_revision and receives the complete recovery snapshot followed by its matching stale result
- **THEN** the stale message appears once as a narrative error line, the lock releases only after both recovery revision and result have arrived, and the client never resubmits automatically

#### Scenario: One recognized result yields one line
- **WHEN** the same non-success result is delivered or re-observed by the client more than once, including with another request's result observed in between
- **THEN** the narrative shows the message once and a successful result appends no error line

#### Scenario: Creation mode keeps one presenting surface
- **WHEN** a non-success result arrives while the creation overlay is mounted
- **THEN** the overlay shows the envelope's message verbatim in its result region and the narrative feed gains no duplicate line

#### Scenario: A message-less non-success still speaks
- **WHEN** a recognized non-success result carries no usable message
- **THEN** the narrative shows the single stable fallback line rather than failing silently

#### Scenario: Messages are never rewritten or fabricated
- **WHEN** a recognized non-success result carries a message, or carries none
- **THEN** the client SHALL NOT paraphrase, translate, or synthesize replacement text while the envelope carries a message
- **AND** it SHALL show a single stable fallback line when a recognized non-success result carries none

#### Scenario: Successful results stay silent
- **WHEN** the client recognizes a successful result
- **THEN** it SHALL surface no additional line

#### Scenario: Creation overlay is the sole presenting surface
- **WHEN** the creation overlay is mounted and a recognized non-success result arrives
- **THEN** the overlay SHALL be the presenting surface and SHALL render the result's message verbatim in an always-reachable result region across every wizard stage, and no narrative line SHALL be appended for that result

#### Scenario: Surfacing never alters dispatch safety rules
- **WHEN** a non-success result message is surfaced
- **THEN** surfacing SHALL NOT alter the in-flight lock, the revision-gated release including the stale rule requiring committed recovery, the uncertain-result notice, or the no-automatic-resubmit rule
