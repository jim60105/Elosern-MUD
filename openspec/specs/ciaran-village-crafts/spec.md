# ciaran-village-crafts Specification

## Purpose
Give 暗影谷村 the two makers the lore document names but the village never had — an
adornment-maker and a herbalist — trading from their own dwellings on the ordinary
merchant path, and pin the pricing philosophy that makes their goods the village's
everyday things regardless of what the same keys fetch in the capital.

## Requirements

### Requirement: The village supplies adornments and remedies from two more homes
The village SHALL carry adornment-making and herbal-remedy trade in two homes through the ordinary merchant path. Staffing, personal identity and sex SHALL follow authored place declarations. Declared hosts SHALL retain dwelling-appropriate titles rather than shopkeeper, merchant or proprietor titles; personnel edits SHALL NOT alter the two homes or introduce settlement-specific trade logic.

#### Scenario: Both homes trade like any shop
- **WHEN** a player enters each and buys
- **THEN** the transaction resolves through the ordinary merchant path, and nothing in that
  path tests for this settlement or its archetype

#### Scenario: Neither host is titled as a shopkeeper
- **WHEN** every declared craft-home host's title is inspected
- **THEN** none describes its bearer as a shopkeeper, merchant or proprietor

### Requirement: An elven-made good is everyday at home whatever it is worth abroad
A good the village makes SHALL be priced in the village as the everyday thing it is there,
independently of its rarity and of what the same key fetches elsewhere. The same item key MAY
therefore carry two very different prices in two settlements, and SHALL remain one item:
what a player buys in the village is indistinguishable from what they buy in the capital.

#### Scenario: One key, two prices, one item
- **WHEN** a key offered in both settlements is bought in each
- **THEN** the resolved prices differ, and the two acquired items are the same item definition

#### Scenario: Rarity does not raise the village price
- **WHEN** a village good's rarity and its village price are compared
- **THEN** the price follows the village's everyday scale, and rarity is read nowhere in
  resolving it
