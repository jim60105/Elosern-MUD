# generative-character-concept — Design

## Context

The creation wizard (`world/rules/character_creation.py` + `creation_wizard.py`) is fully
deterministic: preset and custom flows, adult gate, all-or-nothing activation. The prompt library
registers `character_creation.system` (`world/prompts/registry.py`, key `character_creation.yaml`)
and validates it, but no runtime consumer exists — the registry comment marks it a
forward-declared seam. The generative layer set (`world/ai/profiles.py::LAYER_NAMES`) has no
`character_creation` layer, and the guardrail's validator/degrade registration rejects unknown
layers.

The generative-character-concept design
(`docs/superpowers/specs/2026-08-09-generative-character-concept-design.md`) activates the seam as
a concept-to-proposal layer: the player describes a character idea, the LLM maps it onto real
registry keys plus a persona draft, deterministic preflight validates it, and the result guides
the existing creation flow.

**Key constraint discovered during review:** the Telnet `character create` flow is interactive and
activates directly — it never saves a wizard draft (the draft is a WebClient-era staging
mechanism). Therefore this change's command cannot "fill a draft": it presents the proposal and
collects the remaining player-entered fields interactively. Draft integration and persona
persistence belong to the `creation-persona-persistence` change.

Constraints:

- The LLM never chooses mechanical numbers or ages (§7.2 anti-hallucination; the proposal carries
  no age field — the adult gate stays player-entered and deterministic).
- `world/ai/` never writes; the layer proposes, the deterministic wizard validates and activates.
- Prompt text lives only in `prompts/*.yaml`; the prompt-library registry is the placeholder
  contract.
- No backward compatibility or migration (unreleased project).

## Goals / Non-Goals

**Goals:**

- A `character_creation` generative layer registered in the guardrail (layer name, output schema,
  semantic validation, retry-with-error, stable degrade) with idempotent startup registration.
- A deterministic proposal contract validated against the lore/skill registries and race bands.
- A `character concept <構想>` command that presents the proposal and completes the missing
  fields interactively through the adult gate, then activates through the ordinary path.
- Prompt-library activation of `character_creation.system` with `{concept}` and `{race_catalog}`.
- Offline degradation that never touches character or account state.

**Non-Goals:**

- Any wizard-draft changes or draft fill (owned by `creation-persona-persistence`).
- Activation-time persona persistence (owned by `creation-persona-persistence`).
- The WebClient concept adapter (owned by `creation-persona-persistence`).
- Generating names, classes, ranks, or ages (the LLM only maps existing keys; age is never
  delegated).

## Decisions

### D1: New layer name and registration — `character_creation` in `LAYER_NAMES` + guardrail + startup

Add `character_creation` to `world/ai/profiles.py::LAYER_NAMES` (joining narrator,
npc_dialogue, scenario_director, scene_builder), so `default_profiles()` (server/conf/settings.py)
constructs its `LLMProfile` automatically and the guardrail's layer checks accept it. Register the
layer's output schema, semantic validators, and degrade fallback through the existing
`register_semantic_validator` / `register_degrade_fallback` mechanisms, and add an idempotent
`character_creation` registration helper called from `server/conf/at_server_startstop.py::
at_server_start()` — every existing layer is registered there, and a layer missing its startup
hook would be unregistered in production while unit tests that register manually stay green.

- Alternatives considered: reusing an existing layer with a per-call schema. Rejected: the
  guardrail's per-layer registry and `LLM_PROFILES` are the project's swappable per-layer seam
  (D6 of the master design); a distinct creation layer keeps profile tuning independent and the
  degrade fallback honest.

### D2: Proposal contract and deterministic validation

Output contract (exactly these fields):

```jsonc
{
  "race_key": "elf", "subrace_key": "ciaran",
  "allocations": {"atk_phys": 2, "agility": 3},
  "suggested_skills": ["flight"],
  "persona": {"personality": "…", "life_story": "…", "habit": "…"}
}
```

Validation (all deterministic, mirroring `preflight_character_creation`):

- `race_key` / `subrace_key` exist in the lore registries and are compatible (subrace belongs to
  the race).
- `allocations` keys are valid allocation axes and values fall inside that race's bands.
- Every `suggested_skills` key exists in the skill registry.
- `persona` has exactly the three bounded text fields.
- No age field and no numeric field outside `allocations` — rejected (adult gate is the only age
  authority).
- **Any failure — including an invalid persona shape or over-length text — is a whole-proposal
  validation failure**: retry with the appended error; exhaustion degrades to the stable
  unavailable message. Partial proposals (e.g. "accept race but discard persona") never fill any
  state, keeping the accepted-proposal contract exact.

### D3: Prompt and catalog — `{concept}` + `{race_catalog}` placeholders

`prompts/character_creation.yaml` template gains `{concept}` (the player's idea) and
`{race_catalog}` (a bounded, registry-derived brief of valid race/subrace and selectable skill
keys). `world/prompts/registry.py` extends the key's allowlist accordingly. The catalog is
rendered deterministically from `PLAYER_PRESET_REGISTRY` / race and skill registries with a hard
size bound; a broken or missing key degrades the layer exactly as the prompt-library contract
requires (logged warning, layer degrade, startup unaffected).

- Alternatives considered: hardcoding the registry brief inside the template text. Rejected: the
  template would drift from the registries (D9 — balance data as data), and the prompt-library
  contract forbids Python constants.

### D4: Command surface — proposal-guided interactive completion (no draft)

`character concept <構想>` (aliases 構想) on the pending-character command set:

1. Validates the concept input (non-empty, bounded) — no generative call on invalid input.
2. Runs the guarded layer with the injected client (composition-root pattern, mirroring the
   dialogue seams).
3. On a validated proposal, presents the summary — race, subrace, allocations, suggested skills
   (informational), and the persona preview — then interactively collects the display name,
   actual age, and apparent age through the existing prompts and adult gate (the proposal never
   supplies these; the LLM is not the age authority).
4. Builds the ordinary `CharacterCreationRequest` from the proposal values plus the collected
   fields and activates through the existing `_activate` path (the same preflight and
   all-or-nothing activation every flow uses).
5. On degrade, returns 生成不可用，請手動創角 and changes nothing.

The persona preview and suggested skills are presentation only in this change: nothing persists
them. `creation-persona-persistence` adds draft storage and the WebClient surface.

### D5: Offline and failure behavior

LLM offline, timeout, malformed output, or retry exhaustion → stable unavailable message; no
draft, character, or account state changes; the deterministic wizard remains fully usable.
Command-docs contract (`docs/game/commands.md`, `command-reference.md`,
`tests/test_command_docs.py`) is updated in the same change.

## Risks / Trade-offs

- [The LLM may propose a plausible but wrong race/skill key] → Deterministic registry validation
  rejects unknown keys before any state changes; retries append the error.
- [The race catalog may grow beyond prompt bounds] → Hard size bound and deterministic truncation
  strategy in the catalog renderer; validation of the proposal is unaffected.
- [Telnet users lose the generated persona at activation in this change] → Accepted and explicit:
  the persona preview is informational until `creation-persona-persistence` wires draft storage
  and the activation write, at which point the Telnet flow moves through the draft.
- [Adding a layer name to `LAYER_NAMES` changes `LLM_PROFILES` shape] → The profile follows the
  same defaults as other layers; the guardrail degrade path keeps offline play byte-identical.

## Open Questions

- None blocking. Whether the concept field later supports multi-turn refinement is deferred (the
  single-turn guarded pipeline is the seam it would extend).
