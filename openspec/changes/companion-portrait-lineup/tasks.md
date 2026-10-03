# companion-portrait-lineup — Tasks

## 1. Server: party panel v2 with portrait_ref resolution

- [ ] 1.1 In `web/webclient/presentation/party.py`, add `_resolve_portrait_ref(npc)` using the existing canonical `world.art.subjects.character_subject_for()` policy and read-only gallery `record_for(create=False)`/`cards_for()`: emit the art panel's decimal identity catalog key only when the default card exists; otherwise return `None`. Never invent an NPC subject kind or create a record.
- [ ] 1.2 In `present_party()`, call `_resolve_portrait_ref(npc)` for each companion and emit the result as `portrait_ref` (string or null) in each slot row. Bump `PARTY_SCHEMA_VERSION` to `2`.
- [ ] 1.3 In `_validate_slot()`, accept `portrait_ref` as either `None` or an ASCII decimal string matching `[0-9]+`, length 1–32, at schema version 2.
- [ ] 1.4 In `party.py`, resolve the party OWNER before listing companions (design D6): when the session actor is a character whose `party_member` back-reference names a live player, use that player as the party root for `live_companions()` and owner-keyed `stage_for()` bond stages; when the back-reference resolves to no live player, raise the registry-unavailable error so the panel takes the shared unavailable form. A non-possessing player puppet is unaffected (actor is already the root).
- [ ] 1.5 Extend `world.rules.art_view._exploration_entities()` membership to include the owner's live, co-located companions (design D7), including the controlled companion while possessing, in party order after dialogue hosts and named-policy characters, honoring the 32-entry cap. Cap eviction uses the client placeholder.

## 2. Client: UMD and Vue validator mirrors

- [ ] 2.1 In UMD `protocol/constants.js` and `protocol/panels/misc.js`, update party schema and allowlist to `2`, accepting null or 1–32 ASCII decimal digits (matching the server).
- [ ] 2.2 Reuse the Vue store's existing shared UMD protocol validator and update its party fixtures to v2; introduce no second validator.
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

- [ ] 4.1 Create `companion-lineup.js`: export pure `companionSlots(count)` and `companionLineupSpan(count)` for counts 1–5. Every figure has scale 1 and lift 0; only horizontal overlap and baseline z vary. An optional maximum span bounds dialogue geometry without resizing.
- [ ] 4.2 Deterministically test solo geometry, equal sizes/ground lines, monotonic leftward offsets and decreasing baseline z, and bounded five-figure overlap at all acceptance viewports, including dialogue choice clearance.

## 5. Client: CompanionLineup.vue component

- [ ] 5.1 Create `CompanionLineup.vue`: ordered slots include identity, portrait, displayName and isControlled. Render equal-size StageActors; only the controlled figure gets beats. Companions use the shared speaking dim except when their committed dialogue host identity is speaking; that companion temporarily rises above all baseline z, then restores without geometry changes (also after possession/re-key). Keep all figures decorative and motion-tier aware.
- [ ] 5.2 Register the component in `component-manifest.json` and add `CompanionLineup.stories.js` with 0/1/2/4 companion variants, possession swap variant, and placeholder-only variant — deterministic fixture portraits (the `stage_journey.js`/`art_panels.js` fixture precedent), each variant framed at the actor-left anchor size and at 1280x720 so the left-half geometry claim is inspectable in the offline showcase.

## 6. Client: AppClient wiring

- [ ] 6.1 In `AppClient.vue`, add computed properties:
  - `isControllingCompanion`: true when possession banner is available
  - `companionLineupSlots`: normalize each integer party identity to its decimal string for joining the committed bounded-string `status.actor.identity`; swap the controlled companion and A in their exact original positions. Resolve catalog entries with `portraitFor()`; no prose/banner-name identity inference.
  - Correct `status.actor.identity` to the session actor while preserving every other owner-keyed hybrid field and the existing string wire type. Feed companion speaking focus from committed dialogue host identity and the existing speaker signal only.
- [ ] 6.2 Render CompanionLineup in actor-left, retaining solo geometry. Suppress the duplicate actor-right dialogue host only when its committed identity already joins to a party/controlled lineup figure; preserve non-party hosts, all foes, name plate/pagination/focus/keyboard paths.

## 7. HudFrame: actor-left overflow

- [ ] 7.1 In `HudFrame.vue`, set `overflow: visible` on `[data-anchor="actor-left"]` unconditionally.

## 8. Server tests

- [ ] 8.1 Update `web/webclient/presentation/tests/test_party_panel.py`: add test for v2 portrait_ref resolution (companion with gallery portrait → non-null ref, companion without → null). Verify the emitted ref resolves through the art panel's portrait_catalog.
- [ ] 8.2 Verify validator tests at schema v2: accept non-null portrait_ref string, reject non-string non-null values.
- [ ] 8.3 Preserve current-main v1 requirement annotations during APPLY; list archive-time v2 re-points in the report (the possession-controls slug is unchanged). Cover owner-keyed party/bonds, unavailable owner, companion catalog membership, and real possession's controlled string status identity with unchanged owner resources/name/conditions.
- [ ] 8.4 Add a browser acceptance journey to the existing managed-suite exploration-journey file: at 1280x720 with four companions and an open dialogue choice list, the companion figures stay within the left half, no figure box intersects the choice list or the foe line-up, and the front figure swaps on `explore.possess` and back on release. Author the assertions here; execution of the managed browser suite is CI-owned.

## 9. Verify

- [ ] 9.1 Run the focused server test modules (party panel, possession presentation, and the art-panel presenter module touched by 1.5/8.3) with `uv run --locked --env-file=<file-with-MUD_TEST_SETTINGS=1> evennia test --settings test_settings.py --keepdb <label>` per module (single-token `--env-file=`). Focused labels only — never the full non-browser suite.
- [ ] 9.2 Run the focused Vitest tests (`pnpm test` scoped to the touched test files) and the Node gate (`node --test web/static/webclient/js/tests/*.test.js`, fast per AGENTS.md). No full-suite runs.
- [ ] 9.3 Review screenshots at 1920x1080 and 1280x720 for populated HUD, 0/2/4 companions, possession swap, placeholder fallback, dialogue speaking focus, and PartyDrawer stories; perform a polish pass. Every lineup figure has equal size.
- [ ] 9.4 Run `uv run --locked python -m tools.contract_gate` (seconds; traceability + lints + shard manifests — not a test run; required before handoff).
- [ ] 9.5 `openspec validate companion-portrait-lineup --strict` passes.
- [ ] 9.6 Run the Storybook gates: `pnpm run build-storybook` and `pnpm run showcase-coverage`. This change moves components in the frozen required-set manifest (PartyStrip out, CompanionLineup in) — update the manifest in the same change per the coverage-check contract, and eyeball the built showcase: possession swap, placeholder-only, and the four-companion 1280x720 variant.
- [ ] 9.7 Run `pnpm run build`, `tools.spec_traceability check`, `tools.test_data_lint`, `git diff --check`, and compileall-check authored browser files; register the browser method in the shard manifest. Do not run the CI-owned managed browser suite.
