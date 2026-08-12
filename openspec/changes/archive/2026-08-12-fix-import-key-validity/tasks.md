## 1. Key charset contract

- [x] 1.1 Add `pattern` and `maxLength` to `key` in `CHARACTER_SCHEMA_V1` and matching world-entry validation
- [x] 1.2 Mirror the separator/length rules in `_validate_name` (`world/rules/character_creation.py`): reject `/`, `:`, `}` and cap names at 64 characters
- [x] 1.3 Mirror the 64-char display-name bound at the wizard (`NAME_MAX_LENGTH`), messages, webclient action adapter, and webclient JS UI
- [x] 1.4 Update any example/fixture imports that violate the new rules

## 2. Batch character-key uniqueness

- [x] 2.1 Extend the duplicate-key check in `world/imports/validate.py::validate_batch` to character records (fail the batch as a structural issue)

## 3. Tests and verification

- [x] 3.1 Tests: `|`-key and over-long-key imports rejected structurally; character creation rejects the same separators and the 64-char bound
- [x] 3.2 Test: batch with duplicate character keys fails wholly; unique keys pass
- [x] 3.3 Test: an NPC with a valid key takes damage normally (regression for the event-construction failure)
- [x] 3.4 Run imports, loader, combat, and character-creation tests
