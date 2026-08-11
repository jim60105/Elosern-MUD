## Why

Two import-validation defects from audit run-1: (F18) imported entity keys containing `|` pass validation but corrupt the `|`-serialized `PendingEffect` descriptions, so every combat action against such an NPC rejects after initiative — effective damage immunity and consumed turns; (F23) a batch containing duplicate character keys creates two entities that share one portrait subject and an ambiguous stable identity.

## What Changes

- Imported entity keys are restricted to a safe charset (no `|`, `/`, `:`, or control characters) with a bounded length, enforced at the schema and validation layers, and mirrored at character-creation so every entity-key producer obeys the same contract.
- Batch validation rejects duplicate character keys alongside the existing world-entry uniqueness check.
- Regression coverage for both.

## Capabilities

### Modified Capabilities

- `import-schema`: key pattern and length constraints.
- `import-validation`: batch-level character-key uniqueness and key-charset structural checks.

## Impact

- `world/imports/schema.py`, `world/imports/validate.py`, `world/rules/character_creation.py` (name validation parity), tests; no data migration (no users).
