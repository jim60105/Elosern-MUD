# Proposal

## Why

Opening a companion's exploration verb card creates a duplicate actor-right figure while the existing actor-left companion remains dim. The shell already suppresses actor-right for lineup dialogue hosts and already has companion dim/z focus behavior.

## What Changes

- Join the focused interact identity to the actual rendered committed `companionLineupSlots`, using the existing decimal-string identity convention across numeric party identities and string status identities. Do not infer membership from name, portrait key, raw party membership or art availability.
- Suppress actor-right for an identity already represented in that lineup. While its verb card is open, light and elevate the selected non-controlled companion through existing `CompanionLineup`/`StageActor` behavior, keeping the controlled figure's existing dim and beat semantics.
- Derive emphasis from current focus and committed lineup, restoring baseline after back, look-close, departure, movement, panel loss, mode/epoch reset or lineup/control changes. Dialogue commit takes over through the existing dialogue speaker signal without duplicating the companion.
- Preserve actor-right for non-lineup targets, existing card payloads, focus restoration, portrait fallbacks, equal dimensions, ground lines and reduced/off motion. Amend the specs that require every target on actor-right and an unconditional right-side handover.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-presence-rail`: lineup-aware person focus, closure and conditional card-to-dialogue standee continuity.
- `webclient-contextual-hud`: extend companion dim/z focus to exploration without changing possession/control or dialogue speaker semantics.

## Impact

Primary implementation is `web/webclient-app/AppClient.vue` with existing `companionFigures` and `CompanionLineup.vue`. The existing store/composable owns card lifecycle and dispatch; change it only if a focused regression demonstrates missing derived-state cleanup. No schema, backend, gameplay-state mutation, second actor renderer, motion/geometry redesign or art precedence change.

Extend `app_client_presence_rail.test.js`, `tests/core/companion_lineup.test.js`, presence/AppShell/CompanionLineup stories and focused synthetic browser evidence. Any new browser methods receive exact ownership in `.github/browser-shards.json`.

## Acceptance

Opening a rendered companion's card sends no action and creates no router frame or actor-right figure; exactly its existing non-controlled figure becomes lit with z above every baseline figure while geometry stays fixed. Closing or invalidation restores the current baseline. A companion host remains represented once at dialogue commit, then follows dialogue host/player speaking signals. A same-name non-lineup target still uses actor-right. Possession swaps retain the controlled front figure and its beat/dim behavior, including unavailable party rows, and reduced/off motion produces the same final state.

## Scope Size

One engineer, eight hours: shell identity join/focus derivation 1.5h; synthetic integrated lifecycle and possession tests 2.5h; component regressions/stories 1h; focused browser/live evidence 2h; docs and final focused gates 1h. No backend or independent geometry work.

## Batch:

```text
depends-on: none
soft-depends-on: restore-exploration-portrait-refs
```

The portrait fix is a soft proof prerequisite, not a functional dependency. This change must also work with null portraits and the current accepted schema. Recommended application order is `restore-exploration-portrait-refs`, then this change, sequentially because of shared files.

| Surface | Shared with restore-exploration-portrait-refs | Conflict handling |
| --- | --- | --- |
| Code | `AppClient.vue` and `use-person-focus.js` potentially | Keep catalog lookup changes separate from rendered-lineup membership and emphasis |
| Main specs | `openspec/specs/webclient-presence-rail/spec.md` | Preserve portrait/fallback scenarios while amending anchor/closure/handover assumptions |
| Integrated tests | `web/webclient-app/tests/app_client_presence_rail.test.js` | Add companion cases to the image-bearing and null-art cases, preserving non-party handover |
| Shared fixtures | `tests/store/protocol_fixtures.js`, Node `protocol_fixtures.js`, `stories/fixtures.js` potentially | Consume latest schema defaults; do not duplicate a fixture version switch |
| Stories | `stories/Core/PresenceRail.stories.js` potentially; `stories/Core/AppShell.stories.js` | Keep both real-image and lineup focus examples |
| Documentation | `docs/development/frontend-vue-architecture.md`, frontend developer guide potentially | Preserve protocol/catalog notes while extending the companion-lineup section |
| Browser files/fixtures | `web/tests/browser/test_browser_exploration_nav.py` and its synthetic seed/helpers | Reuse first proposal's art-bearing fixture; distinct lifecycle assertions |
| Manifests | `.github/browser-shards.json`; `.github/evennia-shards.json` only if existing module ownership changes | Sequential merge of exact method labels; no standalone manifest refactor |

`webclient-contextual-hud`, `CompanionLineup.vue`, `companion-lineup.js` and its focused tests belong to this slice; exploration producer/validators, completion push and schema versioning belong to the portrait slice. Planning artifact directories do not overlap.
