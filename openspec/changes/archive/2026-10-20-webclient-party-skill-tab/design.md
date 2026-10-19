# Design: Party window 技能 tab

## Context

See proposal.md. `SkillBook.vue` (1,017 lines) renders active/passive segments, search, the category tree, `SkillDetailPane` and the practice control, and hands casting to the dock via the skill-use store. The prototype `tabs/SkillTab.vue` defines the tab layout and the 威力與消耗 row.

## Goals / Non-Goals

**Goals:** move the book content into the frame for any member; render growth facts and the ladder from the payload; delete SkillBook.

**Non-Goals:** combat casting (command card unchanged), new skill rules.

## Decisions

- **Port, not rewrite**: segment/search/tree logic moves from `SkillBook.vue` into the tab (or small child components) so existing ordering and search tests carry over.
- **Ladder** renders `freeform_ladder` entries verbatim (`mp_cost` or `需 Lv {unlock_level}`); no scale arithmetic in the client.
- **Casting handoff** reuses the existing skill-use store with the viewed member's `actor_id`; the window closes before the dock takes focus (same owner rule as the book).
- **Unread** clearing rides the selection dispatch on tab open; 新 tags read `fresh`. The tab sends that one selection only while the rail row is `unread` or the committed `selected_skill` differs from the row it shows, never while the shared dispatch lock is closed, and retries a refused request when the lock opens.
- **No local knocked-out gate**: the prototype's `{name}倒地中` reason would restate a rule the server preview already decides; a knocked-out caster's 施放 shows the preview's refusal as the caster-scoped notice instead.
- **Every category opens** on a selection reset, matching the prototype's flat list; the tree's collapse controls still work.

## Risks / Trade-offs

- [Large component move] → Kept within 7h by porting logic and reusing `SkillDetailPane`; the Vitest suites of SkillBook are re-pointed, not rewritten.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: segment/search/tree parity, meter/level/新, ladder rendering for master/non-master, lineage link, companion 施放 payload and dock handoff, 排入修煉 payload, combat-disabled reasons, unread clearing dispatch. Stories (book, freeform scales, in combat) at both sizes; Storybook build and showcase coverage; one browser method (companion field heal from the tab) in `.github/browser-shards.json`; command docs and AGENTS.md. `tools.contract_gate`.
