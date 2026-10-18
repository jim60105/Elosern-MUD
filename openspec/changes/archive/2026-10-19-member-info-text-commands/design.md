# Design: 狀態 and 技能 member text views

## Context

See proposal.md. `world/rules/status_text.py` renders the breakdown layers the `看` self view prints; `build_character_read_model(entity)` accepts any entity; the v9 character rows add growth facts from rules read helpers.

## Goals / Non-Goals

**Goals:** two read-only commands sharing the panel's read models; possession-identical output.

**Non-Goals:** editing anything; `系譜` (lineage change); unread clearing (the text client has no unread dot).

## Decisions

- **Resolution**: empty argument → `resolve_commander(caller)`; otherwise `resolve_member_token` (membership only, presence not required, matching the panel's viewing rule).
- **Rendering** reuses `status_text` for traits/layers and a new `skills_text` helper shaped like the v9 rows (levels, `（見頂）`, `［修煉中］`, `［新］`, prerequisite/next, ladder rungs as `1/4 MP 2 ‧ … ‧ 2 需 Lv.6`).
- **Key names** `狀態`/`技能` must not collide with existing keys or aliases; the implementation checks the merged cmdsets in a test.

## Risks / Trade-offs

- [`status`/`skills` alias collisions with Evennia defaults] → The test enumerates the character cmdset; if a collision exists the alias is dropped and the documents say so.

## Migration Plan

Pre-release additive; revert the implementation commit.

## Verification and documentation ownership

Command tests: commander default, companion with disguise (true values), possession-identical output, non-member refusal, absent member viewable, skill growth parity with the presenter. Both command documents; `tests/test_command_docs.py`; shard registration; `tools.contract_gate`.
