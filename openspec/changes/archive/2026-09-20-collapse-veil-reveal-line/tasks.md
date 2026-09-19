Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard. All new coverage goes into the two
already-registered veil modules, so `.github/evennia-shards.json` needs no entry.

## 1. Retire the strength vocabulary

- [x] 1.1 In `world/skills/effects.py`, delete the `RevealStrength` enum and strip the `strength`
  field from `RevealDisguiseEffect`, leaving a payload-free frozen marker modelled on
  `RevokeGrantsEffect`. Verify `grep -rn "RevealStrength" world/ commands/ typeclasses/` returns
  nothing.
- [x] 1.2 Simplify the `reveal_disguise` branch of `parse_effect` so the bare prefix returns the
  marker and EVERY payload — including the retired `reveal_disguise:true_name` — raises `ValueError`
  with a message naming the bare form as the only accepted spelling. Verify with behavior tests that
  `parse_effect("reveal_disguise")` returns the marker and that `reveal_disguise:true_name` and
  `reveal_disguise:everything` both raise:
  `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests.test_effects`.

## 2. Simplify the reveal primitives

- [x] 2.1 In `world/rules/skill_effects.py`, drop the `strength` parameter from `reveal_can_pierce`
  so it reports only whether the entity carries a veil, and update its docstring to state that the
  reveal path no longer reads the veil's companion record.
- [x] 2.2 Drop the `strength` parameter from `reveal_disguise_effect`, keeping its
  cleared/reported-no-op return contract. Verify with a behavior test over a synthetic veiled entity
  that a veil of either origin is cleared and an unveiled target returns the no-op.
- [x] 2.3 In `world/rules/action/effects/conferral.py`, stop threading a strength through
  `_handle_reveal_disguise` and its pending-effect lambda. Verify the reveal handler's staged outcome
  report is unchanged for both the cleared and the nothing-to-reveal cases:
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_veil_reveal`.
- [x] 2.4 Verify the reveal path no longer reads the veil's companion record at all: neither
  `reveal_can_pierce`, `reveal_disguise_effect`, nor `_handle_reveal_disguise` references
  `disguise_provenance` in any form. This precondition is what makes task group 3's rename a
  single-reader rename.

## 3. Rename the record to its one meaning

Run this group only after group 2, so the record has a single reader when it is renamed.

- [x] 3.1 In `world/rules/skill_effects.py`, delete the `DISGUISE_PROVENANCE_DIVINE` and
  `DISGUISE_PROVENANCE_MUNDANE` constants, replace `disguise_provenance_of(entity) -> str` with
  `was_cast_placed(entity) -> bool` reading `entity.db.disguise_placed_by_cast` under an
  absent-is-False rule per design D5, and replace `record_disguise_provenance(entity, provenance)`
  with a no-argument `record_cast_placement(entity)` per design D6. Verify with a behavior test that
  a fresh cast reads True while both an authored veil and an entity with no record read False.
- [x] 3.2 Update `apply_divine_disguise` to call `record_cast_placement(entity)` and
  `clear_disguise_effect` to delete `disguise_placed_by_cast` alongside `disguised_stats`. Verify
  with a behavior test that clearing leaves no stale placement record.
- [x] 3.3 Update the sole reader in `world/rules/action/effects/conferral.py` to
  `was_cast_placed(target)`. Verify the self-cast toggle's behavior is unchanged — a veil the verb
  placed is lifted, an authored veil is refreshed:
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_veil_cast`.
- [x] 3.4 Rename the record's key in the three carrier sites that move it without deciding from it:
  the `("disguise_provenance", None)` shell-default entries in `world/rules/cast_settlement.py` and
  `world/rules/clock.py`, and the snapshot/restore pair in `world/rules/action/transaction.py`.
  Verify the rollback test asserting that the display mapping and its companion record restore
  byte-equal together still passes.
- [x] 3.5 Re-point — do NOT delete — the boundary regression assertion in
  `world/rules/tests/test_disguise_boundary.py`. It asserts that `combat.py`, `dice.py` and
  `targeting.py` contain no `disguise_provenance`, and its module comment names that attribute as the
  record written beside the display mapping. Both the assertion literal and the comment become
  `disguise_placed_by_cast`. Deleting the assertion to satisfy task 3.6's grep would silently drop
  the guarantee that no combat, dice or targeting module ever reads the placement record — and CI
  would stay green either way, because those modules contain neither name today. Verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_disguise_boundary`.
- [x] 3.6 Verify the old name is gone everywhere:
  `grep -rn "disguise_provenance\|DISGUISE_PROVENANCE" world/ commands/ typeclasses/ tests/` returns
  nothing.

## 4. Remove the node from the catalog

- [x] 4.1 Delete the `unveiling_eye` skill definition from `world/skills/registry.py` and change
  `true_name_sight`'s prerequisite to `SkillPrerequisite("status_disguise", 5)` per design D3. Verify
  the registry imports cleanly and its load-time lineage validation reports no dangling edge:
  `uv run --locked python -c "import world.skills.registry"`.
- [x] 4.2 Change `true_name_sight`'s declared effect from `reveal_disguise:true_name` to the bare
  `reveal_disguise`, and remove `unveiling_eye` from the catalog key assertion in
  `world/skills/tests/test_skill_registry.py`. Verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests.test_skill_registry`.
  (Discovered during implementation: `status_disguise`'s derived proficiency cap in
  `test_chain_roots_derive_the_maximum_consuming_threshold` moves from 3 to 5, because that test
  computes the cap as the maximum threshold any consumer's prerequisite names, and `true_name_sight`
  now consumes `status_disguise` at Lv.5 directly instead of via `unveiling_eye` at Lv.3. The node
  table's `status_disguise` row in `divine-mystery.md` and the 熟練度換算 prose were updated to match
  — the 帷幕線 chain is now two levels deep instead of three, 75 rather than 90 practice-days to a
  confluence-ready Lv.10, so the confluence threshold is set by 統御線／傳承線's 80 instead.)
- [x] 4.3 Verify no shipped content granted the removed skill:
  `grep -rn "unveiling_eye" world/ commands/ typeclasses/ tmp/` returns nothing after the edits.

## 5. Behavior coverage for the defect

- [x] 5.1 In `world/rules/tests/test_divine_veil_reveal.py`, convert the mundane-strength cases: the
  "cannot pierce a divine veil" case becomes a parse-rejection test for any payload on the prefix,
  and the "lifts an authored veil" case becomes an unqualified-reveal test. No assertion may be
  weakened to accommodate the signature change.
- [x] 5.2 Add the regression test this change exists for, over a SYNTHETIC divine-capable entity
  wearing an authored veil — never a shipped preset card, which would be a data-echo test. Assert
  that no reveal a skill can now declare clears that veil except the one the catalog's reveal node
  casts, and that a payload-carrying reveal cannot be declared at all. Verify it fails against the
  pre-change catalog and passes after.
  (Discovered during implementation: the "exactly one shipped skill can declare a reveal" half of
  this assertion names `SKILL_REGISTRY` and the literal key `true_name_sight`, which
  `tools.test_data_lint` flags as shipped-content references in an unexempted behavior-test file. It
  lives in `world/skills/tests/test_skill_registry.py` instead — already a registered
  `Data-contract test:`-tagged file — next to the existing catalog-key assertions; the
  payload-rejection and synthetic-authored-veil-lift halves stay in `test_divine_veil_reveal.py` as
  pure behavior tests with no shipped-content reference.)
- [x] 5.3 Update `world/rules/tests/test_divine_veil_cast.py` to the renamed accessor and boolean
  record. Its fixtures and assertions are unaffected by the reveal collapse, so this is a purely
  mechanical substitution — per design D6, any assertion that needs real restructuring means behavior
  moved and must be investigated rather than accommodated.
- [x] 5.4 Verify the two halves did not interact by running both veil modules together:
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_veil_cast world.rules.tests.test_divine_veil_reveal`.

## 6. Docs, traceability and spec hygiene

- [x] 6.1 Update `docs/lore/skill-trees/divine-mystery.md`: remove `unveiling_eye` from the veil-line
  diagram and node table, rewire the documented prerequisite of 真名之視 to 狀態偽裝 Lv.5, and rewrite
  the 帷幕線 boundary bullet so it states the class guarantee without referring to a two-strength
  division or to the 雜學秘術 lineage that `dissolve-utility-lineage` deletes. Verify
  `grep -n "揭帷之眼\|unveiling_eye\|雜學秘術\|真知鑑定" docs/lore/skill-trees/divine-mystery.md`
  returns nothing.
- [x] 6.2 Re-point the `covers_requirement` annotations for the two REPLACED requirements: the
  traceability ID derives from the requirement name, so tests covering the retired
  `disguised-stats-boundary` provenance requirement and the retired `skill-handler`
  provenance-scoped reveal primitive must move to the replacements' IDs, taken literally from
  `uv run --locked python -m tools.spec_traceability list`. Verify with
  `uv run --locked python -m tools.spec_traceability check`.
- [x] 6.3 Verify the new coverage stays behavior-only and is not added to
  `tools/test_data_freeze.json`: `uv run --locked python -m tools.test_data_lint check`.
- [x] 6.4 AFTER this change is archived, correct the two carried-over scenario titles by direct edit
  to `openspec/specs/skill-effect-model/spec.md` per design D4, so no scenario title names a retired
  strength.

## 7. Verification

- [x] 7.1 Run the focused modules this change touches and verify they pass:
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_veil_cast world.rules.tests.test_divine_veil_reveal world.rules.tests.test_disguise_boundary world.skills.tests.test_skill_registry world.skills.tests.test_effects`.
- [x] 7.2 Run `openspec validate collapse-veil-reveal-line --strict` and verify it reports no errors.
- [x] 7.3 Re-read the design's Non-Goals and verify the diff re-introduces no grade axis under any
  name, adds no mundane veil source, changes no observable behavior from the rename half, and
  touches no lore page other than `divine-mystery.md`.
