# Design: character panel v8 for the viewed member

## Context

See proposal.md. `character_presenter(context)` raises unavailable outside exploration, builds `build_character_read_model(actor)` for the puppet, and resolves the possession owner only for persona. `status.py` already derives condition rows with deterministic matched modifiers for the stage figure.

## Goals / Non-Goals

**Goals:** viewed-member read model in both modes; exact v8 shape; condition rows the 狀態 tab can render without inventing text.

**Non-Goals:** skill growth fields (`character-skill-growth-fields`), the 狀態 tab UI, changing `status` v3.

## Decisions

- **Subject** = `resolve_viewed_member(context)` (party v3 helper). The read model is the same `build_character_read_model(member)`, so true values and disguise comparison semantics are unchanged.
- **Conditions** reuse the status read model's matched-modifier rows for the member and add `source` (the buff's registry source label, or the equipment/skill/state origin already known to the breakdown read model). `remaining_seconds` is null for indefinite conditions.
- **Combat availability**: the mode gate is removed; nothing in the read model mutates state, which the existing read-only test proves for both modes.
- **Keep `equipment` and `wallet`** (not removed by the design text, still consumed by the transitional drawer); the final cleanup does not touch them.
- **Bounds**: conditions ≤ 32 rows; `modifiers` and `source` bounded like existing labels; maximal fixture within the canonical byte bound.

## Risks / Trade-offs

- [Two panels feeding one old drawer] → Transitional only; `webclient-party-status-tab` deletes the drawer.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Presenter tests for commander and companion subjects, possession-identical payload, combat availability, condition rows (buff with source and remaining time, indefinite debuff), absence of persona/intimate, read-only snapshot; validator/mirror parity; Vitest drawer persona/intimate rebinding and persona edit refresh. No command changes. `tools.contract_gate`.
