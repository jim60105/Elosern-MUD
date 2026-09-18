## 1. Registry block swap

- [x] 1.1 Replace the dev-era divine-mystery block in `world/skills/registry.py` with the twelve
      authored nodes from `docs/lore/skill-trees/divine-mystery.md` §2, each with `cost={}`,
      `requires_divine_arts=True`, `usable_out_of_combat=True`,
      `category=SkillCategory.DIVINE_MYSTERY`, its declared target spec, its prerequisites, and its
      per-occurrence `EffectPolicy` carrying the scale and (for party nodes) `EffectAudience.ALLIES`.
- [x] 1.2 Keep `status_disguise` and `dominion_art` as their existing keys with no prerequisites.
- [x] 1.3 Delete the four placeholder skills with no aliases.
- [x] 1.4 Confirm the registry imports: the lineage graph validator accepts the three chains and the
      three-parent capstone, and each chain end derives a cap of 10.

## 2. Retire the data-echo suite

- [x] 2.1 Remove `DivineMysteryRegistryTests` and the placeholder key lists from
      `world/skills/tests/test_skill_registry.py`.
- [x] 2.2 Read `world/rules/tests/test_divine_mystery_gate.py`: its fixtures derive from the category,
      so they now resolve to the new nodes. Update each assertion so it establishes a mechanic (the
      bloodline gate, the preview parity) rather than a placeholder's inertness.
- [x] 2.3 Remove any entry in `tools/test_data_freeze.json` left stale by the retirement, and run
      `uv run --locked python -m tools.test_data_lint check`.

## 3. Behavior contract tests

- [x] 3.1 New module `world/rules/tests/test_divine_mystery_progression.py`, composed from synthetic
      skill definitions only — no shipped-content skill names, no data-contract tagging: a later
      conferral rung yields a strictly larger effective value than an earlier one; an ally-audience
      conferral reaches every ally in the resolved audience; a three-parent node stays unusable until
      its last parent meets its threshold; a chain root is usable with no prerequisite.
- [x] 3.2 Family-invariant tests over the category: every member declares an empty cost,
      `requires_divine_arts=True`, and no damage or healing effect. Assert the property over the
      category, never a per-row list of keys and labels.
- [x] 3.3 Annotate with `covers_requirement` using IDs from
      `uv run --locked python -m tools.spec_traceability list`.
- [x] 3.4 Register the new module in exactly one shard of `.github/evennia-shards.json`.

## 4. Docs

- [x] 4.1 Update `docs/lore/skill-trees/divine-mystery.md` §7 to record that the engine work has
      landed, keeping §4's uncatalogued mysteries as the stated expansion area.

## 5. Verification

- [x] 5.1 Run the focused label
      `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_mystery_progression`
      with `MUD_TEST_SETTINGS=1` passed through the tool's `env` input.
- [x] 5.2 Run the focused labels `world.skills.tests.test_skill_registry`,
      `world.rules.tests.test_divine_mystery_gate` and `world.rules.tests.test_skill_lineage`.
- [x] 5.3 Run `uv run --locked python -m tools.spec_traceability check`,
      `uv run --locked python -m tools.test_data_lint check`, and
      `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [x] 5.4 `openspec validate divine-mystery-catalog --strict`.
