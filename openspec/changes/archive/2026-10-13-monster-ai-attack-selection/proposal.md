# Proposal

## Why

Complete production utility attack dispatch with independent sampling, real execution identity and diagnostics. This is a bounded part of the approved monster combat AI roadmap, not a claim that configuration alone completes attack behavior.

## What Changes

- Attack utility SHALL equal w_damage*damage + w_preference*preference + i*(w_kill*finishing - w_cost*cost - w_waste*waste), with i=intelligence/100. Preference SHALL combine configured target, owned-skill and area bias as bounded stable ranks with shared ranks for ties.
- Selection SHALL sort by canonical skill, normalized targets and scale and sample stable softmax using maximum-score subtraction and T=1.25-1.17*i. Selection RNG SHALL be independent of combat dice and injectable. Equal scores SHALL sample uniformly; invalid scores or non-positive/non-finite temperatures SHALL fail explicitly.
- Production selection seeds SHALL use versioned SHA-256 encoding of session ID, actual round, stable actor ID, actual action-slot index and configuration fingerprint. Scope SHALL restore on return and exception while preserving two-argument providers. Inspection without scope SHALL use canonical identities and read-only snapshot fingerprint with slot zero.
- The session adapter SHALL construct the normal or overwhelm settlement context before selection. Selected requests SHALL retain targets including recognized shorthands and authored non-default scale. Every actual action SHALL settle through the existing resolver.
- Malformed startup tuning SHALL fail. A typed invalid runtime AI state SHALL emit a facade warning with identifiers and exception context and use configured legacy fallback or diagnostic None. Empty legal sets, unsupported individual candidates, late rejection, database errors and programming exceptions SHALL retain their normal boundaries.

## Capabilities

### New Capabilities

- `monster-ai-utility-selection`: Complete production utility attack dispatch with independent sampling, real execution identity and diagnostics.

### Modified Capabilities

- `monster-action-policy`: Scope target/skill/shape/dice contracts to permanent legacy mode; authorize ephemeral execution seams and replace affected source-only constraints.

## Impact

world/rules/combat_session/policies.py::_enemy_policy currently selects before rebuilding context, converts targets through list() and omits scale. world/rules/combat/rounds.py repeats provider calls for multiple slots; overwhelm loops invoke successive actual rounds. The current main policy spec prohibits round module changes and requires shared combat dice. Implementation must update AI authoring/development documentation and the release changelog. Player command documentation remains unchanged because no command is added. No new service, package dependency, persistent AI schema or compatibility layer is authorized.

## Batch:

```text
depends-on: monster-ai-variant-tuning
depends-on: monster-ai-bounded-candidates
depends-on: monster-ai-damage-estimation
```

Code-conflict notes. Shares policy/spec deltas, session policies, combat rounds and overwhelm with observation lifecycle; observation hooks apply after these scope changes. Shared shard manifests and release notes require integration in dependency order.

Downstream apply uses `feat/monster-ai-attack-selection` and `.worktrees/monster-ai-attack-selection`; proposal artifacts are committed on master and this planning operation creates neither.
