## 1. Remove the page

- [x] 1.1 Delete `docs/lore/skill-trees/utility.md` with `git rm`, and verify
  `git status` shows the deletion staged and no other file in that directory touched.
- [x] 1.2 Remove the `- [雜學秘術系譜樹](/lore/skill-trees/utility)` line from `docs/_sidebar.md`,
  and verify the surrounding skill-tree list renders as a contiguous block with no blank entry
  (`grep -n -A2 -B2 "skill-trees" docs/_sidebar.md`).

## 2. magic-system.md

- [x] 2.1 Delete `## 15. 江湖術士與假貨市場` in full, from its heading through the `---` that closes
  it, and verify no orphaned section separator or dangling intra-page reference to §15 remains
  (`grep -n "江湖術士\|假貨\|第 15 節" docs/lore/magic-system.md` returns nothing).
- [x] 2.2 Renumber any section headings after the deleted §15 and fix every intra-page cross
  reference that names a renumbered section, verifying with
  `grep -n "^## \|第 [0-9]* 節" docs/lore/magic-system.md` that headings run in an unbroken sequence
  and every referenced number resolves to the intended section.
- [x] 2.3 Rewrite §9 as the decision record per design D2: no learnable nodes, why, the three
  abilities' actual homes (儲物 → `storage_pouch`; 鑑定 → no information asymmetry about objects
  exists in this world; 偽裝與揭示 → the divine-mystery veil line), and that this is the second
  emptying, naming 狀態偽裝/統御術 as the first. Verify the section no longer links to
  `/lore/skill-trees/utility` and no longer claims any content is 已系譜化.
- [x] 2.4 Rewrite the `雜學秘術 | UTILITY` row in the `:28` category table per design D3, and verify
  the table no longer equates the lore category with the enum and names 「特殊」 as the enum's actual
  display label.
- [x] 2.5 Update the `:3` opening paragraph's list of what the page establishes so it no longer
  promises a 雜學秘術 boundary the page now records as dissolved.

## 3. Remaining lore cross-references

- [x] 3.1 In `docs/lore/skill-trees/index.md` §7, keep the 雜學秘術 row per design D4: remove the
  link, and set 性質 to state it has no nodes and point at magic-system §9. Verify the table's other
  rows are untouched with `git diff docs/lore/skill-trees/index.md`.
- [x] 3.2 In `docs/lore/skill-trees/light.md`, rewrite the 避孕 bullet's 歸屬 clause so it no longer
  directs a future mechanization to the dissolved category, and verify the bullet still records that
  避孕 deliberately has no node.
- [x] 3.3 In `docs/lore/skill-trees/water.md`, rewrite the 假貨市場 bullet in the 與相鄰系統的接縫
  section. It links to the deleted §15 and calls 鑑定系譜 its 標準靶, and it contains neither
  `skill-trees/utility` nor 雜學秘術, so the substring greps this change relies on do not see it.
  Keep the flavour fact that 治癒泉水 does not work; drop the appraisal-lineage claim and the §15
  link. Verify `grep -n "假貨\|鑑定" docs/lore/skill-trees/water.md` returns nothing.
- [x] 3.4 In `docs/lore/items.md`, extend the `storage_pouch` row (or the prose around it) with the
  in-world reason the inventory has no capacity limit, and verify the claim is consistent with the
  item's registered `rarity`/`price_table_key` in `world/lore/items.py`.

## 4. divine-mystery.md is NOT this change's file

- [x] 4.1 Make no edit to `docs/lore/skill-trees/divine-mystery.md`. `collapse-veil-reveal-line` owns
  that page in full and strips the 雜學秘術/真知鑑定 reference from its 帷幕線 bullet as part of its
  own task 5.1, because that same bullet also describes the two-strength division that change
  retires. Verify the file is absent from this change's diff.

## 5. Regression test

- [x] 5.1 Add a plain repository check asserting that `docs/lore/skill-trees/utility.md` does not
  exist and that no file under `docs/` contains the string `skill-trees/utility`. It carries no
  `covers_requirement` annotation and needs no `tools/test_data_freeze.json` entry: it reads
  documentation paths, not game data, which is the same footing as the existing
  `tests/test_design_draft_contract.py`. Verify it fails against the pre-deletion tree and passes
  after.
- [x] 5.2 If task 5.1 created a NEW test module rather than extending an existing one, register its
  dotted label in exactly one shard of `.github/evennia-shards.json` in this same change, or the CI
  ownership contract fails on every later branch. Verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`,
  passing `MUD_TEST_SETTINGS=1` through the Bash tool's `env` input rather than as an inline prefix.

## 6. Verification

- [x] 6.1 Verify by CONCEPT, not only by exact string — the substring grep has a proven blind spot
  (it missed `water.md`). Run both `grep -rn "skill-trees/utility\|雜學秘術" --include="*.md"
  --include="*.py" --include="*.yaml" --include="*.json" .` and
  `grep -rn "假貨\|鑑定系譜\|真知鑑定\|儲物" docs/`, excluding `openspec/changes/`, and verify every
  surviving hit is intentional: the magic-system §9 record, the index §7 row, the `storage_pouch`
  entries in `items.md` and magic-system §13, and the 鑑定真偽 flavour line in
  `settlement-locations.md` — an NPC checking an heirloom's authenticity is about provenance and
  history rather than hidden magical properties, so it survives the premise change. Confirm that
  reading rather than assuming it.
- [x] 6.2 Run the focused label covering the new check — `uv run --locked evennia test --settings
  test_settings.py --keepdb <the module's dotted label>` with `MUD_TEST_SETTINGS=1` supplied through
  the Bash tool's `env` input — and verify it passes. Do not run a broader suite: nothing this change
  touches is reachable from game code.
- [x] 6.3 Serve or preview the Docsify site and verify the skill-tree sidebar section has no broken
  entry and magic-system's table of contents is continuous.
- [x] 6.4 Run `openspec validate dissolve-utility-lineage --strict` and verify it reports no errors.
