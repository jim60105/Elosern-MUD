## Context

The skill-tree documentation set uses two distinct page shapes, and the project already treats the
distinction as load-bearing:

- A **lineage page** carries a node table whose columns `index.md` §2 defines (Key, 前置條件, MP,
  威力係數, cap). `index.md` §1 states these tables are the data a later change writes into
  `SKILL_REGISTRY` verbatim, and `enhancement.md` tightens it further: the 效果 column must carry the
  actual rule-table numbers, never an adjective.
- A **non-lineage page** explicitly records that something exists in the setting but has no node.
  `movement.md` does this for 空間扭曲 ("世界觀上存在……但沒有系譜節點、沒有 Key"), `innate-gift.md`
  does it for the whole 天賦異能 family, and `light.md` §避孕 does it inline for a single ability.

`utility.md` is written in the first shape while describing content that qualifies only for the
second. The question this design answers is not whether to soften the page, but whether the page
should exist at all once its six rows are gone.

Verified before writing: `grep -rn "skill-trees/utility\|雜學秘術"` across `*.md`, `*.py`, `*.yaml`
and `*.json` returns ten referencing locations, all under `docs/`. `openspec/` and all production
code are clean. No test reads any `docs/lore/` file; `tests/test_design_draft_contract.py` is scoped
to `docs/design/elosern-redesign/` only.

That substring grep is NOT sufficient on its own, and this change is written knowing why.
`docs/lore/skill-trees/water.md` invokes both deleted concepts — it links 假貨市場 and calls 鑑定系譜
its 標準靶 — while containing neither search string. Verification therefore runs a second pass over
the concept words (假貨, 鑑定系譜, 真知鑑定, 儲物); see task 6.1.

## Goals / Non-Goals

**Goals:**

- Remove the standing implementation contract for six unimplementable nodes.
- Leave a durable record of WHY, placed where a future designer will actually meet it.
- Leave no dangling link, and no page whose stated scope no longer matches its contents.
- Explain the no-capacity inventory from within the setting rather than leaving it an unexplained
  engine limitation.

**Non-Goals:**

- Adding any node to `SkillCategory.UTILITY`, in this change or as follow-up work. A non-divine
  mundane reveal was considered and rejected upstream of this change: 狀態偽裝 is bloodline-gated and
  deliberately rare, so a three-race counter would erode the very guarantee it exists to provide.
- Removing or renaming the `SkillCategory.UTILITY` enum member. It has two live uses — the 「特殊」
  display label in `world/rules/combat_view.py` and the neutral synthetic category the test suite
  relies on — and deleting it would break tests for a cosmetic gain.
- Designing 附魔/crafting. It stays parked in magic-system §13 as the one genuinely unclaimed area.
- Any code, rulebook, or spec change. See `collapse-veil-reveal-line` for the mechanical work.

## Decisions

### D1: Delete the page rather than gut it

A gutted `utility.md` would hold three redirects and nothing else. The two non-lineage precedents
that justify keeping such a page do not apply: `movement.md` earns its place with a cross-category
table collecting skills from two different mechanical families plus a `flight`/`flash_step`
behavioral comparison, and `innate-gift.md` with a real catalog of acquired passives. Neither
equivalent exists here, because after the deletion the category owns no skills at all.

*Alternative rejected:* keeping a short "this category is deliberately empty" page. It duplicates
magic-system §9, which readers already reach from the category table, and it leaves a page in the
lineage directory that a future contributor can mistake for a lineage stub to fill in — which is the
exact failure mode being corrected.

### D2: The decision record goes in magic-system §9, not in a new file

§9 already exists, is already titled 〈雜學秘術：戰鬥之外的魔法應用〉, and is already the section that
defines this category's boundary. Rewriting it in place costs one section and creates no new
document. It is also the landing point from the `:28` category table, so the reader who asks "what is
雜學秘術?" meets the answer and the reasoning in the same place.

The record must state that this is the SECOND emptying and name what was removed both times. A bare
"this category has no nodes" invites someone to add some; "twice now, and here is what failed both
times" does not.

### D3: The lore category and the code enum are decoupled explicitly

`magic-system.md:28` currently reads `雜學秘術 | UTILITY`. After this change that mapping is
false in both directions: the lore category has no skills, and the enum holds test fixtures rendered
as 「特殊」. Leaving the row as-is would re-assert the association the rest of the change removes, so
the row states what the enum actually is and that it does not correspond to the lore category.

### D4: `index.md` §7 keeps its row, without a link

Decided by the user. §7 is the skill-tree overview's index of non-magic branches; a reader who knows
雜學秘術 exists will look for it there, and a row reading "無節點，見 magic-system §9" answers them at
the cost of one line. The row carries no link, because the link target is what is being deleted.

### D5: §15 is deleted outright rather than rewritten

Its three "現實支柱" are an appraisal lineage that this change deletes, an enforcement regime that
exists nowhere in code, and a guild PR dynamic with no mechanical surface. Its 冒險者公會緊急類 hook
would commit quest content to a premise the project has now rejected. Nothing in it survives contact
with the rest of this change, and it is an unapproved draft, so it is removed rather than repaired.

The one fact worth keeping from its neighbourhood — that a `storage_pouch` is ordinary adventurer
equipment — is relocated to `items.md`, where the item itself is catalogued.

### D6: A regression test pins the deletion

A plain repository check (no `covers_requirement` annotation, matching
`tests/test_design_draft_contract.py`'s precedent) asserting that `docs/lore/skill-trees/utility.md`
does not exist and that no committed file under `docs/` links to it. Scoped to this one target rather
than a general link checker, so it cannot fail on pre-existing dangling links elsewhere in the docs
tree and cannot become a maintenance burden.

## Risks / Trade-offs

- **The worldbuilding category becomes mechanically empty.** Accepted and intended: every non-combat
  mechanical surface in the project is already owned (movement by the 身法 tag, information reveal by
  the divine-mystery veil line, capacity by items, knowledge by the lore codex, prices by guild and
  shop data). There is no unclaimed territory for it, and pretending otherwise is what produced the
  six unimplementable nodes.
- **§15 deletion loses authored flavour text.** It is recoverable from git history if a future change
  wants a counterfeit-goods storyline built on a premise that can actually hold.
- **A concept can outlive its keywords.** The `water.md` miss shows that deleting a worldbuilding
  concept cannot be verified by grepping the deleted page's name. The concept-word pass in task 6.1
  is the mitigation, stated as a method rather than a one-off fix, because the next lore deletion
  will have the same shape.
- **No file is shared with `collapse-veil-reveal-line`.** That change owns
  `docs/lore/skill-trees/divine-mystery.md` in full, including the 雜學秘術 reference this change
  would otherwise have had to strip, so the two can be applied in either order, independently.
