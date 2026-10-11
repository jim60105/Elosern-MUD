# Proposal

## Why

Score focus and threat from resolved eligible history without overriding mandatory target rules. This is a bounded part of the approved monster combat AI roadmap, not a claim that configuration alone completes attack behavior.

## What Changes

- Focus SHALL sum eligible already resolved allied pressure against still-live opponents within the memory window and normalize by maximum positive pressure. Empty history SHALL contribute zero; multi-target plans SHALL average distinct recipient focus values.
- Threat SHALL use observed incoming damage and successful opposing healing/control impact, normalized by current faction capacity and decayed with event age. Only profiles valuing threat SHALL use it in preference. Unknown or unobserved events SHALL contribute zero and mandatory legality/target restrictions SHALL remain authoritative.
- Completed utility SHALL add i*w_focus*observed_focus to damage, baseline healing, preference and intelligence-scaled finishing/control/cost/waste. Same-process replay SHALL require identical initial observations, state, scope and tuning. Traces SHALL record the initial observation snapshot.

## Capabilities

### New Capabilities

- `monster-ai-observed-coordination`: Score focus and threat from resolved eligible history without overriding mandatory target rules.

### Modified Capabilities

None.

## Impact

Attack preferences and tactical support already produce bounded signed features. Transaction-safe observation rings now supply eligible public outcomes. No unresolved teammate decision or player submission is an allowed coordination input. Implementation must update AI authoring/development documentation and the release changelog. Player command documentation remains unchanged because no command is added. No new service, package dependency, persistent AI schema or compatibility layer is authorized.

## Batch:

```text
depends-on: monster-ai-support-valuation
depends-on: monster-ai-observation-lifecycle
```

Code-conflict notes. Shares utility scoring, traces and snapshot projections with support and observation lifecycle; apply after both interfaces are complete. Shared shard manifests and release notes require integration in dependency order.

Downstream apply uses `feat/monster-ai-observed-coordination` and `.worktrees/monster-ai-observed-coordination`; proposal artifacts are committed on master and this planning operation creates neither.
