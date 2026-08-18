## ADDED Requirements

### Requirement: Current situation freshness gates session-backed suggestions
The action-options service SHALL expose one shared, read-only exploration situation derivation that
produces the same fingerprint and deterministic input data for scheduling and presentation. The
presentation-context factory SHALL carry the current derived fingerprint, or `None` when no
exploration situation can be derived. Before rendering any session snapshot with status
`generating`, `ready`, or `degraded`, the `context_actions` suggestions presenter SHALL require its
snapshot fingerprint to equal the context fingerprint; a missing or mismatched fingerprint SHALL
emit exact `{"status": "unavailable"}` with a bounded diagnostic and SHALL emit none of the old
cards. This gate SHALL be read-only and SHALL not schedule, evict, or mutate canonical state.

#### Scenario: Combat terminal state cannot revive pre-combat cards
- **WHEN** a ready session state produced before combat remains on the session after the terminal
  combat action returns the actor to exploration with a different eligible-affordance digest
- **THEN** the first exploration snapshot emits `suggestions.status = "unavailable"` until a fresh
  generation replaces the stale session state, and no pre-combat card reaches the wire

#### Scenario: Direct relocation suppresses an old in-flight state
- **WHEN** an actor is relocated with `move_to()` while a prior room's options state is generating
  or ready
- **THEN** presentation compares the snapshot fingerprint with the new location's derived
  fingerprint and renders unavailable rather than the prior room's generating line or cards

### Requirement: All committed player relocations and terminal combat returns trigger options
Every committed relocation of an account-owned `PlayerCharacter`, including Exit traversal and a
direct `move_to()` call with movement hooks enabled, SHALL register one fire-and-forget
action-options scheduling callback through `transaction.on_commit`. The observer SHALL not run for
NPC movement, rollback compensation with hooks disabled, or a failed transaction. A successful
  combat action that has returned its actor to exploration SHALL schedule action options only after
  the dispatcher has published its completion update and action result, using every current live
  watcher returned by `watchers_for(actor)`. These lifecycle triggers
  SHALL use the existing watcher, token, epoch, and no-raise scheduling contract.

#### Scenario: Direct teleport schedules fresh options
- **WHEN** a puppeted player is moved directly from one exploration room to another through
  `move_to()` and the relocation transaction commits
- **THEN** watchers of that player receive the normal generating or replay path for the destination
  situation, and no exit-specific hook is required

#### Scenario: Terminal combat schedules after the result
- **WHEN** a successful `combat.cast`, `combat.flee`, or `combat.forfeit` action ends the active
  combat session
- **THEN** the dispatcher sends its terminal completion presentation and action result first, then
  schedules the exploration options trigger for every live watcher of the actor, whose later
  update carries the fresh destination situation only

### Requirement: Dismissal prevents replay from a concurrent older generation
The service SHALL tag each cache entry and pending generation for a fingerprint with a monotonic
ephemeral generation number. `evict(session, actor)` SHALL record a per-session,
per-fingerprint minimum displayable generation number in a separate bounded `session.ndb` barrier
store, in addition to its existing state/token eviction. The barrier store SHALL retain no more
than the option-cache capacity, SHALL clear on puppet change and unpuppet, and SHALL never alter
the exact `options_state` shape. A later trigger for that session SHALL not replay a cache entry or
join a pending generation whose number is older than the recorded minimum. Each fingerprint SHALL
own a chain with one joinable active generation and at most one successor. If another session
still subscribes to an older active generation, the service SHALL retain its delivery and queue the
dismissed session on the successor. If that active generation later loses its final subscriber, it
SHALL leave the joinable registry immediately while an identity-guarded detached completion owned
by the chain starts the still-current successor exactly once when the old Deferred settles. The
successor SHALL derive fresh context after that settlement. Older completions SHALL never overwrite
a newer cache entry, and a barrier SHALL clear only when its session receives an outcome from an
eligible generation.

#### Scenario: One window dismisses while another window remains pending
- **WHEN** sessions A and B share an in-flight generation, A dismisses, and B remains subscribed
- **THEN** B receives the old generation normally, A receives none of it, and A's next trigger
  receives a successor generation rather than a replay of the old generation's cache entry

#### Scenario: A later cache replay is fresh for the dismissing session
- **WHEN** the successor generation for a dismissed fingerprint completes successfully
- **THEN** its cache entry has a generation number meeting the session's barrier, the barrier is
  cleared on delivery, and later triggers for that session may replay that successor entry

#### Scenario: A detached predecessor hands off exactly once
- **WHEN** A dismisses and queues a successor behind an active generation, B then dismisses as the
  active generation's final subscriber, and the detached active Deferred completes
- **THEN** the old generation is absent from the joinable registry, its completion starts the
  current successor exactly once through chain identity checks, and A receives only that successor
  outcome

#### Scenario: A second dismissal bars the queued successor
- **WHEN** a session already queued on a successor dismisses again — raising its barrier above the
  successor's generation — and then triggers
- **THEN** the session never joins the pre-dismiss successor, settles degraded in place with the
  barrier standing, and a later trigger starts fresh work above the barrier

#### Scenario: A successor that cannot name the old situation settles without clearing the barrier
- **WHEN** the actor moved on or the situation vanished before the queued successor started
- **THEN** the successor settles its queued watchers degraded with no memo and without clearing
  their dismissal barriers for the old fingerprint, and the chain drops the successor

### Requirement: Retired pending generations are removed by identity immediately
When `evict()` removes the final subscriber from a pending generation, the service SHALL mark that
generation retired and remove that exact generation from the joinable pending registry immediately.
When a current successor waits behind it, the fingerprint chain alone MAY retain an
identity-bearing detached completion reference solely for successor handoff; that reference SHALL
not be discoverable or joinable by scheduling. The eventual completion and Deferred cleanup SHALL
remain identity-guarded: it SHALL write no cache, memo, or session state, and SHALL not remove a
newer active or successor generation registered for the same fingerprint.

#### Scenario: A retired completion cannot remove replacement work
- **WHEN** the last subscriber dismisses generation N, a later trigger starts generation N+1 for
  the same fingerprint, and generation N then completes
- **THEN** generation N's completion produces no cache or delivery and generation N+1 remains in
  the pending registry until it settles
