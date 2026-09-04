# Delta: affinity-system

## MODIFIED Requirements

### Requirement: Deterministic gains apply at talk, trade, and guild success paths
A known-keyword talk answer SHALL grant +1 affinity (`talk` source) with the host NPC through a
deterministic talk writer that resolves the keyword and applies the affinity gain in one
transaction with cache restoration on failure; unknown
keywords and no-keyword paths SHALL grant nothing. A successful buy or sell SHALL grant +1
(`trade` source) with the local Merchant host. Successful guild registration, board acceptance,
and examination start SHALL each grant +1 (`guild` source) with the respective host. Every gain
SHALL be applied through the sole-writer API inside the host operation's all-or-nothing commit, so
a failing or rejected host operation grants nothing. Service hosts SHALL be NPC instances: a
host that cannot hold affinity is rejected before any write, so a successful operation always
carries its gain. When a capped source is blocked by the daily
budget, the call site SHALL present a fixed non-numeric Traditional Chinese hint and SHALL NOT
expose the cap or any number.

#### Scenario: Keyword talk grants affinity and unknown keywords grant nothing
- **WHEN** the player talks to a scripted-dialogue host with a known keyword and then with an
  unknown keyword
- **THEN** the known-keyword answer raises the host's value by 1 and the unknown keyword changes
  nothing

#### Scenario: A failed operation grants no affinity
- **WHEN** a trade, registration, acceptance, or examination is rejected before committing
- **THEN** the involved NPC's affinity record is unchanged

#### Scenario: A non-NPC service host is rejected before any write
- **WHEN** an operation targets a service host that is not an NPC (for example an object
  carrying a Merchant component)
- **THEN** the operation is rejected before any write and no affinity is granted

#### Scenario: A budget-capped gain gives non-numeric feedback
- **WHEN** a capped source would gain affinity but the daily budget is exhausted
- **THEN** the player receives a fixed Traditional Chinese hint that does not contain the cap,
  the budget, or any number, and the NPC's value is unchanged
