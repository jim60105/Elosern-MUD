# Delta spec: quest-auto-settlement (quest-auto-settlement)

## ADDED Requirements

### Requirement: Automatic settlement is planned by a pure function

`plan_auto_settlement(actor, completed_records)` SHALL compute, without performing any write and
without reading the world clock, the settlement plan for every supplied record that has just reached
`COMPLETED`. A record SHALL contribute to the plan only when its issuance resolves, that issuance's
settlement mode is `AUTO`, and its quest ID is absent from the actor's reward-claim ledger. The plan
SHALL carry the wallet delta, the inventory additions, and the claim identities to append, derived
from the resolved issuance's immutable reward — never from a value stored on the record. A record
under a `COUNTER` issuance, an already-claimed record, or a record whose issuance no longer resolves
SHALL contribute nothing.

#### Scenario: An automatic commission contributes its registered reward
- **WHEN** a record completing under an `AUTO` issuance with copper and item rewards is planned
- **THEN** the plan carries exactly that issuance's copper delta, its item additions, and that quest
  ID as a claim

#### Scenario: A counter commission contributes nothing
- **WHEN** a record completing under a `COUNTER` issuance is planned
- **THEN** the plan is empty and the quest remains claimable at its counter

#### Scenario: An already-claimed quest contributes nothing
- **WHEN** a record whose quest ID is already in the reward-claim ledger is planned
- **THEN** the plan is empty

#### Scenario: An unresolvable issuance contributes nothing without raising
- **WHEN** a record completes under an issuer key for which no issuance is registered any more
- **THEN** the plan is empty and no error is raised

#### Scenario: Planning writes nothing
- **WHEN** the planner runs against an actor with completing records
- **THEN** the actor's wallet, inventory, quest log, and reward claims are byte-for-byte unchanged

### Requirement: Automatic settlement commits atomically with the completing transition

Every quest-log write path SHALL commit the settlement plan inside the same transaction that writes
the completing record, so a quest can never be observed complete but unpaid, nor paid but not
complete. `apply_quest_log_replacement` SHALL commit it inside its existing transaction;
`apply_quest_log_delta` SHALL commit it inside the caller's transaction, performing no nested
transaction of its own; and `pending_effects_for_transition` SHALL expose it as additional
`PendingEffect` values so the action resolver commits it with the originating action's own effects.
A failure anywhere in the settlement SHALL roll back the completion together with the payout,
restoring every snapshotted surface.

#### Scenario: Arrival completion settles in the same transaction
- **WHEN** a REACH objective completes on room arrival under an `AUTO` issuance
- **THEN** the record is `COMPLETED`, the wallet and inventory carry the reward, and the quest ID is
  claimed, all committed together

#### Scenario: Combat completion settles with the action
- **WHEN** a DEFEAT objective completes from a committed combat action under an `AUTO` issuance
- **THEN** the reward is committed by the action resolver alongside the action's own effects, in one
  transaction

#### Scenario: Inventory-driven completion settles inside the caller's transaction
- **WHEN** an ACQUIRE objective completes from a committed inventory delta under an `AUTO` issuance
- **THEN** the settlement commits inside that caller's transaction with no nested transaction

#### Scenario: A failed payout rolls back the completion
- **WHEN** persistence is fault-injected during the settlement write of a completing automatic quest
- **THEN** the quest log, wallet, inventory, reward claims, and their in-process caches all equal
  their pre-transition values

#### Scenario: A settlement reward completes another active ACQUIRE quest
- **WHEN** a completing automatic quest's item rewards satisfy another active ACQUIRE objective
- **THEN** that quest completes in the same transaction and its own automatic reward settles with
  it, exactly as a counter-paid reward item would advance the objective

#### Scenario: A counter reward completing an automatic quest keeps both claims
- **WHEN** a counter turn-in's reward items complete an active ACQUIRE quest under an automatic
  issuance
- **THEN** both quest IDs appear exactly once in the shared ledger and both rewards are paid

### Requirement: Automatic settlement never grants merit and never needs a host

Automatic settlement SHALL pay only copper and items. It SHALL NOT write guild merit, SHALL NOT
require a local service host, SHALL NOT require a guild registration, and SHALL NOT consult a
service schedule. Merit remains guild currency granted only by the counter turn-in path, and the
private-commission issuance validation already guarantees a zero merit reward.

#### Scenario: A private commission pays no merit anywhere
- **WHEN** an automatic commission settles
- **THEN** the actor's guild merit is unchanged

#### Scenario: Settlement succeeds far from any service host
- **WHEN** an automatic commission completes in a wilderness room with no NPC present
- **THEN** the reward is settled and no host resolution is attempted

### Requirement: Automatic settlement emits its own boundary event

Each automatic settlement SHALL emit the settlement boundary event through the observability facade,
carrying at least the `char`, `quest`, and `issuer` context keys, so an automatic payout is
distinguishable in the log from a counter turn-in. A settlement that pays nothing because the plan
was empty SHALL emit no payout event.

#### Scenario: A payout is traceable
- **WHEN** an automatic commission settles
- **THEN** one settlement event is emitted carrying the character, quest, and issuer context

#### Scenario: An empty plan is silent
- **WHEN** a quest completes under a `COUNTER` issuance
- **THEN** no automatic-settlement payout event is emitted
