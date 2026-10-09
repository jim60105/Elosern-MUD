## MODIFIED Requirements

### Requirement: The quest book discloses each quest's commissioner and settlement

Each quest book row SHALL render the issuer label from its `quest_log` row and SHALL indicate whether
the quest settles at a counter or on completion, so a player can tell a guild commission from a
private one and knows whether a return trip is required. The row SHALL render the structured reward
when the panel carries one, formatting copper, merit, and each item with its quantity from the
`reward` object alone, and SHALL render nothing in its place when the panel carries `null`. The
client SHALL render exactly one client-owned 獎勵 label without duplicating it, and SHALL NOT
render a merit figure of zero.

#### Scenario: A guild quest shows its counter requirement
- **WHEN** a row whose settlement is `counter` renders
- **THEN** it shows the issuing guild label and indicates the reward is claimed at the counter

#### Scenario: A private commission shows automatic settlement
- **WHEN** a row whose settlement is `auto` renders
- **THEN** it shows the commissioner's label and indicates the reward settles on completion

#### Scenario: A missing reward line renders nothing rather than a placeholder
- **WHEN** a row's `reward` is `null`
- **THEN** no reward text and no placeholder appears on that row

#### Scenario: The reward renders from the structured object exactly once
- **WHEN** a row's `reward` carries copper 50, merit 25, and two of one item
- **THEN** the row shows the copper amount, the merit amount, and the item name with quantity two, and the reward label appears once
