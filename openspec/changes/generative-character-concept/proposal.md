# generative-character-concept

## Why

The creation wizard is fully deterministic, and the `character_creation.system` prompt key has
been registered and validated since the prompt-library change but has no runtime consumer — the
registry comment calls it a forward-declared seam. The generative-character-concept design
(`docs/superpowers/specs/2026-08-09-generative-character-concept-design.md`) activates it as a
concept-to-proposal layer: a player describes a character idea and the LLM maps it onto real
registry keys with a persona draft, so creation is story-driven while every number stays
deterministic.

## What Changes

- Adds a `character concept <構想>` command (aliases 構想) on the pending-character command set:
  it runs the new guarded generative layer, presents the validated proposal (race, subrace,
  allocations, suggested skills, and a persona preview), interactively collects the display name
  and both ages through the deterministic adult gate, and activates through the ordinary path.
- Activates the `character_creation.system` prompt key: the prompt-library registry gains the
  `{concept}` and `{race_catalog}` placeholders and a real runtime consumer.
- Introduces a deterministic proposal contract `{race_key, subrace_key, allocations,
  suggested_skills, persona{personality, life_story, habit}}` whose every key is validated against
  the lore/skill registries and race bands; the LLM chooses no numeric values and no age.
- Registers a new `character_creation` generative layer in the guardrail (layer name, output
  schema, semantic validation, retry-with-error, stable degrade) and wires its idempotent startup
  registration.
- Persona and suggested skills are informational in this change: the Telnet flow presents them as
  a preview. Draft integration, activation-time persona persistence, and the WebClient concept
  adapter are owned by the `creation-persona-persistence` change.
- Keeps the adult gate untouched: age remains player-entered and deterministically validated; the
  proposal carries no age field.

## Capabilities

### New Capabilities
- `generative-character-concept`: the concept-to-proposal layer — the guarded generative
  pipeline, the deterministic proposal validation, the `character concept` command with
  proposal-guided interactive completion, and the stable offline degrade.

### Modified Capabilities
- `character-creation-ux`: the pending-character creation surface gains the `character concept`
  command as an alternative entry into custom creation.
- `prompt-library`: the `character_creation.system` key gains the `concept` and `race_catalog`
  placeholders in its allowlist and stops being a zero-consumer seam.

## Impact

- `world/ai/` (new module): `character_creation` layer — schema, semantic validation, retry,
  degrade; layer name added to `LAYER_NAMES`; idempotent startup registration in
  `server/conf/at_server_startstop.py`.
- `world/prompts/registry.py` + `prompts/character_creation.yaml`: placeholder allowlist and
  template text.
- `world/rules/character_creation.py`: proposal validation reuses `preflight_character_creation`
  checks (no new write path in this change).
- `commands/character_creation.py`: `character concept` command; command-docs contract
  (`docs/game/commands.md`, `command-reference.md`, `tests/test_command_docs.py`) updated.
- No changes to activation semantics, the adult gate, the wizard draft, or the deterministic
  wizard flow; no persona persistence in this change.
