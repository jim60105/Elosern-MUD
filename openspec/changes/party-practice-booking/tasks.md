# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Booking rule and skip semantics (2.5h)

- [ ] 1.1 Add `book_member_practice` with `booking_in_combat`, member preflight and the `practice_booked` info event; stop unlabeled skips (`advance_skip`, `CmdSleep`, `CmdWaitUntil`, `CmdRest` without clause) from clearing bookings; verify in `world/rules/tests/test_party_practice_booking.py` two members settled by one three-hour rest, a member elsewhere untouched, movement leaving bookings, sub-hour consumption with zero growth, rebooking replacement, and rollback restoring both bookings; run `uv run --locked python -m tools.observability_lint check`.

## 2. Action and SkillBook control (2h)

- [ ] 2.1 Change `explore.practice` to `{actor_id, skill}` booking-only; verify schema rejections (including `seconds`), forged member, combat refusal and the success message in the exploration action tests.
- [ ] 2.2 Replace the SkillBook practice duration sub-screen with one booking control sending the controlled figure's id; verify the Vitest SkillBook practice tests.

## 3. Text command and documentation (1h)

- [ ] 3.1 Add `修煉 <技能> [= <成員>]` (alias `practice`) and update both player command documents (including the 技能書 practice paragraph and `rest ... practice` wording); verify command parity tests and `tests/test_command_docs.py`.

## 4. Integration (1h)

- [ ] 4.1 Update existing skip/practice tests that asserted clearing, register the new module in one shard, annotate canonical IDs for every modified/added requirement, run the focused labels, the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate party-practice-booking --strict`.
