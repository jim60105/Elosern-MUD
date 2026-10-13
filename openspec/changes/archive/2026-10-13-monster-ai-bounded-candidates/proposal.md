# Proposal

## Why

Enumerate semantically legal, deduplicated damage plans under a hard proposal budget. This is a bounded part of the approved monster combat AI roadmap, not a claim that configuration alone completes attack behavior.

## What Changes

- Candidates SHALL use owned active supported hostile damage skills and their authored scale and target policies. SINGLE SHALL enumerate valid targets; enemy AREA SHALL use one legal group; SELF and NONE SHALL use existing implicit binding. Mixed plans SHALL use bounded legal audience combinations without arbitrary subset enumeration.
- Hostile SINGLE damage SHALL first restrict to applicable lamb_seal bearers. Without a genuinely castable non-strike hostile SINGLE damage alternative, displaced targets SHALL be removed. With seals, the first remaining bearer in canonical order SHALL be used. Strike-only candidates SHALL always exclude displaced targets.
- Equivalent candidates SHALL be deduplicated by skill, scale and sorted stable explicit target identifiers after shorthand expansion. The selected request SHALL retain its legal runtime target representation and scale.
- The initial candidate budget SHALL be 256 and configurable in integer 1..4096. It SHALL bound deduplicated examined proposals including rejected plans. Slots SHALL be allocated round-robin across canonical skill/semantic-plan families after mandatory filtering, with a scope-digest starting offset.

## Capabilities

### New Capabilities

- `monster-ai-legal-candidates`: Enumerate semantically legal, deduplicated damage plans under a hard proposal budget.

### Modified Capabilities

None.

## Impact

Existing monster policy chooses area shape before target/skill ranking and uses all-enemies. TargetSpec and effect audience planning already distinguish SELF, NONE, SINGLE and AREA. The utility candidate producer must respect these current semantics without changing legacy selection. Implementation must update AI authoring/development documentation and the release changelog. Player command documentation remains unchanged because no command is added. No new service, package dependency, persistent AI schema or compatibility layer is authorized.

## Batch:

```text
depends-on: monster-ai-legal-snapshots
```

Code-conflict notes. Shares candidate and target-plan modules with support valuation; support must extend this producer rather than create another one. Shared shard manifests and release notes require integration in dependency order.

Downstream apply uses `feat/monster-ai-bounded-candidates` and `.worktrees/monster-ai-bounded-candidates`; proposal artifacts are committed on master and this planning operation creates neither.
