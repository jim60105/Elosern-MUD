# Spec Delta

## ADDED Requirements

### Requirement: Counter claims require the exclusive group's selected winner
Grouped counter payout SHALL require its persisted selected winner and existing completed/local-authorized-issuer/registered-offer/unclaimed-ledger gates. Invalidated and no-commission results SHALL have no entitlement. Private rewards SHALL remain merit-free and registry-derived. Later claims SHALL not re-arbitrate or reopen offers.

#### Scenario: Winner alone may claim later
- **WHEN** a counter-mode group resolves and the winner and an invalidated alternative are subsequently submitted for turn-in
- **THEN** the winner receives its registered reward once through the existing ledger and the loser receives a named ineligible refusal with no wallet/item/merit/claim changes

#### Scenario: Repeated counter claim and no-commission claim pay nothing
- **WHEN** a winner's claim repeats or a physical result without an accepted commission is presented for payout
- **THEN** the existing claim refusal or missing-entitlement result changes no reward state

#### Scenario: Complete counter claims require the exclusive group's selected winner contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** Counter settlement SHALL retain existing parsed completed record, actual authorized local issuer/registered offer, immutable reward and exactly-once ledger requirements. A grouped record SHALL additionally be the persisted arbitration-selected winner. Invalidated alternatives and no-commission results SHALL have no counter entitlement. Private rewards SHALL grant no merit. A later counter claim SHALL not re-arbitrate a resolved group or reopen offers. General/temporary companion affinity consumers SHALL use the canonical effective roster at settlement under existing then-in-party rules.
