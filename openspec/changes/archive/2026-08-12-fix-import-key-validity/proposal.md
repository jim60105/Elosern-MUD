## Why

Two import-validation defects from audit run-1: (F18) imported entity keys containing `|` pass validation but corrupt the `|`-serialized `PendingEffect` descriptions, so every combat action against such an NPC rejects after initiative — effective damage immunity and consumed turns; (F23) a batch containing duplicate character keys creates two entities that share one portrait subject and an ambiguous stable identity.

## What Changes

- Imported entity keys are restricted to a safe charset (no `|`, `/`, `:`, `{`, `}`, or control characters) with a maximum length of 64 characters, enforced at the schema and validation layers, and mirrored at character-creation (player display names become entity keys and obey the same rules) so every entity-key producer obeys the same contract.
- Batch validation rejects duplicate character keys alongside the existing world-entry uniqueness check.
- Regression coverage for both.

## Capabilities

### Modified Capabilities

- `import-schema`: key pattern and length constraints.
- `import-validation`: batch-level character-key uniqueness and key-charset structural checks.
- `player-character-creation`: display-name charset/length parity with the shared entity-key contract.
- `webclient-character-creation-ui`: the advertised display-name bound mirrors the deterministic bound.

## Impact

- `world/imports/schema.py`, `world/imports/validate.py`, `world/rules/character_creation.py` (name validation parity), `world/rules/creation_wizard.py` + `world/rules/creation_messages.py` + `web/webclient/actions/creation_actions.py` + webclient JS (bound mirrors), tests; no data migration (no users).
