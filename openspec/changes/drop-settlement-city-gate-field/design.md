# Design

## Context

Facts below were checked on master at e076e764, with the state after
`retire-limbo-city-gates` assumed.

- `packages/map-core/elosern_map_core/schema.py` (around line 638) declares
  `"city_gate": _nullable(_mapping({node, exit_key, exit_aliases}))` on the settlement
  kind. The field walker rejects any key that is not declared, with `unknown_field`
  (around line 1221). So the schema and the documents must change in the same commit.
- `documents.py` defines `CityGateDeclaration` (around line 183) and
  `SettlementDocument.city_gate`, parsed around lines 587 to 611. Around line 630 it adds
  the gate node to the set of referenced nodes.
- `authoring.py` (around line 1045) checks that `city_gate.node` is an authored node.
- After `retire-limbo-city-gates`, nothing under `world/`, `web/`, `server/`,
  `typeclasses/` or `commands/` reads `document.city_gate`, except test inline YAML.
- Map editor backend: `commands.py:441` (field list), `relationships.py` (`CITY_GATE`,
  `SetCityGate`, registered at line 505), `settlements.py:271,435` (new-settlement
  default, protected rows), `snapshot.py:504` (snapshot payload). Frontend:
  `relationship_refs.js::cityGateRef`, `relationships.js` (parse, label 「起始房間入口」,
  views, `setCityGate`), `relations.js:82`, `settlement.js:192`, `map_scene.js:248,307`,
  `objects.js:147`, `diagnostics.js:54`, `EntranceForm.vue` (radio
  `kind-city_gate`), and `RelationshipInspector.vue:144`.
- Synthesis: `generate.py:1361,1556` write `"city_gate": None`. `rework.py:92,279`
  protect and carry the node.
- Data: 338 settlement documents. 334 have the line `city_gate:` with nothing under it.
  Four have a populated block (node, exit_key, exit_aliases).

## Goals / Non-Goals

Goal: no authored, parsed, edited or generated `city_gate` anywhere. A document that
still carries the key is rejected by the existing unknown-field rule.

Non-goals: no change to wilderness entries, anchor rooms or the nodes the populated rows
pointed at. Those nodes (for example 暗影谷村's concealed path) stay as ordinary nodes,
still reachable through their wilderness gates. No editor UI replacement for the removed
kind.

## Decisions

### D1. Remove the field from map-core; rely on the existing unknown-field rule

Delete the schema entry, `CityGateDeclaration` (with its `__all__` entry), the parse
block, the field, the referenced-node addition, and the authoring check. Do not add a
special "city_gate is retired" diagnostic. The generic `unknown_field` message is the
mechanism, and the `map-settlement-sources` scenario pins it.

### D2. Data edit by a throwaway script

Write `strip_city_gate.py` in the session scratchpad (not in the repository). For each
`content/maps/settlements/*.yaml`, it deletes the line that matches `^city_gate:` and
every following line that starts with a space or `-`, up to the next line that starts
with a non-space character or the end of the file. It leaves every other byte alone.
Check the result:
- `rg -c "^city_gate:" content/maps/settlements` prints nothing;
- `git diff --numstat content/maps/settlements` shows only deletions: 338 files, 334 with
  1 deletion, 4 with 3 or 4;
- `uv run --locked python -m tools.contract_gate` and the map-core load (task 3.1) pass.

Then regenerate in the order `world/maps/AGENTS.md` gives: district partition, road
network, reference context. Commit whatever changes. Most likely only
`content/map-reference-context.json` changes, through its source digests.

### D3. Map editor: delete the kind end to end

- Backend: remove `("city_gate", "city_gate")` from `commands.py`. Remove `CITY_GATE`,
  `SetCityGate` and its registration from `relationships.py`, and the
  `set_city_gate` line in the module docstring. Remove `"city_gate": None` from the
  new-settlement default and the `city_gate` protected row in `settlements.py`. Remove
  the `city_gate` snapshot key in `snapshot.py`.
- Frontend: delete `cityGateRef` and every import of it. In `relationships.js`, remove the
  `CITY_GATE` pattern, its label, its parse branch, its view and kind branches,
  `setCityGate`, and its delete branch. Remove the `city_gate` rows in `relations.js`,
  `settlement.js`, `map_scene.js` (gate set and label list), `objects.js` and
  `diagnostics.js`. In `EntranceForm.vue`, remove the `city_gate` radio, the
  `setCityGate` emit branch and the start-entry paragraph. In `RelationshipInspector.vue`,
  remove the `city_gate` template.
- Run `rg -n "city_gate|cityGate|CityGate|起始房間入口" tools packages` afterwards. It
  must print nothing.

### D4. Synthesis tools

`generate.py`: delete both `"city_gate": None` entries. `rework.py`: delete the
protected-node addition (lines 92 and 93) and the carry-over block (around line 279).

## Risks / Trade-offs

- [The 338-file diff collides with an in-flight settlement edit.] Mitigation: apply from
  current master, and run the script last, after code and tests are green. Re-run it if
  a rebase brings new documents.
- [Editor browser tests that click the start-entry radio.] Task 4.4 runs
  `web.tests.browser.test_map_editor_relationships` and removes any step that selects
  `kind-city_gate`.
