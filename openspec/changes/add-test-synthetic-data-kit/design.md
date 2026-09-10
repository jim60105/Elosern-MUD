# Design: Synthetic Test-Data Kit

## Context

Behavior tests need game entities (item, skill, region, preset, quest, title, buff, act)
whose ids and prose the test controls. Shipped catalogs come in two runtime shapes
(surveyed in the gate change): plain dicts (`ITEM_REGISTRY`, `SKILL_REGISTRY`,
`SUBRACE_REGISTRY`, `ANCHOR_REGISTRY`, `WILDERNESS_REGION_REGISTRY`,
`QUEST_*_REGISTRY`, `PRICE_TABLE`, `MP_COST_TIERS`, `BUFF_DEFINITIONS`, ...) and frozen
`MappingProxyType` (`NPC_TIER_REGISTRY`, `MONSTER_TIER_REGISTRY`, `CITY_GATE_REGISTRY`,
`FIXED_TITLE_REGISTRY`, `DIALOGUE_TABLE`, `SCENE_ARCHETYPE_REGISTRY`, ...). Production
consumers import registries by name (`from world.lore.npc_tiers import
NPC_TIER_REGISTRY`), so the repo's established mocking pattern — patching the consumer
module's binding (e.g. `test_bootstrap.py:300` patches `world.maps.bootstrap.MAPSTR_MAP`)
— is the injection seam. The single-writer invariant is untouched: this is test-only
input substitution, not state mutation.

## Goals / Non-Goals

**Goals:** one shared stand-in world; exact patch/restore; gate-clean by construction;
usable from Evennia tests, plain unittest, Node gate, and Vitest.
**Non-Goals:** a fake game engine (rules still run for real); migrating any existing
test; any production refactor (a migration that needs a better seam requests one in its
own change).

## Decisions

### D1 — One Python module, catalog dicts, `t_` prefix

`world/tests/synthetic_data.py` defines, per catalog, a module-level dict built from the
REAL definition dataclasses (importing classes is not importing content): `SYNTH_ITEMS:
dict[str, ItemDefinition]`, `SYNTH_SKILLS`, `SYNTH_SUBRACES`, `SYNTH_PRESETS`,
`SYNTH_NPC_TIERS`, `SYNTH_MONSTER_TIERS`, `SYNTH_ANCHORS`, `SYNTH_REGIONS`,
`SYNTH_CITY_GATES`, `SYNTH_ARCHETYPES`, `SYNTH_SHOPS`, `SYNTH_QUESTS`,
`SYNTH_QUEST_ISSUANCE`, `SYNTH_TITLES`, `SYNTH_DIALOGUE`, `SYNTH_BUFFS`,
`SYNTH_ACTS`, plus economy/cost-tier maps. All keys use the reserved prefix `t_`
(`t_ember_spray`, `t_iron_fang`, `t_wayfarer_pass`, ...) and every display field uses
invented zh-TW prose (`熾焰噴射`, `鐵牙`, `行旅通行證`), chosen so neither keys nor labels
appear in shipped data. The kit must stay small: ~3-6 entries per catalog, covering the
shapes tests need (weapon/consumable/material, spell/physical/martial skill, city +
wilderness region, one shop with stock, one starter preset, one quest with one objective,
...). Deep entries exist only where a migration genuinely needs them; growth happens in
migration changes via the `make_*` factories.

### D2 — Injection: target table + discovered bindings + scoped patch/restore

`REGISTRY_TARGETS` maps logical names (`"items"`, `"skills"`, `"npc_tiers"`, ...) to
`(module, attribute)` pairs. Consumer coverage is not hand-maintained: at patch time
the kit discovers (AST pass over the `world/`/`commands/`/`typeclasses/`/`server/`/
`web/` source tree, cached) every module binding that name-imported a target attribute
and patches each discovered binding for the scope — the `from x import Y` identity
problem is enumerable, so it is enumerated instead of remembered in a list that rots.
`world/lore/sync.py::_ALL_REGISTRIES` captures registry references at import time for
DB mirroring and is an explicit named target: scopes whose path invokes `sync_all()`
include it; scopes that never sync exclude it and depend on no DB-mirror content.
`synthetic_registries("items", "skills")` is both a context manager and a class/test
decorator that, per target: `patch.dict` for plain dicts; `patch.object(module, attr,
synth)` (and each discovered consumer binding) for `MappingProxyType`. Restoration is
exact (unittest.mock semantics), satisfying the `evennia-test-optimization`
registry-restoration requirement. The target table lives ONLY in the kit so catalog
refactors touch one place.

### D2b — Process-scoped install for separate test processes

The managed-browser harness runs its seed (`python -m web.tests.browser.seed`) and the
Evennia server (`evennia --settings browser_settings`) in their own processes against a
private SQLite DB, and `at_server_start` lore/map sync mirrors whatever the catalogs
hold into persistent rows — an in-process `patch.dict` in the Playwright process can
reach neither. The kit therefore also exposes an idempotent `install_synthetic_catalogs()`
bootstrap: when its opt-in environment flag is set, `web/tests/browser/browser_settings.py`
installs the synthetic catalogs in the seed process and the server process before any
startup mirroring — the same seam pattern as the existing `ART_SD_CLIENT` fake-client
override. `migrate-browser-tests-off-real-data` owns wiring the flag and proving one
end-to-end `t_`-key journey.

### D3 — Local fixtures over shared-catalog bloat

`make_item(key=..., **overrides)`, `make_skill(...)`, etc. return real dataclass
instances; tests needing exotic shapes pass locally-built entries to
`synthetic_registries(extra={"items": {key: item}})` instead of adding to the shared
dicts. Shared catalogs stay representative, not exhaustive — a fixture that no test
asserts against is debt, not coverage.

### D4 — JS mirror by payload, not by structure

The JS corpora never hold game logic — they hold payloads. The mirrors export
`SYNTH_ITEM`, `SYNTH_SKILL`, `SYNTH_PRESET`, `SYNTH_QUEST`, `SYNTH_TITLE` payload objects
(id + CJK label + fields the panels/actions read), identical values in both mirror files,
with a Node self-test asserting they match the Python kit's literals (the JS file embeds
the expected literals; the Python self-test asserts both sides) — drift becomes a red
test, not a silent fork.

### D5 — Gate-clean by construction

The kit self-test runs `tools.test_data_lint`'s scanner API over the kit file and the JS
mirrors: zero flags. If a future shipped-data rename collides with a `t_` key (or an
invented CJK label appears in shipped prose), the self-test fails first — the kit's
independence is a tested invariant, not a naming hope.

## Risks / Trade-offs

- **Name-import bindings**: handled by discovery (D2). If a binding escapes the AST pass
  (dynamic imports), it is added as an explicit recorded target with a reason, and the
  self-test exercises every discovered binding through its real consumer path — not one
  representative.
- **Kit drift from real shapes**: real dataclasses gaining a required field breaks the
  self-test immediately (it constructs instances from the real classes).
- **MappingProxyType attribute-swap vs frozen promise**: the swap lives inside the patch
  window only; shipped code never mutates the proxy; frozen semantics outside tests are
  untouched.
- **DB-mirrored lore**: in-process patches do not rewrite already-synced Script rows.
  Tests must not depend on DB mirror content; browser and DB-mirror paths use the
  process install (D2b) so mirroring itself happens from synthetic data.

## Migration Plan

Land alone; no behavior change. Migrations consume it; the final migration's closure
proves the kit absorbed the whole corpus.
