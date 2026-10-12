# Proposal

## Why

Validate variant-authored intelligence and decision modes while leaving every production variant on legacy. This is a bounded part of the approved monster combat AI roadmap, not a claim that configuration alone completes attack behavior.

## What Changes

- The system SHALL accept intelligence only as an explicit registered-variant integer from 0 through 100. Every effective utility variant SHALL have a validated value. Intelligence SHALL change decision evaluation only and SHALL NOT change stats, resources, owned skills, proficiency or combat formulas.
- The effective mode SHALL use a validated variant override when present and otherwise the actual resolved archetype mode. Missing archetype mode SHALL mean legacy. Utility without a valid runtime species/variant pair or explicit intelligence SHALL produce a typed invalid decision state.
- Startup SHALL validate four mandatory legacy fields, optional decision_mode and complete named utility weights, variant maps and candidate budget. Unknown fields, invalid modes, primitive types, boolean numbers, negative or non-finite weights and budgets outside integer 1..4096 SHALL be rejected.
- The system SHALL record immutable resolved tuning and its fingerprint in process for a session. Startup configuration SHALL remain fixed without hot reload. Restart SHALL clear recorded tuning and reconstruct existing sessions with validated startup configuration; no durable AI fields or per-entity intelligence copies SHALL be added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monster-behaviour-profile`: Extend authored mode/intelligence contracts and replace affected source-only acceptance with behavior.

## Impact

Current profile loading in world/rules/monster_behaviour.py requires four fields. MonsterVariant records in world/lore/monster_species.py have complete species relationships. Stored behaviour_tree already determines the actual archetype. Implementation must update AI authoring/development documentation and the release changelog. Player command documentation remains unchanged because no command is added. No new service, package dependency, persistent AI schema or compatibility layer is authorized.

## Batch:

```text
depends-on: none
```

Code-conflict notes. Shares monster_behaviour.py, rulebook YAML, profile tests and session tuning with attack selection and staged activation; apply those afterward. Shared shard manifests and release notes require integration in dependency order.

Downstream apply uses `feat/monster-ai-variant-tuning` and `.worktrees/monster-ai-variant-tuning`; proposal artifacts are committed on master and this planning operation creates neither.
