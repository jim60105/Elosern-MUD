## ADDED Requirements

### Requirement: raise_affinity_cap is the sole cap writer and is monotonic and idempotent
`world/rules/affinity.py` SHALL expose `raise_affinity_cap(npc, player, new_cap) -> bool` as the
only function that mutates a record's `cap`. For a player without a record it SHALL create a fresh
record (value 0, cap 99) and then raise it, so a milestone can never silently fail on a
recordless companion. It SHALL raise the cap only when `new_cap` is strictly greater than the
record's current cap, SHALL leave the value and the daily-gain fields unchanged, SHALL run no
daily-budget logic and no auto-leave hook, and SHALL return whether the cap changed. The ladder
SHALL continue to map values at or above 100 to the topmost stage (絕對羈絆) with no numeric
rendering.

#### Scenario: A matching milestone raises the cap once
- **WHEN** a record's cap is 99 and `raise_affinity_cap` is called with 150
- **THEN** the cap becomes 150, the value is unchanged, and the function returns `True`

#### Scenario: The raise is idempotent
- **WHEN** `raise_affinity_cap` is called again with 150 on a record already at cap 150
- **THEN** the cap stays 150 and the function returns `False`

#### Scenario: The cap only grows
- **WHEN** `raise_affinity_cap` is called with 99 on a record at cap 150
- **THEN** the cap stays 150 and the function returns `False`

#### Scenario: A recordless player gets a fresh raised record
- **WHEN** `raise_affinity_cap` is called for a player with no affinity record on the NPC
- **THEN** a fresh record is created with value 0 and the cap set to `new_cap`, and the function
  returns `True`

#### Scenario: Values above the old natural cap render the topmost stage
- **WHEN** a record's cap is 150 and its value is 130
- **THEN** the displayed stage is 絕對羈絆 and no numeric value or cap is rendered anywhere

### Requirement: The cap_breaks rulebook table drives milestone cap raises at quest turn-in
`rulebook/affinity.yaml` SHALL define a `cap_breaks` list; each entry SHALL carry a `quest_key`
that resolves in the quest definition registry, exactly one matching identity (`npc_key` or
`role`), and an integer `new_cap` strictly above the natural cap 99. Loading SHALL fail closed on
a missing, non-string, or empty `quest_key`, an unresolvable `quest_key`, an entry with neither
`npc_key` nor `role`, an entry carrying both `npc_key` and `role` (decided by key presence, so a
mistyped selector never silently falls back to the other one), a non-integer `new_cap`, a
`new_cap` at or below 99, or two entries with the same `quest_key` and the same selector
(`npc_key` and `role` are distinct selectors). When a
guild quest is turned in, the deterministic reward
settlement SHALL look up `cap_breaks` by the completed `quest_key` and, for every then-in-party
companion matching the entry's `npc_key` or role, call `raise_affinity_cap` with the entry's
`new_cap` inside the same atomic transaction as the reward and the `quest_completion` affinity
gain, and SHALL apply the cap raise before the `quest_completion` gains so a record sitting at the
old cap cannot clamp the +2 gain. A companion matching multiple entries of one quest SHALL resolve
to the highest `new_cap`, independent of entry order. Entries matching no in-party companion
SHALL be no-ops.

#### Scenario: Turn-in raises the cap for each matching companion
- **WHEN** a turn-in completes a quest with a `cap_breaks` entry while two matching companions are
  in the party
- **THEN** both companions' caps rise to the entry's `new_cap` in the same transaction as the
  reward, and a non-matching companion's cap is unchanged

#### Scenario: A cap break does not lose the turn-in gain
- **WHEN** a matching companion's record sits at value 99 with cap 99 at turn-in
- **THEN** the cap rises to the entry's `new_cap` first and the +2 `quest_completion` gain then
  applies, leaving the value at 101 with the raised cap

#### Scenario: A recordless matching companion still gets its cap break
- **WHEN** a matching in-party companion has no affinity record at turn-in
- **THEN** the turn-in creates a fresh record raised to the entry's `new_cap` and applies the +2
  gain on top

#### Scenario: A non-matching entry is a no-op
- **WHEN** a turn-in completes a quest whose `cap_breaks` entry matches no in-party companion
- **THEN** the reward and +2 gains commit normally and no cap changes anywhere

#### Scenario: Re-completing a milestone is idempotent
- **WHEN** a milestone quest is turned in again after its cap break already fired
- **THEN** no cap changes and the transaction commits normally

#### Scenario: Multiple matching entries resolve to the highest new_cap
- **WHEN** one companion matches two entries of the same quest with different `new_cap` values
- **THEN** the cap is raised to the highest of the two, regardless of entry order

#### Scenario: A malformed cap_breaks table is rejected at load
- **WHEN** an entry omits `quest_key`, references an unknown quest, omits both `npc_key` and
  `role`, declares both `npc_key` and `role`, duplicates another entry's `quest_key` and selector,
  or declares `new_cap` at or below 99
- **THEN** loading the rulebook fails closed with a named validation error