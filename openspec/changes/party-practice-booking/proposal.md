# Proposal: Per-member practice booking

## Why

Design §4.5 and §6.4 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: each member owns one `db.practice_booking`; the commander can book practice for any member (排入修煉), and the next SKIP advance settles every in-scope member's booking. Today a booking exists only as a clause of one skip (`rest ... practice`, `explore.practice {skill, seconds}`), and every unlabeled skip clears bookings, so booking several members for one rest is impossible.

## What Changes

- New rule `world/rules/time_skip.py::book_member_practice(acting, member_id, skill_key)`: member boundary (acting purpose), `booking_in_combat` refusal, the existing practice preflight against the member, then one booking write. Rebooking replaces.
- SKIP advances no longer clear standing bookings; each settled member's booking is consumed by the existing practice stage (party scope from `party-rest-move-settlement`). `rest <duration> practice <skill>` still books the caller then skips.
- **BREAKING (pre-release)** `explore.practice` becomes a booking-only action `{actor_id, skill}` with no clock advance.
- New text command `修煉 <技能> [= <成員>]` (alias `practice`).
- The current SkillBook practice control becomes a single booking button (no duration sub-screen) until the 技能 tab replaces it; command documents updated (including the practice paragraph that described the duration screen).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `party-time-settlement`: per-member standing bookings and the `修煉` command.
- `time-skip-commands`: skips settle standing bookings instead of clearing them.
- `settlement-stage-order`: the practice-stage note matches standing bookings.
- `webclient-exploration-menu`: `explore.practice` books for a member without advancing time.
- `webclient-skillbook-casting`: SkillBook practice is a booking control.
- `webclient-contextual-hud`: the reference-drawer scenario and the declared-practice sub-screen requirement (renamed to a booking control) no longer describe a duration sub-screen.

## Impact

- `world/rules/time_skip.py`, `commands/skip.py` (clear-on-skip removed), new `CmdPractice` in `commands/skip.py`, `web/webclient/actions/exploration_actions.py`, `web/webclient-app/components/SkillBook.vue` and its store/composable wiring.
- Docs: both player command documents.
- Tests: `world/rules/tests/test_party_practice_booking.py`, `commands/tests` skip tests, exploration action tests, Vitest SkillBook practice tests.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **11 of 32**.

- depends-on: party-rest-move-settlement
- depends-on: companion-field-cast-actions
- depends-on: companion-field-item-use

### Code and spec conflicts within the new batch

- `party-rest-move-settlement`: shared files `world/rules/time_skip.py`, `commands/skip.py`; shared specs `time-skip-commands`, `settlement-stage-order` (F; that change first; this delta keeps its scope text).
- `companion-field-cast-actions`: shared file `components/SkillBook.vue`; shared spec `webclient-skillbook-casting` (different requirements, S; that change first).
- `companion-field-item-use`: both command docs (F; that change first).
- `party-unlock-notices`: shared file `world/rules/clock.py` practice stage (F; this change first).
- `character-skill-growth-fields`: reads the booking for the `booked` row flag (D).
- `webclient-party-skill-tab`: removes `SkillBook.vue` (F; ordered) and re-modifies the `webclient-contextual-hud` reference-drawer requirement (S; ordered).

### Active change coordination

No active OpenSpec change.
