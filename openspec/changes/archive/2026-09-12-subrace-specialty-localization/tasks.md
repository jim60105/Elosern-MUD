# Tasks: subrace-specialty-localization

Mirror design doc §4 (scope) and §8 (testing). Prerequisite: Change 1
`human-subrace-lineage-rework` is applied AND archived, so the main spec already carries its
renamed human keys and its five zh-TW `specialty` strings. This change edits ONLY the ten
elf/beastfolk `specialty` string values — never the human five, never keys/names/modifiers/anchors.

## 1. Registry data

- [x] 1.1 Confirm the working tree is post-Change-1: `SUBRACE_REGISTRY` keys include
      `human_coastal`/`human_plains`/`human_highland` and the five human `specialty` values are
      the zh-TW lineage prose from Change 1's delta. Verify: reading `world/lore/races.py` shows
      zero ASCII letters in the five human `specialty` strings; if not, STOP — this change must
      not run before Change 1 lands.
- [x] 1.2 Replace the three elf `specialty` values in `world/lore/races.py` with the delta-spec
      strings verbatim — `fionnen` → 「翠綠森林村的森林精靈。親和光屬性魔法，弓術與光法並修，從容而精準。」;
      `ciaran` → 「暗影谷村的黑暗精靈。親和火與暗屬性魔法，刀術造詣尤深，攻勢凌厲。」;
      `eolas` → 「幽月谷村的幻童精靈。外表永駐童年，親和所有屬性魔法，並擅長神之秘法。」 — touching
      nothing else on those entries. Verify: importing `world.lore.races` succeeds and the values
      match `specs/lore-registries/spec.md` character-for-character.
- [x] 1.3 Replace the seven beastfolk `specialty` values in `world/lore/races.py` with the
      delta-spec strings verbatim — `wolfkin` 「群居狩獵的狼人，體格均衡而耐力出眾，慣於配合同伴作戰，無突出短板亦無驚人天賦。」,
      `catkin` 「身形輕盈、舉步無聲的貓人，敏捷遠出同族之上，代價是肌骨纖薄，難以吃下正面重創。」,
      `bearkin` 「骨架厚重、力大無窮的熊人，慣用重型武器，卻因轉身遲鈍而追不上靈活的對手。」,
      `rabbitkin` 「奔躍如風的兔人，為獸人之中最快的亞種，擅長遊走遠射，卻經不起近身的一擊。」,
      `bovinekin` 「身軀如山、皮糙肉厚的牛人，防禦最厚而善於陣地戰，只因其行動緩慢而難以追擊機動的敵人。」,
      `tigerkin` 「爆發力驚人、攻速兼備的虎人，出擊凌厲而防禦為全亞種最弱，講求一擊制敵而非持久消耗。」,
      `foxkin` 「體格在獸人之中不突出的狐人，以體力換來同族最深厚的魔力底蘊，是最接近施法者的亞種。」 —
      each tradeoff clause MUST match that entry's own `static_modifiers` (per `world_info.md`'s
      「亞種數值傾向」 block); keep `StatModifiers` and `foxkin`'s `vital_overrides` unchanged.
      Verify: the values match the delta spec character-for-character and no beastfolk
      `static_modifiers` line changed.

## 2. Tests

- [x] 2.1 Add one behavior test to `world/lore/tests/test_races.py` (an existing shard-registered
      module — `world.lore` is label 4 `quests-skills-art-ai-lore` in
      `.github/evennia-shards.json`, so NO manifest change is needed in this change) asserting
      the language contract for ALL fifteen entries: every `SUBRACE_REGISTRY[*].specialty`
      contains at least one CJK ideograph and ZERO ASCII letters (`re.search(r"[A-Za-z]", …)` is
      `None`), and its length is at most `MAX_SPECIALTY_CODE_POINTS` (256) — the precise rule of
      delta scenario 2/3, with no parenthetical exception mechanism (design D3); also assert
      `len(SUBRACE_REGISTRY) == 15` in the same test so a sixteenth entry can never enter the
      registry without confronting the language rule (the MODIFIED requirement already
      enumerates the exact 5 + 3 + 7 keys). Annotate it
      `@covers_requirement("lore-registries::subrace-specialty-prose-is-server-owned-traditional-chinese-for-every-entry")`
      — the slug was computed with the tool's own `normalize_requirement_name` algorithm
      (running `uv run --locked python -c "from tools.spec_traceability import
      normalize_requirement_name as n; print(n('Subrace specialty prose is server-owned
      Traditional Chinese for every entry'))"` yields
      `subrace-specialty-prose-is-server-owned-traditional-chinese-for-every-entry`); after
      archive, `uv run --locked python -m tools.spec_traceability list` must show the canonical
      ID `lore-registries::subrace-specialty-prose-is-server-owned-traditional-chinese-for-every-entry`;
      do not hand-construct the slug. Verify: targeted run of
      `world.lore.tests.test_races` passes and `tools.spec_traceability check` reports the new
      requirement covered.
- [x] 2.2 Extend `world/lore/tests/test_races.py` with verbatim-pinning tests for the two new
      scenarios this delta adds under the existing Subrace-registry requirement (elf trio;
      beastfolk seven), annotating each
      `@covers_requirement("lore-registries::subrace-registry-covers-elf-branches-beastfolk-subspecies-and-human-bloodline-subraces-with-stat-modifiers")`
      (existing canonical ID, unchanged by this change). Verify: targeted run of
      `world.lore.tests.test_races` passes.

## 3. Specs

- [x] 3.1 Apply this change's delta to `openspec/specs/lore-registries/spec.md` during archive —
      the ADDED specialty-language requirement plus the MODIFIED Subrace-registry requirement
      with its two new pinned-prose scenarios. Do NOT hand-edit the main spec ahead of archive,
      and do NOT reintroduce Change 1's text (the MODIFIED block must sit on top of Change 1's
      post-archive version; if the main spec no longer matches the delta's carry-over, reconcile
      the carry-over first). Verify: `openspec archive` output contains
      `Subrace specialty prose is server-owned Traditional Chinese for every entry`.

## 4. Verification

- [x] 4.1 Run the canonical Evennia runner —
      `MUD_TEST_SETTINGS=1 uv run --locked python -m evennia test --settings test_settings.py --noinput world.lore world.rules`
      — and confirm it passes (bare pytest fails with `ModuleNotFoundError: No module named
      'django'`; do not use it).
- [x] 4.2 Run `uv run --locked python -m tools.spec_traceability check` and
      `uv run --locked python -m tools.test_data_lint check`; both pass, every
      `@covers_requirement` slug still resolves (no heading was renamed), and the new requirement
      is covered.
- [x] 4.3 Sweep the registry to zero English prose: a regex over the fifteen `specialty` VALUES
      in `world/lore/races.py` finds no `[A-Za-z]` (item keys, `home_anchor_key`, and element
      names are separate fields and are legitimately ASCII — the sweep covers `specialty` only,
      per design D3). Verify: `grep -n 'specialty' -A1` style inspection of the ten edited lines
      shows no ASCII letter, and task 2.1's assertion is the durable form of this sweep.
- [x] 4.4 Confirm the player-visible symptom is gone without any renderer edit: `git diff`
      touches ONLY `world/lore/races.py` (ten string values) and `world/lore/tests/test_races.py`
      (plus spec files at archive). `commands/character_creation.py:191` and
      `web/static/webclient/js/elosern/creation_menu.js:247` are unchanged, so the CLI line
      `子種族（…）——…` and the WebClient menu description render the zh-TW field as-is. Verify:
      `git diff --name-only` lists exactly the expected files.
