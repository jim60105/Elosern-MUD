# Proposal

## Why

Create immutable no-write snapshots and share complete deterministic legality with settlement. This is a bounded part of the approved monster combat AI roadmap, not a claim that configuration alone completes attack behavior.

## What Changes

- Snapshots SHALL contain stable identity, real execution scope, resolved context, true literal/effective traits, resources, capabilities, factions, owned skill metadata, active buff projections and settled public observations. Snapshot construction SHALL NOT create handlers or caches, regenerate gauges, update timestamps or write entity state.
- Utility validation SHALL use the actual context, scale and submitted plan with shared ownership, active-kind, identity, lineage, proficiency, resource, capability, cast, interaction and target gates. Submission and initiative-time resolver revalidation SHALL remain authoritative.
- The system SHALL read registry, owned-skill metadata, costs, participant traits and buff projections once per decision and reuse these inputs across target plans. It SHALL refresh them for the next action.

## Capabilities

### New Capabilities

- `monster-ai-decision-inputs`: Create immutable no-write snapshots and share complete deterministic legality with settlement.

### Modified Capabilities

None.

## Impact

preview_skill in world/rules/action_preview.py already reads ownership, costs and target gates. world/rules/action/gates.py still owns additional cast conditions. evaluate_combat_modifiers_no_create provides an existing stored-state reader; gauge and handler access still require explicit no-create audit. Implementation must update AI authoring/development documentation and the release changelog. Player command documentation remains unchanged because no command is added. No new service, package dependency, persistent AI schema or compatibility layer is authorized.

## Batch:

```text
depends-on: monster-ai-variant-tuning
```

Code-conflict notes. Shares action preview/gates and modifier readers with damage estimation and support valuation; serial apply when those extract scalar helpers. Shared shard manifests and release notes require integration in dependency order.

Downstream apply uses `feat/monster-ai-legal-snapshots` and `.worktrees/monster-ai-legal-snapshots`; proposal artifacts are committed on master and this planning operation creates neither.
