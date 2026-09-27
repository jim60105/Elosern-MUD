<script setup>
// SceneBackdrop (H1, webclient-hud-01-shell-and-scene, design D3/D8): the
// full-bleed cinematic stage backdrop. Renders the committed `art` panel's
// scene truthfully:
// - `done` with a same-origin URL → cover-cropped `<img>` as the lowest
//   stage layer.
// - `pending` with a prior image already rendered → the prior image,
//   visibly dimmed, with the explicit `目前場景圖片生成中` label (never
//   presented as the current scene).
// - `missing` / `failed` / invalid / `pending` without a prior image /
//   panel unavailable → the current mode's gradient stage with the
//   truthful placeholder label rendered as text outside the bitmap.
// A failed image URL is remembered (client-local) so it is not re-fetched
// without a new URL or a user reload (art degradation never blocks
// gameplay). The scene label and alternative text always render as DOM
// text nodes, so no required information exists only inside the bitmap.
//
// The scene full view (MODIFIED webclient-art-panel): the backdrop's scene
// control opens a full-screen view on click or Enter, Escape closes it and
// restores focus to the control.
//
// The scene crossfade (webclient-scene-transitions, design D2): the image
// the committed state asks for (`targetImage`) is kept apart from the image
// on screen (`shownImage`). A new URL is decoded first; until its pixels are
// ready the previous image stays up, dimmed like a pending scene's prior
// image (never presented as the current scene), and only then does the new
// image fade in over it while the previous one fades out, so the fade never
// passes through an empty frame. The label, alternative text, and
// placeholder follow the committed state at once. Mount shows its image
// without a fade, and at the `off` motion level the swap is instant.
import { computed, nextTick, onBeforeUnmount, ref, shallowRef, watch } from "vue";
import { inertWhileLeaving } from "../lib/transition_hooks.js";

const props = defineProps({
  // The committed `art` v1 panel payload: `available: true` carries
  // `scene` + `portrait_catalog`; the registry-unavailable form carries
  // `available: false` + `reason`.
  art: { type: Object, required: true },
  // The committed mode (the store's reducer mode). Selects the gradient
  // stage for degraded scenes: exploration → explore gradient, combat →
  // combat gradient, creation → dialogue gradient (design D7: the gradient
  // stage differs per mode and carries the inset vignette, applied by the
  // shell's stage, not the backdrop itself).
  mode: { type: String, default: "exploration" },
  // The EFFECTIVE motion level (`store.view.motionLevel`,
  // webclient-scene-transitions D1): at `off` the transition has no CSS
  // phase, so the final state is on screen in the commit's frame (a CSS
  // phase would outlive the commit by a double frame even at 0s).
  motionLevel: { type: String, default: "full" },
});

// The current mode's gradient stage token (design D7/D10): the always-correct
// base layer — a degraded OOB channel is visually indistinguishable from an
// ungenerated scene.
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
const scene = computed(() => (unavailable.value ? null : (props.art.scene ?? null)));

// The client-local memory of the last successfully rendered scene image
// (design D3): a pending scene retains that prior image dimmed.
const priorImage = ref(null);
// The set of scene URLs that failed to load in the browser (task 4.7):
// a failed URL is not re-fetched before a user reload.
const failedUrls = new Set();
const imageLoadFailed = ref(false);
// The full-view open state (task 4.6) + the opener element for focus
// restore.
const fullViewOpen = ref(false);
const controlEl = ref(null);
const fullViewEl = ref(null);

// When the full view opens, focus moves into it (focus trap: while open,
// Tab stays within the view; Escape closes and returns focus to the
// control that opened it).
watch(fullViewOpen, (open) => {
  if (open) {
    fullViewEl.value?.focus();
  }
});

watch(
  () => props.art,
  () => {
    // A new scene (a fresh URL) resets the load-failure flag; a failed URL
    // stays remembered until a new URL arrives or the page reloads.
    if (scene.value?.url) {
      imageLoadFailed.value = false;
    }
  },
  { deep: true },
);

const sceneUrl = computed(() => {
  const url = scene.value?.url;
  if (url && failedUrls.has(url)) {
    return null;
  }
  return url ?? null;
});

// Which image the committed state asks for:
// - done + a live URL → the current image
// - pending + a prior image → the dimmed prior image
const targetImage = computed(() => {
  if (scene.value?.status === "done" && sceneUrl.value && !imageLoadFailed.value) {
    return { url: sceneUrl.value, dimmed: false };
  }
  if (scene.value?.status === "pending" && priorImage.value) {
    return { url: priorImage.value, dimmed: true };
  }
  return null;
});

// The image on screen (design D2). Mount takes the target at once: there is
// nothing to fade from, and mounting plays no transition.
const shownImage = shallowRef(targetImage.value);
// The URL whose decode is in flight, or null.
const decodingUrl = ref(null);
// The decoder keeps a reference to its `Image` until it settles.
let decoder = null;

const transitionCss = computed(() => props.motionLevel !== "off");

// A new URL's pixels are ready: `decode()` where the engine has it. Returns
// null where there is no decode API (jsdom), so the caller swaps at once.
function decodeImage(url) {
  if (typeof Image === "undefined") {
    return null;
  }
  const img = new Image();
  if (typeof img.decode !== "function") {
    return null;
  }
  img.src = url;
  decoder = img;
  return img.decode();
}

watch(
  () => [targetImage.value?.url ?? null, targetImage.value?.dimmed ?? false],
  ([url]) => {
    const target = targetImage.value;
    if (!target) {
      decodingUrl.value = null;
      decoder = null;
      shownImage.value = null;
      return;
    }
    if (shownImage.value?.url === url) {
      // The same bitmap: only the dimmed treatment changes (it eases).
      decodingUrl.value = null;
      decoder = null;
      shownImage.value = target;
      return;
    }
    if (decodingUrl.value === url) {
      return;
    }
    const pending = decodeImage(url);
    if (!pending) {
      decodingUrl.value = null;
      shownImage.value = target;
      return;
    }
    decodingUrl.value = url;
    const settle = (ok) => {
      // A newer target replaced this one while it decoded: drop it.
      if (decodingUrl.value !== url) {
        return;
      }
      decodingUrl.value = null;
      decoder = null;
      if (!ok) {
        // The URL failed to load or decode: the same failure the rendered
        // image's error path records, so the URL is never fetched again, the
        // previous image fades out, and the placeholder takes over.
        recordFailure(url);
        return;
      }
      if (targetImage.value?.url === url) {
        shownImage.value = targetImage.value;
      }
    };
    pending.then(
      () => settle(true),
      () => settle(false),
    );
  },
);

onBeforeUnmount(() => {
  decodingUrl.value = null;
  decoder = null;
});

// What renders: the shown image, dimmed while the next one decodes — the
// label already names the new scene, so the old bitmap must look stale.
const activeImage = computed(() => {
  const shown = shownImage.value;
  if (!shown) {
    return null;
  }
  return { url: shown.url, dimmed: shown.dimmed || decodingUrl.value !== null };
});

const showPlaceholder = computed(() => {
  if (unavailable.value) {
    return true;
  }
  const s = scene.value;
  if (!s) {
    return true;
  }
  if (s.status === "pending" && priorImage.value) {
    return false;
  }
  if (s.status === "done") {
    return imageLoadFailed.value || !sceneUrl.value;
  }
  return true;
});

const placeholderLabel = computed(() => {
  if (unavailable.value) {
    return props.art?.reason?.message || "無法提供";
  }
  return scene.value?.placeholder?.label || "場景圖片尚未生成";
});

const placeholderKind = computed(() => {
  if (unavailable.value) {
    return props.art?.reason?.code || "unavailable";
  }
  return (imageLoadFailed.value ? "load_failed" : (scene.value?.placeholder?.kind ?? "unavailable"));
});

// The scene label + alt always render as text outside the bitmap.
const sceneLabel = computed(() => scene.value?.label ?? (unavailable.value ? "場景" : ""));
const sceneAlt = computed(() => scene.value?.alt ?? "");
const generating = computed(() => scene.value?.status === "pending" && !!priorImage.value);
const hasControl = computed(() => !unavailable.value && !!scene.value);

// The rendered image's own URL: during a crossfade two images are in the
// DOM, and a late event from the leaving one must not speak for the scene on
// screen.
function eventUrl(event) {
  return event?.currentTarget?.getAttribute?.("src") || null;
}

function onImageLoad(event) {
  const url = eventUrl(event);
  if (!url || url !== shownImage.value?.url) {
    return;
  }
  priorImage.value = url;
  imageLoadFailed.value = false;
}

// A scene URL that failed to load: remembered, so it is not fetched again
// before a new URL or a reload, and — when it is the scene the committed
// state asks for — the placeholder takes over.
function recordFailure(url) {
  failedUrls.add(url);
  if (url !== targetImage.value?.url && url !== shownImage.value?.url) {
    return;
  }
  priorImage.value = null;
  imageLoadFailed.value = true;
}

function onImageError(event) {
  const url = eventUrl(event);
  if (url) {
    recordFailure(url);
  }
}

function openFullView() {
  if (fullViewOpen.value) {
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
    // Focus trap: Tab cycles between the close button and the dialog root,
    // so keyboard users stay within the full view and cannot tab into the
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

// Seed the prior-image memory (stories and tests): a pending scene keeps
// its prior image visibly dimmed — never presented as the current scene.
function setPriorImage(url) {
  priorImage.value = url;
}

defineExpose({ openFullView, closeFullView, setPriorImage });
</script>

<template>
  <div
    class="scene-backdrop"
    data-testid="scene-backdrop"
    :data-available="unavailable ? 'false' : 'true'"
    :data-scene-status="scene?.status ?? 'none'"
    :style="{ background: stageGradient }"
  >
    <div v-if="showPlaceholder && mode !== 'creation'" class="scene-backdrop__sample" aria-hidden="true"></div>
    <p v-if="showPlaceholder && mode !== 'creation'" class="scene-backdrop__sample-label">範例場景 · 非目前地點實際圖片</p>
    <!-- The crossfade (design D2): keyed by URL with no mode, so the
         entering image fades in above the leaving one, which is inert from
         the commit on. -->
    <Transition name="scene-xfade" :css="transitionCss" v-bind="inertWhileLeaving">
      <img
        v-if="activeImage"
        :key="activeImage.url"
        class="scene-backdrop__image"
        data-testid="scene-backdrop-image"
        :src="activeImage.url"
        :class="{ 'scene-backdrop__image--dimmed': activeImage.dimmed }"
        :alt="''"
        aria-hidden="true"
        @load="onImageLoad($event)"
        @error="onImageError($event)"
      />
    </Transition>

    <div
      v-if="showPlaceholder"
      class="scene-backdrop__placeholder"
      data-testid="scene-backdrop-placeholder"
      :data-kind="placeholderKind"
    >
      <span class="scene-backdrop__placeholder-kind" data-testid="scene-backdrop-placeholder-kind">
        {{ placeholderKind }}
      </span>
      <p class="scene-backdrop__placeholder-label" data-testid="scene-backdrop-placeholder-label">
        {{ placeholderLabel }}
      </p>
    </div>

    <!-- The scene caption: one single-line plate holding the pending
         notice, the scene label, the alternative text, and the full-view
         control. A label or alt text longer than the row truncates with an
         ellipsis (the full text stays in the DOM and in `title`), so the row
         keeps the fixed `--scene-caption-h` the dialogue choice list stops
         above. The label and alt render as text outside the
         bitmap (MODIFIED webclient-art-panel): no required information
         exists only inside the image. -->
    <div
      v-if="generating || sceneLabel || sceneAlt || hasControl"
      class="scene-backdrop__caption"
      data-testid="scene-backdrop-caption"
    >
      <div class="scene-backdrop__plate">
        <p
          v-if="generating"
          class="scene-backdrop__generating"
          data-testid="scene-backdrop-generating"
        >
          目前場景圖片生成中
        </p>
        <p v-if="sceneLabel" class="scene-backdrop__scene-label" data-testid="scene-backdrop-label" :title="sceneLabel">
          {{ sceneLabel }}
        </p>
        <p v-if="sceneAlt" class="scene-backdrop__scene-alt" data-testid="scene-backdrop-alt" :title="sceneAlt">
          {{ sceneAlt }}
        </p>
        <!-- The scene control opens the full view (MODIFIED art-panel: click
             or Enter on the control; Escape closes and restores focus). -->
        <button
          v-if="hasControl"
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
        v-if="activeImage"
        class="scene-backdrop__fullview-image"
        data-testid="scene-backdrop-fullview-image"
        :src="activeImage.url"
        :alt="sceneAlt"
      />
      <div v-else class="scene-backdrop__fullview-gradient" data-testid="scene-backdrop-fullview-gradient"></div>
      <p v-if="sceneLabel" class="scene-backdrop__fullview-label">{{ sceneLabel }}</p>
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
/* The dimmed treatment eases in and out on the scene duration. */
.scene-backdrop .scene-backdrop__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: opacity var(--motion-scene) var(--ease-standard);
}

/* A pending scene keeps its prior image visibly dimmed (never presented
   as current), and so does the previous image while the next one decodes. */
.scene-backdrop .scene-backdrop__image--dimmed {
  opacity: 0.45;
}

/* The scene crossfade (webclient-scene-transitions, design D2). The new
   painting fades in ABOVE the old one on a fast-rising curve while the old
   one thins on a slow-starting curve, so the pair never drops through the
   dark gradient beneath them (no dip in brightness mid-fade). The entering
   layer also settles from a hair larger than cover — a slight arrival, not a
   zoom — and only where travel is allowed. */
.scene-backdrop .scene-xfade-enter-active {
  z-index: 1;
  transition:
    opacity var(--motion-scene) var(--ease-standard),
    transform var(--motion-scene) var(--ease-standard);
}
.scene-backdrop .scene-xfade-leave-active {
  z-index: 0;
  transition: opacity var(--motion-scene) var(--ease-exit);
}
.scene-backdrop .scene-xfade-enter-from {
  opacity: 0;
  transform: scale(calc(1 + 0.025 * var(--motion-travel)));
}
.scene-backdrop .scene-xfade-leave-to {
  opacity: 0;
}

.scene-backdrop .scene-backdrop__placeholder {
  position: absolute;
  left: 50%;
  bottom: calc(var(--stage-content-bottom) + 12px);
  transform: translateX(-50%);
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-4);
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: 1px dashed var(--seal-600);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  font-size: var(--text-sm);
  color: var(--paper-300);
}

.scene-backdrop .scene-backdrop__placeholder-kind {
  font-family: var(--f-mono);
  font-size: 0.8em;
  text-transform: uppercase;
  color: var(--paper-500);
}

.scene-backdrop .scene-backdrop__placeholder-label {
  margin: 0;
  color: var(--paper-300);
}

/* The scene caption block: one plate (the pending notice, the label, the
   alt text, and the full-view control). Standalone, it sits at the stage's
   lower left clear of the band and the command-line row; the shell
   (app-shell.css) centres it in the open stage between the portraits. The
   block itself is pointer-transparent; only its children take pointer
   events, so it never blocks the stage beside them. */
.scene-backdrop .scene-backdrop__caption {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: calc(var(--stage-content-bottom) + 12px);
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  pointer-events: none;
}
.scene-backdrop .scene-backdrop__caption > * {
  pointer-events: auto;
}

/* The pending notice leads the plate in the warning tone, split from the
   label by the same gold hairline the alt text uses. */
.scene-backdrop .scene-backdrop__generating {
  flex: none;
  margin: 0;
  white-space: nowrap;
  padding-right: 12px;
  border-right: 1px solid rgba(202, 183, 138, 0.3);
  color: var(--warn);
  font-size: 12px;
  line-height: 1.5;
  letter-spacing: 0.04em;
}

/* The plate reads as a museum caption for the painting: the label in the
   serif display face, the alt text as its quieter description after a gold
   hairline, and the full-view control as a small trailing chip. It is one
   line at the fixed `--scene-caption-h`: within the caption block's width
   the label takes at most 55% and the alt text the rest, each ending in an
   ellipsis; the notice and the control never shrink. */
.scene-backdrop .scene-backdrop__plate {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  column-gap: 12px;
  max-width: 100%;
  box-sizing: border-box;
  min-height: var(--scene-caption-h);
  padding: 5px 6px 5px 14px;
  background: rgba(11, 13, 16, 0.74);
  backdrop-filter: blur(8px);
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
  font: 14px/1.5 var(--f-serif);
  letter-spacing: 0.12em;
}

.scene-backdrop .scene-backdrop__scene-alt {
  flex: 0 1 auto;
  padding-left: 12px;
  border-left: 1px solid rgba(202, 183, 138, 0.3);
  color: var(--paper-500);
  font-size: 12px;
  line-height: 1.5;
  letter-spacing: 0.04em;
}

.scene-backdrop .scene-backdrop__fullview-control {
  flex: none;
  margin-left: 2px;
  background: transparent;
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: var(--text-xs);
  font-family: var(--f-sans);
  letter-spacing: 0.08em;
  padding: 2px 9px;
  cursor: pointer;
}

.scene-backdrop .scene-backdrop__fullview-control:hover {
  border-color: var(--gold-500);
  color: var(--paper-50);
}

/* The full-screen scene view (MODIFIED art-panel keyboard-first): the same
   image (or the mode gradient) at full screen, focus-trapped, Escape closes
   and restores focus to the opener. */
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

.scene-backdrop .scene-backdrop__fullview-gradient {
  width: min(960px, 92vw);
  aspect-ratio: 16 / 9;
  background: inherit;
  border-radius: var(--radius);
}

.scene-backdrop .scene-backdrop__fullview-label {
  margin: var(--sp-3) 0 0;
  color: var(--paper-300);
  font-size: var(--text-sm);
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
