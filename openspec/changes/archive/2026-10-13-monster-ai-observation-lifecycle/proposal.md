# Proposal

## Why

Collect same-round resolved observations with bounded transaction-safe volatile memory and terminal cleanup. This is a bounded part of the approved monster combat AI roadmap, not a claim that configuration alone completes attack behavior.

## What Changes

- Memory SHALL contain public resolved session/round/sequence, source identity/faction, skill/item identity, recipients and outcome magnitudes/status facts. It SHALL retain at most three actual rounds and 128 records per session, whichever expires first, with one compact bounded-recipient record per settled action/upkeep boundary.
- Earlier successful actions SHALL be visible before the next provider decision through a transaction-local overlay. Memory publication SHALL occur only after the outermost successful commit; rollback SHALL discard uncommitted observations while preserving prior committed memory.
- Successful terminal victory/defeat, flee, forfeit, recovery and missing/deleted participant handling SHALL discard session memory and recorded tuning after commit. Terminal cleanup SHALL supersede every earlier publication callback in that transaction. Rollback SHALL preserve prior committed memory.
- Memory SHALL be isolated by session and stable actor identity. Battlefield reconstruction SHALL preserve committed history in process. Eligible projections SHALL use current live participation and faction. Restart SHALL clear history and use validated startup tuning without a durable sidecar.

## Capabilities

### New Capabilities

- `monster-ai-observation-memory`: Collect same-round resolved observations with bounded transaction-safe volatile memory and terminal cleanup.

### Modified Capabilities

None.

## Impact

combat/rounds.py currently accumulates successful logs locally until it returns, including item and upkeep outcomes. Combat sessions own outer atomic settlement and lifecycle recovery. Current observation history is absent; no CombatSessionRecord or ORM additions are authorized. Implementation must update AI authoring/development documentation and the release changelog. Player command documentation remains unchanged because no command is added. No new service, package dependency, persistent AI schema or compatibility layer is authorized.

## Batch:

```text
depends-on: monster-ai-attack-selection
```

Code-conflict notes. Shares combat rounds/overwhelm/session lifetime and tuning state with staged activation and attack integration; serialize those writers. Observation eligibility precedes coordination. Shared shard manifests and release notes require integration in dependency order.

Downstream apply uses `feat/monster-ai-observation-lifecycle` and `.worktrees/monster-ai-observation-lifecycle`; proposal artifacts are committed on master and this planning operation creates neither.
