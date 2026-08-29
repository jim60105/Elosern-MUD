# Tasks: add-equipment-effect-rulebook

Commit ordering: tasks 1.x, 2.x, and 3.2–3.4 form one atomic commit —
strict validation, registry bindings, canonical YAML, loader, and fixtures
must land together so no intermediate import or fixture-construction break
is ever committed.

## 1. Rulebook data and loader (new files first)

- [x] 1.1 Author `world/rules/rulebook/equipment_effects.yaml` with the
      budgets table and the full design balance sheet (existing 35 items incl.
      the empty `storage_pouch` entry, plus the 10 new keys).
- [x] 1.2 Create `world/rules/equipment_effects.py`: frozen dataclasses,
      `load_equipment_effect_rules(path=None)`, `reload_equipment_effect_rules()`
      (idempotent), `EquipmentEffectsRulebookError`; closed vocabularies,
      percent-string format, signedness, positive-only `gauge_caps`,
      gauge-target keys, five-column rarity
      budget checks per design D3, `immune`/`attached_buffs` resolution
      against `BUFF_DEFINITIONS` with the no-entry-attaches-and-immunises-the-
      same-key guard, and the equipment-key ↔ modifier-key ↔ rulebook-entry
      triple bijection (duplicate modifier bindings fail the load) —
      mirroring the `load_item_effect_rules` structure and comment discipline.

## 2. Registry identity and activation (same commit as 1.x)

- [x] 2.1 Add the `EquipmentModifierKey` closed StrEnum to
      `world/lore/items.py` (one member per roster key, canonical snake_case),
      and the `modifier_key` field on `ItemDefinition` with `__post_init__`
      validation: present iff `equipment_slot` is present; reject non-member
      values; register the 10 new `ItemDefinition`s (display/summary zh, icon
      kind, rarity per balance sheet, price-table reuse, `EquipmentSlot`,
      modifier key).
- [x] 2.2 Bind all 35 existing equipment entries to their modifier keys in
      `ITEM_REGISTRY`, list the 10 new items in
      `altoria_general_store.offered_item_keys` (`world/lore/shops.py`), and
      add `item_regen_light` to `world/rules/rulebook/buffs.yaml`
      (`duration: null`, `stacking: unique_per_source`, gentle hp `rate`)
      with its mandatory `status_display.yaml` metadata entry and the
      mandatory `test_buff_item_regen_light` in `world/rules/tests/test_buffs.py`
      (the rule-id/test correspondence contract fails any buff key without a
      named test).
- [x] 2.3 Migrate every test fixture that constructs an equipment-slot
      `ItemDefinition` to pass a valid canonical `modifier_key` (fixtures do
      NOT join `ITEM_REGISTRY`, so loader bijection is untouched). Known
      files: `world/lore/tests/test_items.py`, `commands/tests/test_items.py`,
      `world/skills/tests/test_equipment.py`,
      `world/rules/tests/test_equipment_toggle.py`,
      `world/rules/tests/test_item_use.py`,
      `world/rules/tests/test_shop_economy.py`,
      `world/rules/tests/test_service_view.py`,
      `world/rules/tests/test_guild_config.py`,
      `web/webclient/actions/tests/test_inventory_actions.py` — sweep for
      any others with `rg "ItemDefinition\\("` before handoff.

## 3. Validation tests

- [x] 3.1 Loader rejection tests (`unittest.TestCase`, temp-path overrides):
      canonical file loads; each rejection class fails with the named error —
      unknown field/wrong kind, budget overflow in each of the five columns
      (positive and negative), unknown buff reference, self-contradictory
      immune+attached reference, orphan entry, unbound equipment key, and
      two equipment definitions sharing one modifier key; reload is
      idempotent.
- [x] 3.2 Registry construction tests in `world/lore/tests/test_items.py`:
      equipment without key, key on non-equipment item, unknown member,
      use-mechanics + slot + key combination; existing ambiguous-mechanics
      scenarios stay green.
- [x] 3.3 Roster coverage test: canonical YAML ↔ `ITEM_REGISTRY` bijection,
      every new item registered/offered/price-resolvable/budget-valid, and
      the named-set Church doctrine check (sister_vestments,
      radiant_holy_emblem, saintess_vestments, pilgrim_medallion:
      non-negative `exposure_bias`/`pleasure_gain`, at least one of
      `heal_gain` or curse/dark immunity, no suppression values) per the
      delta spec.

## 4. Inertness and regression

- [x] 4.1 Inertness guards: (a) an AST/import test asserting no production
      module imports `world.rules.equipment_effects` outside the loader
      module itself (allowlist recorded in the test); (b) two behavior tests
      loading deviant rulebook copies whose dormant-only fields differ
      (e.g. different `pleasure_gain`/`immune` values) while combat, act
      resolution, and buff application outputs remain identical.
- [x] 4.2 Run focused suites: `world.lore`, `world.rules`, `commands.tests`,
      `world.skills`, `web.webclient` item actions — Node/Vitest unaffected
      (no payload changes). Then the non-browser suite once with
      `--parallel 16 --noinput --keepdb`.
- [x] 4.3 Record any deviation from the parent design here (or state none),
      and run `openspec validate add-equipment-effect-rulebook --strict`.

## Deviations recorded at handoff

- Fixture list shorter than enumerated: the `rg "ItemDefinition\\("` sweep
  showed `world/rules/tests/test_item_use.py`, `test_shop_economy.py`, and
  `test_guild_config.py` construct only slot-less consumables (meal/potion),
  so only the six slot-bearing fixture files were migrated. `test_guild_config.py`
  received the `len(ITEM_REGISTRY) == 58` pin instead.
- Rubber-Duck #2 remediation: the loader gained a duplicate-key guard (a
  raw-text test covers top-level, entry-level, and adjustment-level
  duplicates), the modifier-binding *identity* (`value == item key`) is now
  enforced at load time inside `validate_equipment_effect_rules` — so a
  registered item borrowing another item's binding is rejected even through
  the production path — and the percent grammar is ASCII-only (a
  non-ASCII-digit rejection test accompanies it). Design D7 records the
  three load-time properties; construction stays permissive per D7's
  fixture policy.
- Duplicate-modifier-binding collapse remains defence in depth (identity
  rejects first), so it is covered through the injectable
  `validate_equipment_effect_rules(document, registry, buff_keys)` seam with
  a synthetic registry copy.
- Dormancy probes strengthened (Rubber-Duck #3): the pleasure probe wears
  the mutated `black_maid_dress`, a separate heal probe wears the mutated
  `sister_vestments`, the immune/attachment probe wears the mutated
  `fearless_brooch`/`apothecary_beads` accessories, and the regen buff is
  granted under the mutated item's `source_key`; post-swap assertions prove
  the two captures really did load different dormant values. The inertness
  import scanner resolves package-relative `ImportFrom` levels against each
  scanned file's package, and the raw duplicate-key test asserts the
  loader's `duplicate YAML mapping key` diagnostic so nested cases cannot
  be masked by a later schema error.
- Rubber-Duck #1 additions: `server/conf/at_server_startstop.py` imports the
  loader at `at_server_start()` so a malformed rulebook fails loudly at boot
  (sanctioned sole production consumer; allowlisted in the inertness AST test,
  which also scans literal dynamic-import forms), and budgets may legitimately
  cap `bias` at 0 (common tier) while all other columns stay ≥ 1.
- Webclient services stock panel caps at `MAX_STOCK_ROWS = 12`
  (`world/rules/service_view.py`), so the ten tail-appended offers are not
  shown in the SPA panel; the CLI `shop stock` (`commands/economy.py`) lists
  all 40 offers, so every item stays player-reachable and the spec scenario
  "general store is inspected" holds on the CLI surface. Presentation
  pagination belongs to a later change (P6/P7).
