# Tasks

Ground rules:
- Edit only the files named.
- Copy D1–D2 contracts and problem codes verbatim.
- Do not change shipped map data.
- Add no `@covers_requirement` for `settlement-map-rework::*` (Workflow follow-up).
- Run `uv run --locked python -m unittest tests.test_settlement_map_rework` standalone.

## 1. Reference-preserving replace

- [ ] 1.1 Create `tools/settlement_synthesis/rework.py` with `ReworkPlan`, `ReworkError`, `protected_nodes` and `apply_bindings`, implementing the D1 order of checks, nearest resolution, suffix renaming and field copying.
  - Protected ids are the union of:
    - interior `exterior.node` values where `exterior.settlement == map_id`;
    - district landmarks with `domain == "settlement_node"` and `map_id == map_id`;
    - `incoming_references` keys starting with `f"settlement_node:{map_id}:"`, taking the part after the second colon;
    - `city_gate.node`;
    - the anchor id.

  When `content/map-reference-context.json` is missing, `protected_nodes` returns every existing node id and `False`.
- [ ] 1.2 Extend the `generate` subcommand in `tools/settlement_synthesis/__main__.py` with `--replace` and `--bind` exactly as D2 describes. Without `--replace`, an existing file is still refused. With `--replace`, the comment-preserving write uses `parse_document(...).round_trip`. Check: `uv run --locked python -m tools.settlement_synthesis generate capital_altoria --replace --bind /dev/null --plan-only` exits 1 with a JSON or binding error and changes nothing. Then `git status --porcelain content` prints nothing.

## 2. Brief and prose

- [ ] 2.1 Create `tools/settlement_synthesis/prose.py` with `role_of(node_id, document, catalogue)`, `build_brief(view, map_id) -> dict` and `apply_prose(view, map_id, entries) -> int`, following D2. `apply_prose` raises `ReworkError` with the D2 problem codes.
- [ ] 2.2 Add the `brief` and `prose` subcommands (D2). Check: `uv run --locked python -m tools.settlement_synthesis brief capital_altoria` prints JSON with 21 `nodes` entries and leaves `git status --porcelain` unchanged. This is manual evidence only.

## 3. Tests (synthetic)

- [ ] 3.1 Create `tests/test_settlement_map_rework.py` with `ReplaceTests`, covering the four scenarios:
  - missing binding for `yard` → exit 1 naming `yard`, digest unchanged;
  - full binding → `gate` and `yard` keep key and desc, `synthetic_hall` `exterior.node == "yard"` still parses through `load_authoring_world`, `lint` exits 0;
  - refused bindings: `gate` bound to a filler, two ids bound to one slot, unknown node, unknown slot;
  - drop and no-index: add an unreferenced node `stray` to the synthetic map before the replace. With the index present it is dropped and listed in the report's `dropped`. With the index absent the replace exits 1 with `unbound_protected:stray`.
- [ ] 3.2 Add `NearestBindingTests`:
  - two nearest bindings to `central_plaza` resolve to the closest and next-closest approach or filler slot. Recompute the distances in the test from the plan-only report's `x_m` and `y_m`. Two runs from a freshly written original give identical bytes.
  - a collision case: bind the existing node `yard` to a slot, and add an existing node named `market_street` bound to `nearest:central_plaza`. The generated `market_street` slot becomes `market_street_2`, and all ids are unique.
- [ ] 3.3 Add `ProseTests`:
  - `brief` prints one entry per node with the D2 fields and leaves the digest unchanged;
  - `prose` with two valid entries changes only those keys and descs. Compare the parsed `document.data` before and after, with those four fields masked;
  - mixed invalid entries exit 1 listing `unknown_node:` and `empty_desc:`, and the file is byte-identical.
- [ ] 3.4 Add `"tests.test_settlement_map_rework"` to shard `index` 4 in `.github/top-level-shards.json`. Check: `tests.test_evennia_test_optimization_contract` passes and the new module passes.

## 4. Documentation

- [ ] 4.1 In `docs/development/settlement-synthesis.md`, add these sections: "Rework with bindings" (D1, with a worked synthetic example), "Prose pass" (D3, verbatim rules) and the D2 command reference. Append to "Human review": prose tone and lore fit, and descriptions whose site cue changed after a move.
- [ ] 4.2 In `.agents/skills/map-data-authoring/references/settlements.md`, add a recipe "Rework or name an existing local map". It covers `brief`, writing a prose JSON in the scratchpad, `prose`, then `lint`, `check_map_sources.py` and partition regeneration. It also states that `--replace` needs a bind file covering every protected node, and that prose is never hand-edited into YAML when the `prose` command can do it. Use the Edit tool. Check: `grep -n "settlement_synthesis prose" .agents/skills/map-data-authoring/references/settlements.md` prints a line.

- [ ] 4.3 In `docs/development/settlement-synthesis.md`, add § "Settlement-sensitive test modules" with the design D5 list, its runner notes and the "Residual pin rule", verbatim. Check: `grep -c "test_travel_plan" docs/development/settlement-synthesis.md` prints at least 1, and `grep -c "Residual pin rule" docs/development/settlement-synthesis.md` prints at least 1.

## 5. Gates

- [ ] 5.1 Run `tools.test_data_lint check`, `tools.spec_traceability check`, `tools.contract_gate` and `openspec validate settlement-rework-and-prose --strict`. Check: all succeed.

## Workflow follow-up

- At archive, decorate the D4 test classes' methods with their `settlement-map-rework::*` IDs and rerun `tools.spec_traceability check`.
