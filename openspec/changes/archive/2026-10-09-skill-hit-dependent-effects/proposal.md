# Proposal

## Why

Damage and transfer components currently resolve independently, so an authored drain rider can execute after a miss. Add trusted per-occurrence hit dependency without additional dice or persistent hit state.

## What Changes

- Add immutable references to earlier damage occurrences in per-effect policies with load-time validation.
- Expose typed invocation-local outcomes from existing damage rolls; intersect dependent recipients with their ordinary valid audience.
- Preserve transactions, practice rollback and effect-before-cost order; prove target isolation, multi-strike any-hit semantics and species-independent reuse.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-effect-model`: Add hit dependencies.

## Impact

world/skills/effects/policies.py and registry/vocab.py; world/rules/action/{contracts,routing,resolver}.py; world/rules/combat/damage.py; existing effect handlers and audience/atomicity tests.

## Non-goals

No other species abilities, beastfolk content, artificial monster races, second handler/registry engine, arbitrary expressions, AI redesign, new combat formulas, cost-order changes, balance recalibration, automatic resets, migrations or compatibility layers. No player command syntax changes. Architecture ownership remains unchanged.

## Batch:

```text
code-conflicts: shared-skill-identity-eligibility, tide-devouring-crocodile-resource-skill
```

Safe apply/verify/archive order is shared-skill-identity-eligibility, then skill-hit-dependent-effects, then tide-devouring-crocodile-resource-skill. Complete and archive each prerequisite before applying the crocodile integration. Eligibility and hit-dependency are logically independent and individually deployable; serialize their implementation because both touch registry/vocab.py, action/resolver or gates, shared test fixtures and shard ownership. Neither prerequisite alone delivers the crocodile feature. Do not apply or archive any change during proposal creation. The unrelated guild-exam-appointment-surface remains outside this batch.

## Size and standalone delivery

One engineer-day, approximately 8 hours. Policy validation and typed trusted outcomes (2h), routing and damage-producer integration (2h), deterministic rollback/multi-target coverage (2h), documentation and focused verification (2h). It can ship against current skills using synthetic dependency consumers without eligibility or production content.
