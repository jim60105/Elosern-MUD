# Proposal

## Why

Estimate supported attack health effects with settlement arithmetic and conservative outcome models. This is a bounded part of the approved monster combat AI roadmap, not a claim that configuration alone completes attack behavior.

## What Changes

- Estimates SHALL reuse scalar base damage, potency, scale, mitigation, strike count and cost rules. They SHALL analytically average supported d100 ranges with the actual hit-gate topology and SHALL NOT roll dice, invoke effect handlers, pay costs, install buffs or emit events.
- Unsupported harmful outcomes SHALL exclude a candidate. Unknown harmless benefits SHALL contribute zero with diagnostics. Uncertain beneficial conditionals SHALL be omitted. Known shielding/diversion limits SHALL reduce estimates; finishing credit SHALL require a supported outcome model or guaranteed-on-hit lower bound.
- Features SHALL be in 0..1 with explicit benefit/harm direction. Enemy damage and allied healing SHALL be positive; ally damage and enemy healing SHALL be negative. Projected effects SHALL be capped by capacity; zero denominators SHALL contribute zero. Non-finite features SHALL be typed invalid states.

## Capabilities

### New Capabilities

- `monster-ai-effect-estimation`: Estimate supported attack health effects with settlement arithmetic and conservative outcome models.

### Modified Capabilities

None.

## Impact

Legacy expected damage compares adjusted attack minus defense. Actual action effect settlement and combat arithmetic include potency, scale, mitigation, ordered multi-strikes and conditional drain outcomes. Utility needs these semantics without executing effect handlers. Implementation must update AI authoring/development documentation and the release changelog. Player command documentation remains unchanged because no command is added. No new service, package dependency, persistent AI schema or compatibility layer is authorized.

## Batch:

```text
depends-on: monster-ai-legal-snapshots
depends-on: monster-ai-bounded-candidates
```

Code-conflict notes. Shares scalar effect settlement and estimation with support valuation; apply scalar extraction before support changes. Shared shard manifests and release notes require integration in dependency order.

Downstream apply uses `feat/monster-ai-damage-estimation` and `.worktrees/monster-ai-damage-estimation`; proposal artifacts are committed on master and this planning operation creates neither.
