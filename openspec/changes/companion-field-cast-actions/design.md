# Design: Caster-explicit skill preview and field cast actions

## Context

See proposal.md. `explore.skill_preview` stores `(skill_key, scale)` on the presentation session (`skill_use_selection.py`) and the `skill_use` presenter rebuilds the preview from `context.skill_use` for `context.actor`. `preview_field_skill(actor, ...)` builds candidates with `field_candidate_entities(actor)` and openings with `field_opening_anchors(actor)`.

## Goals / Non-Goals

**Goals:** carry the caster end to end with exact schemas and no compatibility layer; recompute permission on every publication.

**Non-Goals:** the 技能 tab UI (later), companion combat openings (refused by the rule).

## Decisions

- **Selection triple** `(actor_id, skill_key, scale)` is copied into the read context; the presenter re-authorizes the caster on every publication and falls back to the unavailable form with reason `member_not_present` / `not_party_member` / `member_cannot_act` instead of silently switching to the commander.
- **Caster-relative preview.** `preview_field_skill` takes the caster; `field_candidate_entities(caster)` keeps the caster first; `field_opening_anchors` is empty for a non-commander caster so the client never offers an opening the rule refuses.
- **Version bump** `SKILL_USE_SCHEMA_VERSION = 2`; the registry-version gate, JS mirror and fixtures change together; old v1 payloads are rejected.
- **Transitional client** sends `store` controlled figure id; the selection persists across possession because it is keyed by caster, not by puppet.

## Risks / Trade-offs

- [Preview for a member who leaves the room] → Republication re-authorizes and degrades to the unavailable reason; cast submission re-authorizes again.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Python: schema tests (missing/forged `actor_id`), presenter for commander and companion (cost, enabled, candidates, empty openings), re-authorization on republication. JS: mirror parity, Node gate and Vitest for the skill-use store payload. No text command changes. Shard contract (if modules move), `tools.contract_gate`.
