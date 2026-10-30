# Tasks

Read design.md contracts before starting each group. Paths without a web/ prefix are relative to web/webclient-app/ unless the design names a server module. Use only this slice's named symbols/files and their focused evidence/docs; do not change sub-project1 rule semantics, authored content, camping, other layouts or unrelated windows. Prerequisites are the exact depends-on lines in proposal.md; shared-code conflicts are integration ordering only. Preserve existing non-travel tests and use real protocol fixtures rather than prototype rules.

## 1. Painter and disclosure evidence

- [ ] 1.1 Implement paintTravelMap and bounded buffer caches; replace TravelMap drawing only, retaining lib/travel-grid as its data boundary. Add tests/travel/paint.test.js with synthetic grids, independent alpha/compositing assertions, deterministic world-coordinate texture and paint invalidation counts. Update existing synchronization guidance with repaint keys. Acceptance: pnpm test -- web/webclient-app/tests/travel/paint.test.js exits0; camera-only updates leave the recorded paint-call counter unchanged.

## 2. Camera and glyphs

- [ ] 2.1 Implement travel-camera functions, measured bounds, transform zoom, SVG/HTML overlays and shared glyph travel states. Add tests/travel/camera.test.js and glyph-consumer assertions, preserving old shared states. Update webclient-app/AGENTS.md shared glyph guidance for named travel states. Acceptance: pnpm test -- web/webclient-app/tests/travel/camera.test.js exits0; resize/side exclusions fit synthetic routes without changing canvas pixels.

## 3. Stories and measured budget

- [ ] 3.1 Move Morning/MotionOff stories to real painter fixtures and add synthetic phase variants for Dusk/Night/Woodland, without production rule mocks. Add TravelMapTests.test_repaint_budget and test_map_viewports in web/tests/browser/test_wilderness_travel.py with exact browser-shard entries and screenshots at1451x790/2560x1440. Record actual paint timings, not jsdom timing. Also implement/register TravelMapTests.test_map_fact_layers with synthetic canvas alpha/clipping checks. Acceptance: focused managed TravelMapTests methods pass; all20 warmed paint samples at each viewport are<=50ms and camera-only paint count is0.

## Integration handoff

- [ ] 5.1 After all owned groups are complete, run the focused commands named above, the existing local contract gate and strict OpenSpec validation for this change. Record exercised command output, requirement-to-test mapping and any visual review separately; expected result is no uncovered requirement, schema mismatch, manifest ownership error or validation warning. Do not run broad CI/browser suites locally. Do not implement a dependent slice, sync or archive from this task list.
