# Generative Scene Flavor — Design

**Date:** 2026-08-09
**Status:** Approved
**Scope:** The `scene_builder` LLM profile seam — an asynchronous generative scene-flavor layer
that enriches quest scenes without touching deterministic room descriptions.

This document is a slice of the master design
(`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, §3.1 amendment: "the forward-declared
`scene_builder` LLM profile stays registered and unused as a seam for a future generative
scene-flavor layer"). Where this document conflicts with the master design, the master design wins
unless this document explicitly amends it.

---

## 1. Product Context

The SceneBuilder is the deterministic requirements→prototype→spawn materializer
(`world/quests/scene_builder.py`); it sets `room.db.desc` from `requirement.scene_sentence` or the
archetype's `scene_sentence`. The `scene_builder` LLM profile is registered in
`world/ai/profiles.py` (`LAYER_NAMES`) but has no consumer — the master design reserves it as a
seam for a future generative scene-flavor layer.

This change activates that seam: when a quest scene spawns, an asynchronous generation produces a
flavor paragraph (atmosphere and sensory description) stored separately from `desc`, so the
deterministic description is never overwritten and the LLM is never on the arrival path. With the
LLM offline the rooms simply have no flavor; play is unchanged.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| B1 | **Separate `room.db.scene_flavor` attribute.** `look` shows the deterministic `desc` first and the flavor paragraph after it; generated content never overwrites `desc`. | Owner decision: `desc` is deterministic fact (the scene sentence); flavor is optional dressing. |
| B2 | **Post-spawn asynchronous generation.** Scheduled after the spawn transaction commits (fire-and-forget, never blocking arrival); on completion the deterministic core writes the flavor and pushes it to players currently in the room; idempotent (an existing flavor never regenerates); failure means no flavor (logged only). | Arrival is never delayed by the LLM; present players see the update immediately; no retry loops. |
| B3 | **Bounded-context prompt.** Inputs are the archetype scene sentence, quest name/type, room name, and region; the output must describe atmosphere/senses only — no fabricated entities, numbers, or world state; length is bounded (50–200 characters, configurable). | Anti-hallucination (§7.2 lineage); the context is enough for the flavor to echo the quest without inventing facts. |
| B4 | **A mechanical "no digits" gate.** Output containing any digit character is rejected (retry → exhaustion degrade to no flavor). | "No fabricated numbers" lands as a deterministic rule, not LLM discretion. |
| B5 | **`world/ai` only proposes; the deterministic core applies.** `world/quests/scene_builder.py` — the scene-lifecycle owner — performs the write. | The single-writer boundary holds; SceneBuilder is already the deterministic materializer. |

---

## 3. System Design

### 3.1 Prompt

New `prompts/scene_builder.yaml`:

- `scene_builder.system` with placeholders `{scene_sentence}`, `{quest_context}`, `{room_name}`,
  `{region}`; registered in `world/prompts/registry.py` with the matching placeholder allowlist.
- Output is plain text (flavor paragraph); length and digit validation live in the guardrail.

### 3.2 Generative layer

A new `world/ai/` module using the existing `scene_builder` profile:

- Guardrail registration: output schema (bounded text), semantic validation (50–200 characters;
  **any digit → reject**), retry with appended error, exhaustion → stable degrade (no flavor).
- Input context is assembled on the deterministic side (archetype / quest / room / region
  fragments from the SceneBuilder).

### 3.3 Scheduling and write

`world/quests/scene_builder.py`:

- After the spawn transaction commits, schedule one flavor generation for scenes with a
  `scene_sentence` context.
- Completion callback: write `room.db.scene_flavor` (idempotent), then push the text to players
  currently present in that room (text/OOB line; a later `look` shows it too).
- Failure / offline / timeout: bounded diagnostic log; `scene_flavor` stays `None`; players see
  only the deterministic `desc`.

### 3.4 look rendering

The flavor paragraph is inserted after `desc` and before other blocks when present. The WebClient
look text path shares the same pipeline (plain text; a structured panel is a future seam).

---

## 4. Integration Points

| Integration | Direction |
|---|---|
| `prompts/scene_builder.yaml` (new) + `world/prompts/registry.py` | Placeholder contract |
| `world/ai/profiles.py` | `scene_builder` profile activated (slot already exists in `LAYER_NAMES`) |
| `world/ai/` (new layer module) | Guardrail registration, digit gate, retry/degrade |
| `world/quests/scene_builder.py` | Post-spawn scheduling, `scene_flavor` write, idempotency, push |
| `look` path | Flavor paragraph rendering (Telnet + `explore.look` shared pipeline) |

---

## 5. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| LLM offline / timeout / retry exhausted | No flavor (logged); deterministic `desc` only; play unchanged |
| Output contains digits / overlong | Reject → retry → exhaustion degrades |
| Room already has a flavor | Idempotent: no regeneration |
| Player leaves before completion | The write still completes; the flavor is visible on a later `look` (no chasing push) |
| Other services offline | Irrelevant — this layer is independent |

---

## 6. Testing Strategy

| Area | Method |
|---|---|
| Generative layer | `FakeLLMClient` replays: valid flavor, digit rejection, overlong rejection, offline degrade; retry flow |
| Scheduling/write | Post-spawn scheduling once; idempotency on re-entry; write executed by the deterministic core (`world/ai` zero-write assertion) |
| look rendering | `desc` + flavor paragraph order; no flavor → no paragraph; Telnet / `explore.look` parity |
| Push | Present players receive it; absent players don't; re-look shows it |
| Traceability | New main requirements annotated with `covers_requirement`; `spec_traceability check` passes |

---

## 7. OpenSpec Slicing

Two sequential per-day changes:

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `scene-flavor-layer` | 17 (`llm-client`), prompt-library, 21 (`scene-builder`) | Prompt file + registry, generative layer, digit/length gates, profile activation, FakeLLM tests |
| 2 | `scene-flavor-apply` | 1, 23d (`explore.look`) | Post-spawn scheduling, write + idempotency, present-player push, look rendering, integration tests |

---

## 8. Out of Scope

- Overwriting `desc` (forbidden by B1).
- Regeneration per entry (idempotent by design).
- Player identity/state in the prompt (B3 bounded context).
- Art-queue integration (flavor is text, not an art job).
- A structured WebClient flavor panel (plain-text paragraph; seam preserved).

---

## 9. Open Questions Carried Forward

- None blocking. Whether flavor should later vary by time of day or player presence is a deferred
  decision; the bounded-context prompt and idempotent write are the seams it would extend.
