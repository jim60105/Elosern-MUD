# Proposal

## Why

Identity restrictions currently use a divine-only skill flag, leaving species and subrace abilities without shared qualification. Replace that flag before introducing authored monster content while preserving existing ownership and acquisition rules.

## What Changes

- Add immutable actor-kind, race, subrace, species and race-capability eligibility with one pure record/runtime query.
- **BREAKING** Remove the divine skill marker and its separate gate; migrate every definition, validator, passive/grant reader, acquisition exclusion, presentation consumer and affected test to the shared contract.
- Keep race-profile capability authority, category-based divine practice cadence, existing targeting and ownership semantics; add synthetic eligibility coverage.

## Capabilities

### New Capabilities

- `skill-identity-eligibility`: Shared declarative identity qualification.

### Modified Capabilities

- `skill-lineage`: Replace affected qualification contracts and preserve unrelated scenarios.
- `skill-lineage-panel`: Replace affected qualification contracts and preserve unrelated scenarios.
- `skill-handler`: Replace affected qualification contracts and preserve unrelated scenarios.
- `import-validation`: Replace affected qualification contracts and preserve unrelated scenarios.
- `divine-mystery`: Replace affected qualification contracts and preserve unrelated scenarios.
- `player-character-creation`: Replace affected qualification contracts and preserve unrelated scenarios.
- `sexual-act-registry`: Replace affected qualification contracts and preserve unrelated scenarios.
- `sexual-catalog-divine-core`: Replace affected qualification contracts and preserve unrelated scenarios.
- `sexual-catalog-divine-mutators`: Replace affected qualification contracts and preserve unrelated scenarios.
- `sexual-state-handler`: Replace affected qualification contracts and preserve unrelated scenarios.
- `skill-category-registry`: Replace affected qualification contracts and preserve unrelated scenarios.

## Impact

world/skills/registry/{vocab,builders,data_divine_mystery,data_utility_passives}.py; world/skills/sexual_acts/; world/skills/handler.py; world/imports/validate.py; world/lore/player_presets/validation.py; world/rules/progression/_gates.py; world/rules/action/gates.py; world/rules/action_preview.py; world/rules/lineage_query.py; rule-table/passive and grant consumers; player catalog read models; synthetic fixtures and affected tests.

## Non-goals

No other species abilities, beastfolk content, artificial monster races, second handler/registry engine, arbitrary expressions, AI redesign, new combat formulas, cost-order changes, balance recalibration, automatic resets, migrations or compatibility layers. No player command syntax changes. Architecture ownership remains unchanged.

## Batch:

```text
code-conflicts: skill-hit-dependent-effects, tide-devouring-crocodile-resource-skill
```

Safe apply/verify/archive order is shared-skill-identity-eligibility, then skill-hit-dependent-effects, then tide-devouring-crocodile-resource-skill. Complete and archive each prerequisite before applying the crocodile integration. Eligibility and hit-dependency are logically independent and individually deployable; serialize their implementation because both touch registry/vocab.py, action/resolver or gates, shared test fixtures and shard ownership. Neither prerequisite alone delivers the crocodile feature. Do not apply or archive any change during proposal creation. The unrelated guild-exam-appointment-surface remains outside this batch.

## Size and standalone delivery

One engineer-day, approximately 8 hours. Typed eligibility and load validation (2h), divine consumer cutover (2h), runtime/passive/import/presentation integration (2h), focused regression coverage and authoring docs (2h). Complete clean cutover is one deployment unit; no partial marker replacement is allowed. It ships useful race/subrace/capability qualification without monster content or hit dependencies.
