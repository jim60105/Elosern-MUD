## Context

See proposal.md for motivation. The frontend already has an admitted-request loading pin for concept apply and a separate completion-publish latch. The server already guarantees result-only name rolls through the namegen-creation-ui design D10 / `no_presentation`; neither protocol nor draft state needs to change.

### Confirmed root cause (verbatim)

1. `rollName()` in `web/webclient-app/composables/use-creation-dispatch.js:36-54` dispatches `creation.roll_name` via `props.dispatch` → store `dispatchAction`, which calls `ctx.publishView()` synchronously in its `finally` (`web/webclient-app/stores/elosern/transport.js:427`).
2. Every `publishView()` builds a FRESH `view.creationView` object (`web/webclient-app/stores/elosern/view.js:294-303`), so `props.stage` object identity changes on every publish even when the stage value is unchanged.
3. The stage-mirror watcher in `web/webclient-app/composables/use-creation-stage.js:31-64` watches `props.stage` object identity with a `lastStage` value gate initialized to `null`. Pointer tab clicks go through overlay-local `setMode('custom')` only — they never touch the watcher or the store's `ctx.creation.view`, so `lastStage` stays `null`.
4. The 🎲 click's synchronous publish is therefore the FIRST publish after mount carrying a stage value (`"root"` — roll_name is result-only, zero draft, dock never moves): `"root" !== lastStage(null)` passes the gate → `mode.value = "preset"` → tab kicks back to the first tab.
5. The existing in-flight pin (from change `retool-concept-fill-navigation`) guards only `conceptPending` (`use-creation-stage.js:47`). The roll flow's flag `rollPending` lives in `use-creation-dispatch.js` and was never wired into the stage group → the roll click has zero protection.

Precedent: `web/webclient-app/tests/overlays/concept_fill_navigation.test.js:1-20` documents the identical fresh-creationView / synchronous-finally-publish / null-gate race for concept apply. Its in-flight pin and `latchedStage` completion latch never covered name rolls.

## Goals / Non-Goals

**Goals:** Preserve the pointer-selected custom tab throughout an admitted name roll and settlement without disturbing request-ID backfill, dispatch admission, concept completion navigation, or subsequent keyboard-driven stage changes.

**Non-Goals:** No store publication redesign, stage initialization workaround, new latch, new loading state, draft mutation, backend/protocol change, text-command change, compatibility layer, or migration. Do not broaden this into a composable refactor or alter result/gate settlement semantics.

## Decisions

### D1: Extend the existing in-flight stage pin with the dispatch-owned roll flag

Pass the existing `rollPending` ref from the dispatch group into `useCreationStage` through the overlay facade, following the existing shared-box convention illustrated by `latchedStage` in `use-creation-form.js:33`. Extend the watcher's pin condition from `conceptPending.value` to `conceptPending.value || rollPending.value`. Keep the pin branch's `lastStage = value` assignment and leave the separate `latchedStage` branch intact. Update the watcher comments to describe both concept apply and name roll.

`useCreationOverlay` already constructs dispatch before stage, so the ref exists when the stage watcher registers; preserve this call order and watcher registration order. Reuse the ref rather than copy its value or introduce a second owner.

**Timing argument:** `rollName()` sets `rollPending = true` synchronously after dispatch admission (`use-creation-dispatch.js:47`), before Vue's pre-flush stage watcher runs, even though the store's finally-publish happened inside dispatch. The watcher therefore takes the existing pin branch on that first `"root"` publish and records `lastStage = "root"` without changing `mode`. At matching-result settlement or gate release, existing dispatch watchers clear `rollPending`; later publishes still carrying `"root"` are absorbed by the value gate, so clearing the pin causes no tail jump. A later actual stage-value change resumes normal mirroring. Name rolls need no completion-publish latch because they do not navigate on completion.

Initializing `lastStage` differently or changing store tab state would address this first-publish symptom by a different mechanism; neither reuses the established in-flight protection. A new latch or generic pending abstraction would add unnecessary state for this result-only flow.

## Risks / Trade-offs

- Vue scheduling is essential to this race → use a real-store AppClient harness, not a standalone overlay mock that bypasses `dispatchAction` and its synchronous publish. Keep the test input untouched before rolling so touched-field protection cannot mask the null-gate race.
- Clearing `rollPending` before the settlement stage watcher runs could expose stale-stage mirroring → retain the pin branch's stage-value recording and assert the custom tab after settlement, gate release, and a further unchanged-stage publish.
- Extending a shared navigation guard could affect concept or keyboard behavior → retain `latchedStage` and existing concept-navigation coverage, and run the Vitest suite. The pin ends with the existing roll loading state; no permanent navigation lock is introduced.

## Validation Approach

Add a real-store test in `web/webclient-app/tests/overlays/creation_overlay.test.js`, mirroring the AppClient/fake-transport harness in `concept_fill_navigation.test.js`. Enter creation with no draft, pointer-click the custom tab, click `.creation-roll-button` / `creation-roll-name`, and assert the creation surface's `data-mode` remains `custom` after the synchronous dispatch publish. Deliver a success result with the submitted `requestId` and `data.display_name`; assert backfill lands, the shared gate releases and the button re-enables, and `data-mode` remains `custom` through settlement and an additional unchanged-stage publish. Do not confuse the creation surface's tab mode with the shared action dock's shell `data-mode="creation"`.

Run `pnpm test` as the dev-time JS validation gate after implementation. No new Evennia test module is introduced, so `.github/evennia-shards.json` remains untouched. Command documentation remains untouched because `creation.roll_name` is an allowlisted UI action, not a player text command.
