# companion-portrait-lineup — Tasks

## 1. Server: party panel v2 with portrait_ref resolution

- [ ] 1.1 In `web/webclient/presentation/party.py`, add a `_resolve_portrait_ref(npc)` helper: imports `ArtSubject`, `SubjectKind` from `world.art.subject`, `record_for` from `world.art.gallery`; resolves the NPC's default gallery portrait into the catalog ref key (the same key format the art panel's `portrait_catalog_for()` uses), or returns `None` if no record or no default card exists.
- [ ] 1.2 In `present_party()`, call `_resolve_portrait_ref(npc)` for each companion and emit the result as `portrait_ref` (string or null) in each slot row. Bump `PARTY_SCHEMA_VERSION` to `2`.
- [ ] 1.3 In `_validate_slot()`, accept `portrait_ref` as either `None` or a bounded string (same max-length as the exploration vocabulary's portrait_ref) at schema version 2.
- [ ] 1.4 In `party.py`, resolve the party OWNER before listing companions (design D6): when the session actor is a character whose `party_member` back-reference names a live player, use that player as the party root for `live_companions()` and owner-keyed `stage_for()` bond stages; when the back-reference resolves to no live player, raise the registry-unavailable error so the panel takes the shared unavailable form. A non-possessing player puppet is unaffected (actor is already the root).
- [ ] 1.5 In the exploration art panel presenter (`portrait_catalog_for()`), extend exploration-mode membership to include the player's live companions (design D7), in party order after dialogue hosts and named-policy characters, honoring the 32-entry cap; a companion evicted by the cap needs no special handling — the client placeholder covers an unresolved ref.

## 2. Client: UMD and Vue validator mirrors

- [ ] 2.1 In `web/static/webclient/js/elosern/protocol/panels/party.js`, update the schema version to `2`, and update the slot validator to accept `portrait_ref` as either null or a bounded string (matching the server validator).
- [ ] 2.2 In the Vue store mirror (`elosern-store.js` or wherever the party panel schema is asserted), update the schema version assertion to `2`.
- [ ] 2.3 Update the UMD Node gate fixtures in `web/static/webclient/js/tests/protocol_party.test.js`: `validPartySlot()` keeps `portrait_ref: null` as the default; add positive cases for a decimal catalog key (e.g. `"42"`, and the 32-digit bound) and drift cases (numeric ref, `"4a"`, 33 digits, `schema_version: 1` payload now rejected as unsupported — flip the polarity of the existing "unsupported party schema_version" and "portrait_ref must stay null at version 1" expectations).
- [ ] 2.4 Run the Node test gate (`node --test web/static/webclient/js/tests/*.test.js`) to verify validator parity.

## 3. Client: remove PartyStrip

- [ ] 3.1 Delete `web/webclient-app/components/PartyStrip.vue`.
- [ ] 3.2 In `AppClient.vue`, remove the `PartyStrip` import and its rendering inside the `#vitals` slot.
- [ ] 3.3 Delete `PartyStrip.stories.js` and remove from `component-manifest.json`.
- [ ] 3.4 Remove `party_strip.test.js` if it exists.
- [ ] 3.5 Update `app_client_drawers.test.js` or any test asserting PartyStrip rendering.
- [ ] 3.6 Update the `deferred_surfaces_absent.test.js` surface manifest if it lists PartyStrip.
- [ ] 3.7 Update the storybook fixtures in `web/webclient-app/stories/fixtures/party_panels.js` (and any story importing them — `PartyDrawer.stories.js`) to the v2 party payload: `schema_version: 2` and per-slot `portrait_ref` (a decimal catalog-key string for portrait-having companions, `null` for the rest). The showcase derives shapes exactly as AppClient does, so no story may keep a v1 row.

## 4. Client: companion lineup geometry helper

- [ ] 4.1 Create `web/webclient-app/components/companion-lineup.js`: export `companionSlots(count)` returning `[{ scale, x, lift, z }]` for each slot (0 = controlled character, 1..N = companions in party order), mirroring `foe-lineup.js::foeSlots()`. Table for counts 1-5.
- [ ] 4.2 Unit-test the geometry helper (deterministic pure-function tests): count 1 returns solo position, count 5 returns 5 positions within the left half, x offsets are monotonically decreasing from right to left, scales decrease behind, z-index decreasing behind.

## 5. Client: CompanionLineup.vue component

- [ ] 5.1 Create `web/webclient-app/components/CompanionLineup.vue`: takes a `slots` prop (array of `{ portrait, displayName, isControlled }` objects, pre-ordered: controlled first, then companions in party order), renders each slot as a StageActor instance positioned by `companionSlots()`. Each StageActor receives `portrait`, `dimmed`, and `gesture: null` (companions) or the beat gesture (controlled). All figures are decorative: `aria-hidden="true"`, no pointer events.
- [ ] 5.2 Register the component in `component-manifest.json` and add `CompanionLineup.stories.js` with 0/1/2/4 companion variants, possession swap variant, and placeholder-only variant — deterministic fixture portraits (the `stage_journey.js`/`art_panels.js` fixture precedent), each variant framed at the actor-left anchor size and at 1280x720 so the left-half geometry claim is inspectable in the offline showcase.

## 6. Client: AppClient wiring

- [ ] 6.1 In `AppClient.vue`, add computed properties:
  - `isControllingCompanion`: true when possession banner is available
  - `controlledPortrait`: when possessing, resolve from `party.slots` by matching `elosernStore.actorId` to the slot identity → portrait_ref → portrait_catalog; when not possessing, use `currentPortrait`
  - `companionLineupSlots`: build the ordered slot array for CompanionLineup: `[controlledPortrait, ...companionSlots]` where companionSlots excludes the controlled identity and maps to portrait entries via `portraitFor()`. When not possessing, companions are all party slots; when possessing, A's portrait becomes a companion slot.
- [ ] 6.2 Render `<CompanionLineup :slots="companionLineupSlots" />` inside `<template #actor-left>`, replacing the solo `<StageActor>` with the lineup component. The lineup naturally renders a solo StageActor when no companions exist.

## 7. HudFrame: actor-left overflow

- [ ] 7.1 In `HudFrame.vue`, set `overflow: visible` on `[data-anchor="actor-left"]` unconditionally.

## 8. Server tests

- [ ] 8.1 Update `web/webclient/presentation/tests/test_party_panel.py`: add test for v2 portrait_ref resolution (companion with gallery portrait → non-null ref, companion without → null). Verify the emitted ref resolves through the art panel's portrait_catalog.
- [ ] 8.2 Verify validator tests at schema v2: accept non-null portrait_ref string, reject non-string non-null values.
- [ ] 8.3 Update the `@covers_requirement` slugs in `test_party_panel.py` and `test_possession_presentation.py`: the renamed requirement's canonical ID changes from `…version-1-presentation-panel` to `…version-2-presentation-panel` (verify with `uv run --locked python -m tools.spec_traceability list` after the delta syncs). Add owner-keyed-possession coverage (design D6): possessing a companion keeps both slots with owner-keyed bond stages; a partyless possessed actor sees the unavailable form. Cover the new `portrait_catalog` exploration membership (companion without policy appears in the catalog) in the art panel test module.
- [ ] 8.4 Add a browser acceptance journey to the existing managed-suite exploration-journey file: at 1280x720 with four companions and an open dialogue choice list, the companion figures stay within the left half, no figure box intersects the choice list or the foe line-up, and the front figure swaps on `explore.possess` and back on release. Author the assertions here; execution of the managed browser suite is CI-owned.

## 9. Verify

- [ ] 9.1 Run the focused server test modules (party panel, possession presentation, and the art-panel presenter module touched by 1.5/8.3) with `uv run --locked --env-file=<file-with-MUD_TEST_SETTINGS=1> evennia test --settings test_settings.py --keepdb <label>` per module (single-token `--env-file=`). Focused labels only — never the full non-browser suite.
- [ ] 9.2 Run the focused Vitest tests (`pnpm test` scoped to the touched test files) and the Node gate (`node --test web/static/webclient/js/tests/*.test.js`, fast per AGENTS.md). No full-suite runs.
- [ ] 9.3 Visual smoke: 1920x1080 with 0/2/4 companions; possession swap; placeholder fallback.
- [ ] 9.4 Run `uv run --locked python -m tools.contract_gate` (seconds; traceability + lints + shard manifests — not a test run; required before handoff).
- [ ] 9.5 `openspec validate companion-portrait-lineup --strict` passes.
- [ ] 9.6 Run the Storybook gates: `pnpm run build-storybook` and `pnpm run showcase-coverage`. This change moves components in the frozen required-set manifest (PartyStrip out, CompanionLineup in) — update the manifest in the same change per the coverage-check contract, and eyeball the built showcase: possession swap, placeholder-only, and the four-companion 1280x720 variant.
