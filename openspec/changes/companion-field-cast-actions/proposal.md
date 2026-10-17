# Proposal: Caster-explicit skill preview and field cast actions

## Why

Design §5 (action identifiers) and §6.4 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: field casting gains an actor so the 技能 tab can cast as the viewed member through the existing server preview and target flow. Today `explore.skill_preview` and `explore.cast` bind to the puppet and reject any actor field.

## What Changes

- **BREAKING (pre-release)** `explore.skill_preview` payload becomes `{actor_id, skill_key[, scale]}`; the session selection stores the caster with the skill and scale.
- **BREAKING (pre-release)** `explore.cast` payload adds required `actor_id`; the adapter calls `cast_as_member`.
- **BREAKING (pre-release)** `skill_use` panel v1 → v2 adds `actor_id`; costs, targets, openings and availability are computed for that caster; a companion caster gets no openings. Python validator, JS mirror (`web/static/webclient/js/elosern/protocol/panels/`), parity contract and fixtures move together.
- The current SkillBook / SkillUseDock sends the controlled figure's id until the 技能 tab lands.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-skillbook-casting`: read model v2 with caster identity; preview payload and selection carry the caster; cast payload carries the caster.

## Impact

- `web/webclient/actions/skill_use_actions.py`, `web/webclient/presentation/skill_use.py`, `web/webclient/presentation/skill_use_selection.py`, `world/rules/field_cast.py::preview_field_skill` (caster-relative), JS mirror and stores (`stores/elosern/skill_use.js`, `composables/use-skill-use.js`), fixtures under `web/webclient-app/stories/fixtures/` and protocol fixtures.
- Tests: updated skill-use action/presenter tests, protocol parity test, Node/Vitest skill-use tests.

## Effort

**5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **8 of 30**.

- depends-on: companion-field-cast-rule

### Code and spec conflicts within the new batch

- `companion-field-cast-rule`: shared file `world/rules/field_cast.py` (F; that change first).
- `webclient-party-skill-tab`: consumes `skill_use` v2 and removes `SkillBook.vue` edited here; shared spec `webclient-skillbook-casting` (F; ordered).
- `party-practice-booking`: shared client file `components/SkillBook.vue` practice wiring (F; this change first).
- Protocol fixtures and parity contract files shared with every protocol change (F, conditional; ordered).

### Active change coordination

No active OpenSpec change.
