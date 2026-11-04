# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Add immutable compositions and ecology declarations

- [x] 1.1 Implement the exact values, registries and reference validation in monster_placement.py, without removing AmbientPlacementRule yet or modifying live state. Extend `world/lore/tests/test_monster_placement.py` with synthetic unknown variant, habitat mismatch, duplicate key, bool/count/timing, weight and immutable-registry cases. Document signatures in `docs/development/regional-monster-population.md`. Check: all malformed candidates reject before publication and valid declarations retain exact nested references.

## 2. Validate bounded candidate-world birth geometry

- [x] 2.1 Implement population_geometry.py and wire candidate publication in runtime/geography using the declared pure API. Add `world/maps/tests/test_population_geometry.py` and candidate-publication assertions in `test_geography_source.py`; register the new module once in evennia-shards. Check: E=25,densities 5/12 yields L=2,U=3; footprint/noncapital/point rings exclude births, a dungeon receives no settlement buffer, unconfigured cells are absent, overlapping zones and group-stranded intervals reject, and a rejected candidate leaves the prior published snapshot unchanged. Author the four exact initial declarations and pools listed in the design; production integrity checks resolve references and geometry generically instead of pinning these coordinates/counts. Human-review their ecology in the developer document.

## 3. Slice handoff

- [x] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate regional-ecology-authoring --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.
