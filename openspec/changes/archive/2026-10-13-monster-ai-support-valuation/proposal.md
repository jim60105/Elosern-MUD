# Proposal

## Why

Choose useful existing healing and calculable control through the shared utility selector. This is a bounded part of the approved monster combat AI roadmap, not a claim that configuration alone completes attack behavior.

## What Changes

- Owned active healing, supported buffs and hostile control SHALL enter the same candidate pipeline and legality gates. Estimates SHALL follow the submitted effect audience plan, including implicit SELF/NONE binding. Full-HP heals SHALL remain legal when settlement allows them with zero recovery benefit and real cost/waste.
- Healing SHALL use shared magnitude, potency, proficiency, scale and conditional rules, capped by projected missing HP. Resource payment SHALL precede effect projection. Hit-dependent healing and drain recovery SHALL use modeled prerequisites and actual projected loss.
- Supported control and buff estimates SHALL use existing modifier definitions over one next action opportunity per eligible participant. Expired, redundant non-stacking, stronger existing, capped effects and beneficiaries without opportunity before expiry SHALL have zero marginal benefit.
- The score SHALL add w_heal*useful_healing as a baseline and i*w_control*marginal_control to attack utility. Focus SHALL enter through the observation change. Invalid numeric features SHALL use the existing typed error boundary.

## Capabilities

### New Capabilities

- `monster-ai-tactical-support`: Choose useful existing healing and calculable control through the shared utility selector.

### Modified Capabilities

- `monster-ai-utility-selection`: the completed score adds the unscaled recovery baseline and the intelligence-scaled control term, so its authored formula requirement is restated with both.
- `monster-ai-effect-estimation`: a supported buff or control mount whose definition projects concrete supported modifiers is now valued by its marginal modifier difference instead of contributing zero as an unknown benefit, and the bounded signed feature contract now also covers the control feature.

## Impact

Existing skill effects and modifier compiler already settle heals, drains, buffs and control. The new attack producer and scalar estimator supply legal plans and immutable per-recipient projections. This change supports existing pure calculable semantics only, with real synthetic settlement evidence for healing and marginal control. Implementation must update AI authoring/development documentation and the release changelog. Player command documentation remains unchanged because no command is added. No new service, package dependency, persistent AI schema or compatibility layer is authorized.

## Batch:

```text
depends-on: monster-ai-attack-selection
```

Code-conflict notes. Shares candidates, estimation and utility scoring with observed coordination; scalar support precedes focus scoring. No new ability or state-effect authoring. Shared shard manifests and release notes require integration in dependency order.

Downstream apply uses `feat/monster-ai-support-valuation` and `.worktrees/monster-ai-support-valuation`; proposal artifacts are committed on master and this planning operation creates neither.
