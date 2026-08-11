## Context

`_context_for` (`world/rules/combat_session.py:397-415`) sets `event_context["nonlethal"] = True` for `mode == "guild_exam"`, and `_handle_damage` (`world/rules/combat.py:281-327`) floors protected targets at 1 HP. The exam prompt promises a simulated battle with full restoration, which the nonlethal policy does not deliver: it was introduced to avoid real injury, but the simulated-battle design already solves that by restoring both sides around the fight.

## Goals / Non-Goals

**Goals:**
- Exam combat is ordinary lethal combat; no exam-specific damage policy.
- Full HP/MP/SP restore before the exam and after settlement, win or lose.
- Kill rewards suppressed because the battle is a simulation, not because HP is floored.

**Non-Goals:**
- Changing ordinary combat mechanics, exam settlement/idempotency, or rank/merit rules.
- Introducing a new simulated-battle subsystem — reuse of ordinary combat is the point.

## Decisions

**D1 — Remove the session-wide nonlethal flag for exams.** `_context_for` no longer sets `nonlethal` for `guild_exam`; the per-target `nonlethal_keys` path (party companions) is untouched. The knockout-marking code from the previous fix proposal is therefore unnecessary and is not added.

**D2 — Pre-restore at exam start.** `start_guild_exam` restores the candidate's and the opponent's HP, MP, and SP to full after the opponent is spawned and before the first round (part of the existing all-or-nothing start transaction, so a failed start restores nothing).

**D3 — Post-restore at settlement.** `settle_session`'s exam branch restores both sides' HP, MP, and SP to full after the exam outcome is recorded and before the opponent is deleted.

**D4 — Kill-reward suppression stays, via simulation semantics.** The exam battle remains excluded from kill XP/loot, DEFEAT quest progress, and protected-entity failure — now because the fight is a simulation, matching the existing suppression behavior without the HP floor.

**D5 — Exam intro text states the simulation contract.** The pre-exam description (Telnet `guild exam` output and Web exam intro) states the simulated-battle rule and the full-restoration guarantee.

## Risks / Trade-offs

- **Candidate can die in an exam**: the post-restore makes it consequence-free (simulation), and the settlement already records FAIL without rank change.
- **EventLog/planner consumers**: lethal `target_defeated` entries for the examiner must still be excluded from kill/quest consumers (D4) — the existing suppression hooks are kept; tests pin this.
- **Restore vs. pending effects**: restore runs only after the session clears and outside the round transaction, so no in-round effect can be overwritten mid-fight.
