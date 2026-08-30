# Tasks: skill-lineage-panel

## 1. Read model

- [x] 1.1 `world/rules/lineage_query.py`: `LineageNodeView` /
  `LineageChainView` / `LineageView` frozen dataclasses per the delta; chain =
  reverse-edge closure from each lineage root (a prerequisite-less skill at
  least one edge consumes — a prereq-less skill nobody consumes is not a
  樹 and starts no chain), topological node order; `usable` via
  `can_use_skill`, `capped` via the derived tip cap, `prereq_text_zh` rendered
  from registry edge data.
- [x] 1.2 Pure-unittest suite `world/rules/tests/test_lineage_query.py`:
  determinism (double build equal), saturation text, locked-node text, meter
  math, zero-write assertion. Register in `.github/evennia-shards.json`.

## 2. OOB panel (four mirrors)

- [x] 2.1 `web/webclient/protocol.py` (validator side): panel name `lineage`
  schema version 1, availability discriminator, `LINEAGE_MAX_CHAINS` /
  `LINEAGE_MAX_NODES_PER_CHAIN` / text caps with declared truncation order.
- [x] 2.2 Presenter (`web/webclient/presentation/lineage.py`): serialize
  `LineageView` read-only with `kind: "lineage"`; malformed proficiency entry
  → common unavailable form. Truncation order declared: drop trailing chains
  to `LINEAGE_MAX_CHAINS`, then trailing nodes to
  `LINEAGE_MAX_NODES_PER_CHAIN`, then further trailing chains until the
  payload fits `MAX_CANONICAL_JSON_BYTES`; `completed_count`/`total_count`
  always serialize the FULL view (never recomputed after truncation).
  Register the spec with all four fields (name, schema_version,
  unavailable_reason, presenter).
- [x] 2.3 JS side (`web/static/webclient/js/elosern/protocol.js` +
  `web/webclient-app/`): `lineage` validator mirroring caps + `kind`;
  big-window component with tree expand/collapse, `xp_into_level / 50` meters,
  見頂 marks, header `已完成 N / M 樹`; Vitest component tests.
- [x] 2.4 Boundary tests pinning every cap (Python
  `presentation/tests/test_lineage_panel.py` + JS), including the full-view
  header counts surviving chain truncation and the byte-budget fail-closed.

## 3. Telnet command + mount

- [x] 3.1 `commands/`: `lineage` command class printing the view tree (in and
  out of combat, mutation-free); mount on `CharacterCmdSet` in
  `commands/default_cmdsets.py`.
- [x] 3.2 Integration test `commands/tests/test_lineage_command.py`: printed
  tree equals the view; state unchanged. Register in
  `.github/evennia-shards.json`.

## 4. Unlock toast

- [x] 4.1 `world/rules/progression.py`: `grant_skill_practice_xp` gains an
  optional `unlocks_out` list sink — after a live award, re-check
  `can_use_skill` for edges consuming that skill (reverse-edge cache); newly
  usable skills append one toast line each. Detection is derived, never
  persisted. Auto-seed never calls the grant, so it is intrinsically
  silent (no flag needed). `world/rules/action.py` owns the per-resolve sink
  and folds its lines into `ActionResult.notifications` only after the
  commit succeeds (cleared on `CommitFailed`); every outer settlement
  boundary (cast, combat) forwards them unchanged.

## 5. Command docs

- [x] 5.1 Add the canonical `lineage` entry to
  `docs/game/command-reference.md`, the overview row in
  `docs/game/commands.md`, and the curated manifest row in
  `tests/test_command_docs.py` (same change).

## Verification

- [x] V1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules web.webclient commands tests.test_command_docs`
- [x] V2 `npm test` (Vitest lineage component tests)
- [x] V3 `uv run --locked python -m tools.spec_traceability check` (0 errors)
- [x] V4 `uv run --locked python -m compileall -q world typeclasses commands server`
- [x] V5 `openspec validate skill-lineage-panel --strict`
- [x] V6 one managed browser class for the lineage window locally (budget ≤5 min); full browser suite is CI-owned
- [x] V7 `git diff --check`

## Post-sync traceability (during archive/sync)

- [x] P1 On sync, annotate the `skill-lineage-panel` requirement IDs (from
  `tools.spec_traceability list`) on the §1.2/§2.4/§3.2/§4.2 tests that
  establish them; annotate the new `game-command-docs` requirement on the
  drift-test scenario.
