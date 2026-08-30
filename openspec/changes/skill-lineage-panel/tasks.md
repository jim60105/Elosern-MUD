# Tasks: skill-lineage-panel

## 1. Read model

- [ ] 1.1 `world/rules/lineage_query.py`: `LineageNodeView` /
  `LineageChainView` / `LineageView` frozen dataclasses per the delta; chain =
  reverse-edge closure from each root, topological node order; `usable` via
  `can_use_skill`, `capped` via the derived tip cap, `prereq_text_zh` rendered
  from registry edge data.
- [ ] 1.2 Pure-unittest suite `world/rules/tests/test_lineage_query.py`:
  determinism (double build equal), saturation text, locked-node text, meter
  math, zero-write assertion. Register in `.github/evennia-shards.json`.

## 2. OOB panel (four mirrors)

- [ ] 2.1 `web/webclient/protocol.py` (validator side): panel name `lineage`
  schema version 1, availability discriminator, `LINEAGE_MAX_CHAINS` /
  `LINEAGE_MAX_NODES_PER_CHAIN` / text caps with declared truncation order.
- [ ] 2.2 Presenter (`web/webclient/panels/`): serialize `LineageView`
  read-only; malformed proficiency entry → common unavailable form.
- [ ] 2.3 JS side (`web/webclient-app/`): `lineage` validator mirroring caps;
  big-window component with tree expand/collapse, `xp_into_level / 50` meters,
  見頂 marks, header `已完成 N / M 樹`; Vitest component tests.
- [ ] 2.4 Boundary tests pinning every cap (Python + JS).

## 3. Telnet command + mount

- [ ] 3.1 `commands/`: `lineage` command class printing the view tree (in and
  out of combat, mutation-free); mount on `CharacterCmdSet` in
  `commands/default_cmdsets.py`.
- [ ] 3.2 Integration test `commands/tests/test_lineage_command.py`: printed
  tree equals the view; state unchanged. Register in
  `.github/evennia-shards.json`.

## 4. Unlock toast

- [ ] 4.1 `world/rules/progression.py`: after a live practice grant, re-check
  `can_use_skill` for edges consuming that skill; push one toast via the
  existing OOB toast channel (text line on Telnet). Guard: auto-seed paths
  (import/scene-builder) pass a `silent=True` flag and notify nobody.
- [ ] 4.2 Test: one toast on the flip edge, none on the second grant at the
  same level, none during auto-seed.

## 5. Command docs

- [ ] 5.1 Add the canonical `lineage` entry to
  `docs/game/command-reference.md`, the overview row in
  `docs/game/commands.md`, and the curated manifest row in
  `tests/test_command_docs.py` (same change).

## Verification

- [ ] V1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules web.webclient commands tests.test_command_docs`
- [ ] V2 `npm test` (Vitest lineage component tests)
- [ ] V3 `uv run --locked python -m tools.spec_traceability check` (0 errors)
- [ ] V4 `uv run --locked python -m compileall -q world typeclasses commands server`
- [ ] V5 `openspec validate skill-lineage-panel --strict`
- [ ] V6 one managed browser class for the lineage window locally (budget ≤5 min); full browser suite is CI-owned
- [ ] V7 `git diff --check`

## Post-sync traceability (during archive/sync)

- [ ] P1 On sync, annotate the `skill-lineage-panel` requirement IDs (from
  `tools.spec_traceability list`) on the §1.2/§2.4/§3.2/§4.2 tests that
  establish them; annotate the new `game-command-docs` requirement on the
  drift-test scenario.
