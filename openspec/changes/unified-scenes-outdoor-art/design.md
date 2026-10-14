# Design

## Context

web/static/art/scenes/{wilderness_path,mountain_path,coastal_path}.webp; per-image provenance sidecars; world/art/tests/test_bundled_outdoor_art.py; web/tests/browser/test_browser_bundled_scene_assets.py; shard manifests.

Observed current panel contracts are art v2, roster v2, gallery v2 and dream v2. The official catalog indexes external monster/preset/npc content, while figures/scenes/avatars/editors own separate loading flags. The approved design and proposal.md define the named slice; planned later versions are batch contracts, not existing implementation claims.

## Goals / Non-Goals

**Goals:** Deliver this complete independently testable production boundary with exact source ownership and objective acceptance.

**Non-Goals:** Gameplay, generation scheduling, new production commands, global cache/retry/store, telemetry transport, GM previews, compatibility/migrations and hot reload. Text clients/favicons/unrelated icons remain unchanged.

## Decisions

Produce original, finished layered landscape illustrations, one per owned key, under web/static/art/scenes/<key>.webp. The reference style is the shipped town/forest provenance in web/webclient-app/assets/redesign/generation.json: painterly JRPG environment with open lower foreground, detailed mid/background and no interface or lettering. Development-time image production may use the existing SD client/prompt vocabulary or authored offline illustration, but the delivered bytes must be complete and redistributable; neither runtime acquisition nor a placeholder is permitted. Each asset has a separate <key>.provenance.json recording actual source/license, author or model/input/seed when applicable, production method, WebP processing and SHA-256. An unavailable production tool does not authorize fake output or a narrower delivered inventory.

Owned visual briefs: open grassy/hard-earth country path to a distant horizon; mountain_path follows its named scene identity; coastal_path follows its named scene identity. Visual review must distinguish every owned image from town/forest and each sibling. Full-bleed composition is checked in a real browser at the 1451×790 desktop reference viewport with cover cropping, not only by image dimensions.

Use a pack-local pure image/data-contract test to decode the actual shipped bytes, enforce existing resource limits and cross-check provenance checksums/licenses. Register it as a data-contract test and non-browser shard member. Add one pack-specific method to the dedicated static asset browser test module; it requests actual /static/art/scenes/<key>.webp through the running server with no operator mount/generation. Keep the three packs independent by disjoint asset/sidecar/test paths; serialize shared manifest and common-browser-method registration. No incomplete scene registry or production resolver is introduced in these asset deliveries.

This first pack also owns the closed eleven-path tracked-scene exception in official-artwork-catalog and art-gallery-fallback plus the exact tracked-image test allowlist. Permit not-yet-delivered registered future pack paths but assert actual owned three-image coverage here. Other packs depend on this first contract; catalog adds complete eleven-key coverage only after all four packs. No incomplete registry is published. This adds 0.5 hours to the pack, total 7.0.

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

Apply only after listed prerequisites land. This pre-release project has no compatibility/data migrations. Keep the current single wire shape until its atomic owning serializer/client cutover; remove obsolete internal projections/readers in that owner, never aliases/re-exports. Each named slice delivers its tests/docs/runtime boundary within the itemized 7.0 hours. Rollback reverts the complete owning slice and consumers together. Planning does not apply or archive these artifacts.
