# Migration plan — migrate-rules-sexual-status-tests-off-real-data

## Established idioms (from P03/P06 party+monster migrations)
- `open_synthetic_scope(self, *logicals, extra=...)` at top of setUp (kit class
  decorator skips setUp).
- Runtime vocabulary probes from `_combat_session_helpers`: `_race_key()`,
  `_monster_tier_key()`, `_behaviour_archetype_key()`, `live_skill_registry()`,
  `live_item_registry()`, `unique_live_key(dotted, attr, predicate)`.
- NEVER scope `monster_tiers` when monster rounds run (rulebook YAML keyed by
  shipped tier keys → KeyError on t_* rows).
- Symbol refs (SKILL_REGISTRY, SEXUAL_ACT_REGISTRY, ITEM_REGISTRY names) are
  lint findings → replace `patch.dict(REGISTRY, ...)` with scope `extra=`
  overlays or `_live_registry`-style attribute-string access; importing the
  symbol itself is a finding too (ast.Name match).
- Token = EXACT string equality against harvested universe (catalog keys,
  display-field values, rulebook top-level/wrapper keys). "human", "low",
  CJK body parts, level names 中等/極限 (NOT harvested), 自慰/陰道性交 etc. are
  NOT tokens. Confirmed tokens here: combat_tease, partner_caress,
  solo_self_touch, status_disguise, basic_attack, fire_ball, wind_blade,
  ice_shard, water_bolt, flash_step, shadow_slash, firestorm, hellfire,
  plain_sword, defense_instinct, guardian_instinct, retainer_martial_training,
  precise_mana_control, extreme_endurance, dual_wield_style, body_enhancement,
  elf_longevity, divine_time_dilation, divine_sexual_arts,
  divine_sexual_mastery, reincarnation_boon_yuna, knight_platemail,
  enticing_lace_set, saintess_vestments, sister_vestments,
  passion_silk_choker, shame_hem_lift, 乳交, sexual_forced_penalty,
  participant_multipliers, climax_extension_threshold.

## Per-file approach
1. **test_cast_settlement_sexual_coercion** (B): act carrier → kit act
   `t_hush_brush` (resistible variant via make_act/make_act_skill overlay in
   scope extras for "skills"+"sexual_acts"); scope in setUp; `_resist_log`
   skill field → kit act key; registry imports → helpers.
2. **test_combat_session_sexual_coercion** (B): same idiom as test_combat_party:
   scope skills/elements/races/subraces/static_tiers + synth_innate_overlay;
   basic_attack/fire_ball/wind_blade → SYNTH_SKILLS martial/elemental rows;
   EventLog skill field → kit key; `sexual_forced_penalty` at line 170 — read
   context, derive from load_config() object attribute via getattr-assembled
   name or restate assertion against `self.penalty` already loaded.
   monster tiers: probe only, never scope.
3. **test_equipment_sexual_effects** (A): file-local synthetic equipment items
   (make_item with sexual-effect mechanics) + runtime probe of equipment
   effect ids (unique_live_key over rulebook effects) where the test asserts
   the shipped effect machinery; kit-item overlays via scope "items".
4. **test_ordered_level_trait** (A, 0 findings): already clean — confirm,
   ledger-entry removal only.
5. **test_sexual_act_effects** (A): participant_multipliers /
   climax_extension_threshold → derive from loaded rulebook config object with
   attribute-name assembly probes; registry symbol refs → scope/live helpers.
6. **test_sexual_decay_and_reset** (A, 0 findings): ledger-entry removal only.
7. **test_sexual_event_self_arming** (B): status_disguise carrier →
   make_act_skill("t_self_arm", effects=["sexual_event:stimulus_applied"]) +
   matching make_act; cast inside scope; drop manual registry mutation.
8. **test_sexual_resist** (B): retainer_martial_training passive (+5 atk_phys)
   → file-local synthetic passive skill with the same flat-bonus effect shape
   (read the shipped row to copy the effect-string SHAPE, not the key) granted
   in passive list.
9. **test_sexual_resist_cast_wiring** (B): combat_tease→kit resistible act;
   solo_self_touch → kit act with resistible=False; partner_caress → kit act
   variant; _act_family local rows stay but register via scope extras, not
   patch.dict.
10. **test_sexual_state** (A, 0 findings): ledger-entry removal only.
11. **test_sexual_transitions** (A): 乳交 → expect the experience label
    derived at runtime from the loaded sexual.yaml rules (find the rule whose
    when.event == the event, read its add) — asserts the rule-bridge applies
    the table's add, no shipped literal.
12. **test_sexual_unlock** (A): registry symbol refs → scope "skills"+
    "sexual_acts" with extras for synthetic acts; divine_sexual_mastery →
    make_skill with a SexualMasteryEffect effect (read its definition in
    world/skills/effects/registry); "flee" stays (not token) but
    SKILL_REGISTRY mutation must go through live registry probe.
13. **test_status_query** (A): biggest. Scope skills/elements/sexual_acts(+);
    all skill-key literals → kit rows/locally built t_ rows; element prose
    冰/水/火 → kit element label(s) from live probe; passive-skill effect
    assertions → locally built rows carrying the same effect shapes.
14. **test_status_text** (B): knight_platemail → kit item (t_thorn_knife or a
    file-local make_item with known hp/defense modifiers); PLATE label via
    live item registry probe; asserted layer quantities derived from the kit
    row's values.

## Freeze/closure
- tools/test_data_freeze.json: delete exactly 14 debt entries; seedDebtPaths untouched.
- tests/test_data_independence_rules_sexual.py: copy party closure contract shape
  (MIGRATED_FILES 14 entries; no-exemption, zero-findings, no-violation-naming-manifest,
  seed-array-untouched). NO @covers_requirement until archive.

## Verify
- Per file: MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
  test_settings.py --keepdb world.rules.tests.test_<module>
- Gate: uv run --locked python -m tools.test_data_lint check (must stay green
  with 14 fewer debt entries).
