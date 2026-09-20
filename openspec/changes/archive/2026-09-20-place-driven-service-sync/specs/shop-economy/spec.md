## MODIFIED Requirements

### Requirement: Player-facing shop commands use only a local unambiguous merchant
The character cmdset SHALL expose stock listing, buy, and sell commands with Traditional Chinese
output. The stock listing SHALL identify the shop by its authored place name rather than a
generic word, so two shops in one settlement are distinguishable by their listing alone.
Commands SHALL resolve one Merchant host in the caller's current room and SHALL not permit
remote dbref interaction. Host acceptance SHALL flow through
`world/rules/service_gate.py::service_available`: `remote` keeps the existing remote-interaction
rejection lineage, and an `off_anchor` or `malformed_binding` verdict SHALL refuse the trade with
the gate's fixed registry message; every refusal writes no transaction, and a co-located,
at-anchor (or `person`-bound) merchant behaves exactly as before the gate existed.

#### Scenario: Altoria merchant is usable through commands
- **WHEN** the player enters the general store during opening hours
- **THEN** list, buy, and sell invoke the same deterministic APIs used by integration tests

#### Scenario: Two shops are distinguishable by their stock listing
- **WHEN** a player lists stock in one shop and then in another in the same settlement
- **THEN** each listing names its own place, and the two headers differ

#### Scenario: A traveling place-bound merchant refuses trade with the fixed line
- **WHEN** the merchant host is moved to the town square beside the player and the player lists
  stock or attempts a purchase
- **THEN** the command replies the gate's fixed `off_anchor` message and no wallet, inventory, or
  stock state changes

#### Scenario: A remote merchant keeps its existing rejection lineage
- **WHEN** the player attempts shop interaction with a merchant in another room
- **THEN** the refusal matches the pre-change remote-merchant behavior
