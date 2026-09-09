## ADDED Requirements

### Requirement: run_round accepts an optional first-actor override that reorders the rolled sequence and nothing else
`world/rules/combat.py`'s `run_round()` SHALL accept a keyword-only
`first_actor: str | None = None`. When it is `None`, `run_round()` SHALL behave exactly as it does
without the parameter, including the call it makes into `roll_initiative()`. When it names a key
present in `roll_initiative(battlefield)`'s returned sequence, `run_round()` SHALL move that key to
the head of the sequence and SHALL preserve the relative order of every other key, then iterate the
resulting order. `run_round()` SHALL NOT re-roll, re-score, or bypass `roll_initiative()` in order
to honor the override, SHALL NOT grant the named combatant an additional action, and SHALL NOT skip
any other combatant. A `first_actor` naming a key absent from that sequence — a dead, fled,
knocked-out, or non-roster key — SHALL be a silent no-op that leaves the rolled order untouched and
SHALL NOT raise.

#### Scenario: The named combatant acts first while everyone else keeps their rolled relative order
- **WHEN** `run_round(battlefield, provider, first_actor=key)` runs under a fixed seed for a
  battlefield in which `roll_initiative()` would not have placed `key` first
- **THEN** `key`'s action resolves before every other combatant's, and the remaining combatants act
  in the same relative order they would have under the identical seed with `first_actor=None`

#### Scenario: The override changes order only, never the number of actions
- **WHEN** the same round is run twice under a fixed seed, once with `first_actor=key` and once with
  `first_actor=None`
- **THEN** both rounds resolve exactly one action per capable combatant, and the multiset of acting
  keys is identical between the two runs

#### Scenario: roll_initiative is still the only source of order
- **WHEN** `run_round()`'s implementation is inspected
- **THEN** it obtains its iteration order from `roll_initiative(battlefield)` and applies the
  override as a reordering of that returned sequence, with no alternative scoring path and no extra
  `roll_d100()` call attributable to the override

#### Scenario: A first_actor of None is byte-identical to the pre-parameter behavior
- **WHEN** a round is resolved with `first_actor` omitted and again with `first_actor=None` under
  the identical seed and starting battlefield
- **THEN** every entity's final hp, the emitted `EventLog` sequence including every `"roll"`-kind
  entry's recorded value, and the acting order are identical

#### Scenario: A stale or ineligible first_actor key is a silent no-op
- **WHEN** `run_round()` is called with a `first_actor` naming a combatant who is dead, has fled, is
  knocked out, or is not in the roster at all
- **THEN** the round resolves in the unmodified rolled order without raising, and no combatant is
  added to or removed from the sequence
