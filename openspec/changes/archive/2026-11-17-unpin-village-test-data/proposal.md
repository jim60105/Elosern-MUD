# Proposal

## Why

幽月谷村 and 翠綠森林村 are about to receive hosts, homes and shelves. Several existing tests were written when 暗影谷村 was the only village with hosts, and they pin that data: a count of 25 dialogue tables and 25 hosts, 13 merchant places, exactly one village subrace, exactly two dialogue-only homes, a literal list of shop keys, and a claim that no shared good is of common rarity. Each of these fails the moment a second village gains a host, although no logic changed. This change rewrites those assertions to the logic they stand for, so the village content changes that follow need no test surgery.

It changes tests only. No runtime code, data, specification or requirement changes, so it carries no specification delta (`skip_specs: true`). It adds no test.

## What Changes

- Eight existing assertions stop depending on shipped data. Each keeps its method name unless noted, its decorators and its other assertions:
  - `world/lore/tests/test_dialogue_assembly.py`: the table count and the per-slice key union.
  - `world/rules/tests/test_dialogue_sources.py`: the binding and table counts.
  - `world/rules/tests/test_guild_economy_sync/test_service_host_identity.py`: two host-created event counts.
  - `world/rules/tests/test_guild_economy_sync/test_service_host_merchant_dialogue.py`: the merchant place count.
  - `world/rules/tests/test_guild_economy_sync/_support.py` and `test_ciaran_village_commerce.py`: the single-village-subrace helper and its two callers, the dialogue-only home count, and the rarity claim about shared goods.
  - `world/lore/tests/test_shops.py`: the literal shop-key list.
- No key, name or number is appended anywhere.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Every requirement the edited tests cover keeps its `@covers_requirement` decorator and keeps being proved.

## Impact

- Edited tests only: the six test modules named above and the `_support.py` helper beside them.
- Not touched: all runtime code, all lore data, all rulebooks, every file under `openspec/specs/`.
- No child Git repository is needed.

## Batch:

- depends-on: none
- conflicts: none with `elven-village-local-goods` (item data only), `drop-settlement-city-gate-field` or `retire-limbo-city-gates` (map gate code and documents).
- `eolas-village-craft-homes`, `eolas-village-fare-homes`, `fionnen-village-craft-homes` and `fionnen-village-fare-homes` depend on this change.
