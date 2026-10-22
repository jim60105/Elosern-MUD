# Design

## Context

See proposal.md for the reviewed defects. The rules resolver passes pending effects to `record_action_settlement_evidence` inside `_commit`'s open transaction. The adult resistance producer uses the literal `none` sentinel. Actual emitted kinds include `pleasure_gain`, `buff_applied`, `self_buff_applied` and `buffs_cleansed`; the current adapter's alternate EventLog branch recognizes a different vocabulary. `recent_deeds` currently projects only effects and resistance.

## Goals / Non-Goals

**Goals:** Repair the existing settlement-to-projection contract without changing whether an action resists, what it costs, or what effects it applies. Retain authorized player outcomes through compression.

**Non-Goals:** No generic effect-system rewrite, permissive raw-content passthrough, new consent inference, new trigger, historical parser, or gameplay-resolver replay API.

## Decisions

1. Use the existing authoritative emitted effect kinds and optional-roll convention. Normalize recognized records into detached bounded fields after application; do not implement a second pending-description dialect. Remove the seed/test-only alternate interpretation by making both legitimate input forms converge on the same normalizer. Malformed required evidence still fails its source transaction; do not swallow the sentinel failure or manufacture an empty deed.
2. Preserve actual recipient IDs and established results. Read settled values from the source's existing effect/result surfaces, not a skill-name inference. Keep resistance verdicts distinct from willingness. Operational diagnostics contain IDs and exceptions, never the full payload.
3. Extend the existing authorization projection with separate own-state transition/counter permissions. Another participant's internal state remains absent even for the actor unless its field is explicitly knowable. Retain authorized transitions, counter deltas, distinct effects and linked milestones during aggregation. Join an action's attached milestones before forming the repetition stream, so the same occurrence does not become a spurious boundary or extra count.
4. Keep the first-three candidate and citation contracts unchanged. Regression inputs run real resolver construction through storage and selection; seeded narrative payloads alone cannot establish producer compatibility.

## Risks / Trade-offs

- Shared projection later extracted by E -> leave it pure and recipient-parameterized; E owns the shared memory consumer cutover.
- Planned effects can differ from committed bounded gauge changes -> use actual settled data and include a clamped-result regression, without duplicating mechanic calculations.
- New permission tokens can expose another subject -> test actor, recipient and untouched-control projections with different private state.

## Migration Plan

Clean cutover of current callers and fixtures; no compatibility paths, migrations or backfill. Update only this change's delta specs now. During apply, update behavior-linked traceability and technical documentation and run focused verification; revert code to roll back the implementation.

## Verification and size

Budget: normalization/regressions 2 h; authorized projection/grouping 2 h; boundary and rollback checks 2 h; docs/traceability/gates 2 h. Use synthetic data, existing package tests and independently known outcomes. Implementation verification includes an offline source-to-rendered-JSON smoke, focused tests, observability lint when logging changes, and the contract gate.
