# Proposal

## Why

The shared practice classifier requires magical damage, so elemental healing, defensive buffs and control spells miss affinity and owned elemental-growth multipliers. Their learning rate contradicts the ordinary elemental-magic catalog.

## What Changes

- Classify ACTIVE elemental-magic catalog skills with a registered element as eligible for elemental practice modifiers, including damage-free effects.
- Keep elemental-tagged physical martial arts neutral.
- Use the same predicate for affinity and owned scoped growth on use and booked study.
- Preserve rulebook constants, independent growth factors, practice caps, dedupe, rollback, innate stats, damage and MP calculations.
- Amend the current damage-only scenario and explanatory documentation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-lineage`: elemental learning eligibility for practice accrual.

## Impact

One bounded engineer-day. Runtime work is confined to `world/rules/progression/_practice.py`; use and study already share its factors. Extend existing synthetic practice tests, with no new persistence, balance tuning or freeform eligibility change. No character template or authored skill-row changes. Human review covers explanatory prose against the review checklist in `design.md`.

## Batch:

depends-on: none

Runtime-independent of `complete-elemental-mastery`. Both touch distinct blocks of the `skill-lineage` delta and distinct sections of the progression design / skill-tree overview, so serialize document integration if needed. `align-character-template-development` depends on both changes.
