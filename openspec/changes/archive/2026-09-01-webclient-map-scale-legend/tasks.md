# Tasks: webclient-map-scale-legend

## 1. Server legend (Python)

- [x] 1.1 `web/webclient/presentation/local_map.py`: `from world.maps import
      wilderness_provider` (module import — never `from … import WILDERNESS_KM_PER_CELL`, which
      would freeze the value at import time); build the wilderness-layer payload legend as
      `(*LEGEND_LABELS, f"每格約 {wilderness_provider.WILDERNESS_KM_PER_CELL} 公里")` (wording
      per design open question); other layers keep `LEGEND_LABELS`.
- [x] 1.2 Extend `web/webclient/presentation/tests/test_local_map.py`: wilderness payload legend
      = 4 states + scale note containing the constant's figure; grid/instance/interior legends
      byte-identical to `LEGEND_LABELS`; patched-constant test patching
      `world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL` (module-attribute target);
      validator still accepts
      (bounds: 16 entries, 256 code points).

## 2. Client legend treatment (Vue)

- [x] 2.1 `web/webclient-app/components/MapLattice.vue`: replace the modulo state-cycle
      (`legendState`) for indices ≥ 4 with the neutral `--info` chip treatment; add the
      design-token-based `local-map__legend-chip--info` style (no new hex literals); keep the
      first four entries' treatments and order untouched.
- [x] 2.2 Extend `web/webclient-app/tests/world/map_lattice.test.js` (or `local_map.test.js`
      convention): five-entry legend renders 4 state chips + 1 info chip; info chip never
      carries a state class; island mount still renders no legend element.
- [x] 2.3 Audit and update fixtures/stories that pin legend content or length:
      `web/webclient-app/stories/fixtures.js`, `stories/World/LocalMap.stories.js`,
      `MapLattice.stories.js` — `npm test` and
      `npm run showcase-coverage` green locally.

## 3. Browser + traceability gates

- [x] 3.1 Extend the local-map browser class (`web/tests/browser/test_browser_local_map.py`
      family): overlay renders the scale note as the fifth, info-styled legend entry; island DOM
      unchanged. (Full managed browser suite is CI-owned; run the one class locally.)
- [x] 3.2 Annotate the two new requirement-owning tests with `covers_requirement` literal IDs
      from `uv run --locked python -m tools.spec_traceability list`;
      `... tools.spec_traceability check` clean.
- [x] 3.3 Confirm no player-command surface change (none expected); focused Python runs
      (`web.webclient` presentation tests) and `npm test` green.
