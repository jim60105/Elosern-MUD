# creation-persona-persistence

## Why

The generative-character-concept change lets players complete creation from an LLM-proposed
concept, but nothing persists the proposal's persona: `world/rules/character_creation.py` never
writes `entity.db.persona`, the wizard draft has no persona slot, and the WebClient creation
surface has no concept entry. Created characters (as opposed to imported ones) would permanently
lack the persona that the PersonaStore handler and dialogue injection consume. This change
persists the validated persona at activation, adds the server-owned concept draft, and exposes
the concept entry through the WebClient creation panel.

## What Changes

- Extends the wizard draft with a server-owned concept stage holding the validated proposal values
  (race, subrace, allocations) plus an optional persona block (`personality`, `life_story`,
  `habit`), accepted only from the deterministic concept-proposal path; a custom save whose race
  differs from the concept draft's race clears the persona block.
- Adds a deterministic concept-apply service that stores the concept draft with a draft
  fingerprint compare-and-swap, so a late generative response can never overwrite a draft modified
  by another session or entry while the LLM call was in flight.
- `activate_player_character()` persists the draft's persona block into `entity.db.persona` in the
  import-card shape (all six keys; empty containers as `{}`) inside the existing all-or-nothing
  activation transaction; a persona write failure rolls back activation; drafts without a persona
  block write nothing.
- Adds the fifth creation action `creation.concept` (payload exactly `{concept}`, bounded) and the
  creation-panel concept field; the adapter runs the same guarded pipeline and fills the concept
  draft. **Persona content is never rendered**: the panel shows only the finite controls derived
  from the draft plus a non-content indicator that a background was generated, preserving the
  creation presentation's no-persona-exposure contract.
- Retro-fits the Telnet `character concept` flow to save the concept draft before activation, so
  Telnet and WebClient share the same deterministic apply service and both persist persona.

## Capabilities

### New Capabilities
- `creation-persona-persistence`: the server-owned concept draft with fingerprint-protected
  apply, activation-time persona persistence in the import-card shape, and the WebClient
  `creation.concept` adapter sharing the guarded pipeline.

### Modified Capabilities
- `webclient-character-creation-ui`: the wizard draft gains the concept stage and optional
  persona block; the creation action set grows to five with `creation.concept`; the panel gains
  the concept field while persona content stays unexposed.

## Impact

- `world/rules/character_creation.py` + `world/rules/creation_wizard.py`: concept draft stage,
  apply service with fingerprint compare-and-swap, activation persona write (sole writer for
  creation-generated persona).
- `world/imports/loader.py`: untouched (import-time verbatim storage remains).
- `web/webclient/actions/creation_actions.py`: `creation.concept` adapter (bounded payload, actor
  from session, guarded pipeline, draft save, snapshot refresh).
- `web/webclient/presentation/` + creation panel JS: concept field and draft-form wiring; persona
  content never shipped to the browser.
- `commands/character_creation.py`: concept flow routed through the concept draft.
- Command-docs contract: unchanged (the command surface is owned by generative-character-concept;
  this change alters the internal flow, not the syntax).
