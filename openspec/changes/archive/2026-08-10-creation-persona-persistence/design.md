# creation-persona-persistence — Design

## Context

The generative-character-concept change (dependency) adds the guarded `character_creation` layer
and the Telnet `character concept` command, which currently presents the proposal and activates
directly — persona and suggested skills are preview-only. This change supplies the destinations:
a server-owned concept draft (proposal values + persona block), an activation-time persona write,
and the WebClient concept surface.

Key facts verified during review:

- The Telnet `character create` flow is interactive-then-activate and never saves a draft; the
  wizard draft (`creation_wizard.py`, `character.db.creation_draft`) is the WebClient-era staging
  mechanism (`save_custom_draft` requires a complete request including name and both ages).
- The creation presentation contract forbids exposing persona: the main
  `webclient-character-creation-ui` spec requires the panel to render no persona/import field.
- `activate_player_character()` runs one `transaction.atomic()` block; `world/imports/loader.py`
  is the import-time persona writer and must stay unchanged.

Constraints:

- `world/rules/character_creation.py` is the sole writer for creation-generated persona.
- The persona write must not weaken activation's all-or-nothing guarantee or the adult gate.
- `world/ai/` never writes; the concept adapter runs the guarded pipeline exactly like the command.
- Persona content never reaches the browser (presentation contract).
- No backward compatibility or migration (unreleased project).

## Goals / Non-Goals

**Goals:**

- A server-owned concept draft stage storing the validated proposal values and an optional
  persona block, protected against cross-session overwrite while the LLM call is in flight.
- Persist the persona block at activation in the import-card shape, inside the activation
  transaction.
- `creation.concept` adapter + panel concept field sharing the guarded pipeline with Telnet.
- Retro-fit the Telnet concept flow through the same apply service.

**Non-Goals:**

- Any client-submitted persona field (`creation.custom` never accepts persona; the existing
  unknown-field rejection already covers it).
- Persona retrieval or prompt injection (owned by the persona-store / persona-dialogue-injection
  changes).
- Rendering persona content anywhere in the WebClient.
- Import-path persona changes.

## Decisions

### D1: The concept draft is a distinct stage of the existing wizard draft

The wizard draft gains a `concept_filled` stage storing exactly `{race, subrace, allocations,
persona{personality, life_story, habit}}`, written only by the deterministic concept-apply
service. The persona block is bounded and validated at save. A later `creation.custom` save
preserves the persona block only when the submitted race matches the concept draft's race;
otherwise the block is cleared (the generated background no longer fits). `clear_draft` clears it
with everything else.

- Alternatives considered: a separate persona attribute. Rejected: it would double the
  persistence surface and could survive draft resets; draft ownership and lifecycle already exist
  and clear atomically.

### D2: Concept-apply is a deterministic service with fingerprint compare-and-swap

`world/rules/character_creation.py::apply_concept_proposal(character, proposal)` (or the wizard
service) validates the proposal deterministically (the same checks the layer's semantic
validators run), then saves the concept draft inside a transaction that verifies a draft
fingerprint captured before the generative call; a mismatch returns a stale result and writes
nothing. The Telnet command and the `creation.concept` adapter both call this service, so the two
entries cannot drift and a late LLM response can never clobber a draft changed by another session
or by the interactive flow while the call was in flight.

- Alternatives considered: relying on the session-local dispatcher (`epoch`/`revision`/`in_flight`
  are session-scoped) alone. Rejected: it cannot protect against a different session or the
  Telnet entry modifying the same character's draft during the async gap.

### D3: Activation persists the persona in the import-card shape, in-transaction

`activate_player_character()` gains a step inside the existing `transaction.atomic()` block: when
the draft carries a persona block, write `entity.db.persona` as a six-key dict
(identity/personality/life_story/habit/appearance/social_connection) with the block filling the
three prose fields and `{}` for the remaining keys; a write failure rolls back the whole
activation; no block writes nothing.

- Alternatives considered: post-commit persona write. Rejected: it would break all-or-nothing —
  a crash after activation but before the persona write yields a persona-less active character,
  and a persona write failure could not roll back activation.
- The import-card shape with explicit `{}` containers (rather than a three-key dict) keeps every
  future PersonaStore consumer working with the documented six-key contract.

### D4: `creation.concept` adapter and panel — persona content never rendered

A fifth creation action with payload exactly `{concept}` (non-empty, bounded). It obtains the
actor from the session, rejects unknown fields, captures the draft fingerprint, runs the guarded
`character_creation` layer with the injected client, and calls the concept-apply service; on
success it refreshes the `creation` panel. On degrade or stale fingerprint it returns the stable
outcome with no state change. The panel renders the concept field and the draft's finite controls
(race/subrace/allocations pre-filled) plus a non-content indicator that a background was
generated; the persona block is never part of any payload sent to the browser, preserving the
existing no-persona-exposure presentation contract.

### D5: Telnet retrofit through the same service

The `character concept` command (from generative-character-concept) changes its flow to: run the
guarded layer → call the concept-apply service (saving the concept draft) → present the summary
→ collect name and both ages through the adult gate → activate (persona persisted from the draft).
No syntax or command-docs change.

## Risks / Trade-offs

- [The persona block could grow unbounded] → Bounded text fields validated at concept-draft save
  and again at activation.
- [A player changes race after the concept draft, orphaning the persona] → The custom-save rule
  clears the persona on race mismatch; the panel shows the indicator only when a persona block is
  present.
- [Stale concept responses] → Fingerprint compare-and-swap in the apply service; the existing
  dispatcher epoch/revision checks cover the session path.
- [LLM offline during concept] → The guarded layer degrades to the stable unavailable message;
  the deterministic adapters stay fully usable.
- [Draft-shape change breaking existing reconnect flows] → The concept stage and persona block are
  optional; non-concept drafts behave byte-identically.

## Open Questions

- None blocking. Whether the browser should let players edit the generated persona block before
  activation is deferred; persona content is intentionally not exposed in this change.
