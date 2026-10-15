# Spec Delta

## MODIFIED Requirements

### Requirement: The turn loop consumes actions_per_turn as the round's action count, with zero skipping before ActionResolver is called
`world/rules/combat.py`'s `run_round()` SHALL consult each acting combatant's combat-modifier
evaluation (the merged bundle and the matched rules' per-rule bundles) and consume the table's
`actions_per_turn` output as that combatant's action count for the round. The zero-lock decision
SHALL read the matched rules' per-rule zero-action results, and every entity not locked SHALL
provision its count from the merged bundle's positive `actions_per_turn` value, except an allied actor in an interactive player session SHALL have at most one selected-command slot. This exception never adds a slot under a zero-action lock. Enemy and noninteractive slot behavior SHALL remain unchanged.

#### Scenario: A climax-in-progress combatant's turn is skipped, not attempted
- **WHEN** `evaluate_combat_modifiers(entity)` returns `{"actions_per_turn": 0}` for the acting
  combatant
- **THEN** `ActionResolver.resolve()` is never called for that combatant this round, and the round's
  event list contains an `"action_skipped"` entry naming that combatant

#### Scenario: No source-level branch distinguishes the modifier's origin
- **WHEN** `world/rules/combat.py`'s source is inspected
- **THEN** it contains no conditional that special-cases a sexual-origin `actions_per_turn` modifier
  differently from a buff-origin one — both are read from the identical bundle key

#### Scenario: An absent or one-valued key resolves exactly one action
- **WHEN** a round runs with every combatant's bundle carrying no `actions_per_turn` key or the
  value `1`
- **THEN** each capable combatant receives exactly one provider interaction and the round's event
  sequence matches the pre-widening behaviour value-for-value

#### Scenario: A count of two grants a second slot at the same position and a mid-round defeat cuts it
- **WHEN** a synthetic bundle gives an enemy or noninteractive combatant `actions_per_turn: 2`, the provider returns a
  resolvable request for both slots, and a separate fixture has an earlier actor's strike defeat or
  knock out that combatant after its first slot lands
- **THEN** the first fixture's combatant resolves two provider interactions inside the one round
  transaction with both events ordered after its original sequence position, and the second
  fixture's combatant resolves only its first slot with no event and no provider call for the
  cut slot

#### Scenario: A runaway bundle hits the fuse, not an unbounded loop
- **WHEN** an enemy or noninteractive synthetic merge produces an `actions_per_turn` value above the loop's declared maximum
- **THEN** the combatant provisions exactly the declared maximum number of slots and round
  resolution completes without error

#### Scenario: An action lock dominates a co-existing grant
- **WHEN** a synthetic combatant simultaneously matches a shipped-shaped `actions_per_turn: 0`
  lock rule and a `+1` extra-action grant rule whose generic numeric merge alone would read as a
  positive count
- **THEN** the lock leg is evaluated first and skips the combatant's whole turn (chance rules
  resolving per the chance requirement) with no provider call, exactly as a lone lock does today

#### Scenario: Slots re-check liveness inside the single round transaction

- **WHEN** a combatant's provisioned action slots are requested during the round
- **THEN** each slot re-checks the round's liveness predicate (fled, knocked out, or depleted) before requesting an action, so a combatant defeated or knocked out by an earlier actor's settlement loses its remaining slots without an event, and the round's settlement stays one transaction per round either way

#### Scenario: Pre-widening bundles resolve byte-identically

- **WHEN** any bundle shipped before this widening — none of which co-matches a grant with a lock — is read
- **THEN** an absent `actions_per_turn` key means one action and the bundle resolves byte-identically to pre-widening behavior

#### Scenario: Only output keys are read, never rule identities

- **WHEN** the loop reads the combat-modifier rules' output
- **THEN** it reads the output keys only, with no branch distinguishing which underlying rule (poison, paralysis, arousal, climax phase, or an extra-action grant) produced the value

#### Scenario: A matched zero-action rule skips the turn outright

- **WHEN** an entity matches any zero-action rule
- **THEN** its turn is skipped entirely (producing an `EventLog` with kind `"action_skipped"`) without calling `ActionResolver.resolve()`

#### Scenario: Extra allied action count does not duplicate selected commands
- **WHEN** an interactive allied actor with actions_per_turn2 selects a skill and separately selects an item in a later complete draft
- **THEN** each selected command executes once with no duplicate cost/consumption or policy fallback, while equivalent enemy/noninteractive fixtures retain two ordinary slots


