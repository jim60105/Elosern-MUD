# Tasks

Estimated effort: 8 hours for the implementing worker, including every required verification step below. Follow design.md verification commands and scope; check a box only after its assertions and evidence are verified.

## 1. Island integration (2 hours)

- [x] 1.1 Hold the previous level in LocalMap.vue keyed by current-node map identity and pass the pure projection into only the fixed-canvas lattice branch; keep overlay and graph placement unchanged.
- [x] 1.2 Replace island lattice geometry with a 240-unit centred projection, remove obsolete islandWindow/windowed/ISLAND_MIN_SCALE and island pitch iteration, preserving graph window handling and overlay cellSize.

## 2. Truthful island drawing (2 hours)

- [x] 2.1 Join projected IDs to original state/actions, draw current/exits and small context dots, omit off-canvas context/cross-layer node groups, keep remembered edge markers, and draw only labelled current-to-exit route edges. Preserve stub descriptors for the next change.
- [x] 2.2 Draw uniform world-anchored dots or compressed labelled rings with a 16 px scale caption separate from the current-coordinate readout, token styling and no pointer capture; adapt any matching .elosern-root override.

## 3. Metric stories and focused tests (2 hours)

- [x] 3.1 Create fixed Altoria 21-node and Ciaran 10-node coordinate corpora from parent-design tables plus bounded representative neighbourhood views, wilderness 3x3, south gate and extreme-ratio fixtures. Preserve existing unit-coordinate overlay fixtures; use localMapModelFor.
- [x] 3.2 Add one World/LocalMap story per metric fixture family with play checks for all same-layer exits inside canvas and pairwise marker non-overlap; add focused renderer tests and update only obsolete island assertions, retaining overlay metric ratio tests.

## 4. Mandatory visual and contract evidence (2 hours)

- [x] 4.1 Run each affected local_map.test.js/map_lattice_renderer.test.js Vitest file separately and one selected LocalMapBrowserTest metric method from test_browser_local_map_lattice via unittest_driver. Register every new browser method in .github/browser-shards.json in the same feature commit.
- [x] 4.2 Use agent-browser to capture and inspect all five metric stories at reference viewport and a real-client metric island at the chrome cap, plus one unchanged MapOverlay/graph control; report missing exits, clipping and background shape/text as blocking failures.
- [x] 4.3 Update matching Python traceability evidence using tool-generated IDs, confirm Python shard ownership and browser manifest ownership, run tools.spec_traceability check, tools.contract_gate and openspec validate render-auto-scaled-minimap-island --strict. Update affected story comments/component documentation and handoff evidence.

