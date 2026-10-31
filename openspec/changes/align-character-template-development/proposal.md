# Proposal

## Why

The preset kits omit learned breadth in unused elf trees and still describe innate values as allocation or learning outcomes. The five original story templates already resolve to the original innate values; their learned abilities and prose need alignment without changing those numbers.

## What Changes

- Author initial ownership and positive low-tier proficiency for every currently implemented, eligible ordinary elemental root and common martial/divine root on each elf preset, while preserving deeper specialties.
- Keep existing mastery selections and let the shared closure/seed mechanism provide their complete elemental trees. Add no other masteries.
- Restore Sylwen's innate body enhancement and add the appropriate sword, defensive earth and light-healing training.
- Retain original combat, movement, boon and disguise abilities; keep Yuka's stronger body enhancement exclusive.
- Give Violet explicit learned proficiency and Lidzia her approved second sword technique; correct Elysa/Nazka/Sylwen role prose.
- Remove stale numeric comments and revise Elosia's learning prose to innate magic plus learned proficiency.
- Record approved non-sexual source choices in tracked lore documentation. Ignored personal reference files remain outside runtime and commits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This change authors data through existing preset fields and existing closure/seed mechanics. Character templates, skill choices, initial levels and balance values are game data and MUST NOT become capability requirements. Existing validation and construction tests establish the mechanisms; no requirement or test shall pin roster copy, exact builds or arbitrary levels.

## Impact

One engineer-day of preset/lore data authoring. Runtime rule changes belong to the two prerequisite changes. No race-range, gauge, allocation-budget, innate-stat or multiplier redesign; no migration or compatibility alias. Authored baseline and prose quality receive human review against `design.md` and the tracked roster review document it specifies. Existing generic registry integrity checks and representative construction checks remain the automated evidence.

## Batch:

depends-on: complete-elemental-mastery
depends-on: correct-elemental-practice-eligibility

Runtime data files are disjoint from both prerequisites. This change owns `world/lore/player_presets/data_pack_cards.py`, `data_story_cards.py` and the tracked roster review page. Its root-architecture source-authority amendment is independent of the prerequisites' progression-design amendments. No overlap with the active wilderness proposals.
