# Profession Registries and Declarative Service Hosts — Design

**Date:** 2026-09-05
**Status:** Approved (brainstorming session 2026-09-05); first of three sequenced designs
(R3 → R2 → R1). Consumed downstream by the service-anchoring design
(`2026-09-05-service-anchoring-design.md`) and the companion-possession design
(`2026-09-05-companion-possession-design.md`).
**Scope:** Making "profession" a first-class authored game datum: a rulebook YAML profession
registry that assembles service components, schedule templates, and tier baselines at NPC
construction time; an optional `profession` field on imported character records; and converting
the guild/shop service hosts from hardcoded sync fixtures to a fully declarative host roster.

---

## 1. Product Context

Today the codebase defines no profession entity. "Profession-like" sharing is scattered across
three unrelated mechanisms:

1. **Capability components** (`typeclasses/components.py`: `GuildStaff`, `GuildExaminer`,
   `Merchant`, `ScriptedDialogue`) — self-described as capability markers + service-data
   holders. The shared per-profession rules live in import-time registries keyed by
   `shop_key`/`branch_key`/`service_id`, not by any profession datum.
2. **Schedule role templates** (`world/rules/npc_schedules.py::ScheduleTemplate`) — the only
   existing structure keyed by a "role" name and shared by many NPCs.
3. **Narrative role strings** (`world/ai/scenario_director.py::BlueprintNpcReq.role`) — free
   text fed to the LLM as flavor only.

The concrete pain: `world/rules/guild_economy.py::sync` hardcodes every service host — name,
title, room, component combination — in Python. Adding or re-theming a shop or guild clerk
requires code changes, and the user's authored-content workflow (AI-assisted edits to YAML
rulebooks and JSON import records) has no place to declare "this NPC is a merchant" or "this
NPC is a confessor" at all.

Forward requirements this design unblocks (specified in the sibling documents, stored but not
read here):

- `service_binding: person | place` — whether a companion NPC's services travel with them
  (service-anchoring design).
- Companion possession needs schedule/autonomy silencing keyed on the same component facts
  (possession design).

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Profession is an assembly-time blueprint, never a runtime lens.** After construction, the authoritative state is the NPC's component instances and attributes; runtime gates read component fields, never the profession table. | Preserves the existing single-writer / read-the-declaration pattern (economy, examiner, and quest gates need zero indirection), keeps per-NPC overrides natural, and avoids retroactive effects when YAML changes. |
| D2 | **The registry is a rulebook YAML** (`world/rules/rulebook/professions.yaml`), validated fail-fast against the immutable lore registries at load, mirroring `guild_config.py`. | Matches the project's authored-content split: tunable/structural data in YAML, immutable worldview in frozen Python registries. The user's future content work stays YAML + validation-rerun. |
| D3 | **Blueprint-materialized scenario NPCs keep free-text `role`.** AI-generated scene NPCs are story-only and carry no functional profession. | Explicitly decided: no profession validation, no assembly, for the scenario-director path. |
| D4 | **`profession` on import records is optional.** Absent ⇒ byte-identical current behavior. Present ⇒ must name a registry key or the whole batch is rejected. | No released users, no migration burden; the conservative default keeps every existing record valid. |
| D5 | **Explicit per-record `components` override the profession blueprint** for the component set; the blueprint still supplies schedule template and tier unless separately overridden. | Authored exceptions (a legendary wandering merchant) stay per-NPC data, not code. |
| D6 | **`default_binding` is stored but not read in this change.** The profession row carries `service_binding: person | place` per component, validated only for well-formedness. | The anchoring gate that consumes it is the service-anchoring design's scope; storing early avoids a second schema bump, reading early would weld R3 to R2's undecided semantics. |
| D7 | **The service-host roster becomes declarative data.** `guild_economy.yaml` gains a `service_hosts` section; sync becomes a pure interpreter of the list. | Directly answers the authored-content requirement: opening a new shop or clerk is a YAML edit, zero Python. |
| D8 | **Reuse identity stays the component `service_id` anchor**, never the display name; the one-live-host-per-anchor invariant and `ServiceAnchorIntegrityError` fail-closed behavior are preserved verbatim. | Existing design D3 of the guild-economy line; renaming a host must never orphan it. |
| D9 | **Sync converges to the roster** (no back-compat): surplus legacy hosts are cleaned via the existing `_cleanup_legacy_service_hosts` precedent; the roster is authoritative. | The project policy forbids compatibility layers pre-release. |
| D10 | **Player `guild_rank` stays out of scope.** The PC rank ladder is a progress system orthogonal to NPC professions. | Conflating the two meanings of "profession" would poison both. |

## 3. `professions.yaml` Schema

```yaml
schema_version: 1
professions:
  - key: merchant
    components:
      - { type: merchant, default_binding: place }
    schedule_template: merchant_day      # null = no schedule
    default_tier: null                   # race-baseline tier key, or null
  - key: guild_staff
    components:
      - { type: guild_staff, default_binding: place }
      - { type: scripted_dialogue, default_binding: place }
    schedule_template: guard
    default_tier: null
```

Loader `world/rules/profession_config.py` follows the `guild_config.py` family: frozen
dataclasses, whole-file batch validation, `ProfessionConfigError` with named messages. Load-time
cross-validation:

- `components[].type` ∈ the known service component type set (component name strings from
  `typeclasses/components.py`);
- `components[].default_binding` ∈ `{person, place}` (stored, not consumed — D6);
- `schedule_template` is null or exists in the schedule rulebook;
- `default_tier` is null or a known tier key;
- `key` values unique; `schema_version` present and exact.

The shipped initial professions: `merchant`, `guild_staff`, `guild_examiner` (replicating today's
hardcoded component combinations exactly, so the sync conversion is behavior-neutral).

## 4. Import Records

`world/imports/schema.py` accepts optional `profession: str | null`. Loader behavior when
present:

1. Assemble components from the profession blueprint (skip any the record explicitly lists —
   D5; component kwargs such as `shop_key`/`branch_key`/`service_id` still come from explicit
   record fields, never invented by the blueprint);
2. Apply `schedule_template` via the existing `set_npc_schedule` seam unless the record carries
   its own schedule;
3. Pass `default_tier` into the race-baseline call unless the record overrides traits explicitly.

Validation reuses the batch's all-or-nothing semantics: an unknown profession key rejects the
whole batch with a named issue, same as every other schema violation.

## 5. Declarative Service-Host Roster

`guild_economy.yaml` gains:

```yaml
service_hosts:
  - name: <authored NPC name>
    title: <authored npc_title>
    profession: merchant
    anchor_room: <room tag>
    service_id: general_store_capital
    shop_key: general_store
```

(`anchor_room` is authored here but only *interpreted* as "where the host is placed" in this
change; its anchoring semantics arrive with the service-anchoring design.)

`world/rules/guild_economy.py::sync` becomes an interpreter:

- For each roster row: find-or-create the host anchored on `service_id` (D8), set location to
  `anchor_room`, ensure adult identity and race baseline exactly as today, and assemble
  components through the profession blueprint (replacing the hardcoded `component_specs`).
- The single-host invariant, idempotent sync, `ServiceAnchorIntegrityError`, and the
  observability events (`guild_service_host_created` etc.) are retained; the event context gains
  `profession`.
- Surplus live hosts claiming a `service_id` absent from the roster are removed via the
  legacy-cleanup precedent (D9).

## 6. Error Handling & Failure Modes

| Case | Behavior |
|---|---|
| Unknown component type / template / tier key in YAML | Load-time `ProfessionConfigError`, named field, nothing cached |
| Duplicate profession key | Load-time named rejection |
| Import record with unknown `profession` | Batch rejected with issue on the record |
| Import record with `profession` + explicit `components` | Explicit wins (D5); blueprint supplies only schedule/tier defaults |
| Roster row naming unknown profession / room tag | Sync fails closed with named integrity error (mirrors `ServiceAnchorIntegrityError` posture) |
| Roster shrunk (row removed) | Legacy-cleanup path deletes the orphan host on next sync (party purge hook already unwinds any bindings) |

## 7. Testing

- Pure `unittest`: YAML validator matrix (each named rejection above), blueprint→assembly
  resolution order (explicit-wins), roster validation.
- `EvenniaTestCase`: sync idempotence (double sync neither recreates nor renames hosts),
  roster-driven create/converge, per-row component assembly equals the old hardcoded specs
  (behavior-neutrality pin), surplus-host cleanup.
- Import loader: profession assembly result vs. explicit-override precedence; absent-profession
  byte-identity.
- No LLM/network dependencies anywhere. Shards manifest updated for every new module.

## 8. Non-Goals

- Reading `default_binding` anywhere (service-anchoring design owns that).
- Runtime profession queries, NPC-panel profession display, presentation surfaces.
- Professionizing AI blueprint NPCs (D3).
- Any possession mechanics (companion-possession design).
- New profession content beyond the three replicated service professions.

## 9. OpenSpec Change Mapping

This design lands as changes **R1 `profession-rulebook-registry` → R2
`profession-import-assembly` → R3 `declarative-service-hosts`** (numbers below), plus the
anchoring/presentation/possession line owned by the sibling designs:

| # | Change | Source |
|---|---|---|
| 1 | `profession-rulebook-registry` | this design §3–§4, D1–D6 |
| 2 | `profession-import-assembly` | this design §4, D4/D7 |
| 3 | `declarative-service-hosts` | this design §5, D7–D9 |
| 4 | `service-anchoring-gate` | service-anchoring design D1–D4 |
| 5 | `service-anchor-presentation-silence` | service-anchoring design §4, D5–D7 |
| 6 | `companion-possession-rules` | companion-possession design D1–D8 |
| 7 | `companion-possession-transition` | companion-possession design D3/D7, §3/§5 |
| 8 | `companion-possession-webclient` | companion-possession design D9/D10 |

**Implementation batch order: fully serial `1 → 2 → 3 → 4 → 5 → 6 → 7 → 8`.**
Reviewed in the pre-handoff rubber-duck pass: every candidate parallel wave was rejected — 3
consumes 2's assembly helper; 4 reads 3's roster anchor fields and shared assembly; 5 renders 4's
verdict vocabulary on the same gate module; 6 needs 5's `schedule_silenced`; the possession line
(7, 8) layers on 6. There is no safe overlap; `tmp/propose.md`'s one-at-a-time rule matches the
graph. Sizing notes in each proposal record the intra-change landing order if a slice exceeds one
engineer day.
