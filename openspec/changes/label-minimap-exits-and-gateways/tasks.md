# Tasks

Estimated effort: 7.5 hours for the implementing worker, including every required verification step below. Follow design.md verification commands and scope; check a box only after its assertions and evidence are verified.

## 1. Navigation-priority labels (2 hours)

- [ ] 1.1 Implement eight candidate label boxes using shipped text measures and marker footprints, resolving exits before current before context. Keep failed exit labels via labelMax truncation and leader lines; omit failed context labels and retain full accessible names.
- [ ] 1.2 Restrict old duplicate-region suppression to unchanged overlay behavior; add focused long/crowded label cases that establish never-dropped island exits and current/exit label readability at the 16 px floor. When the current label exhausts all eight candidates, retain its existing truncated placement as documented in design.md; assert this fallback without changing marker positions.

## 2. Gateway rendering and activation (2 hours)

- [ ] 2.1 Draw same-layer gateway glyphs with room label and 通往 second line; replace every cross-layer target node with the projection exit-ring arrow, using current gate metadata on the city side and target metadata on wilderness return.
- [ ] 2.2 Make actionable stubs focusable named buttons with Enter/Space/click dispatch through existing move wiring, preserve opaque descriptors and current_node, stop expand-button fallthrough, and keep locked stubs visible/inert. Preserve remembered markers and overlay/radial behavior.

## 3. Stories and focused behavior evidence (1.5 hours)

- [ ] 3.1 Extend World/LocalMap metric south-gate/return/locked/crowded stories so play checks cover the complete exit set including stubs, inside-canvas marker bounds, non-overlap and retained labels.
- [ ] 3.2 Run affected local_map.test.js, app_client_map_move.test.js and any new focused label-helper Vitest file separately; run only the selected LocalMapBrowserTest methods in interaction/rendering that establish keyboard naming, exact single moves and absence of cross-layer node groups. Register every new method in .github/browser-shards.json.

## 4. Mandatory visual and handoff gates (2 hours)

- [ ] 4.1 Use agent-browser to capture metric gate/return/locked/crowded stories and inspect real-client gateway rendering; use fresh snapshots to tab and activate a stub, checking focus, clipped second lines and no duplicate map-open/move.
- [ ] 4.2 Use canonical requirement IDs on matching Python browser/evidence methods, review changed single-tab-stop/cross-layer requirements without dropping predecessor scenarios, confirm exact manifests, run tools.spec_traceability check, tools.contract_gate and openspec validate label-minimap-exits-and-gateways --strict. Update component/story docs and handoff evidence.

