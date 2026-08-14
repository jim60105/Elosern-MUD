## ADDED Requirements

### Requirement: The character-portrait keyspace reserves the digit-only region for player characters

The shared stable-key contract SHALL reserve the digit-only region of the `portrait:character:` keyspace for player characters: their stable keys are `str(pk)` (`world/rules/character_creation.py`). The contract SHALL host one predicate (`is_reserved_player_stable_key`, alongside `DIGITS_ONLY_KEY_PATTERN`) in `world/art/subjects.py`, and every non-player producer SHALL reject a digit-only key through it: the import schema pattern, the import key-contract check, and the quest characterization helper. A digit-only key SHALL therefore be unreachable from any import record, quest blueprint, or template, so no non-player entity can ever share the asset record of a player character. The art layer itself SHALL keep accepting digit-only keys — players are the legitimate owners and the policy dict cannot distinguish player from NPC.

#### Scenario: A digit-only import key is rejected at import

- **WHEN** a character import record declares a `key` consisting only of ASCII digits (e.g. `"42"`)
- **THEN** the import is rejected with a structural issue naming the reserved digit-only region, and no entity is created

#### Scenario: A digit-only blueprint stable key is rejected

- **WHEN** a quest blueprint assigns `portrait: {"stable_key": "7"}` to an `npc_req` entry
- **THEN** the blueprint is rejected by the shared characterization helper before any record is created

#### Scenario: Player stable keys stay digit-only and still derive their subject

- **WHEN** a player character carries `{"mode": "named", "stable_key": str(pk)}`
- **THEN** the policy remains valid and resolves to `portrait:character:<pk>` exactly as before

#### Scenario: One shared predicate is the rule source for every producer

- **WHEN** the import schema pattern, the import validator, and the quest characterization helper are inspected for the digit-only rule
- **THEN** all three consume the single predicate/pattern hosted in `world/art/subjects.py` with no duplicated rule text
