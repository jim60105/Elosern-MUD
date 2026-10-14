# Proposal

## Why

Exploration currently publishes and validates only null portrait references even when the same committed art catalog carries a real image. This violates the catalog-focus contract and leaves presence medallions and non-party person focus without available portraits.

## What Changes

- **BREAKING**: advance the exact exploration schema from 3 to 4 in the Python producer/registry and JS mirror, accepting null or bounded ASCII-decimal catalog references in both interact targets and look entities; reject older available versions without adapters.
- Populate references through the existing read-only art resolution chain, gated by membership in the current bounded art view and a real runtime/official image. Preserve canonical eligibility, precedence, visibility, ordering and truthful missing-art behavior.
- Refresh exploration descriptors beside a qualifying portrait-art completion update so a null reference can become usable without another game action. Keep unrelated sessions and late departed subjects excluded.
- Prove accepted wire values reach target and bystander medallions and the non-party focus StageActor, including failed loads and replacement artwork. Replace null-only assertions and misleading Storybook fixture commentary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-exploration-menu`: schema-4 cutover and catalog-consistent nullable references for both descriptor paths.
- `webclient-presence-rail`: real-image face crops and non-party focus portraits, truthful fallbacks and refresh behavior.
- `webclient-art-panel`: qualifying exploration portrait completions refresh exploration descriptors in the same update.

## Impact

Producer/validators in `web/webclient/presentation/exploration.py`, `web/static/webclient/js/elosern/protocol/panels/exploration.js` and `protocol/constants.js`; `art_push.py` and its tests; existing art view and resolution owners remain authoritative. Consumers remain `exploration_menu.js`, `PresenceRail.vue` and `use-person-focus.js`, with `StageActor`/`ReferenceArtwork` reused. This protocol fix justifies editing the UMD validator despite the frontend guide's rule against changing UMD merely for Vue presentation; no wrapper can make the null-only protocol valid.

Update shared protocol fixtures, focused Python/Node/Vitest tests, presence/AppShell stories and synthetic browser evidence. No generated bundle edits, gameplay writes, art generation, catalog expansion, migrations or duplicate-focus fix are in scope.

## Acceptance

A production snapshot with an admitted image yields a non-null reference in both matching descriptor paths and a successfully loaded face crop. Non-party focus uses the same catalog image. Excluded/cap-dropped identities and imageless or ineligible subjects stay null; failed media uses the established fallback. A current portrait completion changes null to a usable reference in one newer update without dispatching a focus action. Older available schemas and malformed references fail in both validators. Existing exploration actions remain unchanged.

## Scope Size

One engineer, eight hours: protocol/producer and catalog-join tests 3h; completion refresh and tests 1.5h; consumer integration/fallback tests 1.5h; stories, focused verification, live evidence and documentation 2h. Reuse existing test modules and fixtures; no new subsystem.

## Batch:

```text
depends-on: none
soft-precedes: reuse-lineup-person-focus
```

There is no hard dependency in either direction. Apply this change first for image-bearing integrated proof, then `reuse-lineup-person-focus`. Shared files need sequential integration; the matrix below lists anticipated implementation overlap, not planning-file conflicts.

| Surface | Overlap with reuse-lineup-person-focus | Conflict handling |
| --- | --- | --- |
| Code | `AppClient.vue` only if non-party consumer wiring needs adjustment; `use-person-focus.js` only if reference lookup needs adjustment | Portrait lookup stays independent of lineup identity policy; reuse fresh source |
| Main specs | `openspec/specs/webclient-presence-rail/spec.md` | Distinct requirements except person-focus scenarios; preserve both image and lineup exceptions at sync |
| Integrated tests | `web/webclient-app/tests/app_client_presence_rail.test.js` | Extend image cases first, then lineup cases without deleting non-party coverage |
| Shared fixtures | `web/webclient-app/tests/store/protocol_fixtures.js`, `web/static/webclient/js/tests/protocol_fixtures.js`, `stories/fixtures.js` | Schema-4 defaults belong to this change; keep local focus fixtures synthetic |
| Stories | `stories/Core/PresenceRail.stories.js`, `stories/Core/AppShell.stories.js` | Avoid conflicting fixture/comment rewrites |
| Documentation | `docs/development/frontend-vue-architecture.md`, frontend developer guide potentially | Protocol/catalog contract and exploration-lineup emphasis need separate edits |
| Browser evidence | `web/tests/browser/test_browser_exploration_nav.py`, its existing synthetic seed/helper dependencies | Keep distinct methods and reuse the first change's admitted image seed |
| Manifests | `.github/browser-shards.json`; `.github/evennia-shards.json` only if a Python module is added/moved | Exact ownership for any new method/module; integrate sequentially |
