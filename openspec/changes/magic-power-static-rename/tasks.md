# Tasks: magic-power-static-rename

## 1. Lore registries (world/lore/)

- [ ] 1.1 In `world/lore/races.py`: make `StaticBand` four-dimensional
      (`magic_power: tuple[int, int]`); set the race interim bands (human
      combat (1,22)/magic (5,90), beastfolk (4,34)/(1,30), elf (70,95)/
      (100,900)); delete `RaceProfile.magic_cap` and
      `RaceProfile.starting_magic_level`; replace the uniform `_static_band()`
      helper with explicit per-axis bands.
- [ ] 1.2 In `world/lore/races.py`: add `magic_band: tuple[int, int]` to
      `StaticTier`; author per-tier magic bands (human ladder spans 5–90 with
      `human_adventurer` ≈ 30 mid-band; beastfolk tiers low in (1,30); elf
      tiers within (100,900), `elf_prodigy` closed); extend the existing
      registry-load validation to reject a `magic_band` outside the owning
      race band.
- [ ] 1.3 In `world/lore/monsters.py`: every `MonsterTier.static_band` gains
      `magic_power=(0, 0)`.
- [ ] 1.4 In `world/lore/magic.py`: delete `RankTitle` and
      `RANK_TITLE_REGISTRY`; in `world/lore/sync.py` remove the
      `"rank_titles"` category key (ten registries mirrored).

## 2. Trait construction (world/rules/traits.py)

- [ ] 2.1 `STATIC_KEYS = ("atk_phys", "agility", "defense", "magic_power")`,
      `COUNTER_KEYS = ("guild_merit",)`; `race_floor()` reads
      `static_baseline.magic_power[0]`; `build_initial_traits()` tier path
      also sets `magic_power` from `static_tier.magic_band[0]`.
- [ ] 2.2 `trait_config_for_values(values)` loses the `magic_cap` parameter
      and the magic counter branch; update `_trait_config` and
      `initial_trait_config` and all callers (`typeclasses/`,
      `world/rules/character_creation.py`, monster/NPC population paths).

## 3. Rules consumers

- [ ] 3.1 Rename every `magic_level` read in `world/rules/combat.py`
      (`attack_key` school branch, heal magnitude, appraisal
      `effective_power`), `world/rules/sexual_state.py`
      (`can_cast_spell_tier` consumers unchanged in shape), healing/damage
      helpers, and the `_element_effective_magic_level` docstring wording.
- [ ] 3.2 `world/rules/status_query.py`, `world/rules/status_text.py`,
      `world/rules/displayed_stats.py` (`DISPLAYED_KEYS`, `TRAIT_LABELS`),
      `world/rules/equipment_effects.py` (vocabulary, `_BUNDLE_FLAT_FIELDS`,
      `("magic_power", "魔力")`): rename keys; `status_query` label
      魔法階級 → 魔力; `_STATIC_KEYS`/`_COUNTER_KEYS` mirrors follow.
- [ ] 3.3 `world/rules/progression.py`: delete `MAGIC_RANK_BANDS` and
      `magic_rank_title()`; rename `MAGIC_GROWTH_MULTIPLIER_PREFIX` to
      `growth_rate:practice:`; rename
      `effective_magic_growth_multiplier()` → `effective_growth_multiplier()`
      (sole caller `grant_skill_practice_xp` follows); keep
      `MAGIC_TIER_THRESHOLDS`, `can_cast_spell_tier`, `can_cast_skill`
      reading `entity.traits.magic_power`.
- [ ] 3.4 `world/rules/buffs.py`: `_NO_OP_RATE_TARGETS = {"skill_practice"}`;
      docstring naming the pull reader; update `buffs.yaml` conferred
      growth-rate `rate` target to `skill_practice`.

## 4. Skills

- [ ] 4.1 `world/skills/effects.py`: `GrowthRateEffect` accepts stat key
      `practice` only; `growth_rate:magic:*` raises at parse (fail-closed
      registry load).
- [ ] 4.2 `world/skills/registry.py`: `reincarnation_boon_elosia` effect
      string → `growth_rate:practice:100`. Leave the nine
      `element_mastery_rank:主宰` rows untouched (owned by
      `magic-xp-engine-retirement`).

## 5. Imports (world/imports/)

- [ ] 5.1 `schema.py`: `stats`/`disguised_stats` vocabulary renames
      `magic_level` → `magic_power` (eight keys, count unchanged).
- [ ] 5.2 `validate.py`: above `static_baseline.magic_power[1]` rejects with
      `Issue("stats.magic_power", ...)`; below `[0]` warns like the other
      static axes; disguised subset check keys follow.
- [ ] 5.3 `examples/example_character.json`: `"magic_power": 60`.

## 6. Creation (rules + AI + commands)

- [ ] 6.1 `world/rules/character_creation.py`: delete
      `starting_magic_interval()` and the sampler path; add `magic_power` to
      the allocable static axes (seventh axis; subrace modifiers untouched);
      budget formula unchanged in shape; `CharacterCreationResult.magic_level`
      field → `magic_power`; echo wording 初始魔力.
- [ ] 6.2 `world/ai/character_creation.py`: duplicated `ALLOCATABLE_AXES`
      gains `magic_power` (mirror test keeps pinning equality).
- [ ] 6.3 `commands/character_creation.py` + `web/webclient/actions/
      creation_actions.py`: completion echo → `初始魔力為 X`; creation panel
      payload field `magic_level` → `magic_power`
      (`web/webclient/presentation/creation.py` and wire allowlists).

## 7. Quests + AI surfaces

- [ ] 7.1 `world/quests/scene_builder.py`: NPC stats come from
      `build_initial_traits(race_key, tier=...)` only (no
      `starting_magic_level` read).
- [ ] 7.2 Persona no-leak secret set (`world/ai/`): true-value keys rename to
      `magic_power`.

## 8. WebClient Python mirrors

- [ ] 8.1 `web/webclient/presentation/character.py`: trait labels/keys;
      head-card presenter no longer sends any magic-rank word.
- [ ] 8.2 `web/webclient/actions/tests/test_service_actions.py` trait-key
      allowlist, `presentation/tests/test_creation_panel.py` field list,
      `test_creation_actions.py` payload/trait assertions, combat fixtures
      `traits.magic_level.base = 30` → `traits.magic_power.base = 30`
      (`web/webclient/actions/tests/test_combat_actions.py`,
      `test_combat_dispatcher.py`, `commands/tests/test_combat_actions.py`).

## 9. WebClient app (npm) + vitest

- [ ] 9.1 `character-identity.js`: delete `magicRankTitle` and its band
      table; `CharacterHead.vue`: badge reads `magic_power` row, rank line
      becomes guild-only (`公會 <rank> · 功績 <merit>`, 未加入公會 marker),
      header comments follow.
- [ ] 9.2 `CharacterStatusDrawer.vue`: `ATTRIBUTE_KEYS` renames the fourth
      key; delete `TRAIT_LABEL_OVERRIDES` (server label is now 魔力).
- [ ] 9.3 `CreationOverlay.vue`: allocation reactive object, zeroing, draft
      hydration, briefing, and submit payload gain `magic_power` (seventh
      axis); profile axes come from the server descriptor.
- [ ] 9.4 `stories/fixtures.js`, `stories/Data/CharacterHead.stories.js`,
      vitest suites `character_identity.test.js` (band-table suite deleted),
      `character_head.test.js`, `character_status_drawer.test.js`,
      `status_panel.test.js`, creation-overlay suites: re-key/reword.

## 10. Docs

- [ ] 10.1 `docs/game/command-reference.md`: look-block stat wording row
      魔法階級 → 魔力; creation completion echo wording. Keep
      `tests/test_command_docs.py` green (no command keys/aliases change).

## 11. Python test re-pinning

- [ ] 11.1 `world/rules/tests/`: `test_traits.py` (four-axis bands, static
      type, no-cap config), `test_status_query.py` (mirror-pin allowlist +
      label), `test_progression.py` (rank-title tests deleted; gate tests
      re-keyed), creation/wizard/messages suites (seven-axis budgets,
      sampler seams deleted, echo wording), `test_effects.py` +
      `test_skill_registry.py` (practice prefix), buffs suites.
- [ ] 11.2 `typeclasses/`, `commands/tests/test_background.py` (floor +
      allocation value assertion), `web.webclient` creation suites field
      lists.

## 12. Verification

- [ ] 12.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules world.imports world.skills typeclasses commands web.webclient`
- [ ] 12.2 `npm test` (vitest suites above).
- [ ] 12.3 `uv run --locked python -m tools.spec_traceability check`
- [ ] 12.4 `uv run --locked python -m compileall -q world typeclasses commands server`
- [ ] 12.5 `openspec validate magic-power-static-rename --strict`
- [ ] 12.6 `git diff --check`

## Post-sync traceability (during archive/sync)

- [ ] P.1 After this change's deltas are synced into `openspec/specs/`, run
      `uv run --locked python -m tools.spec_traceability list` and add
      `covers_requirement` annotations mapping the renamed requirement IDs to
      their re-pinned tests in a follow-up sync commit (no annotations for
      not-yet-synced IDs during implementation).
