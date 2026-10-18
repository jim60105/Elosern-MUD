# Design: party_member panel

## Context

See proposal.md. `character.py` validates `persona` (four nullable prose keys) and `intimate` (six level fields, nullable) and resolves the owner while possessing; `party.py` reads `npc.relations.stage_for`; `PartyDrawer.vue` derives possess/release/leave state from exploration affordances and `releaseAffordance`; `possession_verdict(player, npc)` and the leave seam's escort-bound check already return stable reasons.

## Goals / Non-Goals

**Goals:** one exact panel for the 成員 tab; server-authored descriptors; possession-identical commander facts.

**Non-Goals:** the 空位 invite target (the client keeps reading the existing `explore.party_invite` affordance, design §6.1), UI rendering, removing fields from `character` (next change).

## Decisions

- **Extract** the persona and intimate serializers/validators from `character.py` into a shared module (`web/webclient/presentation/persona_sections.py`) used by both panels during the transition, so the next change can drop them from `character` without duplicating validation.
- **Bond pips**: add a pure rules read `bond_stage_position(npc, player) -> (name, step, steps)` beside the existing `stage_for`; the raw value never leaves rules.
- **Descriptors** `{action_id, params, enabled, reason}`; `reason` is the existing bounded Traditional Chinese text or null. Possess/release from `possession_verdict`/current possession; leave from the party leave seam's preflight (`escort_bound`, `handback_first`); persona editor from the `npc.persona.read` availability gate.
- **Mode**: available in exploration and combat; combat-inapplicable actions are simply disabled by their verdicts.
- **Bounds**: commissions reuse `MAX_PARTY_COMMISSION_LABEL`; persona prose reuses `MAX_PERSONA_FIELD_LENGTH`; total payload validated against the canonical byte bound with a maximal fixture.

## Risks / Trade-offs

- [Verdict functions with side effects] → Only the read-only preflight/verdict helpers are called; a test asserts an unchanged attribute snapshot after rendering.

## Migration Plan

Pre-release additive panel; revert the implementation commit.

## Verification and documentation ownership

Presenter tests for companion and commander payloads, escort-bound leave reason, possessed release descriptor with otherwise identical payload, commander persona while possessing, fallback after leave, maximal bounds, no raw affinity; validator/mirror parity; allowlist contract. No command changes. Shard registration; `tools.contract_gate`.
