// The live combat formation (OpenSpec change webclient-combat-formation,
// design D1): the engine (components/combat-formation.js) applied to the
// measured stage.
//
// - The stage geometry is measured from the DOM: the stage box, the vitals
//   dock's box, `--ui-scale` (a plain number on the root), and the length
//   tokens the engine reads (`--actor-h`, `--header-h`, `--band-h`,
//   `--command-line-h`),
//   read as the heights of HudFrame's metrics probe because their computed
//   custom-property text is an unresolved `min()`/`clamp()` expression.
// - A ResizeObserver on the stage, the vitals anchor and the probe re-measures
//   in its own callback (before the frame paints), and it is always on, so the
//   formation exists in the very render that commits a mode change.
// - The formation is a computed of the measurements and the counts, so a
//   roster or mode change re-forms both sides in the same Vue tick.
// - `instant` is true for the frames after a change of the stage's size or of
//   the chrome factor: a resize re-forms in place instead of gliding. A change
//   of the vitals dock alone (it reveals as combat starts) is not instant: the
//   formation re-targets mid-glide, every figure together.
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from "vue";
import { combatFormation, formationInputFromStage } from "../components/combat-formation.js";

function plainRect(rect) {
  return { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
}

function sameRect(a, b) {
  if (!a || !b) return a === b;
  return a.left === b.left && a.top === b.top && a.width === b.width && a.height === b.height;
}

// Reads one measurement of the stage under `root`, or null when the stage is
// not laid out (no layout engine, an unmounted shell).
export function measureStage(root) {
  const stage = root?.querySelector?.('[data-testid="elosern-stage"]');
  if (!stage) return null;
  const stageRect = plainRect(stage.getBoundingClientRect());
  const probe = (name) =>
    stage.querySelector(`.stage-metrics > [data-metric="${name}"]`)?.getBoundingClientRect().height ?? 0;
  const vitalsEl = stage.querySelector('[data-anchor="vitals"]');
  const vitalsRect = vitalsEl ? plainRect(vitalsEl.getBoundingClientRect()) : null;
  const uiScale = Number(getComputedStyle(document.documentElement).getPropertyValue("--ui-scale")) || 1;
  return {
    stage: stageRect,
    uiScale,
    actorHeight: probe("--actor-h"),
    headerHeight: probe("--header-h"),
    bandHeight: probe("--band-h"),
    commandLineHeight: probe("--command-line-h"),
    vitals: vitalsRect && vitalsRect.width > 0 && vitalsRect.height > 0 ? vitalsRect : null,
  };
}

// The formation for one measurement and the counts, or null when the stage is
// unmeasured.
export function formationFor(metrics, counts) {
  if (!metrics || metrics.stage.width <= 0 || metrics.stage.height <= 0 || metrics.actorHeight <= 0) {
    return null;
  }
  const styles = {
    "--ui-scale": metrics.uiScale,
    "--actor-h": metrics.actorHeight,
    "--header-h": metrics.headerHeight,
    "--band-h": metrics.bandHeight,
  };
  // An unmeasured command-line row leaves the engine its default.
  if (metrics.commandLineHeight > 0) styles["--command-line-h"] = metrics.commandLineHeight;
  return combatFormation(formationInputFromStage(metrics.stage, styles, metrics.vitals, counts));
}

// `rootRef`: the client root element; `active`: whether the formation stands;
// `counts`: `{ party, foes }`.
export function useCombatFormation({ rootRef, active, counts }) {
  const metrics = shallowRef(null);
  const instant = ref(false);
  let observer = null;
  let observed = [];
  let settleFrame = 0;

  function settleLater() {
    if (typeof requestAnimationFrame !== "function") return;
    cancelAnimationFrame(settleFrame);
    // Two frames: the instant render paints once before gliding resumes.
    settleFrame = requestAnimationFrame(() => {
      settleFrame = requestAnimationFrame(() => {
        instant.value = false;
      });
    });
  }

  function update() {
    const next = measureStage(rootRef.value);
    if (!next) return;
    const prev = metrics.value;
    if (
      prev &&
      sameRect(prev.stage, next.stage) &&
      sameRect(prev.vitals, next.vitals) &&
      prev.uiScale === next.uiScale &&
      prev.actorHeight === next.actorHeight &&
      prev.headerHeight === next.headerHeight &&
      prev.bandHeight === next.bandHeight &&
      prev.commandLineHeight === next.commandLineHeight
    ) {
      return;
    }
    const resized =
      !!prev &&
      (prev.stage.width !== next.stage.width ||
        prev.stage.height !== next.stage.height ||
        prev.uiScale !== next.uiScale ||
        prev.actorHeight !== next.actorHeight);
    if (resized) {
      instant.value = true;
      settleLater();
    }
    metrics.value = next;
    observeTargets();
  }

  // The observed elements: the stage, the vitals anchor and the probe. They
  // live inside HudFrame, which never remounts them, but the set is refreshed
  // after each measurement in case the shell re-rendered them.
  function observeTargets() {
    if (!observer) return;
    const stage = rootRef.value?.querySelector?.('[data-testid="elosern-stage"]');
    if (!stage) return;
    const targets = [
      stage,
      stage.querySelector('[data-anchor="vitals"]'),
      ...stage.querySelectorAll(".stage-metrics > [data-metric]"),
    ].filter(Boolean);
    if (targets.length === observed.length && targets.every((el, i) => el === observed[i])) return;
    observer.disconnect();
    targets.forEach((el) => observer.observe(el));
    observed = targets;
  }

  onMounted(() => {
    if (typeof ResizeObserver === "function") {
      observer = new ResizeObserver(() => update());
    }
    update();
    observeTargets();
  });
  onBeforeUnmount(() => {
    observer?.disconnect();
    observer = null;
    if (typeof cancelAnimationFrame === "function") cancelAnimationFrame(settleFrame);
  });

  const formation = computed(() => (active.value ? formationFor(metrics.value, counts.value) : null));
  return { formation, metrics, instant, remeasure: update };
}
