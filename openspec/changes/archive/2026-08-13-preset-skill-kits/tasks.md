## 1. Registry shape and load-time validation

- [x] 1.1 Add `active_skills: tuple[str, ...] = ()` and `passive_skills: tuple[str, ...] = ()` to
      the frozen `PlayerPreset` dataclass in `world/lore/player_presets.py`, plus a
      `skill_lists()` helper returning `{"active": list(active_skills), "passive":
      list(passive_skills)}`; add pure tests for the helper's exact shape and order.
- [x] 1.2 Add a module-load validation pass in `world/lore/player_presets.py` that raises
      `ValueError` for any preset whose kit references a key absent from `SKILL_REGISTRY`, whose
      active/passive key mismatches its registry `SkillKind`, or whose `requires_divine_arts`
      skill is declared by a preset whose race lacks `can_use_divine_arts`; add pure tests
      covering each rejection class.

## 2. Catalog content: eight template characters

- [x] 2.1 Populate `PLAYER_PRESET_REGISTRY` with exactly 8 female adult presets, preserving the
      existing three keys first (`human_wanderer` 艾琳, `foxkin_scout` 露芙, `elf_guardian`
      瑟芮雅) and appending five story-cast presets (`violet_altoria` 薇歐蕾特, `lidzia_rosenthal`
      莉茲婭, `yuka_darknight` 悠花, `yuna_darknight` 悠奈, `elosia_shadowmoon` 伊洛希雅), each
      with budget-exact allocations, adult `age`/`apparent_age`, a distinct role and skill kit,
      and a Traditional Chinese `emphasis` + `background` (1..256 code points) consistent with the
      world lore (人類 as the umbrella; 人族/獸人族/精靈族 as the specific races).
- [x] 2.2 Extend `world/lore/tests/test_player_presets.py`: every preset's active/passive keys
      resolve in `SKILL_REGISTRY` with matching kind; divine-arts skills only on
      `can_use_divine_arts` races; catalog ships exactly 8 presets; existing race-coverage and
      budget/bounds assertions stay green.

## 3. Activation grants preset kits

- [x] 3.1 In `world/rules/character_creation.py::activate_player_character`, write the preset's
      `skill_lists()` into the `skills` attribute value for preset mode and keep the empty
      `{"active": [], "passive": []}` shape for custom mode; keep the write inside the existing
      atomic transaction (no snapshot-list change needed: `skills` is already in
      `_CREATION_ATTRIBUTE_KEYS`).
- [x] 3.2 Extend `world/rules/tests/test_character_creation.py` (and the command/action adapter
      tests if they assert the empty shape): preset activation persists the declared kit and
      clears the draft atomically; custom activation leaves innate-only skills; annotate the new
      test with `covers_requirement("player-character-creation::...")` for the added requirement
      once `tools.spec_traceability list` confirms the ID.

## 4. Surface updates

- [x] 4.1 Update the exact preset-key lists in
      `web/webclient/presentation/tests/test_creation_panel.py` (lines ~95–106) to the 8-key
      ordering; confirm `human_wanderer` stays first so the browser creation tests that press
      Enter on the first card are unaffected.
- [x] 4.2 Verify no other surface asserts the catalog size or exact keys (command docs, Node
      fixture tests, browser seed) and that `tests/test_command_docs.py` stays green without
      doc changes; run the affected test domains per AGENTS.md.
