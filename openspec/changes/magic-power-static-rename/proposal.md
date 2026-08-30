# Proposal: magic-power-static-rename

## Why

`magic_level` is a misnomer wearing two hats. It is nominally a magic-rank
progression counter, but `combat.py`, healing, appraisal power scoring, equipment
bundles, `disguised_stats`, and the WebClient 魔力 column all read it as the
magic-school attack stat — a fourth static combat stat that was never declared as
one. The approved growth redesign
(`docs/superpowers/specs/2026-08-30-use-driven-progression-design.md`, decisions
D1/D2) demotes it: the name `magic_level` (which describes a dead XP system)
becomes `magic_power`, and the trait type becomes `StaticTrait`, structurally
symmetric with `atk_phys`, `agility`, and `defense`. This change is the pure,
behavior-preserving half of that cutover: rename, retype, and re-band the data.
It deletes no growth writers yet (the companion change
`magic-xp-engine-retirement` does that next); it only removes the display rank
title band, whose replacement is owned by the title-system change line.

Doing the rename first, while the XP engine still functions, keeps every step
mechanically verifiable: each stage of the cutover is a key change with identical
observable behavior.

## What Changes

- BREAKING: `world/rules/traits.py` — `magic_level` moves from `COUNTER_KEYS`
  into `STATIC_KEYS` as `magic_power`; the counter `min/max` branch of
  `trait_config_for_values` loses its magic-cap argument path.
- BREAKING: `StaticBand` gains a fourth dimension `magic_power: tuple[int, int]`;
  `RaceProfile.magic_cap` and `RaceProfile.starting_magic_level` are DELETED;
  race bands become the lore source (human 5–90, beastfolk 1–30, elf 100–900 —
  interim values per design doc §6). Every `STATIC_TIER_REGISTRY` tier gains a
  `magic_power` sub-band that is a subset of its race band (load-validated).
- BREAKING: the player-character magic sampler is deleted
  (`world/rules/character_creation.py` `starting_magic_interval` and its
  validation): `magic_power` flows through the existing allocable static-axis
  path; presets keep fixing all four static values.
- BREAKING: the magic-rank display band is retired: `magic_rank_title()`,
  `MAGIC_RANK_BANDS`, `RANK_TITLE_REGISTRY`, `RankTitle`, and the `rank_titles`
  DB mirror key are deleted. Numeric tier bands (`MAGIC_TIER_REGISTRY`,
  `spell_tier_for`) stay exactly as-is as cost-tier data labels.
- Mechanical rename of every consumer key with identical behavior:
  `combat.py` (`attack_key` school branch, heal magnitude, appraisal sum),
  `displayed_stats.DISPLAYED_KEYS`, `equipment_effects.py` vocabulary and bundle
  fields, `imports/schema.py` `stats`/`disguised_stats` keys,
  `imports/validate.py` (magic-cap rejection becomes race-band membership:
  above the race band upper bound rejects, below the lower bound warns like the
  other static axes), `quests/scene_builder.py` (four tier bands, no
  `starting_magic_level`), `example_character.json`, and the persona no-leak
  secret set.
- Passive growth-rate prefix re-key: `growth_rate:magic:<N>` becomes
  `growth_rate:practice:<N>` (registry-load fails on the old prefix); the
  conferred-growth buff target `magic_level_growth` becomes `skill_practice`.
  The multiplier itself keeps working unchanged — only keys move.
- WebClient mirrors: `character-identity.js` drops the duplicated
  `magicRankTitle` table and the head card rank line becomes guild-rank-only;
  `CharacterHead.vue` badge reads the `magic_power` trait row;
  `CharacterStatusDrawer.vue` allowlist renames the fourth key and its label
  override is deleted (design D-A6 — the shared server label is now 魔力, so
  no client-side 魔階 abbreviation remains); Storybook fixtures and vitest
  suites follow.
- Chinese display labels are consistent for players everywhere they already
  appear: the look row label 魔法階級 becomes 魔力 (design D-A6 — 「階級」
  advertises the retired rank system to players on every `look`), equipment
  prose keeps 魔力, and the drawer renders 魔力 with no abbreviation. The
  creation completion echo rewords 初始魔法等級 to 初始魔力 because "level"
  describes a system being retired.
- No backward-compatibility or migration work: the project is unreleased with
  zero users. No shim keys, no data migration; existing SQLite rows are simply
  rebuilt (test DB uses `--keepdb` against renamed trait keys as usual for this
  repo's workflow).

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `entity-trait-scales`: eight-key trait set retypes `magic_power` as
  `StaticTrait`; race/monster initial values come from the four-dimensional
  `StaticBand`; no `magic_cap` anywhere.
- `lore-registries`: `RaceProfile` loses `magic_cap`/`starting_magic_level` and
  gains the four-dimensional baseline; `StaticTier` bands gain the fourth axis;
  the `RankTitle` registry requirement is removed.
- `lore-startup-sync`: `sync_all()` mirrors ten registries, not eleven.
- `player-stat-allocation`: `magic_power` becomes a seventh allocable axis from
  the race's fourth static band; the starting-magic sampler requirement is
  removed.
- `player-character-creation`: activation no longer writes a sampled starting
  magic level; identity wording follows the rename.
 - `character-creation-ux`: the allocation briefing states seven axes, not six.
 - `webclient-character-creation-ui`: profile descriptors and the allocation
   briefing carry the seventh axis; the rejection scenario's
   "magic-level"/"starting-magic" field wording follows the rename.
 - `element-affinity`: the gate-only effective-level sentence names the renamed
   `magic_power` trait; the multiplier values and rules are unchanged.
- `import-schema`: the eight documented `stats` keys rename one member.
- `import-validation`: magic-above-cap rejection becomes magic-power-above-race-
  band rejection; band-lower-bound warns.
- `import-reference-example`: the example card carries `magic_power` inside its
  race band.
- `displayed-stats-view` / `disguised-stats-boundary` / `character-breakdown-view`:
  displayed-five and disguise keys rename; labels unchanged.
- `combat-resolution` / `combat-modifier-table` / `damage-effect-handlers` /
  `equipment-effects`: the magic school reads `magic_power` under its new key.
- `element-mastery`: the display-only `magic_rank_title` requirement is removed;
  the numeric cast gates keep working against the renamed static trait.
- `skill-effect-model` / `skill-registry`: `growth_rate` effect stat key and the
  reincarnation-boon effect bytes re-key to `practice`.
- `buff-handler-integration`: the conferred growth-rate target renames to
  `skill_practice`.
- `persona-dialogue-injection`: disguise true-value secret set key renames.
- `scene-builder`: NPC traits derive from the four tier bands with no starting
  magic level.
- `equipment-effects`: the adjustment vocabulary member renames; the flat-bundle
  field set follows.
- `webclient-contextual-hud` / `webclient-component-showcase`: head card badge
  reads `magic_power`; the client-derived magic rank title and its showcase
  counter wording are retired.

## Impact

- Affected code: `world/rules/` (`traits.py`, `combat.py`, `displayed_stats.py`,
  `equipment_effects.py`, `character_creation.py`, `creation_wizard.py`,
  `status_query.py` mirrors), `world/lore/` (`races.py`, `magic.py`, `monsters.py`
  band typing, `sync.py`), `world/skills/` (`effects.py`, `registry.py` boon
  effect string), `world/rules/buffs.py` + `buffs.yaml` target, `world/imports/`
  (`schema.py`, `validate.py`, `examples/example_character.json`),
  `world/quests/scene_builder.py`, `world/ai/character_creation.py` (duplicated
  `ALLOCATABLE_AXES` — must-not-import-rules boundary, updated in lockstep),
  `commands/character_creation.py` echo, `web/webclient/` Python
  creation/presentation surfaces, `web/webclient-app/` (`character-identity.js`,
  `CharacterHead.vue`, `CharacterStatusDrawer.vue`, fixtures, vitest).
- Affected tests: `world/rules/tests/test_traits.py`, `test_status_query.py`
  (mirror-pin allowlist against the Vue component, updated in lockstep),
  `test_progression.py`, `test_character_creation.py`,
  `test_creation_wizard.py`/`test_creation_messages.py`, `world/import` tests,
  `world/skills/tests/test_effects.py`/`test_skill_registry.py`,
  `typeclasses`, `commands`, `web.webclient` creation/combat fixtures
  (`traits.magic_level.base = 30` casts re-key to `magic_power`).
- Affected docs: `docs/game/command-reference.md` (look-block stat wording row).
- `.github/evennia-shards.json`: no new test modules, no manifest change.
- Depends on: nothing. Followed by: `magic-xp-engine-retirement` (deletes the
  now-retired-system writers), then the lineage/title lines.
- No backward-compatibility or migration work: the project is unreleased with
  zero users.
