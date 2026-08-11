## ADDED Requirements

### Requirement: Shop economy stays consistent with the canonical inventory

Buy and sell SHALL keep operating on `db.inventory` as today, and their preflight checks SHALL remain authoritative for stock, funds, and holdings regardless of object containment.

#### Scenario: Sell sees every canonical item including picked-up ones

- **WHEN** a player picked up a registry item via `拿` and then opens the shop sell flow
- **THEN** the item appears in sellable holdings and selling removes its key from `db.inventory`

#### Scenario: Buy materializes the contained object

- **WHEN** a player buys a registry item
- **THEN** the item's Evennia Object exists in the character's containment in the same transaction as the key-list write, so it can be dropped or given
