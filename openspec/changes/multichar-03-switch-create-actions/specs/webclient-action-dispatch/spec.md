# Delta spec: webclient-action-dispatch (multichar-03-switch-create-actions)

The completion requirement is extended to admit one new class of action: one whose committed
effect retires the very sequence its result would be published into. Such an action cannot publish
after its effect, so the ordering constraint is stated explicitly rather than left to be
discovered.

## MODIFIED Requirements

### Requirement: Admitted action completion publishes canonical state before unlocking
After an admitted non-duplicate action settles, the coordinator SHALL build presentation from committed canonical state and allocate exactly one next revision inside one publication critical section. Success or domain rejection with a declared nonempty affected-panel set SHALL emit one update; stale, internal error, or an empty affected-panel set SHALL emit one full snapshot. The server SHALL send that presentation before an exact `ui_action_result` naming the same revision and SHALL release the server in-flight marker only after both sends. The browser SHALL release its mutation lock only after receiving the result and accepting presentation state at or above `presentation_revision`. A cached duplicate MAY replay its prior result without a new presentation, and a busy pre-admission rejection SHALL NOT alter the admitted request's lock.

An action whose committed effect retires the session's presentation and dispatch sequence — a puppet change — SHALL NOT perform that effect inside its adapter, because a retired sequence publishes nothing into its replacement and the request would receive no result at all. Such an action SHALL instead decide and report synchronously and schedule its effect to run only after its result has been sent and both the server in-flight marker and the browser mutation lock have been released. Its result SHALL report the outcome of the authorization decision, which SHALL be complete before the result is sent, and the scheduled effect SHALL re-validate that decision against committed state, report any failure to the player through the ordinary message channel, and publish recovery presentation. Such an action SHALL declare no affected panels and SHALL emit no completion presentation, so no state derived from the retiring puppet is published at the retiring epoch.

#### Scenario: Successful completion refreshes before result
- **WHEN** a proof adapter commits successfully and declares an affected panel
- **THEN** the server emits one newer panel update, then its success result with the same revision, and only then admits a later mutation

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
- **THEN** the player is informed through the ordinary message channel, an operational error event is emitted, and recovery presentation is published, rather than the failure being silently swallowed
