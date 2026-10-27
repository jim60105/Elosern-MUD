# Spec Delta

## MODIFIED Requirements

### Requirement: Player-facing shop commands use only a local unambiguous merchant
The character cmdset SHALL expose stock listing, buy, and sell commands with Traditional Chinese
output. The stock listing SHALL identify the shop by its authored place name rather than a
generic word.
shop stock, buy and sell SHALL accept an explicit terminal @#dbid selecting exactly that visible eligible Merchant in the caller's current room, without substitution. Without that suffix they SHALL retain unambiguous implicit discovery. Remote targets SHALL remain forbidden. Host acceptance SHALL flow through
`world/rules/service_gate.py::service_available`, and every refusal writes no transaction.

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

#### Scenario: Gate verdicts map to fixed refusals
- **WHEN** the service gate returns a verdict on a candidate merchant host
- **THEN** `remote` keeps the existing remote-interaction rejection lineage, and an `off_anchor` or
  `malformed_binding` verdict refuses the trade with the gate's fixed registry message

#### Scenario: An at-anchor merchant behaves exactly as before
- **WHEN** a co-located, at-anchor (or `person`-bound) merchant is used
- **THEN** it behaves exactly as before the gate existed

#### Scenario: Place-named listings distinguish same-settlement shops
- **WHEN** two shops operate in one settlement
- **THEN** they are distinguishable by their listing alone

#### Scenario: Explicit provider survives same-class bystanders
- **WHEN** a player supplies the terminal target suffix for a visible eligible provider while another same-class provider is present
- **THEN** only the selected provider is used; if it departs before execution the command rejects without substituting the bystander
