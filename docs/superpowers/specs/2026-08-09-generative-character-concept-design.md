# Generative Character Concept — Design

**Date:** 2026-08-09
**Status:** Approved
**Scope:** The `character_creation.system` prompt seam — a generative character-proposal layer on
top of the deterministic creation wizard.

This document is a slice of the master design
(`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, §7 anti-hallucination rules and the
`character_creation.system` forward-declared prompt seam in `prompt-library`). Where this document
conflicts with the master design, the master design wins unless this document explicitly amends it.

---

## 1. Product Context

The deterministic creation wizard (`world/rules/character_creation.py` + `creation_wizard.py`)
supports preset and custom flows; everything about it is deterministic. The prompt library
registers `character_creation.system` (`world/prompts/registry.py`) and validates
`prompts/character_creation.yaml`, but no runtime consumer exists — the registry comment calls it a
forward-declared seam ("the character-creation feature is deterministic until its generative task
here").

This change activates the seam as a **concept-to-proposal layer**: the player describes a character
idea, the LLM maps it onto real registry keys (races, subraces, allocations, suggested skills) and
drafts a persona; deterministic preflight validates the proposal before it fills the custom wizard
draft, and the player confirms through the existing activation path. The LLM never chooses numbers
— the same anti-hallucination rule SceneBuilder uses.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| C1 | **Proposal mapping.** The player's concept maps onto real registry keys (`race_key`, `subrace_key`, `allocations`, `suggested_skills`); the LLM chooses no numeric values. | Extends the §7.2 "LLM never chooses numbers" rule to creation. |
| C2 | **Persona draft persists at activation.** A validated persona draft (personality / life_story / habit text) is written into `entity.db.persona` by `world/rules/character_creation.py` — the sole writer for creation-generated persona — in the same shape as import cards. | Created characters gain persona, so the PersonaStore handler (persona-dialogue design) applies to them; `world/rules` is the writer package, so the single-writer boundary holds. |
| C3 | **Age is never delegated.** The adult gate stays player-entered and deterministically validated; the LLM proposal carries no age field. | The adult invariant is non-negotiable and never delegated to a generative layer. |
| C4 | **Dual surface.** A new `character concept <構想>` command (aliases 構想) and the WebClient creation-panel concept field share one guarded pipeline. | Telnet and browser get the same capability (browser-first, Telnet-parity convention). |
| C5 | **Offline degradation.** With the LLM offline or retry-exhausted, the feature returns a stable Traditional Chinese message (生成不可用，請手動創角) and the deterministic wizard is untouched. | The offline-playability acceptance criterion holds unchanged. |

---

## 3. System Design

### 3.1 Prompt

`prompts/character_creation.yaml` + `world/prompts/registry.py`:

- `character_creation.system` gains two allowed placeholders: `{concept}` (the player's idea) and
  `{race_catalog}` (a bounded registry brief listing real race/subrace and selectable skill keys).
- The output contract is a JSON object:
  `{race_key, subrace_key, allocations{...}, suggested_skills[], persona{personality, life_story, habit}}`.

### 3.2 Generative layer

A new `world/ai/` layer module (structure mirroring `npc_dialogue.py`):

- Registered in the guardrail with an output jsonschema, semantic validation, retry-with-error, and
  a stable degrade fallback.
- Deterministic validation of the proposal:
  - `race_key` / `subrace_key` exist in the lore registries;
  - `allocations` fall within that race's bands (reusing `preflight_character_creation`'s checks);
  - `suggested_skills` keys exist in the skill registry;
  - `persona` has exactly the three text fields (type-checked; contents never inspected).
- Invalid proposals retry with the error message appended; exhaustion degrades to the stable
  unavailable message without filling any draft state.

### 3.3 Command and draft

`commands/character_creation.py` gains `character concept <構想>`:

1. Runs the guarded pipeline with the injected client (composition-root pattern);
2. On a validated proposal, fills the existing custom-wizard draft state (same storage the custom
   flow uses);
3. The player may edit any field, then continues through the ordinary custom flow and activation.

### 3.4 Activation persistence

`activate_player_character()` writes the validated persona dict into `entity.db.persona` verbatim
(in the import-card shape) when the draft carries one; drafts without persona write nothing. The
import path (`world/imports/loader.py`) is unchanged.

### 3.5 WebClient

The creation panel gains a concept text field; a new `creation_actions` adapter runs the same
pipeline (actor from the session) and fills the draft form for confirmation.

---

## 4. Integration Points

| Integration | Direction |
|---|---|
| `world/prompts/registry.py` + `prompts/character_creation.yaml` | Placeholder allowlist + output contract |
| `world/ai/` (new layer) | Guardrail registration, schema, retry/degrade |
| `world/rules/character_creation.py` | Proposal validation reuse, draft fill, activation persona write |
| `world/lore/player_presets.py`, races, skills | Bounded `race_catalog` rendering |
| `commands/character_creation.py` | `character concept` command; command-docs contract updated |
| `web/webclient/actions/creation_actions.py` | Concept adapter (panel seam) |

---

## 5. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| LLM offline / retry exhausted | Stable unavailable message; wizard unchanged |
| Proposal references unregistered keys / out-of-band allocations | Retry; exhaustion degrades without filling the draft |
| Persona text overlong / malformed | Truncated or discarded (per validation); the rest of the proposal proceeds |
| Mid-flow disconnect | Draft is persisted by the existing mechanism; reconnect resumes |
| Activation failure | Existing all-or-nothing behavior; persona never half-written |

---

## 6. Testing Strategy

| Area | Method |
|---|---|
| Generative layer | `FakeLLMClient` replays: valid proposal fills the draft; unregistered race/skill rejects; out-of-band allocations reject; malformed persona discarded; offline degrade |
| Command | `character concept` success/failure/offline; command-docs drift contract green |
| Activation | Persona written to `entity.db.persona` in import-card shape; no-persona draft writes nothing; adult gate regression (age 17/17 rejected) |
| Guardrail | Malformed output leaves the DB untouched |
| Traceability | New main requirements annotated with `covers_requirement`; `spec_traceability check` passes |

---

## 7. OpenSpec Slicing

Two sequential per-day changes:

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `generative-character-concept` | 17 (`llm-client`), prompt-library, 8/23g (wizard) | Prompt placeholders, output schema, layer registration, deterministic validation, `character concept` command, degradation tests |
| 2 | `creation-persona-persistence` | 1 | Draft integration, activation persona write, WebClient concept adapter, tests |

---

## 8. Out of Scope

- Generating names, classes, or ranks (the LLM only maps existing keys).
- Generating numeric values (all numbers stay deterministic).
- Using persona in other generative layers (the persona-dialogue design owns dialogue injection).
- Rewriting import-card persona (the import path is unchanged).

---

## 9. Open Questions Carried Forward

- None blocking. Whether the concept field later accepts free-form follow-up refinement turns
  (multi-turn concept editing) is a deferred decision; the guarded single-turn pipeline is the
  seam it would extend.
