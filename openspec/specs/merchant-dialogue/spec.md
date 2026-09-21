# merchant-dialogue Specification

## Purpose
A shopkeeper answers: the rule that every merchant service host carries a dialogue table
alongside its trade capability — a merchant place with no authored table fails load rather
than shipping a silent host — and the rule that a trading host's register follows its
settlement's culture, so a village host sharing what it makes never speaks as a proprietor.

## Requirements

### Requirement: Every merchant host answers when spoken to
A merchant service host SHALL carry a dialogue capability alongside its trade capability, and
every merchant place SHALL author the dialogue table its host answers from. A merchant place
that authors no dialogue key SHALL fail load naming the place: a shopkeeper who cannot be
spoken to is the defect this rule removes, so an unauthored table is an authoring error rather
than a silent default.

#### Scenario: Talking to a shopkeeper gets an answer
- **WHEN** a player talks to a merchant host
- **THEN** its authored greeting is returned, and its authored keywords answer

#### Scenario: A merchant place without a dialogue key fails load
- **WHEN** a synthetic merchant place authoring no dialogue key is loaded
- **THEN** validation raises naming the place and the missing identity kwarg

#### Scenario: Trade is unaffected by the added capability
- **WHEN** stock is listed and goods are bought and sold from a merchant host
- **THEN** the results are identical to before the dialogue capability was added

### Requirement: A trading host speaks as its settlement, not as a shop template
A merchant host's authored dialogue SHALL match the register its settlement's culture
establishes, not a single shopkeeper template applied everywhere. In a settlement whose
premise is that trading is sharing rather than business, the host SHALL NOT speak as a
proprietor, quote business hours as a policy, or describe its goods as stock.

#### Scenario: A village host does not speak as a shopkeeper
- **WHEN** the elven village hosts' authored dialogue is read
- **THEN** none of it presents the host as a proprietor running a business, and none refers to
  its goods as shop stock

#### Scenario: Each host's dialogue names what it deals in
- **WHEN** a player asks each merchant host about its goods
- **THEN** each answers about what that host actually offers, not with a shared generic line
