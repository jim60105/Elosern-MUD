# Proposal

## Why

`narration-core-and-combat-prose` lands the narration engine and the mechanical prose, but
the 42 non-elemental ACTIVE skills — martial arts, holy rites, divine mysteries and the
enhancement line — still open on a category-tier line. A player who casts 劍術 and a player
who casts 祝聖 read the same opening sentence, which is the defect the whole effort exists to
remove.

## What Changes

- Author a per-skill action line for each of the 42 non-elemental ACTIVE skills (16 martial
  arts, 14 holy rites, 11 divine mysteries, 1 enhancement), each with one or two variants in
  the family's own register.
- Add per-skill overrides for the kinds where the skill's identity matters more than the
  shared pool (a rite's blessing/shelter outcome, a divine mystery's authority line).
- Remove the four non-elemental categories from the catalog's frozen pending-family set, so a
  newly added martial, rite, mystery or enhancement skill without a row now fails at import
  instead of silently narrating at the category tier.
- Keep the elemental and sexual families pending; their own changes land next.

## Capabilities

### New Capabilities

### Modified Capabilities
- `action-narration`: adds the per-skill coverage requirement for the non-elemental ACTIVE
  families and shrinks the pending-family set to elemental magic and sexual acts.

## Impact

- `world/skills/narration/data_martial.py`, `data_holy_rite.py`, `data_divine_mystery.py`,
  `data_enhancement.py` (new data modules) and the catalog aggregate's import list.
- The frozen pending-family constant and its pinning test.
- No registry row changes, no `SkillDef` change, no pipeline change, no panel or payload
  change. The coverage contract slice gains the non-elemental assertion.
