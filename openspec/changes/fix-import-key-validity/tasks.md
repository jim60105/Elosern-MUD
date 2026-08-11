## 1. Key charset contract

- [ ] 1.1 Add `pattern` and `maxLength` to `key` in `CHARACTER_SCHEMA_V1` (`world/imports/schema.py`) and matching world-entry validation
- [ ] 1.2 Mirror the separator/length rules in `_validate_name` (`world/rules/character_creation.py`)
- [ ] 1.3 Update any example/fixture imports that violate the new rules

## 2. Batch character-key uniqueness

- [ ] 2.1 Extend the duplicate-key check in `world/imports/validate.py::validate_batch` to character records (fail the batch as a structural issue)

## 3. Tests and verification

- [ ] 3.1 Tests: `|`-key and over-long-key imports rejected structurally; character creation rejects the same separators
- [ ] 3.2 Test: batch with duplicate character keys fails wholly; unique keys pass
- [ ] 3.3 Test: an NPC with a valid key takes damage normally (regression for the event-construction failure)
- [ ] 3.4 Run imports, loader, combat, and character-creation tests
