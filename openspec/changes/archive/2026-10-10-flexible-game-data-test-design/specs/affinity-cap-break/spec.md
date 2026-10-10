# Spec Delta

## MODIFIED Requirements

### Requirement: The cap_breaks rulebook table drives milestone cap raises at quest turn-in
`rulebook/affinity.yaml` SHALL define a `cap_breaks` list; each entry SHALL carry a `quest_key` that resolves in the quest registry, exactly one matching identity (`npc_key` or `role`), and an integer `new_cap` strictly above the natural cap 99; loading SHALL fail closed on malformed entries. When a guild quest is turned in, the settlement SHALL look up `cap_breaks` by the `quest_key` and, for every then-in-party matching companion, call `raise_affinity_cap` with the entry's `new_cap`.

#### Scenario: Turn-in raises the cap for each matching companion
- **WHEN** a turn-in completes a quest with a `cap_breaks` entry while two matching companions are
  in the party
- **THEN** both companions' caps rise to the entry's `new_cap` in the same transaction as the
  reward, and a non-matching companion's cap is unchanged

#### Scenario: A cap break does not lose the turn-in gain
- **WHEN** a matching companion's record sits at value 99 with cap 99 at turn-in
- **THEN** the cap rises to the entry's `new_cap` first and the declared `quest_completion` gain then
  applies, leaving value `min(new_cap, 99 + declared_gain)` with the raised cap

#### Scenario: A recordless matching companion still gets its cap break
- **WHEN** a matching in-party companion has no affinity record at turn-in
- **THEN** the turn-in creates a fresh record raised to the entry's `new_cap` and applies the declared quest-completion
  gain on top

#### Scenario: A non-matching entry is a no-op
- **WHEN** a turn-in completes a quest whose `cap_breaks` entry matches no in-party companion
- **THEN** the reward and the declared quest-completion gains commit normally and no cap changes anywhere

#### Scenario: Re-completing a milestone is idempotent
- **WHEN** a milestone quest is turned in again after its cap break already fired
- **THEN** no cap changes and the transaction commits normally

#### Scenario: Multiple matching entries resolve to the highest new_cap
- **WHEN** one companion matches two entries of the same quest with different `new_cap` values
- **THEN** the cap is raised to the highest of the two, regardless of entry order

#### Scenario: The turn-in lookup is the deterministic reward settlement
- **WHEN** a guild quest is turned in
- **THEN** it is the deterministic reward settlement that performs the `cap_breaks` lookup for the completed `quest_key`, matching each entry's `npc_key` or role

#### Scenario: The cap raise rides the reward transaction and precedes the gain
- **WHEN** the turn-in raises a matching companion's cap
- **THEN** `raise_affinity_cap` runs inside the same atomic transaction as the reward and the `quest_completion` affinity gain, and the cap raise is applied before the `quest_completion` gains so a record sitting at the old cap cannot prematurely clamp the declared quest-completion gain

#### Scenario: Entry identity validation details
- **WHEN** a `cap_breaks` entry is loaded
- **THEN** the exactly-one-identity choice between `npc_key` and `role` is decided by key presence, so a mistyped selector never silently falls back to the other one, and `npc_key` and `role` are distinct selectors for duplicate detection

#### Scenario: The full fail-closed offense list
- **WHEN** the loader validates the `cap_breaks` table
- **THEN** it fails closed on a missing, non-string, or empty `quest_key`, a `quest_key` that does not resolve in the quest definition registry, an entry with neither `npc_key` nor `role`, an entry carrying both `npc_key` and `role`, a non-integer `new_cap`, a `new_cap` at or below 99, or two entries with the same `quest_key` and the same selector

#### Scenario: A malformed cap_breaks table is rejected at load
- **WHEN** an entry omits `quest_key`, references an unknown quest, omits both `npc_key` and
  `role`, declares both `npc_key` and `role`, duplicates another entry's `quest_key` and selector,
  or declares `new_cap` at or below 99
- **THEN** loading the rulebook fails closed with a named validation error

#### Scenario: Independently known cap-order fixture
- **WHEN** a synthetic quest rule grants 2 to value 99 and raises cap to 150
- **THEN** the committed value is 101, whereas a failed reward commit restores both value 99 and cap 99; this does not pin the production quest gain

