# Proposal: character panel v9 skill growth fields

## Why

Design §6.4 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: every skill row of the 技能 tab shows a proficiency meter and level, newly unlocked skills carry a 新 tag, the detail shows the lineage position (prerequisite → skill → next unlock), and the 威力與消耗 row shows the full freeform ladder (1/4, 1/2, 1, 2, 4 from `progression.yaml` `freeform_cast_scales`) with each rung's MP cost or its locking proficiency level, only when the member owns the element's mastery. Today `character` active rows carry only cost, target, field capability and the *allowed* scales.

## What Changes

- **BREAKING (pre-release)** `character` v8 → v9: active rows add only the compact facts `level`, `xp_into_level`, `xp_to_next_level`, `capped`, `fresh`, `booked` (and drop `freeform_scales`); the panel adds `selected_skill` (null, or `key`, `lineage` with `prerequisites[]`/`next[]` and minimum levels, and `freeform_ladder` with five rungs each `mp_cost` xor `unlock_level` for mastery owners only) for the one skill selected in the 技能 tab — summaries for all rows, detail for one, keeping the 65,536-byte bound with 96 active rows.
- **BREAKING (pre-release)** `party.view_member` payload becomes `{member_id, tab, skill_key}`; the selection stores the selected skill and the action republishes `character`.
- Rules read helpers: `freeform_ladder_for(member, skill)` from the skill-anchored ladder loader; lineage position from the registry prerequisite edges and reverse-edge map.
- `fresh` comes from the copied session unlock snapshot (`party-unlock-notices`); `booked` from the member's standing booking (`party-practice-booking`).
- Transitional `SkillBook.vue` reads unlocked rungs from `freeform_ladder`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-exploration-menu`: the character panel requirement (renamed to version 9) plus added row, selected-skill and ladder requirements.
- `webclient-party-panel`: the `party.view_member` requirement carries the selected skill.

## Impact

- `web/webclient/presentation/character.py`, `world/rules/progression/_scaling.py` / `_scales.py` (ladder read), `world/rules/lineage_query.py` (position read), JS mirror, fixtures, `web/webclient-app/components/SkillBook.vue`, `SkillDetailPane.vue`.
- Tests: presenter/validator/parity, progression ladder unit tests, Vitest SkillBook scale tests.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **18 of 33**.

- depends-on: character-panel-v8-viewed-member
- depends-on: party-practice-booking
- depends-on: party-unlock-notices

### Code and spec conflicts within the new batch

- `party-panel-v3-view-member`: this delta modifies its `party.view_member` requirement and shared files `party_view_selection.py`, `party_actions.py` (S/F; informational archive-order notice until synced); `item-holdings-panel` re-modifies the same requirement after this one, preserving `skill_key` (S).
- `character-panel-v8-viewed-member`: shared file `character.py`; this delta renames the version-8 requirement it introduces (F/S; strict validation reports an informational archive-order notice until that change is synced).
- `lineage-panel-v2-graphs`: shared file `world/rules/lineage_query.py` (F; this change adds a read helper the graph rewrite must preserve).
- `webclient-party-skill-tab`: consumes these fields and removes `SkillBook.vue` (F; ordered).
- `member-info-text-commands`: renders these fields in `技能 <成員>` (D).

### Active change coordination

No active OpenSpec change.
