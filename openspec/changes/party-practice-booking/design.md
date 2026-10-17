# Design: Per-member practice booking

## Context

See proposal.md. `advance_skip(actor, seconds, practice_skill=None)` assigns `actor.db.practice_booking = practice_skill` (so an unlabeled skip writes `None`) and restores the previous value on failure; `CmdSleep`/`CmdWaitUntil` set `practice_booking = None`; `_practice_settlement` consumes each entity's booking on SKIP only; `preflight_practice_booking(actor, skill_key)` returns `PRACTICE_SKILL_UNKNOWN`/`PRACTICE_SKILL_CAPPED`.

## Goals / Non-Goals

**Goals:** standing per-member bookings; one SKIP settles every in-scope booking; booking never advances time; text and action parity.

**Non-Goals:** cancelling a booking (rebooking replaces; not requested by the design), booking during combat, booking an absent member.

## Decisions

- **Booking is a separate write.** `book_member_practice` writes only `member.db.practice_booking`. It is a deterministic rules write with an `action_commit`-style info event (`practice_booked`, context member/skill).
- **Skips stop clearing.** `advance_skip` without a clause leaves bookings untouched; with a clause it books the caller first (as today) and restores the caller's previous booking on failure. The clock's own rollback restores every settled member's booking because `practice_booking` is already a snapshotted settlement surface.
- **Stale-booking protection is no longer needed**: the old clearing existed because a booking was only valid for the skip that recorded it; a standing booking is valid until settled, so a rollback restoring it is correct.
- **`explore.practice`** keeps its action id (design §5 says practice booking gains an actor) and drops `seconds`; affected panels: `character` (booked flag arrives later) — publish the full snapshot for simplicity.
- **Messages**: success 「{成員}將在下次休息時修煉「{技能}」。」; `booking_in_combat` 「戰鬥中無法排入修煉。」.

## Risks / Trade-offs

- [Players used to `修煉結束。` immediate growth] → `rest ... practice` keeps the one-step path for the caller.

## Migration Plan

Pre-release; existing stored bookings remain valid standing bookings. Revert the implementation commit.

## Verification and documentation ownership

EvenniaTest: two-member booking settled by one rest, member elsewhere untouched, movement leaves bookings, sub-hour skip consumes with zero growth, rollback restores both bookings, preflight rejections leave the previous booking, combat refusal, forged member. Action schema tests, command tests, Vitest for the booking button. Update both command documents (including the 技能書 practice paragraph) and run `tests/test_command_docs.py`; shard contract; observability lint (new event); `tools.contract_gate`.
