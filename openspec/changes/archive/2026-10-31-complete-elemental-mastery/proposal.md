# Proposal

## Why

Element mastery currently grants freeform entitlement from a bare passive key and sits outside the learning graph. Completing a highest spell leaves ordinary side branches unlearned, and learning endpoints cannot acquire the passive through normal practice.

## What Changes

- **BREAKING**: Attach each existing elemental mastery to every ordinary terminal branch of its element. Preserve terminal caps and existing ordinary edges.
- Grant the mastery automatically when use or booked study satisfies its registry prerequisites, through the deterministic ownership writer and committed unlock notifications.
- Require lawful direct ownership and the whole prerequisite closure for freeform entitlement. Preserve spell eligibility, proportional scaling, per-spell proficiency and caps.
- Count obtained, usable passive nodes as complete without awarding passive practice XP.
- Preserve explicit import proficiency, including insufficient entries, while denying invalid mastery entitlement.
- Amend the approved progression design and current lore explanations that place mastery outside the graph. Retire four data-pinning lineage requirements; retain their authored content in registry/lore authorities.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `element-mastery`: whole-tree prerequisite coverage, lawful entitlement and automatic acquisition.
- `skill-lineage`: closure semantics and lawful mastery gating; replace obsolete authored-tree exclusions with generic mechanisms.
- `skill-lineage-panel`: passive completion in the existing read model.
- `freeform-casting`: scaled-cast refusal for an unlawfully held mastery.

## Impact

One engineer-day, using existing graph caches, closure/seed helpers, ownership writer and notification sinks. No new persisted shape, migration, compatibility layer, magic-stat bonus or spell generation. No character data in specs. Exact endpoints, thresholds and labels are authored content in `design.md` and later tracked registry/lore documents. Wording and lore quality are human-reviewed against `design.md`'s review checklist.

## Batch:

depends-on: none

Code conflicts with `correct-elemental-practice-eligibility` are limited to separate requirement blocks in `skill-lineage` and separate sections of the progression design / skill-tree overview. Their runtime edits are independent. `align-character-template-development` follows this change and consumes its closure and entitlement semantics. Other weapon lineages remain separately scheduled, unimplemented content; this proposal makes no rejection of them.
