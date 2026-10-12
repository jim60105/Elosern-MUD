# Spec Delta

## Purpose
Persist and arbitrate explicit shared physical results across distinct commissions, closing obsolete alternatives and granting at most one settlement entitlement.

## ADDED Requirements

### Requirement: Exclusive groups preserve distinct commissions and durable result identity
Explicit groups SHALL retain distinct commission identities and persist one unique owner/package/group result with committed source and winner or no-commission outcome. Acceptances SHALL have monotonic sequences allocated under the same group lock. Acceptance alone SHALL not close alternatives; thread identity SHALL imply no exclusivity.

#### Scenario: Distinct alternatives stay open until the result
- **WHEN** either issuer is encountered first and physically valid alternatives are accepted in the same world tick
- **THEN** separate records, rewards and protected bindings remain, with distinct acceptance sequences and unresolved group state

#### Scenario: Same storyline does not suppress unrelated offers
- **WHEN** one explicit group resolves while an unrelated commission shares its story thread
- **THEN** the unrelated commission and its offer remain unchanged

#### Scenario: Complete exclusive groups preserve distinct commissions and durable result identity contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** A validated group SHALL name concrete final result semantics and explicit alternative commission references. Thread identity alone SHALL imply no exclusivity. Each alternative SHALL retain its own definition, issuer, record, protected roles, deadline and registered reward. State SHALL be unique under owner/package/group identity and carry unresolved/resolved status, committed resolution source, and winning accepted record or an explicit no-commission result. Acceptance SHALL allocate a monotonic group sequence under the same lock, with stable record identity as a tie-breaker. Accepting one offer SHALL not close the others.

### Requirement: Authoritative result arbitration grants at most one winner
The quest owner SHALL lock/revalidate a satisfying final result before reward planning, select an attributable terminal record by acceptance sequence then stable identity, complete its winner and invalidate active alternatives. Unaccepted obsolete offers SHALL close. All result effects SHALL commit atomically with cache/control compensation.

#### Scenario: Simultaneous alternatives produce one stable winner
- **WHEN** a settled event terminally satisfies several attributable alternatives in fixtures exercising both issuer-first orders
- **THEN** sequence and stable record identity choose one winner, exactly one settlement entitlement exists, accepted losers are invalidated and unaccepted offers close

#### Scenario: Actual moved actor constrains attribution
- **WHEN** an earlier accepted record is physically satisfiable but unrelated to the event's moved/bound protected actors and a later accepted record is attributable
- **THEN** only the attributable candidate can win

#### Scenario: Meeting movement attributes the stationary protected participant
- **WHEN** the exact meeting role moves or activates beside a stationary protected actor bound to a terminally eligible accepted escort
- **THEN** owner-resolved event provenance and indexed meeting/protected references identify that participating exact protected binding, its record may win and receive registered settlement, and unrelated physically satisfiable records are not attributed

#### Scenario: Active intermediate records forbid no-winner fallback
- **WHEN** the declared physical result holds but active alternatives have no pre-event terminally eligible attributable candidate or already consumed that source's transition
- **THEN** the group remains unresolved with result_unsatisfied, no active record is invalidated and no entitlement is lost; a later distinct authoritative source may evaluate the resulting current stage

#### Scenario: Resolution replay and stale acceptance are inert
- **WHEN** the committed source repeats after restart or a closed alternative's old capability is submitted
- **THEN** resolution identity and winner remain unchanged, no reward/source release repeats, and acceptance reports `outcome_resolved`

#### Scenario: Fault after arbitration rolls back the whole result
- **WHEN** failure occurs after group, loser, membership, handback, reward or narrative writes
- **THEN** no outcome is committed and reload plus live control/caches match the pre-result baseline

#### Scenario: Complete authoritative result arbitration grants at most one winner contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** The quest owner SHALL lock/revalidate the group and relevant records on a satisfying final-result event before reward planning. Eligibility SHALL use pre-event stage and consumed-source state. Attribution SHALL identify actual participating protected bindings from moved/bound actors or the indexed declared relation of moved/activated meeting roles, never unrelated physically satisfied records. Several terminally satisfying attributable records SHALL be ordered by monotonic acceptance sequence, then stable record identity. The winner SHALL transition to `COMPLETED`; active alternatives SHALL become `INVALIDATED` with a structured obsolete-outcome reason; unaccepted alternatives SHALL close. The same transaction SHALL release affected source reasons/pins, commit result identity, participant knowledge/dialogue phases and required automatic settlement. Technical failure SHALL restore all durable/cache/control surfaces.

### Requirement: Unaccepted physical results close offers without inventing a quest
Actual declared rendezvous SHALL resolve without a commission when no active alternative exists. The result SHALL commit participant memory/phases and close obsolete offers with no invented record, acceptance or claim. Active accepted alternatives without a terminally eligible attributable candidate SHALL keep the group unresolved; no fallback SHALL bypass their pre-event stage or source-consumption rules. Existing terminal history SHALL gain no retroactive reward.

#### Scenario: Reunion without acceptance has no payout
- **WHEN** actual roles meet under the declared relation before any commission acceptance
- **THEN** the group resolves without a winner, offers close, participant dialogue reaches acknowledgment then closure/everyday content, and wallet/claims/quest log receive no invented reward or record

### Requirement: Outcome operations expose named transaction ownership
`resolve_exclusive_outcome` SHALL accept owner/package/group and authoritative final source and return original resolution, winner/no-commission, invalidated records and closed offers. It SHALL join the event transaction and arbitrate before rewards. `exclusive_outcome_status` SHALL read state/source/winner without mutation. Unknown group, invalid source, unsatisfied result and write failure SHALL have stable named outcomes.

#### Scenario: Downstream consumer reads a no-commission result
- **WHEN** a later story dispatcher queries a resolved group that had no accepted quest
- **THEN** it receives the explicit no-commission result and committed source identity with no side effect

#### Scenario: Complete outcome operations expose named transaction ownership contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** `resolve_exclusive_outcome` SHALL consume owner/package/group identity and an authoritative settled source with actual moved/bound actor identities; return resolution identity, winner or explicit no-commission result, invalidated records and closed offers; and report `unknown_group`, `invalid_source`, `result_unsatisfied`, or `outcome_write_failed`. A resolved replay SHALL return `already_resolved` with the original result. It SHALL join the caller's authoritative event transaction, lock/revalidate before planning rewards, and defer presentation until commit. A read-only `exclusive_outcome_status` operation SHALL return unresolved/resolved state, original source and winner/no-commission result without accepting or paying a commission.
