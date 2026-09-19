## Why

`docs/lore/skill-trees/utility.md` publishes six skill nodes — `basic_appraisal`,
`detailed_appraisal`, `true_sight_appraisal`, `minor_storage`, `greater_storage`,
`dimensional_vault` — in the node-table format that `docs/lore/skill-trees/index.md` declares to be
"下一階段程式實作要直接對照寫入 `SKILL_REGISTRY` 的權威資料". None of the six can be written,
because the engine has no verb for any of them:

- No weight, capacity, or encumbrance field exists anywhere in the project, so the three storage
  nodes modify nothing. The inventory has never had a limit.
- The item data model has no hidden affixes and no per-item "true rarity"; `rarity` is documented as
  presentation-only, and `summary_zh` is a single mandatory description with no tiered variants. The
  three appraisal nodes have nothing to reveal.
- `SkillCategory.UTILITY` has zero members in `world/skills/registry.py` and, in practice, is the
  neutral catch-all the test suite uses for synthetic skills, rendered as 「特殊」 by
  `world/rules/combat_view.py`. It is not a container for this lore category.

The page has now been emptied twice: 狀態偽裝 and 統御術 were moved to the divine-mystery lineage in
an earlier pass, and this pass removes the remaining six. A page whose contents have twice been shown
to be unimplementable is a standing invitation to write a third set, so the decision and its
reasoning are recorded in the magic-system section that already owns this boundary, and the page
itself goes.

The `docs/lore/magic-system.md` §15 counterfeit-goods section is removed with it. It is an
unapproved draft, and it is also self-defeating under any consistent reading: a world where
appraisal is everyday and reliable is a world where selling fakes has no expected return, so the
grey market it describes could not operate. Its only mechanical hook was `detailed_appraisal`, which
is one of the six nodes being deleted.

## What Changes

- Delete `docs/lore/skill-trees/utility.md` and its `docs/_sidebar.md` navigation entry.
- Delete `docs/lore/magic-system.md` §15 (江湖術士與假貨市場) in full.
- Rewrite `docs/lore/magic-system.md` §9 as the decision record: this category has no learnable
  nodes, why, where each of its three abilities actually lives, and that this is the second emptying.
- Break the `雜學秘術 = UTILITY` equation in the `docs/lore/magic-system.md` category table: the lore
  category and the code enum are no longer the same thing, and the table must stop asserting that
  they are.
- Keep the `docs/lore/skill-trees/index.md` §7 row, without a link, marked as having no nodes and
  pointing at magic-system §9.
- Repair the cross-references the deletion strands in `docs/lore/skill-trees/light.md` and
  `docs/lore/skill-trees/water.md`, the latter of which invokes both the deleted §15 and the deleted
  appraisal lineage without naming either in a form this change's greps would have caught.
- Record in `docs/lore/items.md` why the inventory has no capacity limit: `storage_pouch` is standard
  adventurer equipment, so carrying capacity was never an axis of this game.
- Add a repository regression test pinning the deletion, so a future edit cannot quietly relink a
  page that no longer exists.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change edits worldbuilding documentation only. No requirement in any capability describes
the lore pages it touches, no code or rulebook data changes, and `skip_specs: true` is set in the
change's `.openspec.yaml` accordingly.

## Impact

- `docs/lore/skill-trees/utility.md` — deleted.
- `docs/lore/magic-system.md` — §15 deleted, §9 rewritten, category table corrected.
- `docs/lore/skill-trees/index.md`, `docs/lore/skill-trees/light.md`,
  `docs/lore/skill-trees/water.md`, `docs/lore/items.md`, `docs/_sidebar.md` — references repaired.
- `tests/` — one new repository regression check.
- No production code, rulebook YAML, or spec file changes. `openspec/` carries no reference to the
  deleted page.
- `docs/lore/skill-trees/divine-mystery.md` — **not touched by this change**.
  `collapse-veil-reveal-line` owns that page in full and strips its 雜學秘術 reference as part of
  rewriting the veil line, so no file is shared between the two changes.
