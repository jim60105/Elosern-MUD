# Proposal: add-holy-rite-category

## Why

The church redemption catalogue grants ACTIVE skills whose presentation home is
wrong: the 15 church-block ACTIVE rows sit inside `enhancement` (11 rows) and
`sexual_act` (4 placeholder rows), while the three real skill families
(elemental magic, martial/sexual rails) each own a dedicated category. The
approved design (`docs/superpowers/specs/2026-09-23-holy-rite-cast-rail-design.md`
§3) establishes a fourth family — `holy_rite` (神聖聖儀) — as the data contract
for the future fourth skill menu, and this change lands that taxonomy alone,
without any cast mechanics (the mechanics ship in
`implement-holy-rite-cast-rail`, which depends on this category existing).

## What Changes

- `SkillCategory` gains `HOLY_RITE = "holy_rite"` appended last (declaration
  order is the frozen display order; appending is the only legal edit).
- The 15 church-block ACTIVE rows in `world/skills/registry/data_church.py`
  re-classify: 11 rows `ENHANCEMENT → CHURCH_RITE`, the 4 Series D placeholder
  rows `SEXUAL_ACT → CHURCH_RITE`. Every other field of every row is
  byte-identical (`kind`, `cost`, `effects`, `element`, `target_spec`,
  `group`, including the Series D `group="聖禮"`).
- The 5 Series C discipline PASSIVE rows and all non-church rows keep their
  category — the family is defined by *invoked church acts*, not acquisition.
- Registry-agreement consequence: the 4 Series D placeholders leave the
  `SEXUAL_ACT` comparison set of the structural check, shrinking its named
  exclusion list by exactly those keys.
- Presentation mirrors move in lockstep (they are shipped surfaces that pin
  the six-member enum and its closed client validator set): the combat-menu
  and exploration-menu category-ordering rules grow to seven members, the
  panel label mapping gains `神聖聖儀`, and the client
  `SKILL_CATEGORY_KEYS` validator mirror (`web/static/webclient/js/elosern/
  protocol/constants.js`) admits `"holy_rite"` so payloads carrying owned
  church skills keep validating. No new UI is built — this is the existing
  panel contract's closed-set extension, nothing more.
- No player-command surface change, no new effects, no mechanic change of any
  kind: casting availability is exactly unchanged (the re-classified rows keep
  their existing effect declarations, two on rails, thirteen without).

## Capabilities

### New Capabilities

None — this change only re-files existing rows and extends existing closed
vocabularies.

### Modified Capabilities

- `skill-category-registry`: enum grows six → seven with appended
  `HOLY_RITE`; the exact-partition requirement re-pins across seven; the
  per-category group vocabulary gains the `HOLY_RITE` clause (the closed set
  `{None, "聖禮"}`: the four Series D placeholders declare `"聖禮"`, every
  other member `None`); the "classifying changes no other field" pin is
  extended to this re-classification.
- `webclient-combat-menu`: the category-ordering rule reads "seven members"
  (appended last), and the client validator's closed category set admits
  `holy_rite`.
- `webclient-exploration-menu`: the character panel's `actives`/`passives`
  category-ordering rule reads "seven members" (appended last).

## Impact

- Code: `world/skills/registry/vocab.py` (enum member),
  `world/skills/registry/data_church.py` (15 `category=` swaps), the webclient
  presentation category-label map, `constants.js` mirror constant.
- Tests: `world/skills/tests/test_skill_registry/test_category_classification.py`,
  the registry-agreement `_support.py` exclusion list, combat/exploration
  panel tests and the Node protocol fixtures that pin the category enum face.
- Data contract: church keys stay behind the tagged data-contract tests only
  (`tools/test_data_freeze.json` membership unchanged in kind, updated in
  content).
- No migrations, no compat layers (unreleased project, zero users).
- Depends on: nothing. Unblocks: `implement-holy-rite-cast-rail` (its two new
  effect rails land on rows that must already live in `holy_rite`).
