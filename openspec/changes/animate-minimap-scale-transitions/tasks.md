# Tasks

Estimated effort: 7 hours for the implementing worker, including every required verification step below. Follow design.md verification commands and scope; check a box only after its assertions and evidence are verified.

## 1. Scale-aware transition decision (2 hours)

- [x] 1.1 Record previous mode/level with the existing MapLattice pre/post pan frame. Reuse FLIP only for unchanged mode/level and include world-anchored dots in the pan transform; leave radial/overlay behavior unchanged. Apply the cumulative webclient-contextual-hud motion amendment and preserve its unrelated scene/location/vitals scenarios.
- [x] 1.2 For changed level or mode, full motion uses a short token-controlled crossfade with inert outgoing content; reduced/off switch immediately without equal-scale FLIP. Cover changed-scale replacement even with unchanged current ID and clean up interrupted frames on unmount/replacement.

## 2. Focused motion evidence (2 hours)

- [x] 2.1 Extend map_pan.test.js and the smallest renderer/scene-transition file for mode/level decisions, dots moving with ground, immediate reduced/off and inert leaving controls; add controlled World/LocalMap same-scale/ladder/compression movement stories with play geometry assertions.
- [x] 2.2 Run each affected Vitest file separately, update only the matching executed-evidence method and add/run one focused SceneTransitionsBrowserTest method via unittest_driver. Add every new browser method to .github/browser-shards.json.

## 3. Mandatory complete visual journey (2 hours)

- [x] 3.1 Use agent-browser to capture/inspect all five metric fixture stories and movement stories at reference/chrome-cap viewports with full/reduced/off cases; record story IDs, modes/levels and screenshot paths. Story play success alone cannot complete this task.
- [x] 3.2 Use agent-browser in the real client to walk Altoria south gate → wilderness → back with actual controls, recording current node IDs, all adjacent exits, far-side labels and exact return actions. Observe same-scale dots moving on a street step and compare one unchanged overlay/graph control; any unusable exit or animated reduced/off scale blocks completion.

## 4. Traceability and final handoff (1 hour)

- [x] 4.1 Attach canonical tool-generated IDs to the matching Python motion/browser evidence, verify exact manifest ownership, run tools.spec_traceability check, tools.contract_gate and openspec validate animate-minimap-scale-transitions --strict. Record exercised focused checks; no full suites or CI-only complete evidence command.
- [x] 4.2 Update touched transition/story comments and the approved minimap design implementation-status documentation only after the complete batch behavior and visual journey pass; retain excluded full-map follow-up scope and include screenshot/journey results in the handoff.

