# Design: a deterministic farewell beat when the dream ends

## Context

- `world/narrative/dream_surface.py::dream_state` computes
  `ending = render_ending(view.completed)` when the session is not open and
  sets `"ending"` to one of two fixed sentences (with or without climax) and
  `"ending_phase"` to `ending.phase`. `DreamEnding.climax_reached` is the
  existing ending phase switch.
- `server/dream_service.py::act` ends `confirm` and `awaken` with
  `state = dream_state(actor); text = state["ending"] or <draft message>;
  actor.msg(text)`, so whatever `ending` holds is already delivered once
  through ordinary output (which is what the browser's message log and the
  text client show). `commands/dream.py::render_state` prints
  `state["ending"]` for an ended dream. Neither file needs a change.
- `AppClient.vue` mounts
  `<DreamPanel v-if="panel('dream')?.state?.open" :state="panel('dream').state" :store="store" />`
  and uses `!panel("dream")?.state?.open` in `landmarkCardOpen`.
  `composables/use-sleep-handoff.js` computes
  `dreamOpen = !!store.view?.panels?.dream?.state?.open`.
  `composables/use-app-client.js` wires the composables.
- `components/DreamPanel.vue` (after `dream-wish-change-report`) is the
  prototype port without the farewell. The prototype
  (`docs/design/dream-proposal-coediting/DreamWishPrototype.vue`) contains
  the reference farewell: `leaving`, `departed`, `depart`, the watcher on
  `props.state.open`, the `dream-scene--leaving` / `dream-scene--departed`
  classes, `dream-scene__wishlight`, `dream-scene__waking` and their CSS. It
  reads `state.farewell` and `state.outcome`, which do not exist on the real
  wire.
- Review document for the six lines and the transition: the "Farewell"
  section of
  `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md` and
  Storybook `Design/DreamWish` (`FarewellGranted`, `FarewellKept`).

## Goals / Non-Goals

**Goals:** the server line, the browser farewell state, text parity through
the existing `ending` field.

**Non-Goals:** a new wire field or schema bump (the line travels in `ending`,
a string the validator already bounds at 2048 code points); any change to
`server/dream_service.py`, `commands/dream.py`, the departure transaction,
sleep continuation or the dream track; a generated closing line.

## Decisions

1. **Server line.** In `dream_surface.py` add (verbatim; human-reviewed
   copy):

   ```python
   FAREWELL_LINES = {
       ("confirmed", False): "「去吧。這個願望我收下了。醒來之後，它會在路上等你。」",
       ("draft", False): "「願望先替你收著。下次入夢，再接著說給我聽。」",
       ("empty", False): "「空著手也無妨。雲海一直都在。」",
       ("confirmed", True): "「……哈啊。這個願望，我收下了。去吧，醒來之後，它會在路上等你。」",
       ("draft", True): "「……哈啊。願望先替你收著。等我緩過氣來，下次入夢再接著說給我聽。」",
       ("empty", True): "「……哈啊。空著手也無妨。雲海一直都在，我也是。」",
   }

   def farewell_line(outcome: str, climax_reached: bool) -> str:
       return FAREWELL_LINES[(outcome, bool(climax_reached))]
   ```

   In `dream_state`, for a session that is not open:
   `outcome = "confirmed" if confirmed else "draft" if (session.draft_id and
   not dream_proposal.is_empty(proposal)) else "empty"` and
   `"ending": farewell_line(outcome, ending.climax_reached)`. For an open
   session `"ending"` stays `""`. `"ending_phase"` is unchanged. Remove the
   two old ending sentences.

2. **Composable `composables/use-dream-farewell.js` (new, verbatim API).**

   ```js
   export function useDreamFarewell(store)
   // returns { state, held, active, release }
   ```

   - `live = computed(() => store.view?.panels?.dream?.state ?? null)`.
   - `held = ref(null)`: a deep copy
     (`JSON.parse(JSON.stringify(...))`) of the closed state being presented.
   - One watcher over `[live.value?.session_id ?? null, !!live.value?.open]`
     (not `immediate`): when the new state is open → `held.value = null`;
     otherwise when the previous tuple was open, the session id is unchanged
     and `live.value?.ending` is non-empty → `held.value` = the copy of
     `live.value`. A first value that is already closed never sets `held`.
   - A watcher on `store.view.connected`: `false` → `held.value = null`.
   - `state = computed(() => (live.value?.open ? live.value : held.value))`.
   - `active = computed(() => !!state.value)`.
   - `release()` sets `held.value = null`.

3. **Mount.** Create the composable once in `use-app-client.js`
   (`const dreamStage = useDreamFarewell(store)`), expose `dreamStage`, and
   pass `dreamActive: dreamStage.active` in the options of
   `useSleepHandoff`. In `AppClient.vue` the mount becomes
   `<DreamPanel v-if="dreamStage.state.value" :state="dreamStage.state.value" :store="store" @departed="dreamStage.release" />`
   and `landmarkCardOpen` uses `!dreamStage.active.value` in place of
   `!panel("dream")?.state?.open`. In `use-sleep-handoff.js`,
   `dreamOpen` becomes
   `computed(() => !!store.view?.panels?.dream?.state?.open || !!dreamActive?.value)`
   (the new option defaults to `undefined`).

4. **Panel farewell state.** Port from the prototype into
   `components/DreamPanel.vue`: `defineEmits(["departed"])`, `leaving`,
   `departed`, the classes `dream-scene--leaving` / `dream-scene--departed`,
   `data-state` value `farewell` when leaving, `:data-leaving`,
   `:inert="!!leaving || undefined"` on the keepsake card,
   `v-if="!leaving"` on the reply zone, the `leaving` branches of the re-read
   control, key hint (`Enter 醒來` once the line is shown in full), marker
   and toast, `if (leaving.value) return;` in the Escape branch,
   `!leaving.value &&` in the digit branch, and the CSS rules for these
   classes. Differences from the prototype:
   - The watcher on `props.state.open` reads `props.state.ending` where the
     prototype reads `props.state.farewell`, and sets
     `leaving.value = props.state.confirmed ? "confirmed" : "awaken"`. It
     closes every layer (`sheetOpen`, `confirmOpen`, `viewOpen`, `takeOpen`,
     `threadOpen`, `artOpen`), presents
     `[{ kind: "line", text: props.state.ending }]` with typing, announces
     `王座上的女神說：` + the text and focuses the band.
   - `const motionFull = computed(() => props.store.view.motionLevel === "full")`.
     `depart()`: when already departed → `emit("departed")`; otherwise set
     `departed.value = true` and, when `!motionFull.value`,
     `emit("departed")` at once.
   - `<div v-if="leaving === 'confirmed' && motionFull" class="dream-scene__wishlight" aria-hidden="true"></div>`
     and
     `<div v-if="departed && motionFull" class="dream-scene__waking" aria-hidden="true" @animationend="emit('departed')"></div>`.
   - `advance()` calls `depart()` when leaving and no beat remains, as in the
     prototype. A second activation after `departed` therefore releases even
     if no `animationend` arrives.
   The component never dispatches during the farewell.

5. **Tests.**
   - `world/narrative/tests/test_dream_surface.py`: one test per scenario of
     the `dream-sleep-surface` delta. They compare ending texts with each
     other and with `""`; they never compare with a literal line. Replace the
     existing assertions that look for `醒了` in `ending`.
   - `web/webclient-app/tests/dream_farewell.test.js` (new): the composable
     with a reactive fake store — live open→closed same session with ending
     (held, `active` true), first value already closed (not held), different
     session id (not held), empty ending (not held), disconnect clears, a new
     open state clears, `release()` clears.
   - `web/webclient-app/tests/dream.test.js`: panel cases for the farewell
     scenarios, mutating the reactive `state` prop from open to closed. The
     full-motion release is asserted by dispatching an `animationend` event
     on the fade element and, separately, by a further activation; no timers
     or real time.
   - Extend the existing AppClient sleep-handoff test file
     (`tests/app_client_sleep_handoff.test.js`) with one case that the
     handoff cards stay closed while a farewell is held and open after
     `departed`.
   - `web/webclient/tests/test_vue_dream_stage_evidence.py`: one new bridge
     method listing the farewell Vitest cases of both files, without
     `covers_requirement`.

6. **Stories.** Add `FarewellGranted` and `FarewellKept` to
   `stories/World/DreamPanel.stories.js`: the story server's `dream.confirm`
   and `dream.awaken` set `open: false`, `confirmed` accordingly and a
   synthetic `ending` string from the story fixtures; the stories reach the
   state by a delayed publication after mount (as the prototype's `leave`
   argument does), and the wrapper shows a restart button on `departed`.

## Risks / Trade-offs

- [The fade's `animationend` might never fire] → a further activation
  releases the stage (decision 4), and non-full motion never waits for it.
- [Waking surfaces are held behind the farewell] → they already yield to an
  open dream; the committed state beneath is unchanged and appears on
  release.
- [The closing copy is new game text] → human review named in proposal.md;
  tests select by key, not by wording.
