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
- Raise the character panel's flattened actives wire bound from 96 to 128 (server constant plus its
  mirrored JS validator) because the completed elf baseline lifts the largest shipped character's
  legitimate active-row set to 102 rows; the bound stays a fail-closed guard above the content.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-exploration-menu`: MODIFIED 「Character panel skills are grouped by category with the
  same ordering rule as the combat panel」 — the flattened `actives` bound moves 96 → 128 so it
  stays above every legitimately assembled active-row set; `passives` stays 32 and the payload
  shape, grouping rule and envelope are unchanged.

The character data itself stays game data, never a capability requirement: no requirement or test
shall pin roster copy, exact builds, exact levels or prose, and the delta carries only the bound
move. `.openspec.yaml` therefore no longer declares `skip_specs`.

## Impact

One engineer-day of preset/lore data authoring plus one presentation-bound move. Runtime rule changes belong to the two prerequisite changes. No race-range, gauge, allocation-budget, innate-stat or multiplier redesign; no migration or compatibility alias. Authored baseline and prose quality receive human review against `design.md` and the tracked roster review document it specifies. Existing generic registry integrity checks and representative construction checks remain the automated evidence.

## Batch:

depends-on: complete-elemental-mastery
depends-on: correct-elemental-practice-eligibility

Runtime data files are disjoint from both prerequisites. This change owns `world/lore/player_presets/data_pack_cards.py`, `data_story_cards.py` and the tracked roster review page. Its root-architecture source-authority amendment is independent of the prerequisites' progression-design amendments. No overlap with the active wilderness proposals.
