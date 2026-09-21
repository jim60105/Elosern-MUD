# altoria-sanctum Specification

## Purpose
Land the capital's 光明神殿 and its attached 聖所 as one building's three open
counters — worship, the sanctum's ministry, and the shop that supplies it —
authored in the openness register the world document requires, trading through
the ordinary merchant path with no branch anywhere naming the temple, the
sanctum, or the kind of goods its counter keeps.

## Requirements

### Requirement: The temple is one building with three open counters
The capital's sanctuary SHALL be authored as worship, ministry and commerce occupying one
location openly, never as a public face with a concealed interior. Its rooms, descriptions,
host titles and dialogue SHALL NOT frame the sanctum's ministry or its shop as hidden,
restricted, discovered, or as something an outsider is not expected to know about. No lock,
reveal, plot gate, knowledge check or discovery step SHALL stand between a player and any of
the three, because the world holds the sanctum's business to be common knowledge.

#### Scenario: Nothing about the sanctuary is gated
- **WHEN** a player who has never visited walks into the sanctuary and its shop
- **THEN** both are enterable, the shop's stock lists on first request, and no lock, reveal
  step or knowledge prerequisite is consulted

#### Scenario: The authored text does not treat the ministry as concealed
- **WHEN** the sanctuary's room descriptions, host titles and dialogue responses are read
- **THEN** none of them describes the ministry or the shop as hidden, secret, restricted or
  surprising

### Requirement: The sanctum's goods trade through the ordinary path
The sanctum's shop SHALL be an ordinary merchant place. Its goods SHALL be listed, bought and
sold through exactly the commands and the resolution path every other shop uses, with no
branch anywhere in the trade path that tests for this shop, this settlement, or the kind of
goods it carries.

#### Scenario: Buying from the sanctum shop uses the same path as any shop
- **WHEN** a player lists stock and buys from the sanctum's shop
- **THEN** the transaction resolves through the same merchant, wallet and stock code every
  other shop uses, and the goods' category is read nowhere in it

#### Scenario: No special case names this shop
- **WHEN** the trade path is searched for a branch on this shop, its settlement or its goods'
  kind
- **THEN** none exists

### Requirement: Two places may share one doorstep
The sanctuary and its shop SHALL be two place records attached to the same exterior, each with
its own interior and its own doorway name. They are two counters in one building, and the map
SHALL represent that as one square with two doors rather than as two separate buildings.

#### Scenario: One exterior, two doors, two interiors
- **WHEN** synchronization completes
- **THEN** the shared exterior holds one doorway exit per place, each leads to its own
  interior, and each interior leads back out to that same exterior

### Requirement: The sanctuary's host ministers and does not trade
The sanctuary's own host SHALL carry a dialogue capability and no trade capability: her
counter blesses, preaches and answers questions about the ministry, and sells nothing. The
shop's host SHALL carry the trade capability; like every capital merchant she answers from
her own shopkeeper's table about her own goods, never from the sanctuary's offices.
Affinity with the sanctuary SHALL therefore accumulate through conversation and affinity
with its shop through trade, matching how every other location's primary channel is already
decided by which capability its host carries.

#### Scenario: The two hosts' trade offices are disjoint
- **WHEN** both hosts' components are inspected after synchronization
- **THEN** the sanctuary's host carries a scripted-dialogue component and no merchant
  component, and the shop's host carries a merchant component; the priest's own table
  ships no trade guidance she could not execute
