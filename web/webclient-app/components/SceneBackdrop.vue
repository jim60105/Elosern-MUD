<script setup>
// SceneBackdrop (H1, webclient-hud-01-shell-and-scene; scene rendering owned by
// change unified-scene-rendering): the full-bleed cinematic stage backdrop.
//
// It is a RENDERER of the committed `art` panel's scene descriptor and of the
// shared loading core's own result — nothing more. The scene resolution walks
// the ordered source chain (room override, generated archetype, operator
// default, required bundled type, declared terminal) behind the descriptor, and
// the loading core (`useArtwork`) owns the ordered attempt walk, the reached
// faults and the exhausted state; this component only decides WHAT IS ON
// SCREEN:
//
//   * the current successful candidate, as soon as it is at least as high a
//     priority as the retained content;
//   * otherwise the retained content — the good image the player is already
//     looking at, which the backend still authorizes for this exact logical
//     place and generation subject (`lib/scene-artwork.js`);
//   * otherwise this scene's own provisional bundled/terminal background while
//     a higher-priority source is still loading;
//   * otherwise the mode's gradient stage with a truthful status badge.
//
// A scene the backend no longer authorizes discards its pixels on the commit
// that changed it (a new logical place, a removed room binding, a revoked
// source), so previous-place art can never be shown as the current scene and a
// move never crossfades across places. A reached failure stays visible beside
// the healthy fallback that follows it, expected absence carries no error
// styling at all, and an unavailable panel is its own local indication —
// never a synthesized "not generated yet".
//
// The scene full view shares this same displayed resource and failure state:
// there is no second resolution, and it never opens a broken-image-only view.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { artworkAvailability } from "../lib/artwork.js";
import { artworkFailureCategory } from "../lib/artwork-failure.js";
import { applicableRetained, displayedScene, retainedEntry } from "../lib/scene-artwork.js";
import { useArtwork } from "../composables/useArtwork.js";
import { inertWhileLeaving } from "../lib/transition_hooks.js";

const props = defineProps({
  // The committed `art` v4 panel payload: `available: true` carries the
  // canonical `scene` descriptor block plus `portrait_catalog`; the
  // registry-unavailable form carries `available: false` + `reason`.
  art: { type: Object, required: true },
  // The committed mode (the store's reducer mode). Selects the gradient
  // stage for degraded scenes (design D7: the gradient stage differs per mode)
  // and decides whether the art surface is REQUIRED at all: a creation-pending
  // shell has no committed scene surface, so its absence is expected rather
  // than a failure.
  mode: { type: String, default: "exploration" },
  // The EFFECTIVE motion level (`store.view.motionLevel`): at `off` the
  // transition has no CSS phase, so the final state is on screen in the
  // commit's frame.
  motionLevel: { type: String, default: "full" },
});

// The current mode's gradient stage token (design D7/D10): the always-correct
// base layer beneath every image.
const stageGradient = computed(() => {
  if (props.mode === "combat") {
    return "var(--stage-gradient-combat)";
  }
  if (props.mode === "creation") {
    return "var(--stage-gradient-dialogue)";
  }
  return "var(--stage-gradient-explore)";
});

const unavailable = computed(() => props.art?.available === false);
const sceneView = computed(() => (unavailable.value ? null : (props.art?.scene ?? null)));
const artwork = computed(() => sceneView.value?.artwork ?? null);

// The shared availability input: a required scene surface whose committed
// panel is missing/unavailable, or whose committed scene carries no descriptor
// at all, is a FAILURE (the panel-level availability indication), never a
// synthesized generation progress. A mode that does not require the surface is
// expected absence.
const availability = computed(() =>
  artworkAvailability({
    panel: props.art,
    required: props.mode !== "creation",
    hasReference: true,
    artwork: artwork.value,
    viewSubjectId: artwork.value?.subject_id ?? null,
  }),
);

// The ONE provisional source of this scene: its own required bundled type
// illustration, or — for a scene whose bundled image is unavailable — its
// declared terminal image. Nothing else is ever fetched outside the ordered
// walk, so a provisional request can never displace a higher-priority source
// or issue a duplicate attempt for one.
const provisionalSource = computed(() => {
  const descriptor = artwork.value;
  if (!descriptor) {
    return null;
  }
  const attempts = Array.isArray(descriptor.attempts) ? descriptor.attempts : [];
  const bundled = attempts.find(
    (entry) => entry?.type === "image" &&
      entry.resource?.url &&
      String(entry.source_id ?? "").startsWith("scene.bundled:"),
  );
  if (bundled) {
    return bundled.resource;
  }
  const terminal = descriptor.terminal;
  if (terminal?.kind === "scene_image" && terminal.resource?.url) {
    return terminal.resource;
  }
  return null;
});

const load = useArtwork(artwork, availability, { provisionalSource });
onBeforeUnmount(() => load.dispose());

// The retained display content: the last successful image this backdrop is
// authorized to keep. It is re-validated against EVERY committed descriptor,
// so authorization loss (a move, a removed binding, a revoked source) drops it
// synchronously, and a lower-priority successful fallback never displaces it.
const retained = ref(null);
watch(
  [artwork, () => load.selected.value],
  () => {
    retained.value = retainedEntry(retained.value, artwork.value, load.selected.value);
  },
  { immediate: true },
);

const display = computed(() =>
  displayedScene({
    // The retained entry is re-validated against the COMMITTED descriptor at
    // read time, so a commit that revokes its authorization (a move, a removed
    // binding, a changed token) can never paint the previous place's pixels —
    // not even for the one frame a watcher might lag behind.
    retained: applicableRetained(retained.value, artwork.value),
    selected: load.selected.value,
    provisional: load.provisionalSelected.value,
    available: availability.value.state,
  }),
);

// The crossfade is a SAME-PLACE replacement only.
//
// A committed bitmap may fade into its replacement while the logical place and
// the displayed pixels are the same scene's — a successful candidate replacing
// this scene's own provisional background, or a same-scene replacement. Every
// other swap renders instantly: a move, an authorization loss or a dropped
// image must never leave the previous place's painting fading across the
// stage, so those swaps have no CSS phase at all and their outgoing layer is
// gone in the commit's frame.
const crossfade = ref(false);
let shownPlace = null;
watch(
  () => [display.value?.url ?? null, artwork.value?.subject_id ?? null],
  () => {
    const place = artwork.value?.subject_id ?? null;
    crossfade.value = !!display.value && shownPlace !== null && place === shownPlace;
    shownPlace = display.value ? place : null;
  },
  { immediate: true },
);

// The crossfade phase's own hooks.
//
// The swap's enter/leave is driven from here rather than from transition
// classes, so a swap that must NOT animate completes in the commit's frame
// (the hooks call `done` immediately) while a same-place replacement fades
// over the one motion-token duration the client's motion level publishes —
// with no case that can leave an outdated layer on the stage because a CSS
// phase never ended.
const transitionCss = computed(() => props.motionLevel !== "off");

function motionDurationMs() {
  if (typeof getComputedStyle !== "function" || typeof document === "undefined") {
    return 0;
  }
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--motion-scene").trim();
  const value = Number.parseFloat(raw);
  if (!Number.isFinite(value) || value <= 0) {
    return 0;
  }
  return raw.endsWith("ms") ? value : value * 1000;
}

const layerHooks = {
  onBeforeEnter(el) {
    el.inert = false;
  },
  onEnter(el, done) {
    if (!transitionCss.value || !crossfade.value) {
      done();
      return;
    }
    const duration = motionDurationMs();
    el.style.opacity = "0";
    void el.offsetWidth;
    el.style.transition = `opacity ${duration}ms var(--ease-standard)`;
    el.style.opacity = "1";
    setTimeout(done, duration);
  },
  onBeforeLeave(el) {
    el.inert = true;
  },
  onLeave(el, done) {
    if (!transitionCss.value || !crossfade.value) {
      done();
      return;
    }
    const duration = motionDurationMs();
    el.style.transition = `opacity ${duration}ms var(--ease-exit)`;
    el.style.opacity = "0";
    setTimeout(done, duration);
  },
  onAfterLeave(el) {
    el.inert = false;
  },
  onLeaveCancelled(el) {
    el.inert = false;
  },
};

// The layer that presents the scene: the displayed bitmap, rendered on its
// own so the same-place crossfade is one CSS phase of one element. A layer
// whose URL is the live ordered attempt (or the live provisional one) carries
// that element's token, so the shared driver observes the real load/decode of
// the element it issued; a retained or reused bitmap carries no token and
// settles nothing twice.
function layerFor(url, role, token) {
  return { url, role, token };
}

// The root element, so the already-loaded check below can read the real
// elements this component rendered.
const rootEl = ref(null);

const presented = computed(() => {
  const shown = display.value;
  if (!shown) {
    return null;
  }
  const ordered = load.attempt.value;
  const provisional = load.provisionalAttempt.value;
  if (ordered?.url === shown.url) {
    return layerFor(shown.url, "attempt", ordered.token);
  }
  if (provisional?.url === shown.url) {
    return layerFor(shown.url, "provisional", provisional.token);
  }
  return layerFor(shown.url, "content", null);
});

// The hidden probes: one per resource currently being fetched that is not
// already on screen. They report the real natural dimensions the driver needs
// and never paint anything.
const probes = computed(() => {
  const shown = display.value;
  const out = [];
  for (const [candidate, role] of [
    [load.attempt.value, "attempt"],
    [load.provisionalAttempt.value, "provisional"],
  ]) {
    if (!candidate?.url || candidate.url === shown?.url) {
      continue;
    }
    out.push(layerFor(candidate.url, role, candidate.token));
  }
  return out;
});

// The scene label, the alternative text and the status facts always render as
// DOM text outside the bitmap.
const sceneLabel = computed(() => sceneView.value?.label ?? (unavailable.value ? "場景" : ""));
const sceneAlt = computed(() => sceneView.value?.alt ?? "");
const generationState = computed(() => artwork.value?.generation_state ?? "none");
const reachedFailure = computed(() => load.reachedFaults.value[0] ?? null);
const panelUnavailable = computed(
  () => load.panelUnavailable.value || availability.value.state === "failed",
);
const displayPresented = computed(() => !!display.value);

// One local indication for the state the backdrop is actually in:
//   * an unavailable panel is its own availability fact;
//   * a reached failure keeps its error marker even when a healthy fallback
//     follows it (the corrupt-override and failed-regeneration cases);
//   * expected absence says so plainly, with no error styling and no
//     "sample" label.
const failureText = computed(() =>
  panelUnavailable.value
    ? artworkFailureCategory("panel_unavailable")
    : reachedFailure.value
      ? artworkFailureCategory(reachedFailure.value.reason)
      : null,
);
// A resolution that is still walking its chain has NOT concluded anything, so
// it shows the stage's own gradient rather than a badge claiming absence: the
// status badge is for a reached failure, for the panel's own availability
// failure, and for a chain that genuinely ran out — never for the moment
// between a commit and its pixels.
const resolving = computed(
  () => load.phase.value === "loading" && !reachedFailure.value && !panelUnavailable.value,
);
// ONE local indication, never two: while a bitmap is on screen the reached
// failure is stated by the caption row's own leading fact, and the standalone
// status badge belongs to the states with nothing to show (the panel's
// availability failure, a chain that ran out, or a reached failure that left no
// image at all). A resolution that is still walking shows neither.
const showPlaceholder = computed(
  () =>
    panelUnavailable.value ||
    (!displayPresented.value && (!resolving.value || !!reachedFailure.value)),
);
const placeholderKind = computed(() =>
  panelUnavailable.value
    ? "panel_unavailable"
    : reachedFailure.value
      ? reachedFailure.value.reason
      : "missing",
);
const placeholderLabel = computed(() => failureText.value ?? "尚未生成");

// The caption row stands only for a real scene image. While one is on screen,
// the failure marker (if any) leads the row, and a pending regeneration states
// its factual progress there; the failure fact outranks the progress notice
// because it is the one the player must not miss.
const captionFailure = computed(() => (displayPresented.value ? failureText.value : null));
const generating = computed(
  () => displayPresented.value && !captionFailure.value && generationState.value === "pending",
);

// The full-view open state + the opener element for focus restore.
const fullViewOpen = ref(false);
const controlEl = ref(null);
const fullViewEl = ref(null);

watch(fullViewOpen, (open) => {
  if (open) {
    fullViewEl.value?.focus();
  }
});

// A display that is no longer a real image (a move to a scene with nothing to
// show, a revoked source, an unavailable panel) can never leave a full view
// open on a broken bitmap.
watch(display, (value) => {
  if (!value?.url && fullViewOpen.value) {
    closeFullView(false);
  }
});

// An element that ALREADY holds the bytes never fires another load.
//
// A commit can re-issue a load for a resource whose element is on screen and
// complete (the browser served it from its cache, or a re-resolution followed
// the first paint). Waiting for an event that will never come would leave the
// resolution parked on a resource it has, so every rendered layer whose
// element reports `complete` is reported to its owning driver once. The
// driver's own token and cursor checks make a repeated report a no-op.
function reportCompleteLayers() {
  const root = rootEl.value;
  if (!root || typeof root.querySelectorAll !== "function") {
    return;
  }
  for (const element of root.querySelectorAll("img[data-role]")) {
    if (!element.complete || !element.naturalWidth) {
      continue;
    }
    const url = element.getAttribute("src");
    const layer = [...probes.value, presented.value].find((item) => item?.url === url);
    if (layer) {
      onLayerLoad(layer, { target: element });
    }
  }
}

watch([probes, presented], () => {
  void nextTick().then(reportCompleteLayers);
}, { flush: "post" });
onMounted(reportCompleteLayers);

// Which shared driver owns one rendered layer's load/error observations.
function onLayerLoad(layer, event) {
  if (layer.role === "attempt") {
    load.onImageLoad(event);
  } else if (layer.role === "provisional") {
    load.onProvisionalLoad(event);
  }
}

function onLayerError(layer, event) {
  if (layer.role === "attempt") {
    load.onImageError(event);
  } else if (layer.role === "provisional") {
    load.onProvisionalError(event);
  } else if (layer.url === retained.value?.url) {
    // A retained source the browser can no longer load is a known failed
    // source: it stops authorizing itself and the next applicable source (or
    // the truthful status badge) takes its place.
    retained.value = null;
  }
}

function openFullView() {
  if (fullViewOpen.value || !displayPresented.value) {
    return;
  }
  fullViewOpen.value = true;
  void nextTick().then(() => fullViewEl.value?.focus());
}

function closeFullView(restoreFocus) {
  fullViewOpen.value = false;
  if (restoreFocus && controlEl.value instanceof HTMLElement && document.contains(controlEl.value)) {
    controlEl.value.focus();
  }
  controlEl.value = null;
}

function onControlKeydown(event) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openFullView();
  }
}

function onFullViewKeydown(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    closeFullView(true);
  } else if (event.key === "Tab") {
    // Focus trap: Tab cycles between the close button and the dialog root, so
    // keyboard users stay within the full view and cannot tab into the
    // recessed background HUD.
    const root = fullViewEl.value;
    const closeBtn = root?.querySelector(".scene-backdrop__fullview-close");
    if (!root || !closeBtn) {
      return;
    }
    const focusables = [closeBtn, root];
    const activeIndex = focusables.indexOf(document.activeElement);
    event.preventDefault();
    const next = event.shiftKey
      ? focusables[(activeIndex - 1 + focusables.length) % focusables.length]
      : focusables[(activeIndex + 1) % focusables.length];
    next.focus();
  }
}

// Seed the retained display content for the CURRENT committed scene (stories
// and acceptance journeys): the seeded pixels carry the descriptor's own
// retention authorization, so they behave exactly like content this browser
// really had on screen — they survive only while the backend still authorizes
// that source for this logical place.
function setPriorImage(url) {
  const descriptor = artwork.value;
  const source = Array.isArray(descriptor?.retention_sources)
    ? descriptor.retention_sources[0]
    : null;
  retained.value = {
    subjectId: descriptor?.subject_id ?? null,
    generationSubject: descriptor?.generation_subject ?? null,
    sourceId: source?.source_id ?? null,
    token: source?.token ?? null,
    rank: typeof source?.rank === "number" ? source.rank : 100,
    resourceId: null,
    version: null,
    url,
    geometry: null,
    dimensions: null,
  };
}

defineExpose({ openFullView, closeFullView, setPriorImage });
</script>

<template>
  <div
    ref="rootEl"
    class="scene-backdrop"
    data-testid="scene-backdrop"
    :data-available="unavailable ? 'false' : 'true'"
    :data-scene-state="generationState"
    :style="{ background: stageGradient }"
  >
    <!-- The presented bitmap: one element, one CSS phase per swap. A swap the
         spec does not allow to animate (a move, a revocation, the off motion
         level) has no CSS phase at all and is gone in the commit's frame. -->
    <Transition name="scene-xfade" :css="false" v-bind="layerHooks">
      <img
        v-if="presented"
        :key="presented.url"
        class="scene-backdrop__image"
        data-testid="scene-backdrop-image"
        :data-role="presented.role"
        :data-attempt-token="presented.role === 'attempt' ? String(presented.token) : null"
        :data-provisional-token="presented.role === 'provisional' ? String(presented.token) : null"
        :src="presented.url"
        alt=""
        aria-hidden="true"
        @load="onLayerLoad(presented, $event)"
        @error="onLayerError(presented, $event)"
      />
    </Transition>

    <!-- The probes: the resources the shared driver is fetching right now.
         Invisible, never presented, and never carrying the image test hook. -->
    <img
      v-for="probe in probes"
      :key="probe.url"
      class="scene-backdrop__image scene-backdrop__image--probe"
      :data-role="probe.role"
      :data-attempt-token="probe.role === 'attempt' ? String(probe.token) : null"
      :data-provisional-token="probe.role === 'provisional' ? String(probe.token) : null"
      :src="probe.url"
      alt=""
      aria-hidden="true"
      @load="onLayerLoad(probe, $event)"
      @error="onLayerError(probe, $event)"
    />

    <div
      v-if="showPlaceholder"
      class="scene-backdrop__placeholder"
      data-testid="scene-backdrop-placeholder"
      :data-kind="placeholderKind"
    >
      <p class="scene-backdrop__placeholder-label" data-testid="scene-backdrop-placeholder-label">
        {{ placeholderLabel }}
      </p>
    </div>

    <!-- The scene caption: one single-line plate holding the status facts, the
         scene label, the alternative text, and the full-view control. A label
         or alt text longer than the row truncates with an ellipsis (the full
         text stays in the DOM and in `title`), so the row keeps the fixed
         `--scene-caption-h` the dialogue choice list stops above. -->
    <div
      v-if="displayPresented"
      class="scene-backdrop__caption"
      data-testid="scene-backdrop-caption"
    >
      <div class="scene-backdrop__plate">
        <p
          v-if="captionFailure"
          class="scene-backdrop__generating scene-backdrop__generating--failure"
          data-testid="scene-backdrop-failure"
          role="status"
        >
          {{ captionFailure }}
        </p>
        <p
          v-else-if="generating"
          class="scene-backdrop__generating"
          data-testid="scene-backdrop-generating"
        >
          目前場景圖片生成中
        </p>
        <p v-if="sceneLabel" class="scene-backdrop__scene-label" data-testid="scene-backdrop-label" :title="sceneLabel">
          {{ sceneLabel }}
        </p>
        <p v-if="sceneAlt && sceneAlt !== sceneLabel" class="scene-backdrop__scene-alt" data-testid="scene-backdrop-alt" :title="sceneAlt">
          {{ sceneAlt }}
        </p>
        <!-- The scene control opens the full view (click or Enter on the
             control; Escape closes and restores focus). It exists exactly when
             a real scene image is on screen, so no broken-only view can open. -->
        <button
          v-if="displayPresented"
          ref="controlEl"
          type="button"
          class="scene-backdrop__fullview-control"
          data-testid="scene-backdrop-control"
          aria-label="開啟場景全圖"
          @click="openFullView"
          @keydown="onControlKeydown"
        >
          全圖
        </button>
      </div>
    </div>

    <div
      v-if="fullViewOpen"
      ref="fullViewEl"
      class="scene-backdrop__fullview"
      data-testid="scene-backdrop-fullview"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
      @keydown="onFullViewKeydown"
    >
      <button
        type="button"
        class="scene-backdrop__fullview-close"
        data-testid="scene-backdrop-fullview-close"
        aria-label="關閉全圖"
        @click="closeFullView(true)"
      >
        關閉
      </button>
      <img
        v-if="display"
        class="scene-backdrop__fullview-image"
        data-testid="scene-backdrop-fullview-image"
        :src="display.url"
        :alt="sceneAlt"
      />
      <p v-if="sceneLabel" class="scene-backdrop__fullview-label">{{ sceneLabel }}</p>
      <p v-if="captionFailure" class="scene-backdrop__fullview-failure" role="status">
        {{ captionFailure }}
      </p>
    </div>
  </div>
</template>

<style>
.scene-backdrop {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}

/* The mode's gradient stage is the always-correct base layer (design D3):
   the backdrop element's background carries the current mode's gradient. */
/* Every image layer (displayed or probing) covers the stage box; a probe is
   invisible but still loads, so the driver observes real dimensions. */
.scene-backdrop .scene-backdrop__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: opacity var(--motion-scene) var(--ease-standard);
}

.scene-backdrop .scene-backdrop__image--probe {
  opacity: 0;
  pointer-events: none;
}

/* The scene crossfade (webclient-scene-transitions, design D2): the entering
   painting fades in OVER the leaving one (it is the later sibling, so it
   paints above), and the leaving one thins on the slower exit curve, so the
   pair never drops through the dark gradient beneath them. Both phases take
   their duration from the one motion token the client publishes. */
.scene-backdrop .scene-backdrop__image:first-of-type {
  z-index: 1;
}

.scene-backdrop .scene-backdrop__placeholder {
  position: absolute;
  left: 50%;
  bottom: calc(var(--stage-content-bottom) + 12px * var(--ui-scale));
  transform: translateX(-50%);
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-4);
  background: var(--panel);
  backdrop-filter: blur(calc(8px * var(--ui-scale)));
  border: 1px solid rgba(202, 183, 138, 0.25);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  font-size: var(--text-sm);
  color: var(--paper-300);
}

.scene-backdrop .scene-backdrop__placeholder-label {
  margin: 0;
  color: var(--paper-300);
}

/* The scene caption block: one plate (the status facts, the label, the alt
   text, and the full-view control). Standalone, it sits at the stage's lower
   left clear of the band and the command-line row; the shell
   (app-shell.css) centres it in the open stage between the portraits. The
   block itself is pointer-transparent; only its children take pointer
   events, so it never blocks the stage beside them. */
.scene-backdrop .scene-backdrop__caption {
  position: absolute;
  left: calc(16px * var(--ui-scale));
  right: calc(16px * var(--ui-scale));
  bottom: calc(var(--stage-content-bottom) + 12px * var(--ui-scale));
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: calc(6px * var(--ui-scale));
  pointer-events: none;
}
.scene-backdrop .scene-backdrop__caption > * {
  pointer-events: auto;
}

/* The leading status fact of the plate: the pending notice in the warning
   tone, or a reached failure in the error tone. Both are split from the label
   by the same gold hairline the alt text uses. */
.scene-backdrop .scene-backdrop__generating {
  flex: none;
  margin: 0;
  white-space: nowrap;
  padding-right: calc(12px * var(--ui-scale));
  border-right: 1px solid rgba(202, 183, 138, 0.3);
  color: var(--warn);
  font-size: var(--text-xs);
  line-height: 1.5;
  letter-spacing: 0.04em;
}

.scene-backdrop .scene-backdrop__generating--failure {
  color: #f3b9bc;
}

/* The plate reads as a museum caption for the painting: the label in the
   serif display face, the alt text as its quieter description after a gold
   hairline, and the full-view control as a small trailing chip. It is one
   line at the fixed `--scene-caption-h`: within the caption block's width
   the label takes at most 55% and the alt text the rest, each ending in an
   ellipsis; the status facts and the control never shrink. */
.scene-backdrop .scene-backdrop__plate {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  column-gap: calc(12px * var(--ui-scale));
  max-width: 100%;
  box-sizing: border-box;
  min-height: var(--scene-caption-h);
  padding: calc(5px * var(--ui-scale)) calc(6px * var(--ui-scale)) calc(5px * var(--ui-scale)) calc(14px * var(--ui-scale));
  background: rgba(11, 13, 16, 0.74);
  backdrop-filter: blur(calc(8px * var(--ui-scale)));
  border: 1px solid rgba(202, 183, 138, 0.22);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow);
}

.scene-backdrop .scene-backdrop__scene-label,
.scene-backdrop .scene-backdrop__scene-alt {
  margin: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.scene-backdrop .scene-backdrop__scene-label {
  /* The label gives way last: in a narrow caption (combat, between the
     player and the foe line-up) the alt text truncates first. */
  flex: 0 0 auto;
  max-width: 55%;
  color: var(--paper-100);
  font: var(--text-md)/1.5 var(--f-serif);
  letter-spacing: 0.12em;
}

.scene-backdrop .scene-backdrop__scene-alt {
  flex: 0 1 auto;
  padding-left: calc(12px * var(--ui-scale));
  border-left: 1px solid rgba(202, 183, 138, 0.3);
  color: var(--paper-500);
  font-size: var(--text-xs);
  line-height: 1.5;
  letter-spacing: 0.04em;
}

.scene-backdrop .scene-backdrop__fullview-control {
  flex: none;
  margin-left: 2px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: var(--text-xs);
  /* The chip's normal line box (17px at --text-xs) plus padding and border
     makes it 23px tall, overflowing the plate's fixed --scene-caption-h row
     by 1px; an explicit 1.25 leading keeps the chip inside the one-line
     token, the same way .ui-btn pins its leading instead of letting the
     inherited normal line box drive a fixed control's height. */
  line-height: 1.25;
  font-family: var(--f-sans);
  letter-spacing: 0.08em;
  padding: 2px calc(9px * var(--ui-scale));
  cursor: pointer;
}

.scene-backdrop .scene-backdrop__fullview-control:hover {
  border-color: var(--gold-500);
  color: var(--paper-50);
}

/* The full-screen scene view (keyboard-first): the same image the backdrop
   shows at full screen, focus-trapped; Escape closes and restores focus to
   the opener. */
.scene-backdrop .scene-backdrop__fullview {
  position: fixed;
  inset: 0;
  z-index: var(--z-surface-modal);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--ink-950);
  outline: none;
}

.scene-backdrop .scene-backdrop__fullview-image {
  max-width: 100%;
  max-height: 86vh;
  object-fit: contain;
}

.scene-backdrop .scene-backdrop__fullview-label {
  margin: var(--sp-3) 0 0;
  color: var(--paper-300);
  font-size: var(--text-sm);
}

.scene-backdrop .scene-backdrop__fullview-failure {
  margin: var(--sp-2) 0 0;
  color: #f3b9bc;
  font-size: var(--text-xs);
}

/* The full-view close control: a keyboard-reachable close button pinned to
   the top-right of the dialog. */
.scene-backdrop .scene-backdrop__fullview-close {
  position: absolute;
  top: var(--sp-4);
  right: var(--sp-4);
  z-index: 1;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: var(--text-sm);
  font-family: var(--f-sans);
  padding: var(--sp-1) var(--sp-3);
  cursor: pointer;
}

.scene-backdrop .scene-backdrop__fullview-close:hover,
.scene-backdrop .scene-backdrop__fullview-close:focus {
  border-color: var(--gold-500);
  color: var(--paper-50);
  outline: none;
}
</style>
