# Proposal

## Why

Require bounded gateway metadata on every v1 node and preserve it through the browser model. The approved [Minimap Auto-Scale Design](../../../docs/superpowers/specs/2026-10-22-minimap-auto-scale-design.md) addresses metric streets whose adjacent exits lie outside the current 240 px island.

## What Changes

- **BREAKING** Add required `gateway: null | {leads_to}` to every node, updating both exact validators and every producer/fixture together without a version bump or alias.
- Populate city-gate region names and wilderness-adjacent city-gate settlement names from existing registry helpers.
- Keep coordinate-free graph behavior, all coordinates, actions and overlay placement unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-local-map`: Payload schema and gateway transport, approved design §4.1, §6.1–§6.2 and §8.

## Impact

Server local-map builder/adapters/validators, browser validator/reducer, protocol fixtures across Node, Vue and browser tests; focused server/Node evidence.

Estimated implementing-worker effort is **6.5 hours**, including focused verification and artifact/evidence updates, for a gpt-luna-level worker. Each task group in `tasks.md` has a time allocation. This is a pre-release clean cutover with no compatibility path or migration.

Excluded throughout the batch are full-map redesign, whole-area/world data, server display coordinates and changes to instance/interior radial layout. The parent architecture remains authoritative; the approved design amends metric uniform projection for the minimap island only.

## Batch:

depends-on: none
batch-order: 1/5
estimated-hours: 6.5

Implementation order is add-local-map-gateway-metadata → compute-minimap-auto-scale-projection → render-auto-scaled-minimap-island → label-minimap-exits-and-gateways → animate-minimap-scale-transitions. Dependencies mean completed predecessor implementation, with its delta requirements available before the next change is applied. Proposal authoring stays on master; only a later os-apply worker creates its assigned implementation branch/worktree. No implementation is authorized by this proposal.

### Dependency / code-conflict matrix

Use the following pairwise matrix for the whole batch. All changes share `webclient-local-map`; renderer, labels and motion modify the same large existing requirement cumulatively. Serialize these changes and preserve predecessor scenarios at spec sync. The existing unrelated `verify-recent-deed-settlement-flows` proposal has no minimap runtime overlap; coordinate any shared shard manifest edits when applying.

| Pair | Shared code / conflict | Order |
| --- | --- | --- |
| Metadata / projection | `gateway` model contract; executed-evidence ownership may share a file | Metadata first |
| Metadata / renderer | fixtures, local-map evidence and shard manifests | Metadata first |
| Metadata / labels | gateway fixture/model contract and browser fixtures | Metadata first |
| Metadata / motion | shared browser fixtures and shard manifests | Metadata first |
| Projection / renderer | projection API and focused evidence wrapper | Projection first |
| Projection / labels | projected nodes/stubs and tests | Projection first |
| Projection / motion | mode/level frame contract and evidence | Projection first |
| Renderer / labels | MapLattice, geometry/render composables, stories, browser tests, same main requirement | Renderer first |
| Renderer / motion | MapLattice/LocalMap, story fixtures, browser manifests, same main requirement | Renderer first |
| Labels / motion | MapLattice, stories and browser interaction/transition evidence | Labels first |
