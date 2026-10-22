# Proposal

## Why

Keep exit labels visible and render cross-layer travel as accessible gate exit stubs. The approved [Minimap Auto-Scale Design](../../../docs/superpowers/specs/2026-10-22-minimap-auto-scale-design.md) addresses metric streets whose adjacent exits lie outside the current 240 px island.

## What Changes

- Try eight label placements in exit/current/context priority; keep overflow exit labels with truncation and a leader line.
- Draw gate glyphs, room names and `通往 <leads_to>` labels; render cross-layer targets only as focusable exit-ring arrows.
- Preserve the validated move descriptor through click/keyboard activation, including inert locked exits.
- Amend legacy cross-layer-node, tab-order and label rules while leaving the overlay and radial graphs unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-local-map`: Label visibility and gate interaction, approved design §4.2, §6.4, §7 and §8.

## Impact

Island rendering/label placement and activation, `World/LocalMap` metric stories, focused Vue/browser interaction tests, browser-shard ownership.

Estimated implementing-worker effort is **7.5 hours**, including focused verification and artifact/evidence updates, for a gpt-luna-level worker. Each task group in `tasks.md` has a time allocation. This is a pre-release clean cutover with no compatibility path or migration.

Excluded throughout the batch are full-map redesign, whole-area/world data, server display coordinates and changes to instance/interior radial layout. The parent architecture remains authoritative; the approved design amends metric uniform projection for the minimap island only.

## Batch:

depends-on: render-auto-scaled-minimap-island
batch-order: 4/5
estimated-hours: 7.5

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
