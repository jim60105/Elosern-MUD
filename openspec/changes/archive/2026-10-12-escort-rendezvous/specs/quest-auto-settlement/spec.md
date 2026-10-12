# Spec Delta

## ADDED Requirements

### Requirement: Exclusive automatic settlement follows committed winner arbitration
Grouped automatic reward planning SHALL require the arbitration-selected winner before effects are calculated. Invalidated alternatives and no-commission results SHALL contribute no reward or claim. The existing registered-reward planner and exactly-once ledger SHALL remain authoritative, with private rewards merit-free.

#### Scenario: Distinct automatic alternatives pay once
- **WHEN** one event satisfies two separately accepted automatic alternatives
- **THEN** arbitration first selects one winner and exactly its registered copper/items and claim commit; the other record contributes nothing

#### Scenario: Automatic payout failure restores arbitration
- **WHEN** inventory or claim persistence fails after a winner was selected and possession was handed back
- **THEN** group, both records, membership, wallet, inventory, claim ledger, knowledge and live control return to baseline

#### Scenario: Existing cascading acquisition remains atomic
- **WHEN** the winner's reward items satisfy another unrelated automatic ACQUIRE quest
- **THEN** existing inventory progress and both eligible claims commit atomically without granting any invalidated alternative an entitlement

#### Scenario: Complete exclusive automatic settlement follows committed winner arbitration contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** Automatic settlement SHALL retain its pure registered-reward planning and existing claim ledger. For a grouped record, planning SHALL require arbitration-selected winner eligibility before calculating reward effects. Invalidated alternatives and no-commission resolutions SHALL contribute no reward or claim. Group resolution, winner completion, loser invalidation, reason/pin release, participant knowledge and automatic payout SHALL commit in the originating event transaction with existing cache/control compensation. Private rewards SHALL remain merit-free; registry reward values SHALL remain authoritative.
