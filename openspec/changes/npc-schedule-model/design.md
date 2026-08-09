# npc-schedule-model — Design

## Context

The world clock settles ten stages; nine have live sources. `npc_schedules`
(`world/rules/clock.py:41`) has a stage name but no source, and `NPC.schedule`
(`typeclasses/npcs.py:31`) is an unused `AttributeProperty(default=None)`. The
superpowers design `docs/superpowers/specs/2026-08-09-npc-schedule-design.md`
slices the NPC-schedule feature into a data-model change and a runtime change.
This change is the data model: the rulebook templates, the per-NPC storage
contract, validation, and startup synchronization. Nothing here moves NPCs,
changes clock settlement, or gates interactions — the companion
`npc-schedule-runtime` change consumes this model.

The project is unreleased with zero users; no backward compatibility or
migration is required.

## Goals / Non-Goals

### Goals

- Define the immutable role-template data (`rulebook/npc_schedules.yaml`).
- Define the two valid `npc.db.schedule` storage shapes (template reference with
  overrides, or a full custom entry list).
- Validate entries rigorously with named errors — bad schedules are rejected at
  write/load time, never silently accepted.
- Provide an idempotent startup synchronization pass.
- Declare the `npc.db.schedule_state` attribute contract the runtime writes.

### Non-Goals

- No clock settlement, no movement, no interaction gating (runtime change).
- No per-NPC schedule authoring through the import schema.
- No weekly or multi-day cycles (daily repetition only).
- No changes to combat, quest, economy, or dialogue behavior.

## Decisions

### D1: Templates live in a rulebook YAML, referenced per NPC, with a full-custom escape hatch

`world/rules/rulebook/npc_schedules.yaml` defines role templates as ordered
entry lists; an NPC references one with optional `overrides`, or stores a full
custom `entries` list for special NPCs.

- Alternatives: (a) pure per-NPC attribute schedules with no shared templates —
  rejected: duplicates the same data per NPC and misses the D9 "balance is
  data" convention; (b) frozen-dataclass lore registries — rejected: schedule
  templates are gameplay tuning data like combat tables, which the project
  keeps in `rulebook/` YAML.
- Why: one authored template serves many NPCs of the same role; special NPCs
  are not forced into a template shape.

### D2: One unified entry shape with per-kind required fields

Every entry is `{tick_offset, kind, ...}` with `kind in {move, state}`; a
`move` entry requires `target` (stable key or dbref override), a `state` entry
requires `state`. `tick_offset` is `0 <= tick_offset < day_seconds` (resolved
through the existing clock day math) and entries repeat every world day.

- Alternatives: separate move and state entry types — rejected: the superpowers
  design's S1 decision is one model, one settlement path; field presence per
  kind enforces the distinction.
- Why: the runtime settles one shape; a storekeeper retiring to the back room
  and a guard resting at noon differ only in which fields are filled.

### D3: Strict, named validation at assignment and at consumption

Entry validation rejects: unknown template key, non-list entries, unknown
`kind`, missing/extra fields per kind, non-integer or out-of-day `tick_offset`,
oversized entries, unknown `default_state` vocabulary, and malformed
`db.schedule` shapes (bad schema_version, both-shapes-present, non-dict).
Validation failures raise named errors at the sole assignment API
(`set_npc_schedule`) and at consumption; the startup sync degrades that NPC to
"no schedule" with a bounded diagnostic and never blocks startup. Because
`NPC.schedule` is a bare `AttributeProperty` today, the model does not promise
write-time rejection for arbitrary direct attribute writes — the contract is a
validated parser that rejects at assignment and consumption, plus the startup
sync treating any malformed stored value as "no schedule".

- Alternatives: tolerant parsing with best-effort defaults — rejected: a broken
  schedule must surface loudly in development, and silently skipping could
  strand an NPC mid-journey later.
- Why: the runtime depends on a trustworthy model; validation is the first
  gatekeeper in the pipeline (blueprint-style data discipline).

### D4: Template overrides are a shallow per-entry merge

`overrides` replaces whole entries by index (bounded count) or by entry id;
fields not mentioned in an override entry keep template values. Overrides that
reference a non-existent entry index reject.

- Alternatives: deep field-level merge — rejected: more surface area than the
  first consumer needs, harder to validate; a full custom `entries` list exists
  for genuinely different NPCs.
- Why: overrides cover the common "same role, different post/state" case with a
  small, checkable rule.

### D5: Startup sync is idempotent and shared with the runtime's needs

The sync pass loads and validates the rulebook, confirms every NPC's stored
schedule shape (repairing nothing — rejection means "no schedule"), and
confirms the persistent `schedule` tag on every schedule-bearing NPC so the
runtime's tag query finds them. Sync failures log and degrade.

- Alternatives: no startup pass; runtime scans all NPCs on every settlement —
  rejected: expensive and undeclared; the pattern follows `sync_guard_npc()`.
- Why: one authoritative load point keeps template validation and index
  construction deterministic and testable.

### D6: One validated assignment API owns schedule writes and freshness

`set_npc_schedule(npc, schedule)` is the sole writer of `npc.db.schedule`. It
validates the schedule, records `effective_from_tick` (the current world tick
at assignment), and maintains the `schedule` tag. Settlement only fires
occurrences with `due_tick >= effective_from_tick`, so a schedule assigned
mid-day never replays entries whose due moment already passed, and NPCs spawned
or reassigned after startup are always found (no stale index, no fallback
scan).

- Alternatives: direct `npc.db.schedule` writes with a startup-only index —
  rejected: rubber-duck review found post-startup NPCs would be permanently
  missed and mid-day assignment would replay past events.
- Why: one write path with provenance and freshness makes settlement behavior
  deterministic and testable.

## Risks / Trade-offs

- [Template YAML drifts from consumer expectations] → Validation at load with
  named errors; registry tests lock the schema (one test per rule, project
  convention).
- [Override merge semantics surprise authors] → Index-based replacement only,
  documented in the rulebook; tests cover merge and rejection cases.
- [`tick_offset` edge cases at day boundary] → Validation enforces the half-open
  `[0, day_seconds)` range; runtime boundary arithmetic is that change's
  concern.
- [Very large custom entry lists bloat `db.schedule`] → Bounded entry count in
  validation.

## Migration Plan

No migration. Existing NPCs have `db.schedule = None`, which the model treats
as "no schedule" — the sync pass is a no-op for them. The unreleased-project
rule applies: no compatibility layers.

## Open Questions

- None blocking. The exact bound constants (max entries, max override count,
  max template count) are decided during tasks/implementation with the project
  convention of rulebook-adjacent constants; the runtime change owns `target`
  key resolution and `schedule_state` writing.
