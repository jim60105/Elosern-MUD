# creation-persona-persistence — Tasks

## 1. Concept draft stage

- [x] 1.1 Extend the creation-wizard draft service (`world/rules/creation_wizard.py` and
      `world/rules/character_creation.py`): a `concept_filled` stage storing exactly `race`,
      `subrace`, `allocations`, and an optional persona block (`personality`, `life_story`,
      `habit` bounded text fields), written only by the deterministic concept-apply service
- [x] 1.2 Implement the deterministic concept-apply service (`apply_concept_proposal`): re-validates
      the proposal (registry existence/compatibility, allocation bands, persona bounds) and saves
      the concept draft inside one transaction with a draft-fingerprint compare-and-swap
      (fingerprint captured before the generative call; mismatch → stale outcome, no write)
- [x] 1.3 Custom-save persona rule: `save_custom_draft` preserves the concept draft's persona block
      only when the submitted race equals the concept draft's race; otherwise clears it
- [x] 1.4 Confirm `clear_draft` and activation clear the concept stage and persona block atomically;
      non-concept drafts behave byte-identically

## 2. Activation persona write

- [x] 2.1 Extend `activate_player_character()`: inside the existing `transaction.atomic()` block,
      write a validated draft persona block into `entity.db.persona` as the six-key import-card
      dict (identity/personality/life_story/habit/appearance/social_connection; block fills the
      three prose fields, remaining keys stored as `{}`), writing nothing when the draft has no
      block
- [x] 2.2 Confirm a persona write failure rolls back the whole activation (character stays
      pending, no canonical identity/trait/persona state written)
- [x] 2.3 Confirm `world/imports/loader.py` remains unchanged and the import-time persona write is
      untouched

## 3. WebClient concept surface

- [x] 3.1 Register the fifth creation action `creation.concept` in the production action registry
      with payload exactly `{concept}` (non-empty string, declared bound); the adapter obtains
      the actor from the authenticated session, rejects unknown fields, captures the draft
      fingerprint, runs the guarded `character_creation` layer with the injected client, calls
      the deterministic concept-apply service, and refreshes the `creation` panel; degrade or
      stale fingerprint returns the stable outcome with zero state change
- [x] 3.2 Add the creation-panel concept text field (bounded, keyboard-first) that submits
      `creation.concept`; the panel renders the concept stage's finite controls pre-filled plus a
      non-content background-generated indicator, and never ships persona text, keys, or length
      information to the browser
- [x] 3.3 Retro-fit the Telnet `character concept` command (from generative-character-concept) to
      call the concept-apply service before presenting the summary and collecting name/ages, so
      both entries share the same apply service and both persist persona; no command syntax or
      docs change
- [x] 3.4 Amend the `webclient-action-dispatch` delta spec so the production registry allowlist
      gains `creation.concept` (five creation adapters) with its exact-list scenario updated

## 4. Tests

- [x] 4.1 Draft tests: concept stage persists across reconnect; persona block cleared on race
      mismatch in a later custom save; absent block keeps byte-identical draft behavior; reset
      clears the stage; `creation.custom` with a persona field rejects (unknown-field rule)
- [x] 4.2 Apply-service tests: fingerprint mismatch returns stale and writes nothing (simulate a
      draft change during the async gap, including via a second session and via the Telnet flow);
      matching fingerprint saves atomically
- [x] 4.3 Activation tests: concept draft persists persona in the six-key import-card shape with
      `{}` containers; persona write failure rolls back activation; no-block draft writes nothing;
      adult gate regression
- [x] 4.4 Adapter/panel tests: `creation.concept` success fills the draft; offline degrade with no
      state change; unknown fields rejected; stale/duplicate/tampered handling via the existing
      dispatcher; abnormal puppet rejected; persona content absent from every panel payload
- [x] 4.5 Browser acceptance: keyboard-only concept → draft → complete form → activate journey at
      both supported desktop viewports with a deterministic placeholder (no live LLM)

## 5. Traceability and verification

- [x] 5.1 Annotate the discoverable tests covering the new and modified requirements with
      `covers_requirement` using canonical IDs from
      `uv run --locked python -m tools.spec_traceability list`
- [x] 5.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm the
      creation-persona-persistence and webclient-character-creation-ui requirements are covered
- [x] 5.3 Run the focused test packages (world rules creation tests, web webclient actions and
      presentation tests, browser creation journey) and confirm green; keep `git diff --check`
      clean
