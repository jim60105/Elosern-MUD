# Tasks: wilderness-anchor-footprint

## 1. Registry v2 (world/lore)

- [ ] 1.1 Rewrite `world/lore/wilderness_entry.py`: frozen `WildernessGate` +
      `WildernessEntryPoint` (shape mask, origin, gates) with derived helpers `footprint_cells`,
      `anchor_cell`, `approach_cell(gate)`; author the `capital_altoria` 5×5 entry
      (origin `(58,98)`, gates `n→(2,0)`, `s→(2,4)`) per design D1.
- [ ] 1.2 Add `validate_wilderness_entries()` (pure) covering every rejection rule in the
      `WILDERNESS_ENTRY_REGISTRY authored data is validated before persistence` requirement;
      call it from `world/lore/sync.py`'s wilderness mirror step before mirroring.
- [ ] 1.3 Update `world/lore/tests/` for the v2 schema: derived-geometry values, point-shape
      semantics, each validation rejection, `sync_all` fail-fast, LoreRecord mirror idempotence
      (adapt existing `test_sync.py` expectations for the new payload shape).

## 2. Provider boundary (world/maps)

- [ ] 2.1 `world/maps/wilderness_provider.py`: exclude registry footprint cells in
      `is_valid_coordinates` via a registry-identity-keyed cache (design D2); no anchor-key
      special-casing.
- [ ] 2.2 `at_prepare_room`: open the gate exit's locks
      (`traverse:true();view:true()`) at each registered approach cell using the
      `return_direction` long-form key; touch nothing elsewhere (design D3).
- [ ] 2.3 Update/extend provider tests: footprint invalid / approach valid, registry-patch
      honesty, per-approach-cell lock opening, no lock leak when a pooled room re-activates at a
      non-approach coordinate.

## 3. Canonical resolver + traversal lockstep

- [ ] 3.1 `world/maps/wilderness_destination.py`: make `wilderness_neighbor` return `None` for
      provider-invalid neighbors; add the shared gateway helper
      (coordinates + direction → entry+gate via `approach_cell`/`return_direction`, incl.
      point-shape at anchor cell); rewrite `resolve_wilderness_destination` to use both; delete
      the hardcoded `"s"` rule.
- [ ] 3.2 `typeclasses/exits.py`: `WildernessReturnExit.at_traverse` uses the shared helper and
      resolves the destination room via `GridRoom.objects.filter_xyz(gate.grid_xy, z_map_key)`;
      delete `_grid_room_for_anchor`; `WildernessGateExit.at_traverse` lands at
      `approach_cell(gate)` from `db.anchor_key` + `db.gate_direction`. Both branches keep
      `after_successful_movement(cost_key="wilderness_move")` semantics unchanged.
- [ ] 3.3 Gateway tests: north at `(60,97)` → 南門 `(2,0)`, south at `(60,103)` → 北門 `(2,4)`,
      wrong-direction-at-approach = ordinary step, wall step refused (no clock, no knowledge),
      gate exit lands at the right approach cell per gate, missing destination room fails closed;
      extend the resolver↔traversal pinning test to every direction around both approach cells.

## 4. Bootstrap provisioning

- [ ] 4.1 `world/maps/bootstrap.py::sync_wilderness()`: provision one `WildernessGateExit` per
      registered gate on its destination room with `db.anchor_key` + `db.gate_direction`; heal
      mis-provisioned attributes in place; skip a gate whose room is missing with a warning;
      keep the restart description-refresh pass working.
- [ ] 4.2 Bootstrap tests: both gates provisioned, idempotence (no duplicates), attribute
      healing, per-gate graceful skip, immediately-usable gate exits.

## 5. Consumer migration + re-pinned contracts

- [ ] 5.1 `world/maps/wilderness_population.py`: redefine `CAPITAL_ENTRY_XY` as the north gate's
      approach cell `(60, 103)` (hunting-band center); update
      `world/maps/tests/test_wilderness_population.py` (~35 `(60,100)` sites → gate-scoped
      cells; literal pin `population_for_coordinates(60, 103)` →
      `MonsterPopulation(tier="low", name_zh="哥布林")` via `12,667,711 % 10 == 1 < 6`,
      `% 3 == 1`; band scenarios recentre per the reworded spec).
- [ ] 5.2 `world/lore/tests/test_wilderness_entry.py` and
      `world/maps/tests/test_wilderness_provider.py`: v2 schema assertions (shape, origin,
      gates, derived helpers); terrain literal pin moves to
      `terrain_description(60, 103)` → same pinned string per the terrain delta.
- [ ] 5.3 `world/maps/tests/test_wilderness_destination.py` + `typeclasses/tests/test_exits.py`:
      per-gate traversal/return pins (`(60,97)` north → `(2,0)`; `(60,103)` south → `(2,4)`);
      keep the `gateway_rule` injection seam working with a v2-typed rule.
- [ ] 5.4 `world/maps/tests/test_bootstrap.py`, `test_city_wilderness_roundtrip.py`,
      `world/rules/tests/test_{map_knowledge_integration,movement_settlement,party_follow}.py`:
      replace `(60, 100)` entry literals with gate approach cells; roundtrip enters via a gate
      exit and returns via its approach cell; party-follow arrival pins per the party delta
      (companion at the gate's approach cell).
- [ ] 5.5 Re-pin contract tests for the three reworded specs (`wilderness-terrain`
      region/entry + literal-description scenario, `wilderness-monster-population` entry +
      hunting-band scenarios, `party-system` gate-follow scenario) exactly as their delta
      wording states.
- [ ] 5.6 Minimal honest webclient survival migration (full per-gate presentation stays in
      `wilderness-anchor-footprint-local-map`): replace the `entry.wilderness_xy` reads in
      `web/webclient/presentation/local_map.py` — the grid-side gate candidate derives its
      `wild:` identity from the gate exit's own `db.anchor_key`/`db.gate_direction` → registry
      → `approach_cell` when present (key/alias parsing stays until P1b), and the region label
      reads the north-gate approach cell. Payload schema/shape is preserved; node identity
      legitimately changes to the real landing cells — update the `ENTRY_ID` pin, visited-node
      fixtures, and `web/tests/browser/seed.py` entry cell accordingly. `npm test` + the one
      local-map browser class stay green.

## 6. Traceability, docs, gates

- [ ] 6.1 Annotate the requirement-owning tests with `covers_requirement` literal IDs from
      `uv run --locked python -m tools.spec_traceability list` (RENAMED requirements get new IDs;
      run `check` until clean). Register any new test module in exactly one shard of
      `.github/evennia-shards.json`.
- [ ] 6.2 Confirm no player-command surface changed (gates remain directional exits; no alias
      changes) — if any key/alias changed, update `docs/game/commands.md` and
      `docs/game/command-reference.md` and keep `tests/test_command_docs.py` green.
- [ ] 6.3 Focused runs green: `world.lore`, `world.maps`, `world.rules`, `typeclasses` exits
      tests (then the shard-safe full run owned by CI).
