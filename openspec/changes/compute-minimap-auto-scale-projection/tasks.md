# Tasks

Estimated effort: 7.5 hours for the implementing worker, including every required verification step below. Follow design.md verification commands and scope; check a box only after its assertions and evidence are verified.

## 1. Pure projection and scale policy (2 hours)

- [ ] 1.1 Implement the complete minimap_projection.js input/output contract with central constants, correct grid/wilderness metre normalization, tier classification and cross-layer exclusion/stub descriptors. Preserve overlay cellSize and graph paths. Apply the narrow wilderness-legend contract amendment, retaining provider-derived note construction and its focused patchability test.
- [ ] 1.2 Implement fitting-level selection, hysteresis, same-map caller reset helper, strict compression thresholds, logarithmic/inner-linear/equal-distance mappings and finite zero/no-exit defaults.

## 2. Geometry and focused evidence (2 hours)

- [ ] 2.1 Implement bounded symmetric overlap spreading, clipped context, dot world anchors, readable mapped rings and scaleLabel without DOM/Vue access or per-metre allocation.
- [ ] 2.2 Add deterministic minimap_projection.test.js cases for every approved §3.5 edge case and §8 listed unit case, including worked values, map-key reset, 1 km wilderness scaling, action-null exits, cross-layer slot changes and stub action equality.

## 3. Executed traceability and required review (2 hours)

- [ ] 3.1 Add a focused executed-Vitest Python evidence method in an existing evidence module, deriving literal requirement IDs with tools.spec_traceability --repo-root <equivalent-tree> list against the predecessor/current synchronized equivalent spec tree; annotate only substantively matching assertions.
- [ ] 3.2 Run pnpm exec vitest run web/webclient-app/tests/minimap_projection.test.js, then only the new Python evidence method if needed for its wrapper; do not invoke all pnpm tests or the full evidence module. Use agent-browser on retained World/LocalMap stories as renderer controls and state that visual auto-scaling belongs to the next change.

## 4. Handoff gates (1.5 hours)

- [ ] 4.1 Confirm exact existing/new Python and browser shard ownership, updating .github/evennia-shards.json or .github/browser-shards.json only when required; run traceability check and tools.contract_gate with the focused ownership label if changed.
- [ ] 4.2 Run openspec validate compute-minimap-auto-scale-projection --strict; document API/numerical policies beside the pure module and record the focused results and control screenshots.

