# Design

## Context

See `proposal.md` for motivation. All eight spots were read while planning. In the helper module `world/rules/tests/test_guild_economy_sync/_support.py`, `_village_places()` returns every place outside the settlement that owns the guild hall, so it already spans all villages; the pins below are what still assume one village.

The project rule: tests define logic and never pin shipped game data. A rewritten assertion states the relationship the old literal stood for and reads its operands from the live registries.

## Goals / Non-Goals

**Goals:**

- The edited tests pass on today's data and keep passing when any village gains hosts, homes, shelves or dialogue tables.

**Non-Goals:**

- No new test, no new assertion on shipped data, no runtime change.
- No change to what a test proves beyond removing the pin. Other assertions in the same methods stay as they are.

## Decisions

Each decision names the file, the method or helper, the current text, and the replacement. Keep every decorator.

### Decision 1: `world/lore/tests/test_dialogue_assembly.py`

- `test_assembled_dialogue_snapshot_contains_all_25_tables`: rename to `test_assembled_dialogue_snapshot_contains_every_bound_table` and replace the body with:

```python
        from world.lore.settlements.places import PLACE_REGISTRY

        bound = _keys(PLACE_REGISTRY.values())
        self.assertTrue(bound)
        self.assertEqual(len(DIALOGUE_SNAPSHOT), len(bound))
```

- `test_each_table_terrace_matches_its_place_row`: the line `all_bound_keys = lower_places | middle_places | upper_places | ciaran_places` becomes:

```python
        from world.lore.settlements.places import PLACE_REGISTRY

        all_bound_keys = _keys(PLACE_REGISTRY.values())
```

Leave the four per-slice variables and everything after `all_bound_keys` unchanged. If `ciaran_places` is then unused in the method, keep the assignment only if a later line reads it; otherwise delete that one assignment.

### Decision 2: `world/rules/tests/test_dialogue_sources.py`

`test_complete_inventory_of_25_tables`: rename to `test_complete_inventory_of_bound_tables`. Replace

```python
        self.assertEqual(len(bindings), 25)
        self.assertEqual(len(DIALOGUE_SNAPSHOT), 25)
```

with

```python
        self.assertTrue(bindings)
        self.assertEqual(set(bindings), set(DIALOGUE_SNAPSHOT))
```

### Decision 3: `world/rules/tests/test_guild_economy_sync/test_service_host_identity.py`

Two assertions count `guild_service_host_created` events against the literal 25: `self.assertEqual(len(events), 25)` and `self.assertEqual(len(late), 25)`. Replace the literal in both with `len(get_catalog().service_hosts)`; if `get_catalog` is not imported in the module, add `from world.rules.guild_config import get_catalog`. Replace the comment block above the first one (it enumerates the 25 hosts) with one line: one event per derived service-host row.

### Decision 4: `world/rules/tests/test_guild_economy_sync/test_service_host_merchant_dialogue.py`

`self.assertEqual(len(places), 13, "roster lost a merchant place")` becomes `self.assertTrue(places, "roster has no merchant place")`. Trim the comment above it so it no longer counts voices.

### Decision 5: the village subrace helper

In `world/rules/tests/test_guild_economy_sync/_support.py`, replace `_village_subrace_key()` with a helper that returns every village subrace:

```python
def _village_subrace_keys() -> frozenset[str]:
    """The subraces village hosts are authored to carry, registry-derived.

    The villages' people are minority subraces WITHIN the capital's races: a
    village subrace is an authored host subrace that no place of the capital
    (the settlement owning the guild hall) declares.
    """
    places = _places()
    capital_keys = {
        place.settlement_key
        for place in places.values()
        if place.kind == "guild_hall"
    }
    capital_subraces = {
        place.host_subrace
        for place in places.values()
        if place.settlement_key in capital_keys and place.host_subrace
    }
    distinct = frozenset(
        place.host_subrace
        for place in _village_places()
        if place.host_subrace and place.host_subrace not in capital_subraces
    )
    assert distinct, "no village host declares a minority subrace"
    return distinct
```

Update the module's `__all__` or re-export list if it names the old helper. In `test_ciaran_village_commerce.py`:

- the import of `_village_subrace_key` becomes `_village_subrace_keys`;
- in `test_trade_and_shop_command_paths_have_no_archetype_branch`, the tuple entry `"elven_" + f"village_{_village_subrace_key()}",` becomes `*("elven_" + f"village_{key}" for key in sorted(_village_subrace_keys())),`;
- in `test_village_hosts_carry_authored_minority_identity`, delete the line `village_subrace = _village_subrace_key()`, add as the first line of the method `self.assertTrue(_village_subrace_keys())`, and change `self.assertEqual(host.subrace, village_subrace)` to `self.assertEqual(host.subrace, place.host_subrace)`.

Run `grep -rn "_village_subrace_key\b" world` afterwards; it must print nothing.

### Decision 6: the dialogue-only homes

In `CiaranVillageCommonsTests` (`test_ciaran_village_commerce.py`), `_attendants` returns every dialogue-only place of every village. Scope it to the commons' own settlement:

```python
    def _attendants(self):
        settlement_key = self._commons().settlement_key
        return tuple(
            p
            for p in _village_places()
            if p.settlement_key == settlement_key
            and [declaration.type for declaration in p.components] == ["scripted_dialogue"]
        )
```

In `test_three_commons_sync_once_and_the_training_ground_holds_two_doorways`, `self.assertEqual(len(attendants), 2)` becomes `self.assertTrue(attendants)`. Change nothing else in the class. If another method of the class indexes `attendants` by position or unpacks exactly two, leave it: it still receives the same two rows today, and the scoping keeps it so.

### Decision 7: the rarity claim

In `test_rarity_is_read_nowhere_in_resolving_village_prices` (`test_ciaran_village_commerce.py`), inside the loop over `shared`, delete the `self.assertNotEqual(_items()[item_key].presentation.rarity, "common")` statement and reduce the comment above it to: the village price is the everyday one, cheaper than every capital resolution of the key. Keep the `assertLess` beside it. If `_items` is then unused in the module, remove it from the import list.

### Decision 8: `world/lore/tests/test_shops.py`

Replace `test_shipped_registry_carries_the_seven_capital_and_six_village_shops` (keep any decorators it carries) with:

```python
    def test_shop_registry_follows_the_place_registry_order(self):
        # A shop identity is derived from a place's merchant capability, so
        # the registry is exactly the places that author one, in place order.
        # Which places those are is game data and is not pinned here.
        from world.lore.settlements.places import PLACE_REGISTRY, place_shop_identity

        expected = [
            shop_key
            for shop_key in map(place_shop_identity, PLACE_REGISTRY.values())
            if shop_key is not None
        ]
        self.assertTrue(expected)
        self.assertEqual(list(SHOP_REGISTRY), expected)
```

### Decision 9: renamed methods and tooling files

Three methods are renamed. `tools/test_data_freeze.json`, `tools/test_data_lint_seed.json` and `.github/evennia-shards.json` may name test methods or modules. After the edits run `grep -rn "contains_all_25_tables\|inventory_of_25_tables\|seven_capital_and_six_village_shops" tools .github docs openspec/specs world tests`; update any hit outside `openspec/changes/` to the new name.

## Risks / Trade-offs

- [The rewrites cannot be seen failing until a second village has hosts] → Each replacement is the registry-derived form of the old literal, and task 3.1 confirms each new expression equals the old literal on today's data before the literal is removed.
- [Another pin exists that planning did not find] → The village changes carry a rule for it: rewrite to logic, append no key.
