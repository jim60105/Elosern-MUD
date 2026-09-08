## 1. Lore declaration

- [x] 1.1 Add frozen `StartingCompanion` (`preset_key`, `affinity`, `relationship`) to `world/lore/player_presets.py`
- [x] 1.2 Add keyword-only `starting_companions: tuple[StartingCompanion, ...] = ()` to `PlayerPreset`
- [x] 1.3 Declare the symmetric pair: `yuna_darknight` → `yuka_darknight` at 95, `yuka_darknight` → `yuna_darknight` at 95, with relationship labels following 悠奈's background (悠奈 is the elder, 悠花 the younger)
- [x] 1.4 Write `_validate_preset_starting_companions(registry)` rejecting an unregistered `preset_key`, a self-reference, and a duplicate partner within one preset; register it at module bottom
- [x] 1.5 Confirm `world/lore/player_presets.py` still imports nothing from `world.rules`

## 2. Rules-side bounds sweep

- [x] 2.1 In `world/rules/starting_companions.py`, add an import-time sweep over `PLAYER_PRESET_REGISTRY` asserting `len(starting_companions) <= PARTY_MAX_COMPANIONS` and `1 <= affinity <= NATURAL_CAP`, raising with the offending preset key
- [x] 2.2 Import `PARTY_MAX_COMPANIONS` from `world.rules.party` and `NATURAL_CAP` from `world.rules.affinity` so no constant is duplicated

## 3. Builder

- [x] 3.1 Create `world/rules/starting_companions.py` with a module docstring stating its boundary: it builds NPCs and writes no player, party, or affinity state
- [x] 3.2 Implement the builder: resolve the partner preset, `create_object(LLMNPC, key=<display_name>)`, and write `race`, `subrace`, `sex`, the trait config from `resolve_preset_values`, `age`, `apparent_age`
- [x] 3.3 Apply the lineage closure and proficiency seed to the skill lists, matching the player activation rule
- [x] 3.4 Write `inventory` from `inventory_list()`, then apply `starting_equipment` through `toggle_equipment`, raising on a rejected toggle
- [x] 3.5 Resolve `affinity_elements`: an elf seeds from its subrace through `validate_affinity_seed`, every other race uses the preset's declared set
- [x] 3.6 Build the persona from the partner preset's `to_record()` plus a `social_connection` entry keyed by the owning player's name holding the declaration's `relationship`
- [x] 3.7 Set `location` to the owning player's location, and raise a deterministic error when the player has no location
- [x] 3.8 Apply the `-{pk}` key suffix when another persisted entity already holds the name, following `world/rules/guild_exams.py::_key_taken_by_other`
- [x] 3.9 Set `portrait_policy` to `{"mode": "named", "stable_key": str(npc.pk)}` and schedule the portrait ensure, matching `finalize_player_portrait`'s idiom
- [x] 3.10 Call `ensure_npc_canonical_age` following every existing NPC spawn site
- [x] 3.11 On any failure, delete the partially built NPC and re-raise, following `world/rules/guild_exams.py::_spawn_opponent`
- [x] 3.12 Emit `log_info("starting_companion_built", context={...})` with the owner, preset key, and companion key

## 4. Test registration

- [x] 4.1 Create `world/rules/tests/test_starting_companions.py`
- [x] 4.2 Register the new module in exactly one shard of `.github/evennia-shards.json` **in this same change**, or `tests.test_evennia_test_optimization_contract` fails on every later branch
- [x] 4.3 Verify with `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`

## 5. Tests

- [x] 5.1 The twin cards declare each other symmetrically at 95; every other preset declares none
- [x] 5.2 The lore validator rejects an unregistered key, a self-reference, and a duplicate partner
- [x] 5.3 The rules sweep rejects an over-bound companion count and an out-of-range affinity
- [x] 5.4 A built companion's race, subrace, sex, trait values, skills, inventory, and ages equal what activating that preset as a player produces
- [x] 5.5 The built companion is an `LLMNPC` instance
- [x] 5.6 An elf companion's `affinity_elements` equal its subrace seed
- [x] 5.7 Declared equipment is worn with buffs and synced ceilings
- [x] 5.8 The persona carries a `social_connection` entry naming the owning player
- [x] 5.9 A name collision yields a `-{pk}` key while `portrait_policy.stable_key` stays the pk
- [x] 5.10 The builder leaves no affinity record, no `player.db.party` entry, and no `party_member` backref
- [x] 5.11 A failure mid-build leaves no persisted NPC
- [x] 5.12 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 6. Verification

- [x] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_starting_companions world.lore.tests.test_player_presets world.rules.tests.test_character_creation`
- [x] 6.2 `uv run --locked python -m tools.spec_traceability check`
- [x] 6.3 `uv run --locked python -m tools.observability_lint check`
- [x] 6.4 `openspec validate preset-companion-model --strict`
