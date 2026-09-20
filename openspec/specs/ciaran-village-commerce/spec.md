# ciaran-village-commerce Specification

## Purpose
Make 暗影谷村 playable as a settlement with no commerce — goods traded from
villagers' homes out of interest rather than trade — while proving that
costs no mechanism of its own.

## Requirements

### Requirement: A settlement without shops is fully playable
The village SHALL let a player buy and sell as freely as a human town does.
A settlement whose culture has no commercial premises SHALL NOT therefore be
a settlement a player can only look at.

Its trading locations SHALL be villagers' homes: named for their occupant,
described as dwellings, and holding no counter, sign or shopfront. The host
SHALL be the villager, and the goods SHALL be what that villager happens to
be interested in making or collecting.

Host titles SHALL NOT use words denoting a commercial establishment or its
proprietor. The settlement has no such establishments.

#### Scenario: A player supplies themselves in the village
- **WHEN** a player arrives in the village and visits its homes
- **THEN** they can buy and sell goods across the village's several hosts,
  as they could across a town's shops

#### Scenario: The locations read as homes
- **WHEN** a village trading location's name and description are read
- **THEN** they name an occupant and describe a dwelling, and mention no
  shop, counter, sign or trade

#### Scenario: Hosts are not proprietors
- **WHEN** the village hosts' titles are read
- **THEN** none of them uses a word denoting a shop owner or a shopkeeper

### Requirement: Trading without commerce uses the identical mechanism
Buying from and selling to a village host SHALL traverse exactly the code
path a capital shop traverses. There SHALL be no alternative trade verb, no
second host type, no settlement-archetype branch and no special case
anywhere between the player's command and the committed transaction.

Wallet, inventory, stock, acquisition progress and merchant affinity SHALL
settle identically, in one transaction, on the same terms. Opening hours,
restocking and the service-anchoring gate SHALL apply to a village host as
they do to a town merchant.

The difference between a shop and a villager's home SHALL be entirely in
authored data.

#### Scenario: A village purchase settles like a town purchase
- **WHEN** a player buys from a village host
- **THEN** wallet, inventory, stock, acquisition progress and the host's
  affinity settle exactly as they do for a purchase from a town shop

#### Scenario: No archetype branch exists in the trade path
- **WHEN** the trade and shop-command paths are inspected for a settlement
  archetype or village special case
- **THEN** none exists

#### Scenario: A village host obeys the anchoring gate
- **WHEN** a village host is moved away from the home it anchors to and a
  player attempts to trade
- **THEN** the refusal is the same fixed anchoring message a displaced town
  merchant produces

### Requirement: The village's hosts are its own people
Each of the village's hosts SHALL be authored as an elf of the branch native
to that village, and each SHALL carry an authored sex. None SHALL fall back
to a default race.

#### Scenario: Hosts carry the village's own lineage
- **WHEN** the village's hosts are created by synchronization
- **THEN** each carries the elf race and the branch subrace bound to that
  village, with race baselines applied

#### Scenario: Host sex is authored, not defaulted
- **WHEN** the village's hosts are created
- **THEN** each carries its authored sex rather than the unspecified default

### Requirement: One good is sold at two prices in two settlements
A good the village produces and the capital imports SHALL be offered in both
settlements at prices that differ by orders of magnitude, reflecting that
the village trades nothing outward.

Both offers SHALL resolve to one item key backed by one item definition: an
item bought in either settlement SHALL be indistinguishable from the other
in inventory, in equipment, and in every effect it has.

Each settlement SHALL reach that good through its own assortment. A
settlement that trades one imported good SHALL NOT thereby reference the
producing settlement's assortment, because that would stock a foreign
craftsman's whole shelf.

Two shops offering one item key through two different assortments SHALL be
accepted. The duplicate-goods rejection is scoped to a single shop
referencing two assortments that overlap; two shops in two settlements are
the case this whole model exists to serve.

#### Scenario: The same good costs very different amounts
- **WHEN** a player prices the good in the village and in the capital
- **THEN** the capital's price is far higher, and both prices pass band
  validation

#### Scenario: The goods are the same good
- **WHEN** a player buys the item in each settlement
- **THEN** both purchases yield the same item key backed by the same item
  definition, and the two are interchangeable in inventory and in use

#### Scenario: Importing one good does not import a shelf
- **WHEN** the importing settlement's offered goods are collected
- **THEN** they include that one good and none of the other goods in the
  producing settlement's assortment

#### Scenario: Two shops may offer one key through two assortments
- **WHEN** two shops in two settlements each reference an assortment
  containing the same item key
- **THEN** the catalog loads, and each shop resolves that key at its own
  assortment's price
