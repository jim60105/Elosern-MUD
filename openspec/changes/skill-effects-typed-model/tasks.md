## 1. Typed effect module

- [ ] 1.1 Create `world/skills/effects.py` with one frozen dataclass per prefix listed in the
      `skill-effect-model` spec's requirement, plus thin dataclasses wrapping the six already-working
      cast-time prefixes (`confer_skill_partial`, `set_disguise` → named `DisguiseEffect` explicitly,
      `buff_apply`, `self_buff_apply`, `confer_growth_rate`, `sexual_event`) and `damage`/`disengage` —
      `DisguiseEffect` is referenced by name from `conferral-generalization`'s spec, so its class name
      must be pinned here, not left implicit
- [ ] 1.2 Implement `parse_effect(effect_id: str)` as a single dispatch function over the prefix
      (`effect_id.partition(":")[0]`), raising `ValueError` for anything unrecognized
- [ ] 1.3 Write unit tests for every recognized prefix (happy path) and at least one unknown-prefix
      negative test

## 2. Wire SkillDef to the typed model

- [ ] 2.1 Add `parsed_effects: tuple` field to `SkillDef`, populated in `__post_init__` via
      `tuple(parse_effect(e) for e in effects)`
- [ ] 2.2 Confirm `SKILL_REGISTRY`'s module-level construction still imports cleanly (every existing
      effect string must parse under the new dispatch — if any doesn't, fix the string, not the parser)
- [ ] 2.3 Remove the stale "stat_multiply is the only effect-ID convention interpreted by this package"
      claim from `world/skills/registry.py`'s module docstring; point to `effects.py` instead

## 3. Migrate the one existing consumer

- [ ] 3.1 Update `world/skills/handler.py`'s `effective_value`/`_matching_multiplier` to read
      `StatMultiplyEffect` instances from `parsed_effects` instead of re-parsing the raw string with
      `_parse_stat_multiply`
- [ ] 3.2 Confirm the full existing `skill-handler` spec scenario suite still passes unchanged (no
      behavior change intended, only representation)

## 4. body_enhancement reclassification

- [ ] 4.1 Change `kind=SkillKind.ACTIVE` to `kind=SkillKind.PASSIVE` for `body_enhancement`,
      `body_enhancement_extreme`, `body_enhancement_basic` in `world/skills/registry.py`
- [ ] 4.2 Grep the test suite, `game-command-docs`, and webclient skill-menu/OOB surfaces for these
      three keys to confirm nothing assumes they are castable; fix any that do

## 4a. Fix reincarnation_boon_yuna's malformed effect string (moved here from divine-mystery-skills)

- [ ] 4a.1 Change `reincarnation_boon_yuna`'s `effects` from the malformed three-segment
      `["element_mastery_rank:性魔法:主宰"]` to `["sexual_magic_mastery"]` — this is a **hard
      prerequisite for this change's own registry-load validation** (task 2.2/1.3): the malformed
      string does not parse as any recognized prefix under the new dispatch table, and every one of
      the other 17 changes in this batch imports `world.skills.registry` and would inherit an import
      failure if this fix is deferred to a later, non-prerequisite change. `divine-mystery-skills`
      still owns adding `SexualMasteryEffect`'s *behavior* (the two new castable skills, the race
      gate) — only the string correction and its typed-dataclass classification move here

## 5. Cost tier constants

- [ ] 5.1 Add `world/skills/cost_tiers.py` with the five-tier MP range table from design doc §4.3, as a
      `dict`/`NamedTuple` keyed by tier name, for later spell-catalog proposals to import

## 6. Verify

- [ ] 6.1 Run the full existing test suite; only `skill-handler`-adjacent and `skill-registry`-adjacent
      tests should show any diff, and only where explicitly expected by this change
