# Generated Quest Named-NPC Portraits — Design

**Date:** 2026-08-09
**Status:** Approved
**Scope:** The deferred portrait-policy field on quest blueprints — generated quests can spawn
named NPCs with unique portraits, with story-driven identity and age.

This document is a slice of `docs/superpowers/specs/2026-08-02-webclient-art-portrait-ui-design.md`
§1 amendment ("Making generated quests *themselves* spawn named NPCs with unique portraits is
deferred: it requires an optional per-NPC portrait-policy field on
`QuestBlueprint`/`StageSpawnRequirement`"). Where this document conflicts with the art-portrait
design or the master design, those documents win unless this document explicitly amends them.

---

## 1. Product Context

`art-assets` delivered the deterministic portrait machinery: `_schedule_occupant_portraits`
(`world/quests/scene_builder.py:236-257`) schedules a unique-portrait ensure for any spawned
occupant carrying `db.portrait_policy` with `mode == "named"`; `character_subject_for()`
(`world/art/subjects.py:89-112`) derives the subject from that policy; the adult gate
(`world/art/adult.py`) re-checks `age >= 18` and `apparent_age >= 18` immediately before enqueue;
and the internal sd-webui client (`world/art/sd_worker.py`) renders the portrait prompt from the
deterministic `character_description()` output plus the prompt library. Today's role-based scene
NPCs carry no policy and resolve to no portrait.

This change supplies the missing field: quest blueprints may declare portrait identity and
story-driven characterization (name, age) per spawned occupant, and the SceneBuilder spawn path
applies them. The art layer needs no changes — it consumes the policy exactly as designed.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| V1 | **Optional characterization fields flow through the whole pipeline**: `BlueprintNpcReq` (scenario-director) → `QuestBlueprint` validation → `StageSpawnRequirement` (compile) → SceneBuilder spawn. | Every layer is a data gatekeeper; a bad blueprint is rejected before it touches the DB. |
| V2 | **Identity is authored by the LLM and format-validated deterministically.** The blueprint may carry `display_name`, and `portrait: {stable_key}`; validation: `stable_key` non-empty, no colon, bounded; `display_name` bounded text; content is not reviewed (same trust model as speech). | Owner decision: names are presentation identity, not world state; the anti-hallucination rule does not extend here. |
| V3 | **Age is story-driven, race-bounded, and adult-gated.** `npc_req` may carry `age` / `apparent_age` (exact integers, paired or absent); both must be integers with `18 <= v` and `v <=` the race's `RaceProfile.lifespan` upper bound (resolved from the NPC tier's `race_key` — human ≤ 80, beastfolk ≤ 70, elf ≤ 1200). Absent fields default to the deterministic adult baseline 25. | Owner decision: the story's elderly man is a 68-year-old, not a random 25-year-old; lifespan bands come from the lore registry, never copied constants; the adult floor is a code-level invariant that no generative layer can bypass. |
| V4 | **The portrait description stays deterministic.** `character_description(entity, age)` (race label + display name + the story-driven age + style template) is the only content source; with the internal client there is no LLM elaboration stage anywhere in the pipeline. | subjects.py D6 contract unchanged; an LLM-authored description would flow verbatim into the sd-webui prompt with no worker-side buffer. |
| V5 | **No fields → status quo.** Role-based occupants without characterization keep today's no-portrait behavior; the same `stable_key` shares one portrait asset (existing art behavior). | No new rules; the key is identity. |
| V6 | **Master-design scoping note.** §7.2's "the LLM never chooses numbers" rule covers mechanical/balance values (stats, rewards, bands). Characterization fields — `display_name`, `age`, `apparent_age` — are authored by the generative layer like speech, land only after deterministic bounded validation, and can never weaken the code-level adult gate. | Keeps the anti-hallucination line clean without making story-driven characters impossible. |

---

## 3. System Design

### 3.1 Blueprint shape

`npc_req` entry (extended):

```jsonc
{
  "role": "librarian",
  "tier": "civilian",
  "disposition": null,
  "display_name": "莉絲·晨星",           // optional; in-game + portrait description
  "age": 68, "apparent_age": 68,         // optional; paired integers, 18..race lifespan max
  "portrait": { "stable_key": "library_keeper" }  // present => named portrait
}
```

### 3.2 Pipeline

- `world/ai/scenario_director.py`: `BlueprintNpcReq` gains optional `display_name`, `age`,
  `apparent_age`, `portrait_policy`. Schema + semantic validation:
  - `age` and `apparent_age` must appear together; both integers; `18 <= v`; the race bound is
    resolved through `NPC_TIER_REGISTRY[tier].race_key` → `RACE_REGISTRY[race].lifespan` (upper
    bound only; the adult floor is the lower bound, not the lifespan floor).
  - `stable_key` obeys the subject-key rules (non-empty, no colon, bounded, no control
    characters); `display_name` bounded text.
- `world/quests/compile.py`: `StageSpawnRequirement` carries the fields; compile validation
  mirrors the blueprint rules (single source of truth factored into a shared helper).
- `world/quests/scene_builder.py::_spawn_npc`: applies the fields deterministically —
  `npc.db.display_name`, `npc.db.age = npc.db.apparent_age = <validated or baseline 25>`, and
  `npc.db.portrait_policy = {"mode": "named", "stable_key": ...}` when `portrait` is present.
  The existing `_schedule_occupant_portraits` hook picks the occupant up unchanged.

### 3.3 Art layer

No changes. `character_subject_for()`, `character_description()`, the adult gate, the queue, and
the internal sd-webui client all consume the policy and ages exactly as designed.

---

## 4. Integration Points

| Integration | Direction |
|---|---|
| `world/ai/scenario_director.py` | Blueprint schema + validation; template pool may carry portrait fields |
| `world/quests/compile.py` | Field carry-through + mirrored validation |
| `world/quests/scene_builder.py` | Spawn applies display name, ages, portrait policy |
| `world/art/subjects.py`, `adult.py`, `service.py`, `sd_worker.py` | Unchanged (existing seams consume) |
| `world/lore/races.py` / `npc_tiers.py` | Race lifespan bound source |

---

## 5. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| Malformed characterization (bad mode/key/name, unpaired or non-integer or out-of-band age) | Blueprint/compile rejection before the DB |
| Spawn failure | Existing SceneBuilder atomic rejection |
| Art offline | Existing placeholder degrade; never blocks play |
| Age missing (portrait present, no age fields) | Deterministic baseline 25; adult gate passes |
| Same `stable_key` in two quests | Shared portrait (idempotent, no regeneration) |

---

## 6. Testing Strategy

| Area | Method |
|---|---|
| Blueprint | Accept/reject for every malformed case (unpaired age, non-integer, 17, race-lifespan overflow such as elf 1300, colon in key, missing bounds); valid 68-year-old human and 300-year-old elf pass |
| Compile | Field carry-through + mirrored validation |
| Spawn | `db.portrait_policy`, `db.display_name`, `db.age`/`db.apparent_age` set correctly; no fields → nothing set, nothing scheduled |
| Art integration | Named-policy spawn reaches the fake worker with an adult, story-driven description; same-key subjects share one asset; adult gate passes (68, 300) |
| Regression | Existing art-assets / scene-builder suites stay green |
| Traceability | New main requirements annotated with `covers_requirement`; `spec_traceability check` passes |

---

## 7. OpenSpec Slicing

Two sequential per-day changes:

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `blueprint-portrait-policy` | 20 (`scenario-director`), 21 (`scene-builder` compile), 22 (`art-assets`) | Blueprint schema/validation, shared bound helper, compile carry-through, template pool update, unit tests |
| 2 | `spawn-named-portraits` | 1 | Spawn application (name/ages/policy), art integration tests, regression |

---

## 8. Out of Scope

- LLM-authored portrait descriptions or mechanical values (V3/V4).
- Per-instance portrait uniqueness (the key is identity; sharing is intended).
- Persistent NPC identity across quest regeneration (the portrait key provides the identity face).
- The stale "external worker" wording left in the art-portrait focused design (a separate doc
  cleanup, optionally folded into change 2).
- Age affecting anything beyond portrait description and canonical attributes in this change
  (dialogue/persona use is owned by the persona-dialogue design).

---

## 9. Open Questions Carried Forward

- None blocking. Whether `apparent_age` should ever intentionally differ from `age` (a visibly
  younger or older face) is supported by the paired-fields shape but not exercised; a future
  change may decide a policy for divergence.
