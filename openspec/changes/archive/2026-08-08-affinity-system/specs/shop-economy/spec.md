## MODIFIED Requirements

### Requirement: Buying and selling commit wallet, inventory, acquisition progress, and stock atomically
`buy()` and `sell()` SHALL require positive integer quantity, local open Merchant, known offered item,
and sufficient complete funds/stock/inventory. Buying SHALL subtract exact copper, add repeated item keys,
and decrement stock. Selling SHALL remove the quantity, add exact copper, and increment stock without
exceeding max. Buying SHALL stage ACQUIRE progress; selling SHALL not reverse it. A successful buy or
sell SHALL additionally grant +1 affinity (`trade` source) with the local Merchant host through the
sole-writer affinity API (`world/rules/affinity.py`) within the same transaction. Every surface —
wallet, inventory, quest log, merchant stock, the host's `relations_data` affinity attribute, and
the actor's traits — SHALL commit in one transaction with cache restoration: the trade snapshot
SHALL include the host's affinity record and a failed trade SHALL restore it alongside the other
surfaces.

#### Scenario: Successful purchase uses integer copper
- **WHEN** a player with 100 copper buys two 20-copper items from stock 3
- **THEN** wallet is 60, two item keys are added, stock is 1, the merchant's affinity value rises
  by 1, and no float is created

#### Scenario: Insufficient funds changes nothing
- **WHEN** total exact price exceeds wallet
- **THEN** wallet, inventory, quest log, merchant stock, and the merchant's affinity record remain
  unchanged

#### Scenario: Sale cannot overflow merchant stock
- **WHEN** selling the requested quantity would exceed max stock
- **THEN** the complete sale is rejected rather than partially accepted or clamped, and no affinity
  is granted

#### Scenario: Fault injection restores every trade surface
- **WHEN** any wallet, inventory, quest-log, stock, or affinity write raises during trade
- **THEN** database and in-process values for all five surfaces equal their pre-trade values
