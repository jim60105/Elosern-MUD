# Proposal

## Why

The approved crocodile contact drain is still deferred and both variants lack resource pools. Deliver its complete construction-to-combat path using the shared qualification and hit-dependency prerequisites.

## What Changes

- Author tide_devouring_bite in a separate monster declaration module, using water physical damage and hit-dependent fixed MP transfer.
- Configure both approved crocodile profiles, ordered kits and existing first_owned behavior; validate and persist construction atomically.
- Deliver resolver-backed combat-session smoke, exhaustion fallback, reload evidence and public ecology/documentation updates; leave the other five species unchanged.

## Capabilities

### New Capabilities

- `monster-resource-abilities`: Authored resource abilities through shared monster execution.

### Modified Capabilities

- `monster-species-registry`: Adopt the approved executable crocodile configuration.
- `monster-individual-construction`: Adopt the approved executable crocodile configuration.
- `monster-action-policy`: Adopt the approved executable crocodile configuration.

## Impact

world/lore/monster_species.py; world/rules/monster_individual.py; world/rules/monster_behaviour.py; world/rules/rulebook/monster_behaviour.yaml; registry assembly and new separate monster content; construction, policy, session and persistence tests; docs/lore/bestiary.md and existing authoring guides.

## Non-goals

No other species abilities, beastfolk content, artificial monster races, second handler/registry engine, arbitrary expressions, AI redesign, new combat formulas, cost-order changes, balance recalibration, automatic resets, migrations or compatibility layers. No player command syntax changes. Architecture ownership remains unchanged.

## Batch:

```text
depends-on: shared-skill-identity-eligibility
depends-on: skill-hit-dependent-effects
code-conflicts: shared-skill-identity-eligibility, skill-hit-dependent-effects
```

Safe apply/verify/archive order is shared-skill-identity-eligibility, then skill-hit-dependent-effects, then tide-devouring-crocodile-resource-skill. Complete and archive each prerequisite before applying the crocodile integration. Eligibility and hit-dependency are logically independent and individually deployable; serialize their implementation because both touch registry/vocab.py, action/resolver or gates, shared test fixtures and shard ownership. Neither prerequisite alone delivers the crocodile feature. Do not apply or archive any change during proposal creation. The unrelated guild-exam-appointment-surface remains outside this batch.

## Size and standalone delivery

One engineer-day, approximately 8 hours after both prerequisites. Ability/profile declarations (1h), kit validation and atomic construction (2h), minimal policy binding and qualification (1h), real session/reload/rollback coverage and smoke (3h), ecology and authoring documentation (1h). Reuse existing transfer, cost, innate ownership and behavior APIs; no AI planner work.
