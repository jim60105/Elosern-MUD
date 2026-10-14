# Design

## Context

lib/image-attempts.js; composables/useImageAttempts.js; ArtworkFailure.vue and ArtworkAlpha.vue; GalleryFaceRectModal.vue; focused core/editor tests, test-only image fixture and docs.

Observed current panel contracts are art v2, roster v2, gallery v2 and dream v2. The official catalog indexes external monster/preset/npc content, while figures/scenes/avatars/editors own separate loading flags. The approved design and proposal.md define the named slice; planned later versions are batch contracts, not existing implementation claims.

## Goals / Non-Goals

**Goals:** Deliver this complete independently testable production boundary with exact source ownership and objective acceptance.

**Non-Goals:** Gameplay, generation scheduling, new production commands, global cache/retry/store, telemetry transport, GM previews, compatibility/migrations and hot reload. Text clients/favicons/unrelated icons remain unchanged.

## Decisions

The shared pure reducer/local driver is immediately used by the existing GalleryFaceRectModal. It receives a normalized resource request {subjectId, epoch, attempts, terminal, availability}, with stable source rank and resource identity/version key; it does not parse panel versions or resolve business subjects. For the still-current gallery v2 editor, the caller supplies exactly its committed selected original identity/URL/geometry as one original load request and terminal null. This is the same resource construction needed by any original/ruler editor, not a canonical business descriptor, dual-shape validator or compatibility module. No new panel fields are emitted and the current active validators remain unchanged. Gallery v3 later supplies its backend descriptor through useArtwork to this same driver, updating the caller atomically and removing obsolete v2 field reads.

Implement epoch-bound load/decode observation, reached-only bounded faults, canonical byte-resource dedup, local successful-resource reuse on geometry-only update, terminal-policy filtering and safe exhaustion. Include provisional source outcomes in this same mechanism now; they are tested with synthetic multi-source requests and production editor uses normal one-source resolution. Later scene integration activates that option rather than writing another loader. No global store/negative cache, timer retry or second business-data fetch.

ArtworkFailure/ArtworkAlpha are presentation primitives consuming results; alpha has no selector, renders fill only after observed same-URL success, and cannot hide an absent resource as a rectangle. Availability failure is a separate ready/expected_absent/failed input invalidating callbacks and original save eligibility; never invent pending generation. The face editor's actual original success plus natural dimensions gates saving and failed img/crop content is removed. Stage-editor consolidation remains its named later slice. Preserve current action/geometry/focus semantics and register shared/component story/evidence ownership.

### Concrete browser fixture ownership

All new actual-art inventory/scene/dream/media journeys allocate `runtime = web.tests.browser.fixtures.create_runtime()`, set `runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"` BEFORE seed or server startup, and use `ManagedServer(runtime=runtime)` plus ManagedServerTearDownMixin, matching ArtSceneBrowserTest's per-test lifecycle rather than the synthetic shared server. browser_settings already disables the scheduler; set ELOSERN_BROWSER_ART missing/done as needed through runtime.env. For normal default-root absence, extend test-only browser_settings.py to choose an uncreated runtime cache child as its default official root when ART_OFFICIAL_ROOT is not in the environment, while preserving the production settings import's unconfigured provenance. Do not set an explicit environment override for normal absence. Configured-root fault journeys deliberately set ART_OFFICIAL_ROOT to an unavailable runtime child. No production setting/default or new runtime knob changes. Write configured operator fixture bytes/manifests under a runtime-owned temporary root before startup. The built-in root continues to actual repository files. Data-contract docstrings and tools/test_data_freeze.json registration identify shipped-key/artwork usage; do not mark these as synthetic arithmetic evidence.

Loading-core creates `web/tests/browser/seed/image_editor_fixture.py`, with `seed/runner.py` invoking it only for a test-only ELOSERN_BROWSER_UNIFIED_IMAGES mode. It uses `gallery.append_card` and `gallery.set_default` for real runtime card records and fixed valid PNG/WebP bytes under runtime ART_STORE_ROOT. Gallery extends mode "gallery", editor owner mode "editors", portrait owner mode "portraits", scene owner mode "scenes", dream owner mode "dream". All use actual existing activated character/age/policy seeding; direct production mutation routes remain authoritative. New fixture helpers are test-only and named in each task budget.

For live state transitions, implement `web/browser_support/unified_image_transitions.py` plus a bounded test-only Command/CmdSet installed only by the browser seed/settings flag. Allowed transition enums are pending_scene, failed_scene, done_scene, remove_room_binding, move_scene, repaired_original, revoke_source and unavailable_panel. Scene transitions call queue.requeue, queue.claim, queue.settle with the record's actual generation_token (not claimed[0]) and real maps-owned metadata/construction writers, then normal presentation coordinator refresh. repaired_original appends/selects a distinct real original card through gallery writer/actions; no substitute is persisted. dream enters through real sleep association and existing say/awaken actions, never client-only modal injection. unavailable_panel is a test-only presenter failure seam for the required panel, not an injected client snapshot. The helper accepts only fixture-owned identities and predefined operations and is absent from production cmdsets; it adds no production command syntax or telemetry endpoint. Register test fixture ownership/data role where the existing harness contracts require it.

Network interception happens after actual backend serialization/selection, using Playwright page.route restricted to the selected fixture URL: return 404 or invalid image bytes, or delay/release the preferred source. Count requests by canonical source resource key and inspect actual descriptor/state plus DOM natural dimensions/focus/outbound actions. Gallery recovery asserts exact new selected card identity; scene transitions assert real server generation state and movement identity, not manufactured client revisions. Pure source-order/retention/provisional tests remain synthetic and independently expected. Every browser task below implements only its owned mode/method; no full managed suite or new general-purpose fixture framework is planned.


## Risks / Trade-offs

- Cross-surface shape mismatch: every wire owner ships its serializers, active schema/version/validators and all production readers together. Internal loading/source prerequisites keep one current wire until its named cutover.
- Unsafe retention or hidden fault: stable layer ranks and explicit authorized retention tokens distinguish priority/regeneration from removal/access loss; availability failure is separate from expected absence.
- Asset rights/budget uncertainty: all real artwork production has a complete owning pack, including two terminal images; catalog assumes no uncertain promotion/reproduction branch.
- Shared files/manifests: obey Batch dependencies and serialize overlapping edits; unrelated asset bytes have disjoint ownership.

## Migration Plan

Apply only after listed prerequisites land. This pre-release project has no compatibility/data migrations. Keep the current single wire shape until its atomic owning serializer/client cutover; remove obsolete internal projections/readers in that owner, never aliases/re-exports. Each named slice delivers its tests/docs/runtime boundary within the itemized 7.5 hours. Rollback reverts the complete owning slice and consumers together. Planning does not apply or archive these artifacts.
