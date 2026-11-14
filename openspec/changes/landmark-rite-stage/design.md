# Design

## Context

Approved interface: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §12.2 and the prototype `docs/design/landmark-rites/LandmarkRitesPrototype.vue`, which composes the real `HudFrame`, `CompanionLineup`, `MessageWindow` and `useAuthoredScene` and is the reference for every slot and prop this change binds.

Existing code, read on 2026-11-14:

- `web/webclient-app/AppClient.vue` (the shell). `AppShell` receives, among others, `:mode="store.view.mode || 'exploration'"`, `:narrative="store.narrative"`, `:response-marks`, `:dialogue="dialogueVM"`, `:scene="scenePresentation"`, `:scene-hold="sceneHold"`, `:card-open="... || landmarkCardOpen || campOpen"`, `:travel="travelLayout"`, `:travel-log`, `:speaker`, and `@scene-advance="onSceneAdvance"`. `AppShell` forwards `mode`, `dialogue`, `scene`, `sceneHold`, `speaker` and the lines to `MessageWindow` and the layout props to `HudFrame`.
- Slots filled by `AppClient.vue`: `#backdrop` (`SceneBackdrop`, then the `TravelMap` in the travel layout), `#actor-left` (`CompanionLineup`, `v-if="store.view.mode !== 'creation' && !travelLayout"`), `#choices` (a `v-if`/`v-else-if` chain; `LandmarkCard` is `v-else-if="landmarkCardOpen"`), `#map` (rendered by `AppShell` directly under `PlaceCard`).
- `landmarkArrival` / `landmarkCardOpen` / `onLandmarkContinue(id)` and `store.dismissTravelArrival(id)`: the generic landmark card's state. `landmarkCardOpen` already waits for the dream and the sleep-handoff cards.
- `web/webclient-app/stores/elosern/camp.js` is the model of a store group that dispatches one action and adopts its result: `ctx.dispatchAction(actionId, payload, null)` returns a request id or a falsy value; the committed result is read from `rs.lastActionResult` (`requestId`, `epoch`, outcome, `data`) and matched to the pending `{requestId, epoch, generation}`; `ctx.publishView()` publishes the group's view. `web/webclient-app/stores/elosern.js` composes the groups (`applyTravelLog(ctx)` and its neighbours).
- `web/webclient-app/composables/use-authored-scene.js`: `useAuthoredScene(source)` with `source.value = {playable, generation, contextId, delivery, npcId, actorName, hostName, bondStage}`; returns `presentation`, `advance()`, `active`, `speaker`, `onSceneFinished(handler)`. `isAuthoredDelivery` requires `kind` in `["formal", "refusal"]` and non-empty `lines`; the playback key uses `delivery.delivery_id`.
- `web/webclient-app/composables/use-window-hotkeys.js`: one document `keydown` listener with the shared guards (no modifier, no repeat, no text entry, no modal, no open drawer). `LETTER_CODES` maps letters to codes.
- Components of `landmark-rite-surfaces`: `RiteArrivalCard` (`rite`, `artPanel`, `revisit`, `entrance`; `approach`, `leave`), `RitePanel` (`rite`, `performer`, `entrance`; `perform`, `leave`), `RiteBackdrop` (`rite`, `artPanel`), `ritePerformers(rite)`.
- The rite store group of `landmark-rite-store`: `view.rite` (`panel`, `phase`, `revisit`, `pending`, `delivery`, `playing`) and the store methods `openRiteCard`, `approachRite`, `leaveRite`, `performRite(optionKey, memberId)`, `finishRiteScene`.
- Other readers of `store.view.mode` in `AppClient.vue` that the `AppShell :mode` override does not reach: the `stageMode` computed (feeds `SceneBackdrop`), the `ActionDock` `:mode`, `DesktopNavigation` `:mode`, the `vitals-visible` binding, the mode watcher near the dialogue focus code, and `inDialogue`.

## Goals / Non-Goals

**Goals**

- The whole approved flow mounted in the client shell, with the controlled character as performer.
- Rite presentation state is local and derived: it never survives leaving the landmark and never sends anything except the one action.

**Non-Goals**

- No performer picking on the stage, no arrow-key stepping, no `member_id` other than `null` (`landmark-rite-performer-picking`).
- No "newly lit" line and no change to how districts light (`landmark-rite-lighting`).
- No change to `LandmarkCard.vue`, the travel store's arrival slot or the `travel_log` panel (`landmark-rite-arrival-signal-removal`). `LandmarkCard` stays as the card for an arrival whose `rite` panel is unavailable.
- No new scene renderer, pager or typewriter. Playback is `useAuthoredScene` and `MessageWindow` only.
- No auto-play of a delivery found in the panel on a reconnect: a reconnecting client shows the options and the return entry.
- No store logic (`landmark-rite-store`) and no managed browser test (`landmark-rite-journeys`).
- No change to `AppShell.vue`, `HudFrame.vue`, `MessageWindow.vue` or `CompanionLineup.vue`. If one of them cannot be driven through its existing props for a step below, stop and report; do not fork its behaviour.

## Decisions

### D2. Shell composable (`web/webclient-app/composables/use-rite-stage.js`)

`useRiteStage({store, panel, travelLayout, blocked})` where `blocked` is a computed that is true while the dream or a sleep-handoff card owns the choices anchor (the same three sleep-handoff flags and `dreamStage.active` that `landmarkCardOpen` reads). It returns:

```js
{
  rite,            // computed: store.view.rite.panel
  cardOpen,        // computed: phase === "card" && !blocked
  onStage,         // computed: phase === "stage"
  panelShown,      // computed: onStage && !playing && !pending
  entryShown,      // computed: rite && phase === "closed" && store.view.mode === "exploration"
  performer,       // computed: ritePerformers(rite)[0]
  lines,           // computed: [{kind: "out", text: rite.guardian.form, seq: 1}]
  dialogueModel,   // computed: {host: {displayName: rite.guardian.name}, bondStage: null}
  scene,           // useAuthoredScene(source)
  sceneHold,       // computed: !!store.view.rite.pending
  approach, leave, perform, openEntry, advance,
}
```

`source` is a computed: `{playable: onStage && playing, generation: store.view.generation, contextId: "rite:" + rite.district.key, delivery: delivery ? {...delivery, phase_revision: null} : null, npcId: null, actorName: delivery?.actor_name ?? "", hostName: delivery?.guardian_name ?? "", bondStage: null}`. Register `scene.onSceneFinished(() => store.finishRiteScene())` and dispose it with `onScopeDispose`.

`approach` / `leave` / `openEntry` call the store methods; `perform(key)` calls `store.performRite(key, null)`; `advance()` calls `scene.advance()`.

### D3. `AppClient.vue` bindings

Create `const riteStage = useRiteStage({...})` beside the landmark arrival block. Then change exactly these bindings (everything else stays):

| Binding | New value |
| --- | --- |
| `AppShell :mode` | `riteStage.onStage.value ? "dialogue" : (store.view.mode \|\| "exploration")` |
| `AppShell :narrative` | `riteStage.onStage.value ? riteStage.lines.value : store.narrative` |
| `AppShell :response-marks` | `[]` on the stage, else as now |
| `AppShell :dialogue` | `riteStage.dialogueModel.value` on the stage, else `dialogueVM` |
| `AppShell :scene` | `riteStage.scene.presentation.value` on the stage, else `scenePresentation` |
| `AppShell :scene-hold` | `riteStage.sceneHold.value` on the stage, else `sceneHold` |
| `AppShell :speaker` | `riteStage.scene.active.value ? riteStage.scene.speaker.value : "host"` on the stage, else as now |
| `AppShell :travel` | `travelLayout && !riteStage.onStage.value` |
| `AppShell :travel-log` | `null` on the stage, else as now |
| `AppShell :card-open` | add `\|\| riteStage.cardOpen.value` |
| `AppShell @scene-advance` | `riteStage.advance()` on the stage, else `onSceneAdvance()` |
| `landmarkCardOpen` | add `&& !riteStage.rite.value` |
| `#backdrop` | on the stage render `RiteBackdrop` (`:rite`, `:art-panel="panel('art')"`) above `SceneBackdrop` and do not render the `TravelMap` |
| `#actor-left` `CompanionLineup` `v-if` | `store.view.mode !== 'creation' && (!travelLayout \|\| riteStage.onStage.value)` |
| `#choices` | before the `LandmarkCard` branch: `RiteArrivalCard v-else-if="riteStage.cardOpen.value"` (`:rite`, `:art-panel`, `:revisit="store.view.rite.revisit"`, `:entrance="!modeHydrating && store.view.motionLevel !== 'off'"`, `@approach`, `@leave`); `RitePanel v-else-if="riteStage.panelShown.value"` (`:rite`, `:performer`, `:entrance`, `@perform`, `@leave`) |
| `#map` | first child: `RiteEntry v-if="riteStage.entryShown.value"` (`:guardian="riteStage.rite.value.guardian.name"`, `@open="riteStage.openEntry"`) |

Put the ternaries in computeds inside the script (for example `shellMode`, `shellNarrative`) so the template stays readable.

When the rite card opens for a district while `landmarkArrival` holds an arrival, dismiss that arrival with `store.dismissTravelArrival(landmarkArrival.value.id)` in a `watch` on `riteStage.cardOpen`, so the generic card never opens later for the same arrival.

Focus: after `leave` returns the phase to closed, apply the rule `onLandmarkContinue` applies (focus the travel map through `travelMapRef` in the travel layout unless another surface already took focus; in a room, focus the `RiteEntry` button).

The other `store.view.mode` readers named in Context keep the committed exploration mode, with these consequences to handle here: `inDialogue` stays false, so the line-up is not `compact` and no dialogue host stands on the right (correct: the guardian has no figure); `stageMode` stays exploration, which is correct because `RiteBackdrop` covers `SceneBackdrop`; the `ActionDock` must not be operable on the stage, so add `!riteStage.onStage.value` to its `v-if` (the dialogue presentation already recedes its anchor); `DesktopNavigation` and the vitals keep their exploration behaviour.

### D4. `RiteEntry.vue` and the R key

`components/rite/RiteEntry.vue`: one button, the prototype's `.rite-proto__entry` markup and styles renamed `.rite-entry`: a decorative gem, the text `<guardian> 儀式` with the guardian name emphasised, and a `kbd` `R` (`aria-hidden`). `aria-label="<guardian> 儀式"`, `data-testid="rite-entry"`, emits `open` on click. Add an `Entry` story to `stories/World/LandmarkRite.stories.js`.

`use-window-hotkeys.js`: add `r: "KeyR"` to `LETTER_CODES` and a `KeyR` branch that calls a new optional handler option (`onRiteEntry`) under the same shared guards; `AppClient.vue` passes a handler that calls `riteStage.openEntry()` only while `riteStage.entryShown.value`. The key does nothing otherwise.

### D5. Tests

`tests/app_client_rite.test.js` (mount the client the way `tests/app_client_sleep_handoff.test.js` does): arrival opens `rite-arrival-card` and no `landmark-card`; Escape closes it and shows `rite-entry`; R reopens it with the revisit kicker; Enter enters the stage: the frame takes the dialogue presentation, the companion line-up is mounted although the layout is travel, `rite-backdrop` and `rite-panel` are mounted and the travel map is not; digit 1 sends one action; the committed success result unmounts the panel and the message window shows the first scene line; advancing through every line remounts the panel with focus in it; Escape on the panel returns to the map with `rite-entry` shown; a panel that becomes unavailable unmounts everything; a sleep-handoff card keeps the rite card closed until it is dismissed.

### D6. Agent guide

Extend the rite paragraph of `web/webclient-app/AGENTS.md` with the store group, the composable, the rule that the stage is local presentation over exploration mode, and the return entry.

## Risks / Trade-offs

- `AppClient.vue` is large and shared by every stage. The change is confined to the bindings of D3 and one composable; the two serial follow-up changes touch the same lines.
- The rite stage presents as dialogue while the server mode is exploration. The app-level test asserts that the action dock is not mounted on the stage. If another surface stays visible on the stage that the prototype does not show, hide it with `riteStage.onStage` in this change and name it in the hand-off.
