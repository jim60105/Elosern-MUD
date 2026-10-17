# Design: character panel v9 skill growth fields

## Context

See proposal.md. `freeform_scale_entries_for(actor, skill)` returns only allowed `(scale, label, mp_cost)` rungs, empty for non-masters; `_load_freeform_scale_ladder` holds the skill-anchored `(scale, min_level)` rungs; `lineage_query._node_view` already computes level, XP band and capped for one node; `SKILL_REGISTRY` prerequisites carry minimum levels.

## Goals / Non-Goals

**Goals:** server-computed growth facts so the client renders without arithmetic; truthful ladder visibility.

**Non-Goals:** the 技能 tab UI; combat panel scale fields (unchanged `freeform_scales`).

## Decisions

- **Ladder**: `freeform_ladder_for(member, skill)` returns five entries when `freeform_mastery_entitled(member, skill)`; an entry in the allowed set carries the same `mp_cost` the allowed-entries helper computes (one cost path); others carry `unlock_level` from the anchored ladder. Validator enforces exactly-one-of and canonical order.
- **Lineage position**: `prerequisites` = the skill's declared prerequisite edges `{key, label, level}`; `next` = reverse-edge consumers `{key, label, min_level}` filtered by the member's identity eligibility; each list bounded (≤ 8).
- **Progress numbers** reuse the lineage node computation (`xp_into_level`, `xp_to_next_level`) so the meter and the 系譜 tab agree.
- **Passive rows** are unchanged (nothing practises a passive).

## Risks / Trade-offs

- [Payload growth] → Each active row gains bounded fields; the maximal fixture (all active rows with full lineage lists) is checked against the byte bound; if it exceeds, `lineage` lists are capped at 4 with a test pinning the cap.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Unit tests for the ladder (master with locked rungs, non-master empty, zero adjusted cost), lineage position for a merge node; presenter tests for `fresh` before/after a new session and `booked`; validator/mirror parity and maximal bound; Vitest SkillBook rung rendering. No command changes. `tools.contract_gate`.
