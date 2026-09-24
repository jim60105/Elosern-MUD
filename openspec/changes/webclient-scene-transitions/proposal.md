## Why

After `webclient-motion-level` (C11a) the client has one motion level and a complete token vocabulary, but nothing on the stage moves yet:
- A new location swaps the backdrop bitmap in one frame, through a blank frame while the new image loads.
- The place card and the minimap jump.
- The message window replaces its page instantly.
- A new portrait pops in.
- The vitals island appears and disappears with `display` alone.

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §9.3) asks for the location-change row (backdrop crossfade, place card slide, minimap pan, message clear), the appearance-change row (portrait crossfade), and the vitals row (fade and a 12px slide). This change (C11b) adds those transitions. It also sets the rule that an element leaving the view is out of reach the moment its state commits, which C11c and C13 reuse.

**Implementation profile:** visual. The crossfade layering, the slide directions and distances, the pan feel, and the clear's look at the reference viewport need motion and look-and-feel judgement.

## What Changes

- New module `web/webclient-app/lib/transition_hooks.js`: `inertWhileLeaving`, a set of Vue `<Transition>` hook props.
  - `onBeforeLeave` sets `inert` on the leaving element.
  - `onAfterLeave` and `onLeaveCancelled` clear it, and `onBeforeEnter` clears it on the entering element.
  - Every transition this change adds binds it, so a leaving copy is outside the accessibility tree, the tab order, and pointer hit-testing while it animates.
- New pure module `web/webclient-app/lib/map_pan.js`: `panOffset(prev, next)`. It returns the translation, in the new drawing's user units, that puts the previous current node back where it was on screen. It returns `null` when that node is absent from the new placement.
- `web/webclient-app/components/SceneBackdrop.vue`:
  - The scene image becomes a two-layer crossfade over `--motion-scene`: a `<Transition name="scene-xfade">` keyed by the shown URL, with the leaving layer absolutely stacked under the entering one.
  - A new URL is decoded first (`HTMLImageElement.decode()` when available). Until it is decoded, the previous image stays up with the existing dimmed treatment, so the fade never runs over a blank frame and an old scene is never shown as current.
  - The scene label, alt text, placeholder, and `pending` rules are unchanged, and they update at commit.
- `web/webclient-app/components/PlaceCard.vue` (C4b): the location heading is keyed by the location label inside a `<Transition name="place-card">`.
  - The new heading slides in from the left (`--motion-shift-lg`) and fades in over `--motion-reveal`, and the old one fades out.
  - A time-only change does not animate.
- `web/webclient-app/components/MapLattice.vue` gains a `panOnMove` prop, which `LocalMap.vue` sets in minimap mode only. When the committed current node changes and the previous current node is in the new placement, the drawing group starts translated by `panOffset` and eases to rest over `--motion-base`. The translation is multiplied by `--motion-travel`, so `reduced` and `off` snap. The full-map overlay does not pan.
- `web/webclient-app/components/MessageWindow.vue`: the page content is keyed by the response inside a `<Transition name="message-clear">`.
  - When a new response replaces the previous one, the previous page's content leaves as an opaque, inert layer over the new page and fades out over `--motion-clear`.
  - The new page mounts and starts typing at once, so no latency is added.
  - This runs on every new response, not only on a location change (coordinator-approved, design D4).
  - The focusable page surface is not keyed and keeps focus.
- `web/webclient-app/components/StageActor.vue` (C10b):
  - The portrait is keyed by its source (the image URL, or the placeholder label) inside a `<Transition name="actor-xfade">`, crossfading over `--motion-portrait`.
  - The speaking dim gains `transition: filter var(--motion-fast)`.
- `web/webclient-app/components/StatusPanel.vue` (C3): the root that carries C3's `v-show="visible"` is wrapped in `<Transition name="vitals-reveal" v-bind="inertWhileLeaving">`, so the island fades and slides 12px (`--motion-shift-sm`) over `--motion-reveal`. The `visible` prop, its binding in `AppClient.vue`, and C3's pre-flush focus rescue are unchanged.
- Stories:
  - `stories/Core/SceneBackdrop.stories.js` gains a `SceneChange` story.
  - `stories/Core/StageActor.stories.js` gains an `AppearanceChange` story.
  - `stories/Core/PlaceCard.stories.js` gains a `LocationChange` story.
  - `stories/Data/StatusPanel.stories.js` gains a `RevealToggle` story.
- Browser: a new `web/tests/browser/test_browser_scene_transitions.py` runs at `full`, `reduced`, and `off`. It asserts the in-flight layers, their inert state, and their computed durations, not wall-clock timing.
- No OOB schema, presenter, server, persistence, or component-manifest change. No component is added or deleted.

Out of scope:
- Exploration ↔ dialogue, exploration ↔ combat, the choices stagger, and the NPC's entrance: `webclient-mode-transitions` (C11c).
- Combat beats: `webclient-combat-beat-playback` (C13).
- The motion level, the tokens, and the presentation-timing contract: `webclient-motion-level` (C11a).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - ADDED "Location, appearance, and vitals changes transition at the motion level"
  - ADDED "A leaving element is out of reach while it animates out"
  - MODIFIED "The vitals island is shown only in combat or while a vital or a condition needs attention" (main spec, from the archived C3). The island leaves the accessibility tree at commit and reaches `display:none` when its exit transition ends.
  - MODIFIED "The message window presents the current response one page at a time in the band's message region" (C10c text). The previous page may remain only as the clear transition's fading, inert layer.

## Impact

- New:
  - `web/webclient-app/lib/transition_hooks.js`, `web/webclient-app/lib/map_pan.js`
  - Vitest `web/webclient-app/tests/transition_hooks.test.js`, `web/webclient-app/tests/map_pan.test.js`, `web/webclient-app/tests/scene_transitions.test.js`
  - `web/tests/browser/test_browser_scene_transitions.py`
- Edited source:
  - `web/webclient-app/components/{SceneBackdrop,PlaceCard,MapLattice,LocalMap,MessageWindow,StageActor,StatusPanel}.vue`
- Stories: `stories/Core/SceneBackdrop.stories.js`, `stories/Core/StageActor.stories.js`, `stories/Core/PlaceCard.stories.js`, `stories/Data/StatusPanel.stories.js`.
- Tests edited:
  - Vitest: `tests/scene_backdrop.test.js`, `tests/core/stage_actor.test.js`, `tests/place_card.test.js` (C4b), `tests/message_window.test.js`, `tests/data/status_panel.test.js` (C3)
  - Python: `web/webclient/tests/test_node_suite_evidence.py`
  - `.github/browser-shards.json`
- Spec traceability: two new IDs, covered by the evidence test and the new browser file. The two modified titles are unchanged.
- Dependencies:
  - Archive order: C10c → C11a (`webclient-motion-level`) → C11b (this change) → C11c (`webclient-mode-transitions`).
  - Hot-spot files shared with C10b, C10c, and C11c: `MessageWindow.vue`, `StageActor.vue`.
