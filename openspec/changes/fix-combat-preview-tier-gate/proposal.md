## Why

The shared combat preview and submission revalidation (`world/rules/action_preview.py::_skill_wide_failure`) duplicate most `ActionResolver` checks but omit the elemental spell-tier gate. A valid imported character who owns an affordable over-tier spell (e.g. `firestorm` at `magic_level=15`, no fire affinity, no `fire_mastery`) sees it advertised as enabled in Telnet (`combat actions`) and the WebClient combat panel; submission then passes advisory revalidation and is rejected by authoritative preflight before initiative with the misleading `UNKNOWN_SKILL` message (security-audit run-3 finding index 5, severity low: UI/message only, no state consumed).

## What Changes

- Wire the shared side-effect-free cast-eligibility predicate `world.rules.progression.can_cast_skill(entity, skill) -> bool` — introduced by the parallel change `fix-npc-policy-cast-gate` (this change DEPENDS on it and does NOT redefine it) — into `_skill_wide_failure` in `world/rules/action_preview.py`, so the preview and submission revalidation reject an over-tier elemental spell exactly like authoritative preflight.
- The gate reports `RejectReason.UNKNOWN_SKILL` with the skill key, matching the preview's existing unowned-skill shape (`action_preview.py:87`) and the resolver's post-`fix-npc-policy-cast-gate` rejection shape. A malformed spell fails closed (disabled, never raises) because the predicate converts `ValueError` to `False`.
- Because `preview_skill` and `revalidate_submission` are the two choke points consumed by every presentation and submission surface, the fix reaches all of them with no per-surface edits: the shared combat view (`combat_view.py:313`), the Telnet `combat actions` command (`commands/combat.py:115` "可用"), the WebClient combat panel (`combat_panel.py:398` `enabled`), the WebClient cast adapter (`combat_actions.py:203`), and the combat-session facade (`combat_session.py:858`).
- Add preview parity tests for the below-threshold, affinity-boundary, mastery-override, and direct-ownership-override cases, plus a submission-revalidation parity test and a combat-view test proving the descriptor is disabled. Fix the existing parity-test gap: `test_action_preview.py`'s fixture uses `fire_ball` (學徒 tier, threshold 0), which always passes the gate, so the gap was never detected.
- No command-key, alias, syntax, or wire-schema change; no player-facing message change (`player_messages.rejection_message` never interpolates detail). No production code outside `world/rules/action_preview.py` changes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `action-resolution-pipeline`: the "ActionResolver exposes shared side-effect-free action preview" requirement is extended so preview and submission revalidation also cover elemental spell-tier eligibility via the shared predicate (the single-consumer requirement for the predicate itself is owned by `fix-npc-policy-cast-gate`'s `element-mastery` delta; this change only closes the preview surface on the same helper).

## Impact

- `world/rules/action_preview.py` (one gate call in `_skill_wide_failure`, docstring update) — the only production file changed.
- Tests: `world/rules/tests/test_action_preview.py` (new parity tests + under-tier fixture), `world/rules/tests/test_combat_view.py` (disabled descriptor test). Existing `test_action_preview.py::test_preview_has_no_side_effects` stays green, proving the gate keeps preview side-effect-free.
- Downstream consumers inherit the fix with zero edits: `world/rules/combat_view.py`, `commands/combat.py`, `web/webclient/presentation/combat_panel.py`, `web/webclient/actions/combat_actions.py`, `world/rules/combat_session.py`.
- Coordination: this change lands after `fix-npc-policy-cast-gate` (introduces `can_cast_skill`). Until that change lands, this one cannot be implemented — its design consumes that predicate's exact API (`can_cast_skill(entity, skill) -> bool`, fail-closed on `ValueError`).
- No data migration or backward-compatibility work (project has no released users). No schema, command-surface, or player-facing documentation change.
