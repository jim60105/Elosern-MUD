# Proposal: Companion-initiated field combat

## Why

User decision of 2026-10-18 (follow-up to `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md` §4.4/§6.4): a companion's field cast at a co-located monster may open combat, through the same confirmation-before-engaging flow the commander uses. Today the initiation path is hard-wired to the commander as initiator: `world/rules/combat_session/lifecycle.py::engage_group` rejects a non-`PlayerCharacter` (`NOT_A_PLAYER`) and keys `read_session`, `session_id_for`, `combat_companions`, `player_ids` and `opening_first_actor` on the actor; `world/rules/combat_initiation.py::_candidate_record`/`_prepare_opening`/`preview_field_opening` and `world/rules/combat_session/rounds.py::submit_opening_action` make the same assumption, and the initiation snapshots `active_combat`/`dialogue_session` on the actor. Split from `companion-field-cast-rule` after review.

## What Changes

- Split initiator (caster) from commander through initiation: `initiate_field_combat(caster, ...)` resolves the commander with `resolve_commander`; the session id, active-session check, candidate record, battlefield reconstruction, rollback snapshots and `submit_opening_action` are keyed on the commander; `player_ids` = commander plus eligible co-located companions; `opening_first_actor` = the caster's key; the opening skill is seeded as the caster's draft entry through `confirm_actor_command(commander, ..., caster.pk, ...)`.
- `preview_field_opening` validates openings with the companion as caster so previews offer only openings the rule accepts.
- The forward-declared seam left by `companion-field-cast-rule` (companion monster target rejected) becomes the real path; the text `cast … 由 <成員>` at a monster opens combat for the member; both command documents describe it.
- Caster cost and practice are accounted once when the entry resolves in the round; no command time is charged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `field-combat-initiation`: adds the companion-initiator requirement.
- `companion-field-actions`: adds the companion-opened encounter requirement.

## Impact

- `world/rules/combat_session/lifecycle.py` (`engage_group`), `world/rules/combat_initiation.py` (`initiate_field_combat`, `_candidate_record`, `_prepare_opening`, `preview_field_opening`), `world/rules/combat_session/rounds.py` (`submit_opening_action`), `world/rules/field_cast.py` (remove the seam), both command documents.
- Tests: `world/rules/tests/test_companion_field_opening.py` (sharded), updates to existing initiation tests (commander path unchanged).
- Observability: the existing initiation boundary event gains `caster` in context; lint runs.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **9 of 33**.

- depends-on: companion-field-cast-rule

### Code and spec conflicts within the new batch

- `companion-field-cast-rule`: shared file `world/rules/field_cast.py`, shared capability `companion-field-actions` (F/S; that first).
- `companion-field-cast-actions`: consumes the caster-aware `preview_field_opening` for the skill_use v2 openings and its confirmation (D; ordered next).
- `party-rest-move-settlement`, `party-field-settlement-scope`: none in code (combat time only).
- Text-command changes: shared command docs (F; ordered).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change. The v7 opening-routing rule ("an encounter-starting selection may seed the initiating character's draft entry") is reused with the caster as the initiating character.
