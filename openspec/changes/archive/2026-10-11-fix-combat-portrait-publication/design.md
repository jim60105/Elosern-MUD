# Design

## Context

See proposal.md for motivation. Static code confirms that `exploration_actions.AFFECTED_ENGAGE` and the production registry engage declaration omit `art`. `_publish_completion` uses the adapter's affected panels and allocates one revision before sending the correlated result. The coordinator does not automatically add art. `FoeLineup.entryFor` returns null for an absent catalog reference; ReferenceArtwork still has the standing SVG branch when no fallback URL exists. No live first-engage payload or user's runtime record was inspected, so the precise observed timing remains unconfirmed.

The text ingress `refresh_after_command` already sends a full snapshot after settlement. Opening field casts, ordinary casts, flee and forfeit already include art. `MAX_PARTICIPANTS=16` and `MAX_PORTRAIT_CATALOG=32` allow the complete current combat participant catalog without raising limits. Both views use the same opaque identity mapper. Existing green lineup tests (19 tests reported by the supervisor) do not establish real first-engage acceptance.

## Goals / Non-Goals

Keep deterministic gameplay independent of artwork availability and preserve the coordinator's single publication boundary. Do not mutate combat state from presenters, generate URLs in the browser, add an OOB protocol/version or substitute an unconditional stock bitmap. Preserve the current scene identity rules during terminal beat holds.

## Decisions

### D1. Fix the declared publication boundary

Add `art` to successful engage's adapter affected panels and matching action-registry declaration. Publish status, context_actions, dialogue and art through the existing coordinator in one revision, before the matching action result. Do not add a second push, broaden every action to full snapshots or turn presenters into writers. Extend the existing engage/dispatcher test to inspect the actual combined publication and the first opaque participant reference's catalog membership.

Keep ordinary command refresh's full-snapshot path and existing cast/flee/forfeit paths. Their tests establish first entry and later round coherence using the same serializer, rather than adding new independent snapshot machinery. Art serialization must preserve entries for all combat participants, including malformed/unregistered visual provenance classified as monsters by the prerequisite change. A renderer defensive missing entry remains text-only; it is not the intended successful engage result.

### D2. Remove the retired branch completely

Remove ReferenceArtwork's standing humanoid SVG template, its shape styling and pending-motion selectors that target the retired branch. Keep mask styling and motion for a server-carried fallback. Search and update actual shared consumers, component stories and frozen coverage assertions that require the old figure. Do not remove unrelated inventory SVG icons or the labelled adult comparison reference in the gallery editor.

For missing/pending/failed monster imagery use the carried monster_anon alpha mask. A failed real species image uses the carried fallback with a truthful load-failure state; a failed fallback mask or absent entry/identity keeps name and availability text only. No client taxonomy, guessed URL or decorative figure fills that gap. Reset load-error state on URL change as the current component contract requires, so later species artwork can recover.

### D3. Keep retained actor art coherent without freezing canonical art

Foe playback already retains pre-round actors until their defeat beat, but `FoeLineup.entryFor` reads only the current art panel. `stores/elosern/beats.js::syncBeatRound` constructs `planRound` from the previous roster, without previous art. Capture admitted entries from `prev.panels.art.portrait_catalog` for only the pre-round foes into that same plan, expose them through `stageFor`, and let `FoeLineup.entryFor` prefer a current admitted entry then the retained entry by opaque ref. Never join by token/name/tier. Use the existing plan's playback lifecycle to release this bounded data on completion, skip, flush and epoch reset; do not introduce another independent cache. Do not freeze the scene entry, current mode, HP authority or other HUD state. This is limited to existing bounded foe playback, not permanent catalog storage.

### D4. Assertion ownership and traceability

The speaking-state requirement's null-reference scenarios are shared consumers of D2: preserve their initial/name/state outcome, with no invented standing figure. The whole-batch review's alleged legacy worker-push scenario and omitted dialogue-host scenario were absent from the current main specs at the cited locations; the actual old-treatment scenario is explicitly replaced in this delta and a no-fallback dialogue-host case now removes ambiguity.

Extend existing exploration action/dispatcher/art panel tests for the combined engage envelope and catalog coverage. Extend shared ReferenceArtwork/FoeLineup unit cases for no-entry/no-fallback, monster mask, image and mask failure, URL recovery and retained terminal actor release; replace old SVG expectations rather than retaining duplicate tests. Use the root `vitest.config.js` configuration, not an isolated webclient-app run.

Extend the existing managed-browser combat stage journey with an actual authored wilderness goblin: engage without images, inspect the first committed monster_anon mask, complete an action/round, then exercise an admitted goblin-specific image through the supported workflow. Assert same-tier other-species/tier files never appear. Keep failure permutations at the shared unit seam and one representative end-to-end journey rather than a browser Cartesian product. Existing browser silhouette tests retain their unrelated layout/motion coverage. Update only changed assertion mappings in `docs/development/spec-test-traceability.md`'s prescribed main-spec mapping workflow; new Python modules, if genuinely necessary, must be included in `.github/evennia-shards.json`.

## Risks / Trade-offs

The precise live screenshot transition is unobserved; the missing engage-art declaration and legacy SVG branch are confirmed code paths, not claimed live traces. End-to-end acceptance must use the actual population producer from the prerequisite proposal, not a fake species field added only by a fixture. Retained actor entries are decorative and bounded; accidental retention of the whole art panel would violate current-scene authority. Active exploration changes can touch shared integration/browser helpers, so serialize those overlapping edits without adding semantic dependencies.

## Documentation and Delivery

Amend the fallback section of `docs/superpowers/specs/2026-08-02-webclient-art-portrait-ui-design.md` and current stage fallback descriptions to state text-only absence and same-revision first combat catalog delivery. Update the implementation changelog and traceability mappings. No data migration or compatibility branch is required on this pre-release project. This dependent one-day slice completes the end-to-end acceptance after species identity lands.
